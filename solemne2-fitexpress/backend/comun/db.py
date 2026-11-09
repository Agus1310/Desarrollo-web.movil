import os
import sqlite3

def conectar(ruta):
    con = sqlite3.connect(ruta, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def inicializar(ruta, archivo_schema):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    con = conectar(ruta)
    with open(archivo_schema, encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()
    con.close()
