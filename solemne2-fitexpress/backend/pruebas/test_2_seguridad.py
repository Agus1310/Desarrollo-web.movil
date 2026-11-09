import httpx
from conftest import BASE, nueva_clave, registrar_y_entrar

def test_registro_valida_en_el_servidor():
    r = httpx.post(f"{BASE}/auth/registro", json={
        "nombre": "A", "email": "no-es-email", "direccion": "x", "password": "123"
    })
    assert r.status_code == 422

def test_registro_no_devuelve_password_ni_direccion():
    r = httpx.post(f"{BASE}/auth/registro", json={
        "nombre": "Carla Prueba", "email": "carla.unica.123@correo-prueba.cl",
        "direccion": "Los Leones 123, Providencia", "password": "ClavePrueba123"
    })
    assert r.status_code in (201, 409)
    if r.status_code == 201:
        assert set(r.json().keys()) == {"id", "nombre", "email"}

def test_login_con_clave_incorrecta_da_401():
    r = httpx.post(f"{BASE}/auth/login", json={"email": "nadie@correo-prueba.cl", "password": "malaclave1"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Credenciales incorrectas"

def test_operacion_protegida_sin_sesion_da_401():
    r = httpx.post(f"{BASE}/orders", json={"items": [{"product_id": "bowl-pollo", "cantidad": 1}]},
                   headers={"Idempotency-Key": nueva_clave()})
    assert r.status_code == 401

def test_token_inventado_da_401():
    r = httpx.get(f"{BASE}/orders", headers={"Authorization": "Bearer token-inventado"})
    assert r.status_code == 401

def test_cliente_no_puede_administrar_catalogo(cliente_a):
    r = httpx.delete(f"{BASE}/products/bowl-pollo", headers=cliente_a["headers"])
    assert r.status_code == 403
    r = httpx.post(f"{BASE}/products", headers=cliente_a["headers"], json={})
    assert r.status_code == 403

def test_cabeceras_de_identidad_falsas_se_ignoran(cliente_a):
    headers = dict(cliente_a["headers"])
    headers["X-User-Rol"] = "operador"
    headers["X-User-Id"] = "USR-00000000"
    r = httpx.get(f"{BASE}/clients", headers=headers)
    assert r.status_code == 403

def test_acceso_directo_al_backend_sin_llave_da_403():
    for puerto, ruta in [(9001, "/products"), (9002, "/orders"), (9003, "/clients"),
                         (9004, "/internal/payments?order_ids=x"), (8100, "/introspect"), (9005, "/graphql")]:
        metodo = "POST" if ruta in ("/introspect", "/graphql") else "GET"
        r = httpx.request(metodo, f"http://127.0.0.1:{puerto}{ruta}", json={"token": "x", "query": "{x}"},
                          headers={"X-User-Id": "USR-1", "X-User-Rol": "operador"})
        assert r.status_code == 403, (puerto, r.status_code)

def test_acceso_directo_con_llave_falsa_da_403():
    r = httpx.get("http://127.0.0.1:9002/orders",
                  headers={"X-Service-Key": "llave-inventada", "X-User-Id": "USR-1", "X-User-Rol": "operador"})
    assert r.status_code == 403

def test_cliente_ve_su_perfil_completo(cliente_a):
    r = httpx.get(f"{BASE}/clients/me", headers=cliente_a["headers"])
    assert r.status_code == 200
    assert r.json()["email"] == cliente_a["email"]
    assert "password" not in r.json()

def test_listado_de_clientes_del_operador_no_trae_direccion(operador):
    r = httpx.get(f"{BASE}/clients", headers=operador["headers"])
    assert r.status_code == 200
    assert all(set(c.keys()) == {"id", "nombre", "email"} for c in r.json())

def test_logout_revoca_el_token():
    usuario = registrar_y_entrar("luis")
    assert httpx.get(f"{BASE}/clients/me", headers=usuario["headers"]).status_code == 200
    assert httpx.post(f"{BASE}/auth/logout", headers=usuario["headers"]).status_code == 200
    assert httpx.get(f"{BASE}/clients/me", headers=usuario["headers"]).status_code == 401
