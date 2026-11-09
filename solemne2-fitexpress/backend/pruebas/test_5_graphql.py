import httpx
from conftest import BASE, nueva_clave

CONSULTA = """
query ($id: ID!) {
  resumenPedido(id: $id) {
    id estado total
    items { nombre cantidad subtotal tag calorias disponibleHoy }
    pago { estado monto }
  }
}"""

def graphql(cliente, consulta, variables=None):
    return httpx.post(f"{BASE}/graphql", json={"query": consulta, "variables": variables or {}},
                      headers=cliente["headers"])

def nuevo_pedido(cliente):
    return httpx.post(f"{BASE}/orders", json={"items": [{"product_id": "bowl-pollo", "cantidad": 1},
                                                        {"product_id": "snack-energetico", "cantidad": 2}]},
                      headers={**cliente["headers"], "Idempotency-Key": nueva_clave()}).json()

def test_graphql_sin_sesion_da_401():
    r = httpx.post(f"{BASE}/graphql", json={"query": "{ misPedidos { id } }"})
    assert r.status_code == 401

def test_resumen_combina_tres_subsistemas(cliente_a):
    pedido = nuevo_pedido(cliente_a)
    httpx.post(f"{BASE}/payments", json={"order_id": pedido["id"]}, headers=cliente_a["headers"])
    r = graphql(cliente_a, CONSULTA, {"id": pedido["id"]})
    assert r.status_code == 200, r.text
    datos = r.json()["data"]["resumenPedido"]
    assert datos["estado"] == "pendiente_pago"
    assert datos["items"][0]["tag"] is not None
    assert datos["pago"]["monto"] == datos["total"] == 10900

def test_mis_pedidos_trae_solo_los_propios(cliente_a, cliente_b):
    nuevo_pedido(cliente_a)
    r = graphql(cliente_b, "{ misPedidos(limite: 10) { id } }")
    ids_b = [p["id"] for p in r.json()["data"]["misPedidos"]]
    ids_a = [p["id"] for p in graphql(cliente_a, "{ misPedidos(limite: 10) { id } }").json()["data"]["misPedidos"]]
    assert not set(ids_a) & set(ids_b)

def test_resumen_de_pedido_ajeno_no_devuelve_datos(cliente_a, cliente_b):
    pedido = nuevo_pedido(cliente_a)
    r = graphql(cliente_b, CONSULTA, {"id": pedido["id"]})
    cuerpo = r.json()
    assert cuerpo["data"]["resumenPedido"] is None
    assert cuerpo["errors"][0]["message"] == "Pedido no encontrado"

def test_campo_restringido_para_cliente(cliente_a, operador):
    pedido = nuevo_pedido(cliente_a)
    consulta = "query ($id: ID!) { resumenPedido(id: $id) { id clienteId } }"
    r = graphql(cliente_a, consulta, {"id": pedido["id"]})
    assert r.json()["errors"][0]["extensions"]["code"] == "PROHIBIDO"

    r = graphql(operador, consulta, {"id": pedido["id"]})
    assert r.json()["data"]["resumenPedido"]["clienteId"].startswith("USR-")

def test_limite_de_profundidad(cliente_a):
    r = graphql(cliente_a, "{ misPedidos { items { nombre } pago { estado } } }")
    assert r.status_code == 200
    r = graphql(cliente_a, "fragment f on ResumenPedido { items { nombre } } { misPedidos { ...f } }")
    assert r.status_code == 200

    r = graphql(cliente_a, "{ misPedidos { items { nombre { a { b } } } } }")
    assert r.status_code == 400
    assert "profundidad" in r.json()["errors"][0]["message"]

def test_limite_de_alias(cliente_a):
    alias = " ".join(f"a{i}: misPedidos {{ id }}" for i in range(8))
    r = graphql(cliente_a, "{ " + alias + " }")
    assert r.status_code == 400
    assert "alias" in r.json()["errors"][0]["message"]

def test_limite_de_resultados(cliente_a):
    r = graphql(cliente_a, "{ misPedidos(limite: 500) { id } }")
    assert len(r.json()["data"]["misPedidos"]) <= 10

def test_introspeccion_desactivada(cliente_a):
    r = graphql(cliente_a, "{ __schema { types { name } } }")
    assert r.status_code == 400
