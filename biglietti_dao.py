import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'db/cinema.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Restituisce tutti i biglietti di un utente
def get_user_tickets(user_id):
    conn = get_db_connection()
    cur = conn.execute(
        'SELECT t.id, t.projection_id, p.film_id, p.date, p.time, t.category, t.quantity '
        'FROM tickets t JOIN proiezioni p ON t.projection_id = p.id '
        'WHERE t.user_id = ? ORDER BY p.date, p.time',
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

# Statistiche di vendita: per ogni proiezione conta VIP e Normali venduti
def get_sales_statistics():
    conn = get_db_connection()
    cur = conn.execute(
        """
        SELECT p.id AS projection_id, f.title, p.date, p.time,
               SUM(CASE WHEN t.category = 'VIP' THEN t.quantity ELSE 0 END) AS vip_sold,
               SUM(CASE WHEN t.category = 'Normale' THEN t.quantity ELSE 0 END) AS normal_sold
        FROM proiezioni p
        JOIN tickets t ON t.projection_id = p.id
        JOIN film f ON p.film_id = f.id
        GROUP BY p.id, f.title, p.date, p.time
        ORDER BY p.date, p.time
        """
    )
    stats = cur.fetchall()
    conn.close()
    return stats

# Acquista biglietti: restituisce True se ok
def purchase_ticket(data):
    # data: dict con keys user_id, projection_id, category, quantity
    conn = get_db_connection()
    # Verifica posti residui
    capienza = 15 if data['category'] == 'VIP' else 50
    cur = conn.execute(
        'SELECT SUM(quantity) AS sold FROM tickets WHERE projection_id = ? AND category = ?',
        (data['projection_id'], data['category'])
    )
    sold = cur.fetchone()['sold'] or 0
    if sold + data['quantity'] > capienza:
        conn.close()
        return False
    conn.execute(
        'INSERT INTO tickets (user_id, projection_id, category, quantity, timestamp) VALUES (?, ?, ?, ?, ?)',
        (data['user_id'], data['projection_id'], data['category'], data['quantity'], datetime.utcnow())
    )
    conn.commit()
    conn.close()
    return True

# Modifica biglietto: consentito solo 8h prima della proiezione
def update_ticket(ticket_id, new_quantity):
    conn = get_db_connection()
    cur = conn.execute(
        'SELECT p.date, p.time FROM tickets t JOIN proiezioni p ON t.projection_id = p.id WHERE t.id = ?',
        (ticket_id,)
    )
    row = cur.fetchone()
    proj_datetime = datetime.strptime(row['date'] + ' ' + row['time'], '%Y-%m-%d %H:%M:%S')
    if datetime.utcnow() + timedelta(hours=8) > proj_datetime:
        conn.close()
        return False
    conn.execute(
        'UPDATE tickets SET quantity = ? WHERE id = ?',
        (new_quantity, ticket_id)
    )
    conn.commit()
    conn.close()
    return True

# Elimina biglietto (annulla) se prima di 8h
def delete_ticket(ticket_id):
    conn = get_db_connection()
    cur = conn.execute(
        'SELECT p.date, p.time FROM tickets t JOIN proiezioni p ON t.projection_id = p.id WHERE t.id = ?',
        (ticket_id,)
    )
    row = cur.fetchone()
    proj_datetime = datetime.strptime(row['date'] + ' ' + row['time'], '%Y-%m-%d %H:%M:%S')
    if datetime.utcnow() + timedelta(hours=8) > proj_datetime:
        conn.close()
        return False
    conn.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    conn.commit()
    conn.close()
    return True