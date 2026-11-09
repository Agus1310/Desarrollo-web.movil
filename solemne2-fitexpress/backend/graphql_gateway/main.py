import os

from fastapi import FastAPI, Depends, Request, Body
from fastapi.responses import JSONResponse
from ariadne import QueryType, ObjectType, make_executable_schema, graphql_sync
from graphql import GraphQLError, parse
from graphql.language import FieldNode, FragmentSpreadNode, FragmentDefinitionNode, OperationDefinitionNode

from comun.seguridad import exigir_llave, identidad, leer_secretos, llamar_servicio, agregar_logs

CARPETA = os.path.dirname(__file__)
ORDERS_URL = os.getenv("ORDERS_URL", "http://127.0.0.1:9002")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://127.0.0.1:9001")
PAYMENTS_URL = os.getenv("PAYMENTS_URL", "http://127.0.0.1:9004")

MAX_LARGO_CONSULTA = 2000
MAX_PROFUNDIDAD = 4
MAX_ALIAS = 5
MAX_PEDIDOS = 10

app = FastAPI(title="Fit Express - GraphQL Gateway")
agregar_logs(app, "graphql")
llave = exigir_llave("graphql")

with open(os.path.join(CARPETA, "schema.graphql"), encoding="utf-8") as f:
    type_defs = f.read()

query = QueryType()
resumen = ObjectType("ResumenPedido")

def traer(contexto, metodo, url, llave_servicio, **kwargs):
    r = llamar_servicio(metodo, url, contexto["secretos"][llave_servicio], contexto["request_id"], **kwargs)
    return r

def enriquecer(contexto, pedidos):
    ids_productos = sorted({i["product_id"] for p in pedidos for i in p["items"]})
    ids_pedidos = [p["id"] for p in pedidos]

    productos = {}
    if ids_productos:
        try:
            r = traer(contexto, "GET", f"{INVENTORY_URL}/internal/products", "inventory_key",
                      params={"ids": ",".join(ids_productos)})
            if r.status_code != 200:
                raise Exception()
        except Exception:
            raise GraphQLError("inventory no disponible, intenta mas tarde",
                               extensions={"code": "SERVICIO_NO_DISPONIBLE"})
        productos = {p["id"]: p for p in r.json()}

    pagos = {}
    error_pagos = False
    try:
        r = traer(contexto, "GET", f"{PAYMENTS_URL}/internal/payments", "payments_key",
                  params={"order_ids": ",".join(ids_pedidos)})
        if r.status_code != 200:
            raise Exception()
        for pago in r.json():
            pagos[pago["order_id"]] = pago
    except Exception:
        error_pagos = True

    resultado = []
    for p in pedidos:
        items = []
        for i in p["items"]:
            info = productos.get(i["product_id"], {})
            items.append({
                "productoId": i["product_id"],
                "nombre": i["nombre"],
                "cantidad": i["cantidad"],
                "precioUnitario": i["precio_unitario"],
                "subtotal": i["subtotal"],
                "tag": info.get("tag"),
                "calorias": info.get("calorias"),
                "disponibleHoy": info.get("disponible") if info.get("activo", False) else False
            })
        resultado.append({
            "id": p["id"],
            "estado": p["estado"],
            "total": p["total"],
            "creadoEn": p["creado_en"],
            "direccionEntrega": p["direccion_entrega"],
            "_clienteId": p["user_id"],
            "items": items,
            "_pago": "ERROR" if error_pagos else pagos.get(p["id"])
        })
    return resultado

@query.field("misPedidos")
def resolver_mis_pedidos(_, info, limite=5):
    contexto = info.context
    limite = max(1, min(limite, MAX_PEDIDOS))
    r = traer(contexto, "GET", f"{ORDERS_URL}/internal/orders", "orders_key",
              params={"user_id": contexto["usuario"]["user_id"], "limite": limite})
    if r.status_code != 200:
        raise GraphQLError("orders no disponible", extensions={"code": "SERVICIO_NO_DISPONIBLE"})
    return enriquecer(contexto, r.json())

