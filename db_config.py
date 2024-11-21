import sqlite3
from contextlib import contextmanager
from datetime import datetime

DATABASE = 'test.db'

@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
    finally:
        conn.close()

def register_user(username):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            created_at = datetime.now()
            cursor.execute("INSERT INTO users (username, created_at) VALUES (?, ?)", (username, created_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"Error al registrar el usuario: {e}")
            return False

def delete_user(username):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()

def create_tables():
    # Connect to the database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        created_at TIMESTAMP NOT NULL
    )
    ''')

    # Create messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL,
        message_content VARCHAR(100) NOT NULL,
        timestamp TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')

    # Commit changes and close the connection
    conn.commit()
    conn.close()

def users_list():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users")
        return cursor.fetchall()

def is_user_registered(username):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        return cursor.fetchone() is not None

def save_message(username, message_content):
    with get_connection() as conn:
        cursor = conn.cursor()
        user_id = cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,)).fetchone()[0]
        timestamp = datetime.now()
        cursor.execute("INSERT INTO messages (user_id, message_content, timestamp) VALUES (?, ?, ?)", (user_id, message_content, timestamp))
        conn.commit()

if __name__ == "__main__":
    create_tables()
    #register_user("Juan")
    print(users_list())
