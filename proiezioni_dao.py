import sqlite3

DB_PATH = 'db/cinema.db'


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Restituisce tutte le proiezioni ordinate per data e ora,
def get_all_proiezioni():
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            p.id AS id,
            p.film_id,
            f.title AS film_title,
            f.poster_filename,
            f.duration,
            p.date,
            p.time,
            p.sala,
            u.first_name || ' ' || u.last_name AS creator_name
        FROM proiezioni p
        JOIN films f ON p.film_id = f.id
        JOIN users u ON p.creator_id = u.id
        ORDER BY p.date, p.time
        '''
    ).fetchall()
    conn.close()
    return rows

# Restituisce una singola proiezione dato l'ID,
def get_proiezione(proj_id):
    conn = get_db_connection()
    row = conn.execute(
        '''
        SELECT
            p.id AS id,
            p.film_id,
            f.title AS film_title,
            f.poster_filename,
            f.duration,
            p.date,
            p.time,
            p.sala,
            u.first_name || ' ' || u.last_name AS creator_name
        FROM proiezioni p
        JOIN films f ON p.film_id = f.id
        JOIN users u ON p.creator_id = u.id
        WHERE p.id = ?
        ''',
        (proj_id,)
    ).fetchone()
    conn.close()
    return row

# Aggiunge una nuova proiezione, associando l'utente che l'ha creata
def add_proiezione(data):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO proiezioni (film_id, date, time, sala, creator_id) VALUES (?, ?, ?, ?, ?)',
        (data['film_id'], data['date'], data['time'], data['sala'], data.get('creator_id'))
    )
    conn.commit()
    conn.close()
    return True

# Modifica una proiezione esistente
def update_proiezione(proj_id, data):
    conn = get_db_connection()
    conn.execute(
        'UPDATE proiezioni SET film_id = ?, date = ?, time = ?, sala = ? WHERE id = ?',
        (data['film_id'], data['date'], data['time'], data['sala'], proj_id)
    )
    conn.commit()
    conn.close()
    return True

# Elimina una proiezione dal database
def delete_proiezione(proj_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM proiezioni WHERE id = ?', (proj_id,))
    conn.commit()
    conn.close()
    return True

# Restituisce tutte le proiezioni collegate a un film specifico
def get_proiezioni_by_film(film_id):
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT id, date, time, sala FROM proiezioni WHERE film_id = ? ORDER BY date, time',
        (film_id,)
    ).fetchall()
    conn.close()
    return rows

# Restituisce tutte le proiezioni di una data specifica
def get_proiezioni_by_date(date):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            p.id,
            p.film_id,
            f.title      AS film_title,
            f.poster_filename,
            f.duration,
            f.genre,
            f.description,
            p.date,
            p.time,
            p.sala,
            u.first_name || ' ' || u.last_name AS creator_name
        FROM proiezioni p
        JOIN films f ON p.film_id = f.id
        JOIN users u  ON p.creator_id = u.id
        WHERE p.date = ?
        ORDER BY p.time''',(date,)).fetchall()
    conn.close()
    return rows


def get_proiezioni_by_sala(sala):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            p.id, p.film_id, f.title AS film_title,
            f.poster_filename, f.duration,
            p.date, p.time, p.sala,
            u.first_name || ' ' || u.last_name AS creator_name
        FROM proiezioni p
        JOIN films f ON p.film_id = f.id
        JOIN users u ON p.creator_id = u.id
        WHERE p.sala = ?
        ORDER BY p.date, p.time
        ''',
        (sala,)
    ).fetchall()
    conn.close()
    return rows

def get_proiezioni_by_date_and_sala(date, sala):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            p.id, p.film_id, f.title AS film_title,
            f.poster_filename, f.duration,
            p.date, p.time, p.sala,
            u.first_name || ' ' || u.last_name AS creator_name
        FROM proiezioni p
        JOIN films f ON p.film_id = f.id
        JOIN users u ON p.creator_id = u.id
        WHERE p.date = ? AND p.sala = ?
        ORDER BY p.time
        ''',
        (date, sala)
    ).fetchall()
    conn.close()
    return rows 

# Restituisce i film che hanno almeno una proiezione collegata
def get_films_with_proiezioni():
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT DISTINCT f.id, f.title, f.duration, f.genre, f.description, f.poster_filename
        FROM films f
        JOIN proiezioni p ON f.id = p.film_id
        ORDER BY f.title
        '''
    ).fetchall()
    conn.close()
    return rows

# Restituisce tutte le proiezioni per una data e una sala (per verifica sovrapposizioni)
def get_proiezioni_on_date_sala(date, sala):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            p.id,
            p.film_id,
            f.title         AS film_title,
            p.time          AS start_time,
            f.duration      AS duration
        FROM proiezioni p
        JOIN films f ON p.film_id = f.id
        WHERE p.date = ? AND p.sala = ?
        ORDER BY p.time
        ''',
        (date, sala)
    ).fetchall()
    conn.close()
    return rows