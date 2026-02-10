import sqlite3
from models import User

DB_PATH = 'db/cinema.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Restituisce un utente dato l'ID, o None se non esiste
def get_user_by_id(user_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT id, first_name, last_name, email, password_hash, is_admin FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return User(
            row['id'],
            row['first_name'],
            row['last_name'],
            row['email'],
            row['password_hash'],
            bool(row['is_admin'])
        )
    return None

# Restituisce un utente dato l'email, o None se non esiste
def get_user_by_email(email):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT id, first_name, last_name, email, password_hash, is_admin FROM users WHERE email = ?',
        (email,)
    ).fetchone()
    conn.close()
    if row:
        return User(
            row['id'],
            row['first_name'],
            row['last_name'],
            row['email'],
            row['password_hash'],
            bool(row['is_admin'])
        )
    return None

# Crea un nuovo utente; restituisce True se inserimento avvenuto, False se email già esistente
def create_user(first_name, last_name, email, password_hash, is_admin=False):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (first_name, last_name, email, password_hash, is_admin) VALUES (?, ?, ?, ?, ?)',
            (first_name, last_name, email, password_hash, int(is_admin))
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
