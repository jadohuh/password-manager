from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, session, Response
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User, Credential, RevealLog
from cryptography.fernet import Fernet
import base64, hashlib, os, binascii, time, csv, io
from datetime import datetime

views = Blueprint('views', __name__)

def derive_key_from_password(raw_password, salt_hex, iterations=200_000):
    # salt_hex is hex-encoded; returns urlsafe_b64 key bytes
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac('sha256', raw_password.encode('utf-8'), salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(dk)

def get_fernet_from_password(raw_password, salt_hex):
    key = derive_key_from_password(raw_password, salt_hex)
    return Fernet(key)

# legacy: derive key from stored password hash (used by older records)
def legacy_get_fernet_from_hash(pw_hash):
    key = hashlib.sha256(pw_hash.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

@views.route('/')
@login_required
def dashboard():
    credentials = Credential.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', credentials=credentials)

@views.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'appearance':
            theme = request.form.get('theme_select') or 'default'
            flash('Appearance preferences updated.', 'success')
            return redirect(url_for('views.settings'))

        if form_type == 'account':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            username = request.form.get('username', '').strip() or current_user.username
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not first_name:
                flash('First name is required.', 'danger')
                return redirect(url_for('views.settings'))

            if username != current_user.username:
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    flash('That username is already taken.', 'danger')
                    return redirect(url_for('views.settings'))
                current_user.username = username

            current_user.first_name = first_name
            current_user.last_name = last_name or None

            if new_password or confirm_password:
                if not current_password or not bcrypt.check_password_hash(current_user.password, current_password):
                    flash('Enter your current password to update the password.', 'danger')
                    return redirect(url_for('views.settings'))
                if new_password != confirm_password:
                    flash('New password and confirmation do not match.', 'danger')
                    return redirect(url_for('views.settings'))
                current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')

            db.session.commit()
            flash('Account settings updated.', 'success')
            return redirect(url_for('views.settings'))

    return render_template('settings.html')

@views.route('/export-credentials', methods=['POST'])
@login_required
def export_credentials():
    data = request.get_json() or {}
    password = data.get('password', '')
    if not password or not bcrypt.check_password_hash(current_user.password, password):
        return jsonify({'error': 'Invalid password'}), 401

    if not current_user.encryption_salt:
        return jsonify({'error': 'Account encryption salt missing'}), 500

    try:
        f = get_fernet_from_password(password, current_user.encryption_salt)
    except Exception:
        return jsonify({'error': 'Could not derive key'}), 500

    creds = Credential.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['site_name', 'site_username', 'site_password'])

    for cred in creds:
        try:
            plain = f.decrypt(cred.site_password.encode()).decode('utf-8')
        except Exception:
            plain = ''
        writer.writerow([cred.site_name, cred.site_username, plain])

    csv_data = output.getvalue()
    output.close()

    response = Response(csv_data, mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=passvault-credentials-{current_user.username}.csv'
    return response

@views.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        if not first_name:
            flash('First name is required.', 'danger')
            return redirect(url_for('views.register'))
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('views.register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        # generate per-user encryption salt
        salt = binascii.hexlify(os.urandom(16)).decode()
        new_user = User(
            username=username,
            password=hashed_pw,
            first_name=first_name.strip() or None,
            last_name=last_name.strip() or None,
            encryption_salt=salt,
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('views.login'))
    return render_template('register.html')

@views.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            # successful auth
            login_user(user)

            # if user has no encryption_salt (older account), create one and migrate credentials
            if not user.encryption_salt:
                salt = binascii.hexlify(os.urandom(16)).decode()
                user.encryption_salt = salt
                # re-encrypt existing credentials: decrypt with legacy key, encrypt with new key
                try:
                    old_f = legacy_get_fernet_from_hash(user.password)
                    new_f = get_fernet_from_password(password, salt)
                    creds = Credential.query.filter_by(user_id=user.id).all()
                    for c in creds:
                        try:
                            plain = old_f.decrypt(c.site_password.encode()).decode('utf-8')
                            c.site_password = new_f.encrypt(plain.encode()).decode('utf-8')
                        except Exception:
                            # if decryption fails, skip
                            pass
                except Exception:
                    pass
                db.session.commit()

            # store a short-lived marker in session (do not store raw key)
            session['last_auth'] = int(time.time())
            session.modified = True
            if not user.first_name:
                return redirect(url_for('views.complete_profile'))
            return redirect(url_for('views.dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@views.route('/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    if current_user.first_name:
        return redirect(url_for('views.dashboard'))

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        if not first_name:
            flash('First name is required.', 'danger')
            return redirect(url_for('views.complete_profile'))
        current_user.first_name = first_name.strip()
        current_user.last_name = last_name.strip() or None
        db.session.commit()
        flash('Profile updated. Welcome, {}!'.format(current_user.first_name), 'success')
        return redirect(url_for('views.dashboard'))

    return render_template('complete_profile.html')

@views.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('views.login'))

@views.route('/add', methods=['GET', 'POST'])
@login_required
def add_credential():
    if request.method == 'POST':
        site_name = request.form.get('site_name')
        site_username = request.form.get('site_username')
        site_password = request.form.get('site_password')
        master_pw = request.form.get('master_password')
        if not master_pw:
            flash('Enter your account password to encrypt the credential.', 'danger')
            return redirect(url_for('views.add_credential'))
        if not bcrypt.check_password_hash(current_user.password, master_pw):
            flash('Invalid account password.', 'danger')
            return redirect(url_for('views.add_credential'))
        # derive Fernet from provided raw password + user's salt
        f = get_fernet_from_password(master_pw, current_user.encryption_salt)
        encrypted = f.encrypt(site_password.encode()).decode('utf-8')
        cred = Credential(site_name=site_name, site_username=site_username,
                          site_password=encrypted, user_id=current_user.id)
        db.session.add(cred)
        db.session.commit()
        flash('Credential saved!', 'success')
        return redirect(url_for('views.dashboard'))
    return render_template('add_credential.html')

@views.route('/delete/<int:cred_id>')
@login_required
def delete_credential(cred_id):
    cred = Credential.query.get_or_404(cred_id)
    if cred.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('views.dashboard'))
    db.session.delete(cred)
    db.session.commit()
    flash('Credential deleted.', 'success')
    return redirect(url_for('views.dashboard'))


@views.route('/reveal/<int:cred_id>', methods=['POST'])
@login_required
def reveal_credential(cred_id):
    data = request.get_json() or {}
    password = data.get('password', '')
    user = User.query.get(current_user.id)
    # simple rate limiting for reveal attempts in session
    attempts = session.get('reveal_attempts', {'count': 0, 'first': int(time.time())})
    window = 60
    max_attempts = 5
    now = int(time.time())
    if now - attempts.get('first', now) > window:
        attempts = {'count': 0, 'first': now}

    if attempts['count'] >= max_attempts:
        return jsonify({'error': 'Too many attempts, try again later'}), 429

    if not user or not bcrypt.check_password_hash(user.password, password):
        attempts['count'] = attempts.get('count', 0) + 1
        session['reveal_attempts'] = attempts
        session.modified = True
        # log failure
        log = RevealLog(user_id=current_user.id, cred_id=cred_id, timestamp=datetime.utcnow(), success=False, ip=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        return jsonify({'error': 'Invalid password'}), 401

    # reset attempts on success
    session.pop('reveal_attempts', None)

    cred = Credential.query.get_or_404(cred_id)
    if cred.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        f = get_fernet_from_password(password, user.encryption_salt)
        decrypted = f.decrypt(cred.site_password.encode()).decode('utf-8')
    except Exception:
        # log failure
        log = RevealLog(user_id=current_user.id, cred_id=cred_id, timestamp=datetime.utcnow(), success=False, ip=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        return jsonify({'error': 'Decryption failed'}), 500

    # log success
    log = RevealLog(user_id=current_user.id, cred_id=cred_id, timestamp=datetime.utcnow(), success=True, ip=request.remote_addr)
    db.session.add(log)
    db.session.commit()

    return jsonify({'password': decrypted})