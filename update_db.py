import sqlite3
import os

db_path = os.path.join('instance', 'database.db')

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if dob column already exists to avoid errors
        cursor.execute("PRAGMA table_info(permit)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'dob' not in columns:
            print("Adding 'dob' column to 'permit' table...")
            cursor.execute("ALTER TABLE permit ADD COLUMN dob VARCHAR(20)")
            conn.commit()
            print("Successfully updated 'permit' table.")
        else:
            print("'dob' column already exists in 'permit' table.")
            
        conn.close()
    except Exception as e:
        print(f"Error updating database: {e}")
else:
    print("Database file not found. It will be created automatically when the app runs.")
