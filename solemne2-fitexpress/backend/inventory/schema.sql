CREATE TABLE IF NOT EXISTS productos (
    id           TEXT PRIMARY KEY,
    nombre       TEXT NOT NULL,
    tag          TEXT NOT NULL,
    precio       INTEGER NOT NULL CHECK (precio > 0),
    descripcion  TEXT NOT NULL,
    ingredientes TEXT NOT NULL,
    calorias     INTEGER NOT NULL,
    stock        INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    activo       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reservas (
    order_id  TEXT PRIMARY KEY,
    items     TEXT NOT NULL,
    estado    TEXT NOT NULL CHECK (estado IN ('activa', 'liberada')),
    creado_en TEXT NOT NULL
);
