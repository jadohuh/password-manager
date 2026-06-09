from sqlalchemy import inspect, text
from app import create_app, db

app = create_app()

def ensure_user_name_columns():
    inspector = inspect(db.engine)
    if inspector.has_table('user'):
        columns = {column['name'] for column in inspector.get_columns('user')}
        with db.engine.begin() as conn:
            if 'first_name' not in columns:
                conn.execute(text('ALTER TABLE "user" ADD COLUMN first_name VARCHAR(150)'))
            if 'last_name' not in columns:
                conn.execute(text('ALTER TABLE "user" ADD COLUMN last_name VARCHAR(150)'))

if __name__ == '__main__':
    with app.app_context():
        ensure_user_name_columns()
        db.create_all()
    app.run(debug=True, port=5001)