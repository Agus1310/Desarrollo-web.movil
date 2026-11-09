import os
import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field

from comun.db import conectar, inicializar
from comun.seguridad import exigir_llave, identidad, exigir_rol, agregar_logs

CARPETA = os.path.dirname(__file__)
DB = os.path.join(CARPETA, "data", "inventory.db")

app = FastAPI(title="Fit Express - Inventory")
agregar_logs(app, "inventory")
llave = exigir_llave("inventory")

class ProductoIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    tag: str = Field(min_length=2, max_length=40)
    precio: int = Field(gt=0, le=100000)
    descripcion: str = Field(min_length=5, max_length=300)
    ingredientes: list[str] = Field(min_length=1, max_length=15)
    calorias: int = Field(ge=0, le=3000)
    stock: int = Field(ge=0, le=1000)

class NuevoProducto(ProductoIn):
    id: str = Field(min_length=3, max_length=40, pattern=r"^[a-z0-9-]+$")

class StockIn(BaseModel):
    stock: int = Field(ge=0, le=1000)

class ItemReserva(BaseModel):
    product_id: str = Field(max_length=40)
    cantidad: int = Field(gt=0, le=200)

class ReservaIn(BaseModel):
    order_id: str = Field(max_length=40)
    items: list[ItemReserva] = Field(min_length=1, max_length=20)

def producto_publico(fila, con_detalle=False):
    datos = {
        "id": fila["id"],
        "nombre": fila["nombre"],
        "tag": fila["tag"],
        "precio": fila["precio"],
        "descripcion": fila["descripcion"],
        "calorias": fila["calorias"],
        "disponible": bool(fila["activo"]) and fila["stock"] > 0
    }
    if con_detalle:
        datos["ingredientes"] = json.loads(fila["ingredientes"])
    return datos

@app.on_event("startup")
def iniciar():
    inicializar(DB, os.path.join(CARPETA, "schema.sql"))
    con = conectar(DB)
    hay = con.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    if hay == 0:
        with open(os.path.join(CARPETA, "datos_iniciales.json"), encoding="utf-8") as f:
            for p in json.load(f):
                con.execute(
                    "INSERT INTO productos VALUES (?,?,?,?,?,?,?,?,1)",
                    (p["id"], p["nombre"], p["tag"], p["precio"], p["descripcion"],
                     json.dumps(p["ingredientes"], ensure_ascii=False), p["calorias"], p["stock"])
                )
        con.commit()
    con.close()

@app.get("/health")
def health():
    return {"status": "OK", "service": "inventory"}

@app.get("/products", dependencies=[Depends(llave)])
def listar_productos(disponible: str | None = None, tag: str | None = Query(default=None, max_length=40)):
    if disponible not in (None, "true", "false"):
        raise HTTPException(status_code=400, detail="El filtro disponible debe ser true o false")
    con = conectar(DB)
    filas = con.execute("SELECT * FROM productos WHERE activo = 1 ORDER BY nombre").fetchall()
    con.close()
    productos = [producto_publico(f) for f in filas]
    if disponible is not None:
        productos = [p for p in productos if p["disponible"] == (disponible == "true")]
    if tag:
        productos = [p for p in productos if p["tag"].lower() == tag.lower()]
    return productos

@app.get("/products/{product_id}", dependencies=[Depends(llave)])
def ver_producto(product_id: str):
    con = conectar(DB)
    fila = con.execute("SELECT * FROM productos WHERE id = ? AND activo = 1", (product_id,)).fetchone()
    con.close()
    if fila is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto_publico(fila, con_detalle=True)

@app.get("/admin/products", dependencies=[Depends(llave)])
def listar_admin(request: Request):
    exigir_rol(identidad(request), "operador")
    con = conectar(DB)
    filas = con.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
    con.close()
    return [dict(producto_publico(f, True), stock=f["stock"], activo=bool(f["activo"])) for f in filas]

@app.post("/products", status_code=201, dependencies=[Depends(llave)])
def crear_producto(datos: NuevoProducto, request: Request):
    exigir_rol(identidad(request), "operador")
    con = conectar(DB)
    if con.execute("SELECT id FROM productos WHERE id = ?", (datos.id,)).fetchone():
        con.close()
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese id")
    con.execute(
        "INSERT INTO productos VALUES (?,?,?,?,?,?,?,?,1)",
        (datos.id, datos.nombre, datos.tag, datos.precio, datos.descripcion,
         json.dumps(datos.ingredientes, ensure_ascii=False), datos.calorias, datos.stock)
    )
    con.commit()
    fila = con.execute("SELECT * FROM productos WHERE id = ?", (datos.id,)).fetchone()
    con.close()
    return producto_publico(fila, True)

