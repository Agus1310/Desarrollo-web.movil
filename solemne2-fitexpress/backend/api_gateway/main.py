import os
import re
import time
import uuid
import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

SERVICIOS = {
    "auth": os.getenv("AUTH_URL", "http://127.0.0.1:8100"),
    "inventory": os.getenv("INVENTORY_URL", "http://127.0.0.1:9001"),
    "orders": os.getenv("ORDERS_URL", "http://127.0.0.1:9002"),
    "clients": os.getenv("CLIENTS_URL", "http://127.0.0.1:9003"),
    "payments": os.getenv("PAYMENTS_URL", "http://127.0.0.1:9004"),
    "graphql": os.getenv("GRAPHQL_URL", "http://127.0.0.1:9005"),
}

ORIGENES_FRONTEND = os.getenv("FRONTEND_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")

LIMITE_POR_MINUTO = int(os.getenv("LIMITE_POR_MINUTO", "300"))
LIMITE_LOGIN_POR_MINUTO = int(os.getenv("LIMITE_LOGIN_POR_MINUTO", "20"))
MAX_CUERPO = 64 * 1024

RUTAS = [
    ("GET",    "/api/v1/products",                  "publico",     "inventory", "/products"),
    ("GET",    "/api/v1/products/{id}",             "publico",     "inventory", "/products/{id}"),
    ("GET",    "/api/v1/admin/products",            "operador",    "inventory", "/admin/products"),
    ("POST",   "/api/v1/products",                  "operador",    "inventory", "/products"),
    ("PUT",    "/api/v1/products/{id}",             "operador",    "inventory", "/products/{id}"),
    ("PATCH",  "/api/v1/products/{id}/stock",       "operador",    "inventory", "/products/{id}/stock"),
    ("DELETE", "/api/v1/products/{id}",             "operador",    "inventory", "/products/{id}"),

    ("POST",   "/api/v1/auth/registro",             "publico",     "clients",   "/clients/registro"),
    ("POST",   "/api/v1/auth/login",                "publico",     "auth",      "/login"),
    ("GET",    "/api/v1/clients/me",                "autenticado", "clients",   "/clients/me"),
    ("PUT",    "/api/v1/clients/me",                "autenticado", "clients",   "/clients/me"),
    ("GET",    "/api/v1/clients",                   "operador",    "clients",   "/clients"),

    ("POST",   "/api/v1/orders",                    "cliente",     "orders",    "/orders"),
    ("GET",    "/api/v1/orders",                    "autenticado", "orders",    "/orders"),
    ("GET",    "/api/v1/orders/reporte/diario",     "operador",    "orders",    "/orders/reporte/diario"),
    ("GET",    "/api/v1/orders/{id}",               "autenticado", "orders",    "/orders/{id}"),
    ("PATCH",  "/api/v1/orders/{id}/cancelar",      "autenticado", "orders",    "/orders/{id}/cancelar"),
    ("PATCH",  "/api/v1/orders/{id}/estado",        "operador",    "orders",    "/orders/{id}/estado"),

    ("POST",   "/api/v1/payments",                  "cliente",     "payments",  "/payments"),
    ("GET",    "/api/v1/payments/{id}",             "autenticado", "payments",  "/payments/{id}"),

    ("POST",   "/api/v1/payments/webhook",          "publico",     "payments",  "/payments/webhook"),

    ("POST",   "/api/v1/graphql",                   "autenticado", "graphql",   "/graphql"),
]

CABECERAS_PERMITIDAS = ["content-type", "idempotency-key", "x-proveedor-firma"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("gateway")

app = FastAPI(title="Fit Express - API Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_FRONTEND,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

def compilar(ruta):
    patron = re.sub(r"\{(\w+)\}", r"(?P<\1>[A-Za-z0-9_-]{1,40})", ruta)
    return re.compile("^" + patron + "$")

TABLA = [(verbo, compilar(ext), acceso, servicio, interna) for verbo, ext, acceso, servicio, interna in RUTAS]

def buscar_ruta(metodo, path):
    for verbo, patron, acceso, servicio, interna in TABLA:
        coincide = patron.match(path)
        if coincide and verbo == metodo:
            return acceso, servicio, interna.format(**coincide.groupdict())
    return None

_cache_secretos = {"datos": None, "hora": 0}

async def secretos_gateway():
    if _cache_secretos["datos"] and time.time() - _cache_secretos["hora"] < 60:
        return _cache_secretos["datos"]
    if not VAULT_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{VAULT_ADDR}/v1/secret/data/fitexpress/gateway",
                                 headers={"X-Vault-Token": VAULT_TOKEN})
    except httpx.RequestError:
        return None
    if r.status_code != 200:
        return None
    _cache_secretos["datos"] = r.json()["data"]["data"]
    _cache_secretos["hora"] = time.time()
    return _cache_secretos["datos"]

_solicitudes = {}

def supera_limite(clave, limite):
    ahora = time.time()
    lista = [t for t in _solicitudes.get(clave, []) if ahora - t < 60]
    lista.append(ahora)
    _solicitudes[clave] = lista
    return len(lista) > limite

def error(status, mensaje, request_id):
    return JSONResponse(status_code=status, content={"detail": mensaje},
                        headers={"X-Request-Id": request_id})

@app.get("/health")
def health():
    return {"status": "OK", "service": "api-gateway"}

@app.post("/api/v1/auth/logout")
async def logout(request: Request):
    request_id = str(uuid.uuid4())
    token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    secretos = await secretos_gateway()
    if secretos is None:
        return error(503, "Gestor de secretos no disponible", request_id)
    if token:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{SERVICIOS['auth']}/logout", json={"token": token},
                                  headers={"X-Service-Key": secretos["auth_key"], "X-Request-Id": request_id})
        except httpx.RequestError:
            return error(503, "Servicio de autenticacion no disponible", request_id)
    return JSONResponse({"message": "Sesion cerrada"}, headers={"X-Request-Id": request_id})

