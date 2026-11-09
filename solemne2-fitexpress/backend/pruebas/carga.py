import os
import sys
import time
import uuid
import asyncio
import platform
import statistics

import httpx

BASE = "http://127.0.0.1:8000/api/v1"

CATALOGO_TOTAL = 400
CATALOGO_CONCURRENCIA = 20
PEDIDOS_TOTAL = 60
PEDIDOS_CONCURRENCIA = 10
GRAPHQL_TOTAL = 100
GRAPHQL_CONCURRENCIA = 10

def percentil(valores, p):
    valores = sorted(valores)
    k = max(0, int(round(p / 100 * len(valores))) - 1)
    return valores[k]

async def correr(nombre, total, concurrencia, funcion):
    tiempos, errores = [], 0
    semaforo = asyncio.Semaphore(concurrencia)

    async def una(i):
        nonlocal errores
        async with semaforo:
            inicio = time.perf_counter()
            ok = await funcion(i)
            tiempos.append((time.perf_counter() - inicio) * 1000)
            if not ok:
                errores += 1

    inicio_total = time.perf_counter()
    await asyncio.gather(*(una(i) for i in range(total)))
    duracion = time.perf_counter() - inicio_total
    return {
        "escenario": nombre, "solicitudes": total, "concurrencia": concurrencia,
        "duracion_s": round(duracion, 2), "throughput_rps": round(total / duracion, 1),
        "p50_ms": round(statistics.median(tiempos), 1), "p95_ms": round(percentil(tiempos, 95), 1),
        "max_ms": round(max(tiempos), 1), "errores": errores
    }

def medir_recursos():
    try:
        import psutil
    except ImportError:
        return "instala psutil para medir CPU y memoria (pip install psutil)"
    procesos = [p for p in psutil.process_iter(["cmdline"]) if p.info["cmdline"] and "uvicorn" in " ".join(p.info["cmdline"])]
    memoria = sum(p.memory_info().rss for p in procesos) / 1024 / 1024
    cpu = sum(p.cpu_percent(interval=0.2) for p in procesos)
    return f"{len(procesos)} procesos uvicorn | CPU {cpu:.0f}% | memoria {memoria:.0f} MB"

async def main():
    async with httpx.AsyncClient(timeout=15) as client:
        tokens = []
        for i in range(PEDIDOS_CONCURRENCIA):
            email = f"carga.{uuid.uuid4().hex[:6]}@correo-prueba.cl"
            await client.post(f"{BASE}/auth/registro", json={"nombre": "Carga Prueba", "email": email,
                              "direccion": "Av. Carga 100, Santiago", "password": "ClavePrueba123"})
            r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "ClavePrueba123"})
            if r.status_code != 200:
                print("No se pudo preparar usuarios:", r.status_code, r.text)
                sys.exit(1)
            tokens.append({"Authorization": "Bearer " + r.json()["access_token"]})

        async def catalogo(i):
            r = await client.get(f"{BASE}/products")
            return r.status_code == 200

        pedidos_creados = []

        async def pedido(i):
            token = tokens[i % len(tokens)]
            r = await client.post(f"{BASE}/orders", headers={**token, "Idempotency-Key": uuid.uuid4().hex},
                                  json={"items": [{"product_id": "snack-energetico", "cantidad": 1}]})
            if r.status_code == 201:
                pedidos_creados.append((r.json()["id"], token))
            return r.status_code == 201

        async def graphql(i):
            r = await client.post(f"{BASE}/graphql", headers=tokens[i % len(tokens)],
                                  json={"query": "{ misPedidos(limite: 5) { id total items { nombre tag } pago { estado } } }"})
            return r.status_code == 200 and "errors" not in r.json()

        print(f"Equipo: {platform.system()} {platform.machine()} | Python {platform.python_version()}")
        print("Recursos antes:", medir_recursos())
        resultados = [
            await correr("GET /products (anonimo)", CATALOGO_TOTAL, CATALOGO_CONCURRENCIA, catalogo),
            await correr("POST /orders (cliente)", PEDIDOS_TOTAL, PEDIDOS_CONCURRENCIA, pedido),
            await correr("POST /graphql misPedidos", GRAPHQL_TOTAL, GRAPHQL_CONCURRENCIA, graphql),
        ]
        print("Recursos despues:", medir_recursos())

        for pid, token in pedidos_creados:
            await client.patch(f"{BASE}/orders/{pid}/cancelar", headers=token)

    print()
    print(f"{'escenario':28} {'n':>5} {'conc':>5} {'rps':>7} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8} {'errores':>8}")
    for r in resultados:
        print(f"{r['escenario']:28} {r['solicitudes']:>5} {r['concurrencia']:>5} {r['throughput_rps']:>7} "
              f"{r['p50_ms']:>8} {r['p95_ms']:>8} {r['max_ms']:>8} {r['errores']:>8}")

if __name__ == "__main__":
    asyncio.run(main())
