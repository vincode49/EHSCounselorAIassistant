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
    # Add tutorial_completed column
    cursor.execute('ALTER TABLE users ADD COLUMN tutorial_completed INTEGER DEFAULT 0')
    conn.commit()
    print("Successfully added tutorial_completed column to users table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("tutorial_completed column already exists")
    else:
        print(f"❌ Error: {e}")

conn.close()

