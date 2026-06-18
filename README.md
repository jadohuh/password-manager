# PassVault

A secure password manager built with Flask, Flask-Login, and SQLAlchemy.

## Features

- user registration and login
- master password encryption using Fernet and PBKDF2
- encrypted credential storage
- password complexity enforcement
- environment-based configuration for production

## Requirements

- Python 3.12+
- virtualenv or venv

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then update `.env`:

```env
SECRET_KEY=your-secure-secret-key
DATABASE_URL=sqlite:///passwords.db
FLASK_DEBUG=0
PORT=5001
```

## Run locally

```bash
source venv/bin/activate
python run.py
```

For production-style startup:

```bash
gunicorn 'run:app'
```

## Deployment

### Render / Heroku / Railway

- connect your GitHub repo
- set environment variables from `.env`
- use `gunicorn 'run:app'` as the start command

### Notes

- `SECRET_KEY` must be strong and kept secret
- `DATABASE_URL` can be changed to a managed database in production
- avoid running with `FLASK_DEBUG=1` in public deployments
