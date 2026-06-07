from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models import User, Credential
from cryptography.fernet import Fernet
import base64, hashlib

views = Blueprint('views', __name__)

def get_fernet(user_password):
    key = hashlib.sha256(user_password.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

@views.route('/')
@login_required
def dashboard():
    credentials = Credential.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', credentials=credentials)

@views.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('views.register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password=hashed_pw)
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
            login_user(user)
            return redirect(url_for('views.dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

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
        f = get_fernet(current_user.password)
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