@app.api_route("/api/{resto:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def entrada(resto: str, request: Request):
    inicio = time.time()
    request_id = str(uuid.uuid4())
    ip = request.client.host if request.client else "desconocida"
    path = request.url.path

    respuesta = await procesar(request, path, ip, request_id)
    usuario = getattr(request.state, "user_id", "-")
    ms = int((time.time() - inicio) * 1000)

    log.info(f"request_id={request_id} ip={ip} {request.method} {path} "
             f"status={respuesta.status_code} user={usuario} {ms}ms")
    return respuesta

async def procesar(request, path, ip, request_id):
    if supera_limite(ip, LIMITE_POR_MINUTO):
        return error(429, "Demasiadas solicitudes, espera un momento", request_id)

    ruta = buscar_ruta(request.method, path)
    if ruta is None:
        return error(404, "Ruta no publicada", request_id)
    acceso, servicio, ruta_interna = ruta

    if path in ("/api/v1/auth/login", "/api/v1/auth/registro") and supera_limite("login:" + ip, LIMITE_LOGIN_POR_MINUTO):
        return error(429, "Demasiados intentos, espera un minuto", request_id)

    cuerpo = await request.body()
    if len(cuerpo) > MAX_CUERPO:
        return error(413, "El cuerpo de la solicitud es demasiado grande", request_id)

    secretos = await secretos_gateway()
    if secretos is None:
        return error(503, "Gestor de secretos no disponible", request_id)

    cabeceras = {"X-Request-Id": request_id, "X-Service-Key": secretos[f"{servicio}_key"]}
    for nombre in CABECERAS_PERMITIDAS:
        if nombre in request.headers:
            cabeceras[nombre] = request.headers[nombre]

    if acceso != "publico":
        token = request.headers.get("authorization", "")
        if not token.startswith("Bearer ") or len(token) > 300:
            return error(401, "Se requiere iniciar sesion (Bearer token)", request_id)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(f"{SERVICIOS['auth']}/introspect",
                                      json={"token": token[7:]},
                                      headers={"X-Service-Key": secretos["auth_key"], "X-Request-Id": request_id})
        except httpx.RequestError:
            return error(503, "Servicio de autenticacion no disponible", request_id)
        identidad = r.json() if r.status_code == 200 else {"active": False}
        if not identidad.get("active"):
            return error(401, "Sesion invalida o expirada", request_id)

        rol = identidad["rol"]
        if acceso == "operador" and rol != "operador":
            return error(403, "Tu rol no tiene permiso para esta operacion", request_id)
        if acceso == "cliente" and rol != "cliente":
            return error(403, "Esta operacion es solo para clientes", request_id)

        cabeceras["X-User-Id"] = identidad["user_id"]
        cabeceras["X-User-Rol"] = rol
        cabeceras["X-User-Email"] = identidad["email"]
        request.state.user_id = identidad["user_id"]

    destino = SERVICIOS[servicio] + ruta_interna
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            upstream = await client.request(request.method, destino, params=request.query_params,
                                            content=cuerpo, headers=cabeceras)
    except httpx.TimeoutException:
        return error(504, f"El servicio {servicio} no respondio a tiempo", request_id)
    except httpx.RequestError:
        return error(503, f"El servicio {servicio} no esta disponible", request_id)

    headers_respuesta = {"X-Request-Id": request_id}
    if "content-type" in upstream.headers:
        headers_respuesta["content-type"] = upstream.headers["content-type"]
    return Response(content=upstream.content, status_code=upstream.status_code, headers=headers_respuesta)