@query.field("resumenPedido")
def resolver_resumen(_, info, id):
    contexto = info.context
    usuario = contexto["usuario"]
    r = traer(contexto, "GET", f"{ORDERS_URL}/internal/orders/{id}", "orders_key")
    if r.status_code == 404:
        raise GraphQLError("Pedido no encontrado", extensions={"code": "NO_ENCONTRADO"})
    if r.status_code != 200:
        raise GraphQLError("orders no disponible", extensions={"code": "SERVICIO_NO_DISPONIBLE"})
    pedido = r.json()

    if usuario["rol"] != "operador" and pedido["user_id"] != usuario["user_id"]:
        raise GraphQLError("Pedido no encontrado", extensions={"code": "NO_ENCONTRADO"})
    return enriquecer(contexto, [pedido])[0]

@resumen.field("clienteId")
def resolver_cliente_id(obj, info):
    if info.context["usuario"]["rol"] != "operador":
        raise GraphQLError("No tienes permiso para ver este campo", extensions={"code": "PROHIBIDO"})
    return obj["_clienteId"]

@resumen.field("pago")
def resolver_pago(obj, info):
    if obj["_pago"] == "ERROR":
        raise GraphQLError("payments no disponible, no se pudo leer el estado del pago",
                           extensions={"code": "DATO_PARCIAL"})
    return obj["_pago"]

schema = make_executable_schema(type_defs, query, resumen)

def medir_consulta(documento):
    fragmentos = {d.name.value: d for d in documento.definitions if isinstance(d, FragmentDefinitionNode)}
    alias = 0

    def profundidad(nodo, nivel, visitados):
        nonlocal alias
        if nodo.selection_set is None:
            return nivel
        maximo = nivel
        for sel in nodo.selection_set.selections:
            if isinstance(sel, FieldNode):
                if sel.alias:
                    alias += 1
                maximo = max(maximo, profundidad(sel, nivel + 1, visitados))
            elif isinstance(sel, FragmentSpreadNode):
                nombre = sel.name.value
                if nombre in visitados or nombre not in fragmentos:
                    continue
                maximo = max(maximo, profundidad(fragmentos[nombre], nivel, visitados | {nombre}))
            else:
                maximo = max(maximo, profundidad(sel, nivel, visitados))
        return maximo

    nivel_max = 0
    for d in documento.definitions:
        if isinstance(d, OperationDefinitionNode):
            nivel_max = max(nivel_max, profundidad(d, 0, set()))
    return nivel_max, alias

def error_consulta(mensaje):
    return JSONResponse(status_code=400, content={"errors": [{"message": mensaje}]})

@app.get("/health")
def health():
    return {"status": "OK", "service": "graphql"}

@app.post("/graphql", dependencies=[Depends(llave)])
def endpoint_graphql(request: Request, datos: dict = Body(...)):
    usuario = identidad(request)
    consulta = datos.get("query")
    if not isinstance(consulta, str):
        return error_consulta("Falta la consulta")
    if len(consulta) > MAX_LARGO_CONSULTA:
        return error_consulta("La consulta es demasiado larga")
    try:
        nivel, alias = medir_consulta(parse(consulta))
    except Exception:
        return error_consulta("La consulta no es valida")
    if nivel > MAX_PROFUNDIDAD:
        return error_consulta(f"La consulta supera la profundidad maxima ({MAX_PROFUNDIDAD})")
    if alias > MAX_ALIAS:
        return error_consulta(f"La consulta supera el maximo de alias ({MAX_ALIAS})")

    contexto = {
        "usuario": usuario,
        "secretos": leer_secretos("graphql"),
        "request_id": request.headers.get("x-request-id")
    }
    exito, resultado = graphql_sync(
        schema, datos, context_value=contexto,
        introspection=os.getenv("GRAPHQL_INTROSPECCION", "false") == "true"
    )
    return JSONResponse(status_code=200 if exito else 400, content=resultado)
