import os
import sys
import hmac
import json
import uuid
import hashlib

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from iniciar import leer_env

GATEWAY = "http://127.0.0.1:8000/api/v1"

def secreto_proveedor():
    env = leer_env()
    r = httpx.get(f"{env['VAULT_ADDR']}/v1/secret/data/fitexpress/proveedor-simulado",
                  headers={"X-Vault-Token": env["VAULT_TOKEN"]}, timeout=5)
    r.raise_for_status()
    return r.json()["data"]["data"]["provider_webhook_secret"]

def firmar(cuerpo, secreto):
    return hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()

def enviar_aviso(provider_ref, monto, estado="aprobado", event_id=None, secreto=None):
    aviso = {
        "event_id": event_id or "EVT-" + uuid.uuid4().hex[:10],
        "provider_ref": provider_ref,
        "estado": estado,
        "monto": monto
    }
    cuerpo = json.dumps(aviso).encode()
    firma = firmar(cuerpo, secreto or secreto_proveedor())
    return httpx.post(f"{GATEWAY}/payments/webhook", content=cuerpo, timeout=10,
                      headers={"Content-Type": "application/json", "X-Proveedor-Firma": firma})

if __name__ == "__main__":
    ref, monto, estado = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    r = enviar_aviso(ref, monto, estado)
    print(r.status_code, r.text)
