CREATE TABLE IF NOT EXISTS pagos (
    id             TEXT PRIMARY KEY,
    order_id       TEXT NOT NULL,
    user_id        TEXT NOT NULL,
    monto          INTEGER NOT NULL,
    estado         TEXT NOT NULL CHECK (estado IN ('iniciado', 'aprobado', 'rechazado')),
    provider_ref   TEXT NOT NULL UNIQUE,
    creado_en      TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS eventos_proveedor (
    event_id    TEXT PRIMARY KEY,
    provider_ref TEXT NOT NULL,
    resultado   TEXT NOT NULL,
    recibido_en TEXT NOT NULL
);
