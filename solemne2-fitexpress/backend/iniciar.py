import os
import sys
import time
import subprocess

import httpx

CARPETA = os.path.dirname(os.path.abspath(__file__))

SERVICIOS = [
    ("auth_service", 8100),
    ("inventory", 9001),
    ("clients", 9003),
    ("orders", 9002),
    ("payments", 9004),
    ("graphql_gateway", 9005),
    ("api_gateway", 8000),
]

def leer_env():
    variables = {}
    ruta = os.path.join(CARPETA, ".env")
    if not os.path.exists(ruta):
        print("Falta el archivo .env. Copia .env.example como .env y completalo.")
        sys.exit(1)
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                variables[clave.strip()] = valor.strip()
    return variables

def main():
    excepto = []
    if "--excepto" in sys.argv:
        excepto = sys.argv[sys.argv.index("--excepto") + 1].split(",")

    entorno = dict(os.environ)
    entorno.update(leer_env())

    try:
        r = httpx.get(entorno.get("VAULT_ADDR", "http://127.0.0.1:8200") + "/v1/sys/health", timeout=3)
        print("Vault OK" if r.status_code == 200 else f"Vault respondio {r.status_code}")
    except httpx.RequestError:
        print("ATENCION: Vault no responde. Levantalo con Docker y corre cargar_secretos.py")

    procesos = []
    for modulo, puerto in SERVICIOS:
        if modulo in excepto:
            print(f"(se omite {modulo})")
            continue
        comando = [sys.executable, "-m", "uvicorn", f"{modulo}.main:app",
                   "--host", "127.0.0.1", "--port", str(puerto), "--log-level", "warning"]
        procesos.append((modulo, subprocess.Popen(comando, cwd=CARPETA, env=entorno)))
        print(f"Iniciando {modulo} en http://127.0.0.1:{puerto}")

    for modulo, puerto in SERVICIOS:
        if modulo in excepto:
            continue
        for _ in range(40):
            try:
                if httpx.get(f"http://127.0.0.1:{puerto}/health", timeout=1).status_code == 200:
                    break
            except httpx.RequestError:
                time.sleep(0.5)

    if "frontend" not in excepto:
        carpeta_front = os.path.join(os.path.dirname(CARPETA), "frontend")
        procesos.append(("frontend", subprocess.Popen(
            [sys.executable, "-m", "http.server", "5500", "--bind", "127.0.0.1", "--directory", carpeta_front],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))

    print("\nBackend listo. Entrada unica: http://127.0.0.1:8000/api/v1/products")
    print("Frontend: http://127.0.0.1:5500")
    print("Ctrl+C para detener.\n")

    try:
        while True:
            time.sleep(1)
            for modulo, p in procesos:
                if p.poll() is not None:
                    print(f"El servicio {modulo} se detuvo (codigo {p.returncode})")
                    raise KeyboardInterrupt
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
        for _, p in procesos:
            p.terminate()
        for _, p in procesos:
            p.wait()

if __name__ == "__main__":
    main()
