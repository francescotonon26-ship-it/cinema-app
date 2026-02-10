import sqlite3

DB_PATH = 'db/cinema.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Restituisce tutti i film nella tabella
def get_all_films():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM films ORDER BY title').fetchall()
    conn.close()
    return rows

# Restituisce un singolo film dato l'ID
def get_film_by_id(film_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM films WHERE id = ?', (film_id,)).fetchone()
    conn.close()
    return row

# Inserisce un nuovo film; data è un dict con chiavi title, duration, genre, description, poster_filename
def add_film(data):
    conn = get_db_connection()
    cur = conn.execute(
        'INSERT INTO films (title, duration, genre, description, poster_filename) VALUES (?, ?, ?, ?, ?)',
        (data['title'], data['duration'], data['genre'], data['description'], data['poster_filename'])
    )
    conn.commit()
    film_id = cur.lastrowid
    conn.close()
    return film_id

# Modifica un film esistente
def update_film(film_id, data):
    conn = get_db_connection()
    conn.execute(
        'UPDATE films SET title = ?, duration = ?, genre = ?, description = ?, poster_filename = ? WHERE id = ?',
        (data['title'], data['duration'], data['genre'], data['description'], data['poster_filename'], film_id)
    )
    conn.commit()
    conn.close()
    return True

# Elimina un film dal database
def delete_film(film_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM films WHERE id = ?', (film_id,))
    conn.commit()
    conn.close()
    return True

def get_all_genres():
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT DISTINCT genre FROM films ORDER BY genre'
    ).fetchall()
    conn.close()
    # restituisce una lista di stringhe
    return [row['genre'] for row in rows]

