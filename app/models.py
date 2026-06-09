from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(150), nullable=True)
    last_name = db.Column(db.String(150), nullable=True)
    # per-user salt for deriving an encryption key from the raw password
    encryption_salt = db.Column(db.String(64), nullable=True)
    credentials = db.relationship('Credential', backref='owner', lazy=True)


class RevealLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    cred_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    ip = db.Column(db.String(45), nullable=True)

class Credential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(150), nullable=False)
    site_username = db.Column(db.String(150), nullable=False)
    site_password = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)