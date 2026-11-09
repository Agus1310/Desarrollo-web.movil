import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from pydantic import BaseModel, Field, ConfigDict

from comun.db import conectar, inicializar
from comun.seguridad import (exigir_llave, identidad, exigir_rol, leer_secretos,
                             llamar_servicio, agregar_logs)

CARPETA = os.path.dirname(__file__)
DB = os.path.join(CARPETA, "data", "orders.db")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://127.0.0.1:9001")
CLIENTS_URL = os.getenv("CLIENTS_URL", "http://127.0.0.1:9003")

app = FastAPI(title="Fit Express - Orders")
agregar_logs(app, "orders")
llave = exigir_llave("orders")

TRANSICIONES = {
    "pendiente_pago": ["pagado", "cancelado"],
    "pagado": ["en_preparacion"],
    "en_preparacion": ["despachado"],
    "despachado": ["entregado"],
    "entregado": [],
    "cancelado": []
}

class ItemPedido(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: str = Field(max_length=40)
    cantidad: int = Field(gt=0, le=10)

class PedidoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ItemPedido] = Field(min_length=1, max_length=20)

class EstadoIn(BaseModel):
    estado: str

class PagoConfirmado(BaseModel):
    payment_id: str

def ahora():
    return datetime.now(timezone.utc).isoformat()

def armar_pedido(con, fila, incluir_usuario=False):
    items = con.execute(
        "SELECT product_id, nombre, precio_unitario, cantidad, subtotal FROM detalle_pedido WHERE pedido_id = ?",
        (fila["id"],)
    ).fetchall()
    pedido = {
        "id": fila["id"],
        "estado": fila["estado"],
        "total": fila["total"],
        "direccion_entrega": fila["direccion_entrega"],
        "creado_en": fila["creado_en"],
        "items": [dict(i) for i in items]
    }
    if incluir_usuario:
        pedido["user_id"] = fila["user_id"]
    return pedido

def buscar_pedido_visible(con, pedido_id, usuario):
    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()

    if fila is None or (usuario["rol"] != "operador" and fila["user_id"] != usuario["user_id"]):
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return fila

def cambiar_estado(con, pedido_id, nuevo, actor):
    con.execute("UPDATE pedidos SET estado = ?, actualizado_en = ? WHERE id = ?", (nuevo, ahora(), pedido_id))
    con.execute("INSERT INTO historial_estados (pedido_id, estado, actor, fecha) VALUES (?,?,?,?)",
                (pedido_id, nuevo, actor, ahora()))

@app.on_event("startup")
def iniciar():
    inicializar(DB, os.path.join(CARPETA, "schema.sql"))

@app.get("/health")
def health():
    return {"status": "OK", "service": "orders"}

@app.post("/orders", status_code=201, dependencies=[Depends(llave)])
def crear_pedido(datos: PedidoIn, request: Request,
                 idempotency_key: str = Header(min_length=8, max_length=64)):
    usuario = identidad(request)
    exigir_rol(usuario, "cliente")
    req_id = request.headers.get("x-request-id")
    secretos = leer_secretos("orders")

    con = conectar(DB)

    previo = con.execute(
        "SELECT * FROM pedidos WHERE user_id = ? AND idempotency_key = ?",
        (usuario["user_id"], idempotency_key)
    ).fetchone()
    if previo:
        pedido = armar_pedido(con, previo)
        con.close()
        return pedido

    cantidades = {}
    for item in datos.items:
        cantidades[item.product_id] = cantidades.get(item.product_id, 0) + item.cantidad

    r = llamar_servicio("GET", f"{CLIENTS_URL}/internal/clients/{usuario['user_id']}",
                        secretos["clients_key"], req_id)
    if r.status_code == 404:
        con.close()
        raise HTTPException(status_code=409, detail="Completa tu registro antes de pedir")
    direccion = r.json()["direccion"]

    r = llamar_servicio("GET", f"{INVENTORY_URL}/internal/products", secretos["inventory_key"], req_id,
                        params={"ids": ",".join(cantidades.keys())})
    productos = {p["id"]: p for p in r.json()}
    for product_id in cantidades:
        if product_id not in productos or not productos[product_id]["activo"]:
            con.close()
            raise HTTPException(status_code=404, detail=f"Producto {product_id} no existe")

    pedido_id = "PED-" + uuid.uuid4().hex[:8]

    r = llamar_servicio("POST", f"{INVENTORY_URL}/internal/reservas", secretos["inventory_key"], req_id,
                        json={"order_id": pedido_id,
                              "items": [{"product_id": k, "cantidad": v} for k, v in cantidades.items()]})
    if r.status_code != 200:
        con.close()
        raise HTTPException(status_code=r.status_code, detail=r.json().get("detail", "No se pudo reservar stock"))

    total = 0
    try:
        con.execute(
            "INSERT INTO pedidos VALUES (?,?,?,?,?,?,?,?)",
            (pedido_id, usuario["user_id"], "pendiente_pago", 0, direccion, idempotency_key, ahora(), ahora())
        )
        for product_id, cantidad in cantidades.items():
            precio = productos[product_id]["precio"]
            subtotal = precio * cantidad
            total += subtotal
            con.execute(
                "INSERT INTO detalle_pedido (pedido_id, product_id, nombre, precio_unitario, cantidad, subtotal) "
                "VALUES (?,?,?,?,?,?)",
                (pedido_id, product_id, productos[product_id]["nombre"], precio, cantidad, subtotal)
            )
        con.execute("UPDATE pedidos SET total = ? WHERE id = ?", (total, pedido_id))
        con.execute("INSERT INTO historial_estados (pedido_id, estado, actor, fecha) VALUES (?,?,?,?)",
                    (pedido_id, "pendiente_pago", usuario["user_id"], ahora()))
        con.commit()
    except Exception:
        con.rollback()
        con.close()

        llamar_servicio("POST", f"{INVENTORY_URL}/internal/reservas/{pedido_id}/liberar",
                        secretos["inventory_key"], req_id)
        raise HTTPException(status_code=500, detail="No se pudo registrar el pedido")

    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    pedido = armar_pedido(con, fila)
    con.close()
    return pedido

