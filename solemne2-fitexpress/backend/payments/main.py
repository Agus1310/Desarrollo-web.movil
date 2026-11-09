import os
import hmac
import json
import uuid
import hashlib
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from comun.db import conectar, inicializar
from comun.seguridad import (exigir_llave, identidad, leer_secretos, llamar_servicio, agregar_logs)

CARPETA = os.path.dirname(__file__)
DB = os.path.join(CARPETA, "data", "payments.db")
ORDERS_URL = os.getenv("ORDERS_URL", "http://127.0.0.1:9002")

app = FastAPI(title="Fit Express - Payments")
agregar_logs(app, "payments")
llave = exigir_llave("payments")

class PagoIn(BaseModel):
    order_id: str = Field(max_length=40)

class AvisoProveedor(BaseModel):
    event_id: str = Field(max_length=60)
    provider_ref: str = Field(max_length=60)
    estado: str
    monto: int

def ahora():
    return datetime.now(timezone.utc).isoformat()

def pago_publico(fila):
    return {
        "id": fila["id"],
        "order_id": fila["order_id"],
        "monto": fila["monto"],
        "estado": fila["estado"],
        "provider_ref": fila["provider_ref"]
    }

@app.on_event("startup")
def iniciar():
    inicializar(DB, os.path.join(CARPETA, "schema.sql"))

@app.get("/health")
def health():
    return {"status": "OK", "service": "payments"}

@app.post("/payments", status_code=201, dependencies=[Depends(llave)])
def iniciar_pago(datos: PagoIn, request: Request):
    usuario = identidad(request)
    req_id = request.headers.get("x-request-id")

    r = llamar_servicio("GET", f"{ORDERS_URL}/internal/orders/{datos.order_id}",
                        leer_secretos("payments")["orders_key"], req_id)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = r.json()
    if pedido["user_id"] != usuario["user_id"]:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if pedido["estado"] != "pendiente_pago":
        raise HTTPException(status_code=409, detail="Este pedido no esta pendiente de pago")

    con = conectar(DB)

    existente = con.execute(
        "SELECT * FROM pagos WHERE order_id = ? AND estado IN ('iniciado', 'aprobado')", (datos.order_id,)
    ).fetchone()
    if existente:
        con.close()
        return pago_publico(existente)

    pago_id = "PAG-" + uuid.uuid4().hex[:8]
    provider_ref = "PRV-" + uuid.uuid4().hex[:12]
    con.execute(
        "INSERT INTO pagos VALUES (?,?,?,?,?,?,?,?)",
        (pago_id, datos.order_id, usuario["user_id"], pedido["total"], "iniciado", provider_ref, ahora(), ahora())
    )
    con.commit()
    fila = con.execute("SELECT * FROM pagos WHERE id = ?", (pago_id,)).fetchone()
    con.close()
    return pago_publico(fila)

@app.get("/payments/{pago_id}", dependencies=[Depends(llave)])
def ver_pago(pago_id: str, request: Request):
    usuario = identidad(request)
    con = conectar(DB)
    fila = con.execute("SELECT * FROM pagos WHERE id = ?", (pago_id,)).fetchone()
    con.close()
    if fila is None or (usuario["rol"] != "operador" and fila["user_id"] != usuario["user_id"]):
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago_publico(fila)

@app.post("/payments/webhook", dependencies=[Depends(llave)])
async def aviso_proveedor(request: Request, x_proveedor_firma: str = Header(default="")):
    cuerpo = await request.body()
    return await run_in_threadpool(procesar_aviso, cuerpo, x_proveedor_firma, request.headers.get("x-request-id"))

def procesar_aviso(cuerpo, x_proveedor_firma, request_id):
    secreto = leer_secretos("payments")["provider_webhook_secret"]
    firma_esperada = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(x_proveedor_firma, firma_esperada):
        raise HTTPException(status_code=401, detail="Firma del proveedor no valida")

    try:
        aviso = AvisoProveedor(**json.loads(cuerpo))
    except Exception:
        raise HTTPException(status_code=400, detail="Aviso mal formado")
    if aviso.estado not in ("aprobado", "rechazado"):
        raise HTTPException(status_code=400, detail="Estado de pago no valido")

    con = conectar(DB)

    if con.execute("SELECT 1 FROM eventos_proveedor WHERE event_id = ?", (aviso.event_id,)).fetchone():
        con.close()
        return {"recibido": True, "duplicado": True}

    pago = con.execute("SELECT * FROM pagos WHERE provider_ref = ?", (aviso.provider_ref,)).fetchone()
    if pago is None:
        con.close()
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if aviso.monto != pago["monto"]:
        con.close()
        raise HTTPException(status_code=409, detail="El monto no coincide con el pedido")
    if pago["estado"] != "iniciado":
        con.close()
        raise HTTPException(status_code=409, detail="El pago ya fue resuelto")

    if aviso.estado == "aprobado":
        r = llamar_servicio("POST", f"{ORDERS_URL}/internal/orders/{pago['order_id']}/pagado",
                            leer_secretos("payments")["orders_key"], request_id,
                            json={"payment_id": pago["id"]})
        if r.status_code != 200:
            con.close()

            raise HTTPException(status_code=409, detail="El pedido no acepto el pago")

    con.execute("UPDATE pagos SET estado = ?, actualizado_en = ? WHERE id = ?", (aviso.estado, ahora(), pago["id"]))
    con.execute("INSERT INTO eventos_proveedor VALUES (?,?,?,?)",
                (aviso.event_id, aviso.provider_ref, aviso.estado, ahora()))
    con.commit()
    con.close()
    return {"recibido": True, "duplicado": False, "estado": aviso.estado}

@app.get("/internal/payments", dependencies=[Depends(llave)])
def pagos_por_pedidos(order_ids: str):
    lista = [i for i in order_ids.split(",") if i][:50]
    if not lista:
        return []
    con = conectar(DB)
    marcas = ",".join("?" * len(lista))
    filas = con.execute(
        f"SELECT * FROM pagos WHERE order_id IN ({marcas}) ORDER BY creado_en", lista
    ).fetchall()
    con.close()
    return [pago_publico(f) for f in filas]