@app.put("/products/{product_id}", dependencies=[Depends(llave)])
def reemplazar_producto(product_id: str, datos: ProductoIn, request: Request):
    exigir_rol(identidad(request), "operador")
    con = conectar(DB)
    cambio = con.execute(
        """UPDATE productos SET nombre=?, tag=?, precio=?, descripcion=?, ingredientes=?,
           calorias=?, stock=? WHERE id = ? AND activo = 1""",
        (datos.nombre, datos.tag, datos.precio, datos.descripcion,
         json.dumps(datos.ingredientes, ensure_ascii=False), datos.calorias, datos.stock, product_id)
    )
    con.commit()
    if cambio.rowcount == 0:
        con.close()
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    fila = con.execute("SELECT * FROM productos WHERE id = ?", (product_id,)).fetchone()
    con.close()
    return producto_publico(fila, True)

@app.patch("/products/{product_id}/stock", dependencies=[Depends(llave)])
def cambiar_stock(product_id: str, datos: StockIn, request: Request):
    exigir_rol(identidad(request), "operador")
    con = conectar(DB)
    cambio = con.execute("UPDATE productos SET stock = ? WHERE id = ?", (datos.stock, product_id))
    con.commit()
    con.close()
    if cambio.rowcount == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"id": product_id, "stock": datos.stock}

@app.delete("/products/{product_id}", status_code=204, dependencies=[Depends(llave)])
def eliminar_producto(product_id: str, request: Request):
    exigir_rol(identidad(request), "operador")

    con = conectar(DB)
    cambio = con.execute("UPDATE productos SET activo = 0 WHERE id = ? AND activo = 1", (product_id,))
    con.commit()
    con.close()
    if cambio.rowcount == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return None

@app.get("/internal/products", dependencies=[Depends(llave)])
def productos_por_ids(ids: str = Query(max_length=1000)):
    lista = [i for i in ids.split(",") if i][:50]
    if not lista:
        return []
    con = conectar(DB)
    marcas = ",".join("?" * len(lista))
    filas = con.execute(f"SELECT * FROM productos WHERE id IN ({marcas})", lista).fetchall()
    con.close()
    return [dict(producto_publico(f), activo=bool(f["activo"])) for f in filas]

@app.post("/internal/reservas", dependencies=[Depends(llave)])
def reservar_stock(datos: ReservaIn):
    con = conectar(DB)
    try:
        con.execute("BEGIN IMMEDIATE")
        previa = con.execute("SELECT estado FROM reservas WHERE order_id = ?", (datos.order_id,)).fetchone()
        if previa:
            con.rollback()
            return {"order_id": datos.order_id, "estado": previa["estado"], "repetida": True}

        for item in datos.items:
            fila = con.execute(
                "SELECT stock, activo FROM productos WHERE id = ?", (item.product_id,)
            ).fetchone()
            if fila is None or not fila["activo"]:
                raise HTTPException(status_code=404, detail=f"Producto {item.product_id} no existe")
            if fila["stock"] < item.cantidad:
                raise HTTPException(status_code=409, detail=f"No queda stock suficiente de {item.product_id}")
            con.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (item.cantidad, item.product_id))

        con.execute(
            "INSERT INTO reservas VALUES (?,?,?,?)",
            (datos.order_id, json.dumps([i.model_dump() for i in datos.items]), "activa",
             datetime.now(timezone.utc).isoformat())
        )
        con.commit()
    except HTTPException:
        con.rollback()
        raise
    finally:
        con.close()
    return {"order_id": datos.order_id, "estado": "activa", "repetida": False}

@app.post("/internal/reservas/{order_id}/liberar", dependencies=[Depends(llave)])
def liberar_stock(order_id: str):
    con = conectar(DB)
    con.execute("BEGIN IMMEDIATE")
    reserva = con.execute("SELECT * FROM reservas WHERE order_id = ?", (order_id,)).fetchone()
    if reserva is None:
        con.rollback()
        con.close()
        raise HTTPException(status_code=404, detail="No hay reserva para ese pedido")
    if reserva["estado"] == "activa":
        for item in json.loads(reserva["items"]):
            con.execute("UPDATE productos SET stock = stock + ? WHERE id = ?", (item["cantidad"], item["product_id"]))
        con.execute("UPDATE reservas SET estado = 'liberada' WHERE order_id = ?", (order_id,))
    con.commit()
    con.close()
    return {"order_id": order_id, "estado": "liberada"}
