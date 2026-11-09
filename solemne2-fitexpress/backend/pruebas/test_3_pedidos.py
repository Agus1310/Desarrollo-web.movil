import httpx
from conftest import BASE, nueva_clave, stock_de

def crear_pedido(cliente, items, clave=None):
    return httpx.post(f"{BASE}/orders", json={"items": items}, headers={
        **cliente["headers"], "Idempotency-Key": clave or nueva_clave()
    })

def test_total_lo_calcula_el_servidor(cliente_a):
    r = crear_pedido(cliente_a, [{"product_id": "bowl-pollo", "cantidad": 2},
                                 {"product_id": "batido-proteico", "cantidad": 1}])
    assert r.status_code == 201, r.text
    pedido = r.json()
    assert pedido["estado"] == "pendiente_pago"
    assert pedido["total"] == 5900 * 2 + 3200

def test_precio_enviado_por_el_navegador_se_rechaza(cliente_a):
    r = crear_pedido(cliente_a, [{"product_id": "bowl-pollo", "cantidad": 1, "precio": 1}])
    assert r.status_code == 422

def test_pedido_sin_idempotency_key_da_422(cliente_a):
    r = httpx.post(f"{BASE}/orders", json={"items": [{"product_id": "bowl-pollo", "cantidad": 1}]},
                   headers=cliente_a["headers"])
    assert r.status_code == 422

def test_reintento_con_misma_clave_no_duplica(cliente_a, operador):
    antes = stock_de(operador, "bowl-vegano")
    clave = nueva_clave()
    r1 = crear_pedido(cliente_a, [{"product_id": "bowl-vegano", "cantidad": 2}], clave)
    r2 = crear_pedido(cliente_a, [{"product_id": "bowl-vegano", "cantidad": 2}], clave)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]
    assert stock_de(operador, "bowl-vegano") == antes - 2

def test_stock_insuficiente_da_409_y_no_descuenta(cliente_a, operador):
    httpx.patch(f"{BASE}/products/ensalada-fit/stock", json={"stock": 5}, headers=operador["headers"])
    r = crear_pedido(cliente_a, [{"product_id": "bowl-pollo", "cantidad": 1},
                                 {"product_id": "ensalada-fit", "cantidad": 6}])
    assert r.status_code == 409
    assert stock_de(operador, "ensalada-fit") == 5
    httpx.patch(f"{BASE}/products/ensalada-fit/stock", json={"stock": 100}, headers=operador["headers"])

def test_producto_inexistente_da_404(cliente_a):
    r = crear_pedido(cliente_a, [{"product_id": "pizza-gigante", "cantidad": 1}])
    assert r.status_code == 404

def test_operador_no_puede_crear_pedidos(operador):
    r = crear_pedido(operador, [{"product_id": "bowl-pollo", "cantidad": 1}])
    assert r.status_code == 403

def test_cliente_solo_ve_sus_pedidos(cliente_a, cliente_b):
    pedido = crear_pedido(cliente_a, [{"product_id": "snack-energetico", "cantidad": 1}]).json()

    r = httpx.get(f"{BASE}/orders/{pedido['id']}", headers=cliente_b["headers"])
    assert r.status_code == 404
    assert "items" not in r.json()

    ids_b = [p["id"] for p in httpx.get(f"{BASE}/orders", headers=cliente_b["headers"]).json()]
    assert pedido["id"] not in ids_b

    assert httpx.get(f"{BASE}/orders/{pedido['id']}", headers=cliente_a["headers"]).status_code == 200

def test_cliente_no_puede_anular_pedido_ajeno(cliente_a, cliente_b):
    pedido = crear_pedido(cliente_a, [{"product_id": "snack-energetico", "cantidad": 1}]).json()
    r = httpx.patch(f"{BASE}/orders/{pedido['id']}/cancelar", headers=cliente_b["headers"])
    assert r.status_code == 404

def test_anular_devuelve_el_stock_y_conserva_el_pedido(cliente_a, operador):
    antes = stock_de(operador, "bowl-vegetariano")
    pedido = crear_pedido(cliente_a, [{"product_id": "bowl-vegetariano", "cantidad": 3}]).json()
    assert stock_de(operador, "bowl-vegetariano") == antes - 3
    r = httpx.patch(f"{BASE}/orders/{pedido['id']}/cancelar", headers=cliente_a["headers"])
    assert r.status_code == 200 and r.json()["estado"] == "cancelado"
    assert stock_de(operador, "bowl-vegetariano") == antes

    assert httpx.get(f"{BASE}/orders/{pedido['id']}", headers=cliente_a["headers"]).json()["estado"] == "cancelado"

def test_operador_no_puede_marcar_pagado_a_mano(cliente_a, operador):
    pedido = crear_pedido(cliente_a, [{"product_id": "snack-energetico", "cantidad": 1}]).json()
    r = httpx.patch(f"{BASE}/orders/{pedido['id']}/estado", json={"estado": "pagado"}, headers=operador["headers"])
    assert r.status_code == 403

def test_transicion_invalida_da_409(cliente_a, operador):
    pedido = crear_pedido(cliente_a, [{"product_id": "snack-energetico", "cantidad": 1}]).json()
    r = httpx.patch(f"{BASE}/orders/{pedido['id']}/estado", json={"estado": "entregado"},
                    headers=operador["headers"])
    assert r.status_code == 409

def test_operador_administra_catalogo(operador):
    nuevo = {"id": "wrap-atun", "nombre": "Wrap de Atún", "tag": "Alto en proteína", "precio": 4500,
             "descripcion": "Tortilla integral con atún, palta y tomate.",
             "ingredientes": ["Tortilla integral", "Atún", "Palta", "Tomate"], "calorias": 410, "stock": 15}
    r = httpx.post(f"{BASE}/products", json=nuevo, headers=operador["headers"])
    assert r.status_code in (201, 409)
    nuevo.pop("id")
    nuevo["precio"] = 4700
    r = httpx.put(f"{BASE}/products/wrap-atun", json=nuevo, headers=operador["headers"])
    assert r.status_code in (200, 404)
    r = httpx.delete(f"{BASE}/products/wrap-atun", headers=operador["headers"])
    assert r.status_code in (204, 404)

    assert httpx.get(f"{BASE}/products/wrap-atun").status_code == 404