@app.get("/orders", dependencies=[Depends(llave)])
def listar_pedidos(request: Request, estado: str | None = None):
    usuario = identidad(request)
    if estado and estado not in TRANSICIONES:
        raise HTTPException(status_code=400, detail="Estado no valido")
    con = conectar(DB)
    sql = "SELECT * FROM pedidos WHERE 1 = 1"
    params = []
    if usuario["rol"] != "operador":
        sql += " AND user_id = ?"
        params.append(usuario["user_id"])
    if estado:
        sql += " AND estado = ?"
        params.append(estado)
    filas = con.execute(sql + " ORDER BY creado_en DESC LIMIT 50", params).fetchall()
    pedidos = [armar_pedido(con, f) for f in filas]
    con.close()
    return pedidos

@app.get("/orders/reporte/diario", dependencies=[Depends(llave)])
def reporte_diario(request: Request):
    exigir_rol(identidad(request), "operador")
    con = conectar(DB)
    filas = con.execute(
        """SELECT substr(p.creado_en, 1, 10) AS dia, d.product_id, d.nombre,
                  SUM(d.cantidad) AS unidades, SUM(d.subtotal) AS ventas
           FROM pedidos p JOIN detalle_pedido d ON d.pedido_id = p.id
           WHERE p.estado NOT IN ('pendiente_pago', 'cancelado')
           GROUP BY dia, d.product_id ORDER BY dia DESC, ventas DESC"""
    ).fetchall()
    con.close()
    return [dict(f) for f in filas]

@app.get("/orders/{pedido_id}", dependencies=[Depends(llave)])
def ver_pedido(pedido_id: str, request: Request):
    usuario = identidad(request)
    con = conectar(DB)
    fila = buscar_pedido_visible(con, pedido_id, usuario)
    pedido = armar_pedido(con, fila)
    con.close()
    return pedido

@app.patch("/orders/{pedido_id}/cancelar", dependencies=[Depends(llave)])
def cancelar_pedido(pedido_id: str, request: Request):
    usuario = identidad(request)
    con = conectar(DB)
    fila = buscar_pedido_visible(con, pedido_id, usuario)
    if fila["estado"] != "pendiente_pago":
        con.close()
        raise HTTPException(status_code=409, detail="Solo se pueden anular pedidos que aun no se pagan")

    cambiar_estado(con, pedido_id, "cancelado", usuario["user_id"])
    con.commit()
    llamar_servicio("POST", f"{INVENTORY_URL}/internal/reservas/{pedido_id}/liberar",
                    leer_secretos("orders")["inventory_key"], request.headers.get("x-request-id"))
    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    pedido = armar_pedido(con, fila)
    con.close()
    return pedido

@app.patch("/orders/{pedido_id}/estado", dependencies=[Depends(llave)])
def avanzar_estado(pedido_id: str, datos: EstadoIn, request: Request):
    usuario = identidad(request)
    exigir_rol(usuario, "operador")

    if datos.estado in ("pagado", "pendiente_pago"):
        raise HTTPException(status_code=403, detail="Ese estado lo define el sistema de pagos")
    con = conectar(DB)
    fila = buscar_pedido_visible(con, pedido_id, usuario)
    if datos.estado not in TRANSICIONES[fila["estado"]]:
        con.close()
        raise HTTPException(status_code=409, detail=f"No se puede pasar de {fila['estado']} a {datos.estado}")
    cambiar_estado(con, pedido_id, datos.estado, usuario["user_id"])
    con.commit()
    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    pedido = armar_pedido(con, fila)
    con.close()
    return pedido

@app.get("/internal/orders", dependencies=[Depends(llave)])
def pedidos_de_usuario(user_id: str, limite: int = 10):
    con = conectar(DB)
    filas = con.execute(
        "SELECT * FROM pedidos WHERE user_id = ? ORDER BY creado_en DESC LIMIT ?", (user_id, min(limite, 20))
    ).fetchall()
    pedidos = [armar_pedido(con, f, incluir_usuario=True) for f in filas]
    con.close()
    return pedidos

@app.get("/internal/orders/{pedido_id}", dependencies=[Depends(llave)])
def pedido_interno(pedido_id: str):
    con = conectar(DB)
    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if fila is None:
        con.close()
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = armar_pedido(con, fila, incluir_usuario=True)
    con.close()
    return pedido

@app.post("/internal/orders/{pedido_id}/pagado", dependencies=[Depends(llave)])
def marcar_pagado(pedido_id: str, datos: PagoConfirmado):
    con = conectar(DB)
    fila = con.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if fila is None:
        con.close()
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if fila["estado"] == "pagado":
        con.close()
        return {"id": pedido_id, "estado": "pagado", "repetido": True}
    if fila["estado"] != "pendiente_pago":
        con.close()
        raise HTTPException(status_code=409, detail=f"El pedido esta {fila['estado']}")
    cambiar_estado(con, pedido_id, "pagado", f"payments:{datos.payment_id}")
    con.commit()
    con.close()
    return {"id": pedido_id, "estado": "pagado", "repetido": False}
