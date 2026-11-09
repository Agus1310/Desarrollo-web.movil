import os

import httpx
import pytest
from conftest import BASE

@pytest.mark.skipif(bool(os.getenv("CAIDA")), reason="no aplica en pruebas de caidas")
def test_muchos_intentos_de_login_dan_429():
    codigos = [httpx.post(f"{BASE}/auth/login", json={"email": "fuerza@bruta.cl", "password": "intento123"}).status_code
               for _ in range(25)]
    assert 401 in codigos
    assert codigos[-1] == 429
