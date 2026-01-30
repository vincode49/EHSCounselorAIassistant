import sqlite3
import os

# Database path
if os.path.exists('/home/VihaanAgrawal'):
    DB_PATH = '/home/VihaanAgrawal/emerald-counselor-ai/users.db'
else:
    DB_PATH = 'users.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # Add display_name column
    cursor.execute('ALTER TABLE users ADD COLUMN display_name TEXT')
    conn.commit()
    print("Successfully added display_name column to users table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("display_name column already exists")
    else:
        print(f"Error: {e}")

try:
    # Add current_grade column
    cursor.execute('ALTER TABLE users ADD COLUMN current_grade INTEGER')
    conn.commit()
    print("Successfully added current_grade column to users table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("current_grade column already exists")
    else:
        print(f"Error: {e}")

try:
    # Add bio/interests column
    cursor.execute('ALTER TABLE users ADD COLUMN bio TEXT')
    conn.commit()
    print("Successfully added bio column to users table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("bio column already exists")
    else:
        print(f"Error: {e}")

conn.close()

