CREATE TABLE IF NOT EXISTS perfiles (
    user_id   TEXT PRIMARY KEY,
    nombre    TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    direccion TEXT NOT NULL,
    telefono  TEXT,
    creado_en TEXT NOT NULL
);
