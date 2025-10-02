import sqlite3

DB_PATH = 'ecology.db'

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    with open('schema.sql') as f:
        c.executescript(f.read())
    conn.commit()
    conn.close()
