import httpx
from conftest import BASE, nueva_clave
from proveedor_simulado import enviar_aviso

def pedido_con_pago(cliente):
    pedido = httpx.post(f"{BASE}/orders", json={"items": [{"product_id": "batido-proteico", "cantidad": 2}]},
                        headers={**cliente["headers"], "Idempotency-Key": nueva_clave()}).json()
    pago = httpx.post(f"{BASE}/payments", json={"order_id": pedido["id"]}, headers=cliente["headers"])
    assert pago.status_code == 201, pago.text
    return pedido, pago.json()

def estado_pedido(cliente, pedido_id):
    return httpx.get(f"{BASE}/orders/{pedido_id}", headers=cliente["headers"]).json()["estado"]

def test_monto_del_pago_viene_de_orders(cliente_a):
    pedido, pago = pedido_con_pago(cliente_a)
    assert pago["monto"] == pedido["total"] == 6400
    assert pago["estado"] == "iniciado"

def test_no_se_paga_pedido_ajeno(cliente_a, cliente_b):
    pedido, _ = pedido_con_pago(cliente_a)
    r = httpx.post(f"{BASE}/payments", json={"order_id": pedido["id"]}, headers=cliente_b["headers"])
    assert r.status_code == 404

def test_aviso_con_firma_falsa_se_rechaza(cliente_a):
    pedido, pago = pedido_con_pago(cliente_a)
    r = enviar_aviso(pago["provider_ref"], pago["monto"], "aprobado", secreto="secreto-inventado")
    assert r.status_code == 401
    assert estado_pedido(cliente_a, pedido["id"]) == "pendiente_pago"

def test_aviso_con_monto_alterado_se_rechaza(cliente_a):
    pedido, pago = pedido_con_pago(cliente_a)
    r = enviar_aviso(pago["provider_ref"], 1, "aprobado")
    assert r.status_code == 409
    assert estado_pedido(cliente_a, pedido["id"]) == "pendiente_pago"

def test_aviso_valido_marca_pagado_y_duplicado_no_reprocesa(cliente_a):
    pedido, pago = pedido_con_pago(cliente_a)
    r1 = enviar_aviso(pago["provider_ref"], pago["monto"], "aprobado", event_id="EVT-" + pedido["id"])
    assert r1.status_code == 200 and r1.json()["duplicado"] is False
    assert estado_pedido(cliente_a, pedido["id"]) == "pagado"

    r2 = enviar_aviso(pago["provider_ref"], pago["monto"], "aprobado", event_id="EVT-" + pedido["id"])
    assert r2.status_code == 200 and r2.json()["duplicado"] is True

    r3 = httpx.post(f"{BASE}/payments", json={"order_id": pedido["id"]}, headers=cliente_a["headers"])
    assert r3.status_code == 409

def test_cliente_no_puede_confirmar_su_propio_pago(cliente_a):
    pedido, pago = pedido_con_pago(cliente_a)
    r = httpx.post(f"{BASE}/internal/orders/{pedido['id']}/pagado", json={"payment_id": pago["id"]},
                   headers=cliente_a["headers"])
    assert r.status_code == 404
    r = httpx.patch(f"{BASE}/orders/{pedido['id']}/estado", json={"estado": "pagado"}, headers=cliente_a["headers"])
    assert r.status_code == 403

def test_flujo_completo_hasta_entregado(cliente_a, operador):
    pedido, pago = pedido_con_pago(cliente_a)
    enviar_aviso(pago["provider_ref"], pago["monto"], "aprobado")
    for estado in ["en_preparacion", "despachado", "entregado"]:
        r = httpx.patch(f"{BASE}/orders/{pedido['id']}/estado", json={"estado": estado}, headers=operador["headers"])
        assert r.status_code == 200 and r.json()["estado"] == estado
    reporte = httpx.get(f"{BASE}/orders/reporte/diario", headers=operador["headers"])
    assert reporte.status_code == 200
    assert any(f["product_id"] == "batido-proteico" for f in reporte.json())
