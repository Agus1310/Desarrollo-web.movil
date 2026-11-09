import os
import sys
import secrets

import httpx

from iniciar import leer_env

env = leer_env()
VAULT_ADDR = env.get("VAULT_ADDR", "http://127.0.0.1:8200")
VAULT_TOKEN = env.get("VAULT_TOKEN")
HEADERS = {"X-Vault-Token": VAULT_TOKEN}

def leer(nombre):
    try:
        r = httpx.get(f"{VAULT_ADDR}/v1/secret/data/fitexpress/{nombre}", headers=HEADERS, timeout=5)
    except httpx.RequestError:
        print(f"No se pudo conectar a Vault en {VAULT_ADDR}. Revisa que el contenedor este corriendo (docker start vault-dev).")
        sys.exit(1)
    if r.status_code == 403:
        print("Vault rechazo el token. Revisa VAULT_TOKEN en el .env.")
        sys.exit(1)
    return r.json()["data"]["data"] if r.status_code == 200 else None

def escribir(nombre, datos):
    r = httpx.post(f"{VAULT_ADDR}/v1/secret/data/fitexpress/{nombre}", headers=HEADERS,
                   json={"data": datos}, timeout=5)
    r.raise_for_status()

def main():
    rotar = "--rotar" in sys.argv
    actual = None if rotar else leer("gateway")

    if actual:
        llaves = {k: v for k, v in actual.items()}
        pagos = leer("payments") or {}
        llaves["provider_webhook_secret"] = pagos.get("provider_webhook_secret", secrets.token_urlsafe(32))
        print("Los secretos ya existian, se vuelven a escribir con los mismos valores.")
    else:
        llaves = {
            "auth_key": secrets.token_urlsafe(32),
            "inventory_key": secrets.token_urlsafe(32),
            "orders_key": secrets.token_urlsafe(32),
            "clients_key": secrets.token_urlsafe(32),
            "payments_key": secrets.token_urlsafe(32),
            "graphql_key": secrets.token_urlsafe(32),
            "provider_webhook_secret": secrets.token_urlsafe(32),
        }

    rutas = {
        "gateway": ["auth_key", "inventory_key", "orders_key", "clients_key", "payments_key", "graphql_key"],
        "auth": ["auth_key"],
        "inventory": ["inventory_key"],
        "clients": ["clients_key", "auth_key"],
        "orders": ["orders_key", "inventory_key", "clients_key"],
        "payments": ["payments_key", "orders_key", "provider_webhook_secret"],
        "graphql": ["graphql_key", "orders_key", "inventory_key", "payments_key"],

        "proveedor-simulado": ["provider_webhook_secret"],
    }

    try:
        for nombre, lista in rutas.items():
            escribir(nombre, {k: llaves[k] for k in lista})
            print(f"  secret/fitexpress/{nombre}: {', '.join(lista)}")
    except httpx.HTTPError as e:
        print("No se pudo escribir en Vault:", e)
        sys.exit(1)

    print("\nListo. Los valores no se muestran a proposito.")
    if rotar:
        print("Llaves rotadas: los servicios las toman solas en maximo 60 segundos.")

if __name__ == "__main__":
    main()
