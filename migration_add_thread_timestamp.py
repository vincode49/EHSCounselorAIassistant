import sqlite3
import os

if os.path.exists('/home/VihaanAgrawal'):
    DB_PATH = '/home/VihaanAgrawal/emerald-counselor-ai/users.db'
else:
    DB_PATH = 'users.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE users ADD COLUMN thread_created_at TIMESTAMP')
    conn.commit()
    print("Success: Added thread_created_at column to users table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("Column thread_created_at already exists")
    else:
        print(f"Error: {e}")

conn.close()

