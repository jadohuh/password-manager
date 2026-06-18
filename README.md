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
# For local development, SQLite is fine; for production, use Postgres or another managed DB.
DATABASE_URL=sqlite:///passwords.db
FLASK_DEBUG=0
PORT=5001
```

## Use PostgreSQL in production

For a production deployment, set `DATABASE_URL` to a PostgreSQL connection string, for example:

```env
DATABASE_URL=postgresql://username:password@host:port/dbname
```

Render, Heroku, and Railway can all provide a managed Postgres database.

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
