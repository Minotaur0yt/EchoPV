import sqlite3

def get_connection():
    return sqlite3.connect("pos.db")

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            total REAL,
            ganancia REAL,
            destinatario TEXT,
            descripcion TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_venta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER,
            producto TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            costo_unitario REAL,
            FOREIGN KEY(venta_id) REFERENCES ventas(id)
        )
    """)
    conn.commit()
    conn.close()
