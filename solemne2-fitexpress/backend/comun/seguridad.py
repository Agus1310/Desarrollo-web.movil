import os
import time
import uuid
import secrets
import logging

import httpx
from fastapi import Header, HTTPException, Request

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

CACHE_SEGUNDOS = 60
_cache = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

def leer_secretos(nombre):
    guardado = _cache.get(nombre)
    if guardado and time.time() - guardado["hora"] < CACHE_SEGUNDOS:
        return guardado["datos"]

    if not VAULT_TOKEN:
        raise HTTPException(status_code=503, detail="VAULT_TOKEN no configurado")

    url = f"{VAULT_ADDR}/v1/secret/data/fitexpress/{nombre}"
    try:
        respuesta = httpx.get(url, headers={"X-Vault-Token": VAULT_TOKEN}, timeout=3.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Gestor de secretos no disponible")

    if respuesta.status_code != 200:
        raise HTTPException(status_code=503, detail="No fue posible leer los secretos")

    datos = respuesta.json()["data"]["data"]
    _cache[nombre] = {"datos": datos, "hora": time.time()}
    return datos

def exigir_llave(servicio):
    def verificar(x_service_key: str = Header(default="")):
        esperada = leer_secretos(servicio)[f"{servicio}_key"]
        if not secrets.compare_digest(x_service_key, esperada):
            raise HTTPException(status_code=403, detail="Llamada no autorizada")

    return verificar

def identidad(request: Request):
    user_id = request.headers.get("x-user-id")
    rol = request.headers.get("x-user-rol")
    if not user_id or not rol:
        raise HTTPException(status_code=401, detail="Se requiere sesion")
    return {"user_id": user_id, "rol": rol, "email": request.headers.get("x-user-email")}

def exigir_rol(usuario, *roles):
    if usuario["rol"] not in roles:
        raise HTTPException(status_code=403, detail="Tu rol no tiene permiso para esta operacion")

def llamar_servicio(metodo, url, llave, request_id=None, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["X-Service-Key"] = llave
    headers["X-Request-Id"] = request_id or str(uuid.uuid4())
    try:
        return httpx.request(metodo, url, headers=headers, timeout=5.0, **kwargs)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Un servicio interno no respondio a tiempo")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Un servicio interno no esta disponible")

def agregar_logs(app, nombre):
    log = logging.getLogger(nombre)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("x-request-id", "-")
        inicio = time.time()
        respuesta = await call_next(request)
        ms = int((time.time() - inicio) * 1000)
        log.info(f"request_id={request_id} {request.method} {request.url.path} "
                 f"status={respuesta.status_code} {ms}ms")
        return respuesta
