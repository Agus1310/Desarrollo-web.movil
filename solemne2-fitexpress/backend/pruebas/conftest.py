import os
import sys
import uuid

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iniciar import leer_env

BASE = "http://127.0.0.1:8000/api/v1"

def registrar_y_entrar(nombre):
    email = f"{nombre}.{uuid.uuid4().hex[:6]}@correo-prueba.cl"
    password = "ClavePrueba123"
    r = httpx.post(f"{BASE}/auth/registro", json={
        "nombre": nombre.capitalize() + " Prueba",
        "email": email,
        "direccion": "Av. Siempre Viva 742, Santiago",
        "telefono": "+56 9 1234 5678",
        "password": password
    })
    assert r.status_code == 201, r.text
    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"email": email, "id": None, "headers": {"Authorization": f"Bearer {token}"}}

@pytest.fixture(scope="session")
def cliente_a():
    return registrar_y_entrar("ana")

@pytest.fixture(scope="session")
def cliente_b():
    return registrar_y_entrar("pedro")

@pytest.fixture(scope="session")
def operador():
    env = leer_env()
    r = httpx.post(f"{BASE}/auth/login", json={"email": env["ADMIN_EMAIL"], "password": env["ADMIN_PASSWORD"]})
    assert r.status_code == 200, r.text
    return {"headers": {"Authorization": f"Bearer {r.json()['access_token']}"}}

@pytest.fixture(scope="session", autouse=True)
def reponer_stock(request):
    if os.getenv("CAIDA"):
        return
    op = request.getfixturevalue("operador")
    for p in httpx.get(f"{BASE}/admin/products", headers=op["headers"]).json():
        if p["activo"]:
            httpx.patch(f"{BASE}/products/{p['id']}/stock", json={"stock": 100}, headers=op["headers"])

def nueva_clave():
    return "idem-" + uuid.uuid4().hex

def stock_de(operador, product_id):
    r = httpx.get(f"{BASE}/admin/products", headers=operador["headers"])
    return next(p["stock"] for p in r.json() if p["id"] == product_id)
