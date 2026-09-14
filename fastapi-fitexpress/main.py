from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from contextlib import asynccontextmanager

MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "bd_fitexpress"
COLL_NAME = "productos"

client: AsyncIOMotorClient = AsyncIOMotorClient(MONGODB_URL)
DB = None
coll = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, DB, coll
    client = AsyncIOMotorClient(MONGODB_URL)
    DB = client[DB_NAME]
    coll = DB[COLL_NAME]
    yield
    client.close()

app = FastAPI(title="Fit Express API", version="1.0.0", lifespan=lifespan)

class Producto(BaseModel):
    nombre: str = Field(min_length=1, description="nombre del producto")
    precio: float = Field(gt=0, description="precio del producto")
    tags: List[str] = Field(default_factory=list)
    activo: bool = True

class ProductoIn(BaseModel):
    nombre: str = Field(min_length=1, description="nombre del producto")
    precio: float = Field(gt=0, description="precio del producto")
    tags: List[str] = Field(default_factory=list)
    activo: bool = True

class ProductoOut(Producto):
    id: str

def doc_to_productoout(doc) -> ProductoOut:
    return ProductoOut(
        id=str(doc["_id"]),
        nombre=doc["nombre"],
        precio=doc["precio"],
        tags=doc.get("tags", []),
        activo=doc.get("activo", True)
    )

# Endpoints

@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}

@app.get("/productos", response_model=List[ProductoOut], tags=["productos"])
async def listar_productos(
        q: Optional[str] = Query(None, description="Filtro por nombre que contenga q"),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200)
):
    query = {}
    if q:
        query["nombre"] = {"$regex": q, "$options": "i"}
    cursor = coll.find(query).skip(skip).limit(limit)
    productos = []
    async for doc in cursor:
        productos.append(doc_to_productoout(doc))
    return productos

@app.post("/productos", response_model=ProductoOut, status_code=201, tags=["productos"])
async def crear_producto(producto: ProductoIn):
    res = await coll.insert_one(producto.model_dump())
    doc = await coll.find_one({"_id": res.inserted_id})
    return doc_to_productoout(doc)

@app.get("/productos/{producto_id}", response_model=ProductoOut, tags=["productos"])
async def obtener_producto(producto_id: str):
    if not ObjectId.is_valid(producto_id):
        raise HTTPException(400, "ID inválido")
    doc = await coll.find_one({"_id": ObjectId(producto_id)})
    if not doc:
        raise HTTPException(404, "Producto no encontrado")
    return doc_to_productoout(doc)

@app.put("/productos/{producto_id}", response_model=ProductoOut, tags=["productos"])
async def actualizar_producto(producto_id: str, producto: ProductoIn):
    if not ObjectId.is_valid(producto_id):
        raise HTTPException(400, "ID inválido")
    res = await coll.update_one({"_id": ObjectId(producto_id)},
                                 {"$set": producto.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(404, "Producto no encontrado")
    doc = await coll.find_one({"_id": ObjectId(producto_id)})
    return doc_to_productoout(doc)

@app.delete("/productos/{producto_id}", status_code=204, tags=["productos"])
async def eliminar_producto(producto_id: str):
    if not ObjectId.is_valid(producto_id):
        raise HTTPException(400, "ID inválido")
    res = await coll.delete_one({"_id": ObjectId(producto_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Producto no encontrado")
    return None
