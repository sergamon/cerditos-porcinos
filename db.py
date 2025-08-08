
import sqlite3
DB_PATH = "cerditos.db"
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS animals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        arete TEXT UNIQUE,
        categoria TEXT,
        sexo TEXT,
        raza TEXT,
        fecha_nacimiento TEXT,
        estado TEXT,
        notas TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reproducciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marrana_id INTEGER,
        macho_id INTEGER,
        fecha_monta TEXT,
        tipo TEXT,
        fecha_parto_esperado TEXT,
        notas TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS partos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reproduccion_id INTEGER,
        fecha_parto TEXT,
        nacidos_vivos INTEGER,
        nacidos_muertos INTEGER,
        destetados INTEGER,
        fecha_destete TEXT,
        notas TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ventas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        tipo TEXT,
        cantidad INTEGER,
        peso_total_kg REAL,
        precio_total REAL,
        comprador TEXT,
        notas TEXT
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        categoria TEXT,
        descripcion TEXT,
        monto REAL
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alimentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        etapa TEXT,
        kg REAL,
        costo REAL,
        notas TEXT
    );""")
    conn.commit()
    return conn
def ensure():
    init_db()
