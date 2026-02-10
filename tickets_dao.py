import sqlite3
from datetime import datetime

DB_PATH = 'db/cinema.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def count_user_tickets(user_id, projection_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT COUNT(*) AS cnt FROM tickets WHERE user_id = ? AND projection_id = ?',
        (user_id, projection_id)
    ).fetchone()
    conn.close()
    return row['cnt']

def count_tickets_by_category(projection_id, category):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT COUNT(*) AS cnt FROM tickets WHERE projection_id = ? AND category = ?',
        (projection_id, category)
    ).fetchone()
    conn.close()
    return row['cnt']

# Inserisce tanti ticket quanti specificati nel parametro quantity
def add_ticket(user_id, projection_id, category, quantity=1):
    conn = get_db_connection()
    timestamp = datetime.now().isoformat()
    for _ in range(quantity):
        conn.execute(
            'INSERT INTO tickets (user_id, projection_id, category, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
            (user_id, projection_id, category, 1, timestamp)
        )
    conn.commit()
    conn.close()
    return True

def get_tickets_by_user(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT
            t.id               AS ticket_id,
            t.projection_id    AS proj_id,
            t.category         AS category,
            t.quantity         AS quantity,
            t.timestamp        AS timestamp,
            p.film_id          AS film_id,
            f.title            AS film_title,
            f.poster_filename  AS poster_filename,
            p.date             AS date,
            p.time             AS time,
            p.sala             AS sala
        FROM tickets t
        JOIN proiezioni p ON t.projection_id = p.id
        JOIN films f      ON p.film_id = f.id
        WHERE t.user_id = ?
        ORDER BY p.date, p.time
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_tickets_by_projection(projection_id):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT t.id, u.first_name || ' ' || u.last_name AS user_name,
               t.category, t.quantity, t.timestamp
        FROM tickets t
        JOIN users u ON t.user_id = u.id
        WHERE t.projection_id = ?
        ORDER BY t.timestamp
        ''',
        (projection_id,)
    ).fetchall()
    conn.close()
    return rows


def get_ticket_by_id(ticket_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM tickets WHERE id = ?',
        (ticket_id,)
    ).fetchone()
    conn.close()
    return row


def update_ticket_category(ticket_id, new_category):
    conn = get_db_connection()
    conn.execute(
        'UPDATE tickets SET category = ? WHERE id = ?',
        (new_category, ticket_id)
    )
    conn.commit()
    conn.close()


def delete_ticket(ticket_id):
    conn = get_db_connection()
    conn.execute(
        'DELETE FROM tickets WHERE id = ?',
        (ticket_id,)
    )
    conn.commit()
    conn.close()


def update_ticket_projection(ticket_id, new_projection_id):
    """
    Aggiorna la proiezione (projection_id) associata al biglietto.
    """
    conn = get_db_connection()
    conn.execute(
        'UPDATE tickets SET projection_id = ? WHERE id = ?',
        (new_projection_id, ticket_id)
    )
    conn.commit()
    conn.close()
    return True
