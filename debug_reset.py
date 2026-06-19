import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from extensions import db

print(f"Working directory: {os.getcwd()}")

app = create_app()
print(f"App instance path: {app.instance_path}")
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

with app.app_context():
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("Done!")
    
    # Check what tables exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables created: {tables}")
    
    if 'users' in tables:
        columns = inspector.get_columns('users')
        print(f"Users table columns: {[col['name'] for col in columns]}")
