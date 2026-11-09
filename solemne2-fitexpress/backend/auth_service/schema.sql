CREATE TABLE IF NOT EXISTS usuarios (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('cliente', 'operador')),
    activo        INTEGER NOT NULL DEFAULT 1,
    creado_en     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sesiones (
    token_hash TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES usuarios(id),
    expira_en  TEXT NOT NULL,
    revocada   INTEGER NOT NULL DEFAULT 0
);
