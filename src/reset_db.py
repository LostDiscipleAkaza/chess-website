import os
import time
from app import create_app
from extensions import db

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'chess.db')

# Remove the old database file if it exists
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print(f"Deleted old database file: {db_path}")
    except PermissionError:
        print(f"Warning: Could not delete {db_path} (file locked). Proceeding with reset...")
        time.sleep(1)

# Create a fresh app and reset the database
app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    print("Database reset successfully with new schema.")