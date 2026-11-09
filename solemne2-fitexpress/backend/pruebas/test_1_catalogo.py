import httpx
from conftest import BASE

def test_catalogo_anonimo_devuelve_productos_del_frontend():
    r = httpx.get(f"{BASE}/products")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert {"bowl-pollo", "bowl-vegano", "snack-energetico"} <= ids

def test_catalogo_no_expone_campos_internos():
    producto = httpx.get(f"{BASE}/products").json()[0]
    assert set(producto.keys()) == {"id", "nombre", "tag", "precio", "descripcion", "calorias", "disponible"}
    assert "stock" not in producto

def test_filtro_invalido_da_400():
    r = httpx.get(f"{BASE}/products", params={"disponible": "talvez"})
    assert r.status_code == 400

def test_detalle_incluye_ingredientes():
    r = httpx.get(f"{BASE}/products/bowl-pollo")
    assert r.status_code == 200
    assert "Quinoa" in r.json()["ingredientes"]

def test_detalle_inexistente_da_404():
    assert httpx.get(f"{BASE}/products/no-existe").status_code == 404

def test_ruta_no_publicada_da_404():
    assert httpx.get(f"{BASE}/internal/products", params={"ids": "bowl-pollo"}).status_code == 404
