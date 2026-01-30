import sqlite3

# Delete old database if it exists
import os
if os.path.exists('users.db'):
    os.remove('users.db')
    print("✓ Deleted old database")

# Create new database
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Users table with class_of column
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    class_of INTEGER NOT NULL,
    thread_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()

print("✅ Database created successfully with class_of column!")
