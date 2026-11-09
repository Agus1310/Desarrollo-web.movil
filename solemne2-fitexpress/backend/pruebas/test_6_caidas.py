import os
import uuid

import httpx
import pytest
from conftest import BASE

CAIDA = os.getenv("CAIDA")

def usuario():
    email = f"caida.{uuid.uuid4().hex[:6]}@correo-prueba.cl"
    httpx.post(f"{BASE}/auth/registro", json={"nombre": "Caida Prueba", "email": email,
                                              "direccion": "Calle Falsa 123, Santiago", "password": "ClavePrueba123"})
    token = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": "ClavePrueba123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.skipif(CAIDA != "inventory", reason="solo con inventory apagado")
def test_catalogo_con_inventory_caido_da_503_controlado():
    r = httpx.get(f"{BASE}/products")
    assert r.status_code == 503
    assert r.json() == {"detail": "El servicio inventory no esta disponible"}

@pytest.mark.skipif(CAIDA != "inventory", reason="solo con inventory apagado")
def test_pedido_con_inventory_caido_no_se_crea():
    headers = usuario()
    r = httpx.post(f"{BASE}/orders", json={"items": [{"product_id": "bowl-pollo", "cantidad": 1}]},
                   headers={**headers, "Idempotency-Key": "idem-" + uuid.uuid4().hex})
    assert r.status_code == 503
    assert httpx.get(f"{BASE}/orders", headers=headers).json() == []

@pytest.mark.skipif(CAIDA != "payments", reason="solo con payments apagado")
def test_graphql_con_payments_caido_responde_parcial_identificado():
    headers = usuario()
    pedido = httpx.post(f"{BASE}/orders", json={"items": [{"product_id": "bowl-pollo", "cantidad": 1}]},
                        headers={**headers, "Idempotency-Key": "idem-" + uuid.uuid4().hex}).json()
    r = httpx.post(f"{BASE}/graphql", headers=headers, json={
        "query": "query ($id: ID!) { resumenPedido(id: $id) { id total items { nombre } pago { estado } } }",
        "variables": {"id": pedido["id"]}})
    cuerpo = r.json()
    assert cuerpo["data"]["resumenPedido"]["total"] == 5900
    assert cuerpo["data"]["resumenPedido"]["pago"] is None
    assert cuerpo["errors"][0]["extensions"]["code"] == "DATO_PARCIAL"
