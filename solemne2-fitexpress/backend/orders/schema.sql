CREATE TABLE IF NOT EXISTS pedidos (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL,
    estado            TEXT NOT NULL CHECK (estado IN
                      ('pendiente_pago', 'pagado', 'en_preparacion', 'despachado', 'entregado', 'cancelado')),
    total             INTEGER NOT NULL,
    direccion_entrega TEXT NOT NULL,
    idempotency_key   TEXT NOT NULL,
    creado_en         TEXT NOT NULL,
    actualizado_en    TEXT NOT NULL,
    UNIQUE (user_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS detalle_pedido (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       TEXT NOT NULL REFERENCES pedidos(id),
    product_id      TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    precio_unitario INTEGER NOT NULL,
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    subtotal        INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS historial_estados (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id TEXT NOT NULL REFERENCES pedidos(id),
    estado    TEXT NOT NULL,
    actor     TEXT NOT NULL,
    fecha     TEXT NOT NULL
);
