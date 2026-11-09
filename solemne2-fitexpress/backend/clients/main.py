import os
import re
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator

from comun.db import conectar, inicializar
from comun.seguridad import (exigir_llave, identidad, exigir_rol, leer_secretos,
                             llamar_servicio, agregar_logs)

CARPETA = os.path.dirname(__file__)
DB = os.path.join(CARPETA, "data", "clients.db")
AUTH_URL = os.getenv("AUTH_URL", "http://127.0.0.1:8100")

app = FastAPI(title="Fit Express - Clients")
agregar_logs(app, "clients")
llave = exigir_llave("clients")

REGEX_EMAIL = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
REGEX_TELEFONO = r"^[0-9+\s]{7,15}$"

class Registro(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    email: str = Field(max_length=120)
    direccion: str = Field(min_length=5, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("email")
    @classmethod
    def validar_email(cls, v):
        if not re.match(REGEX_EMAIL, v):
            raise ValueError("email no valido")
        return v.lower()

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v):
        if v and not re.match(REGEX_TELEFONO, v):
            raise ValueError("telefono no valido")
        return v or None

class PerfilUpdate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    direccion: str = Field(min_length=5, max_length=150)
    telefono: str | None = Field(default=None, max_length=20)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v):
        if v and not re.match(REGEX_TELEFONO, v):
            raise ValueError("telefono no valido")
        return v or None

def perfil_propio(fila):
    return {
        "id": fila["user_id"],
        "nombre": fila["nombre"],
        "email": fila["email"],
        "direccion": fila["direccion"],
        "telefono": fila["telefono"]
    }

@app.on_event("startup")
def iniciar():
    inicializar(DB, os.path.join(CARPETA, "schema.sql"))

@app.get("/health")
def health():
    return {"status": "OK", "service": "clients"}

@app.post("/clients/registro", status_code=201, dependencies=[Depends(llave)])
def registrar(datos: Registro, request: Request):
    con = conectar(DB)
    if con.execute("SELECT 1 FROM perfiles WHERE email = ?", (datos.email,)).fetchone():
        con.close()
        raise HTTPException(status_code=409, detail="Ese email ya esta registrado")

    respuesta = llamar_servicio(
        "POST", f"{AUTH_URL}/internal/usuarios", leer_secretos("clients")["auth_key"],
        request_id=request.headers.get("x-request-id"),
        json={"email": datos.email, "password": datos.password}
    )
    if respuesta.status_code == 409:
        con.close()
        raise HTTPException(status_code=409, detail="Ese email ya esta registrado")
    if respuesta.status_code != 201:
        con.close()
        raise HTTPException(status_code=502, detail="No se pudo crear la cuenta")

    user_id = respuesta.json()["user_id"]
    con.execute(
        "INSERT INTO perfiles VALUES (?,?,?,?,?,?)",
        (user_id, datos.nombre, datos.email, datos.direccion, datos.telefono,
         datetime.now(timezone.utc).isoformat())
    )
    con.commit()
    con.close()

    return {"id": user_id, "nombre": datos.nombre, "email": datos.email}

@app.get("/clients/me", dependencies=[Depends(llave)])
def mi_perfil(request: Request):
    usuario = identidad(request)
    con = conectar(DB)
    fila = con.execute("SELECT * FROM perfiles WHERE user_id = ?", (usuario["user_id"],)).fetchone()
    con.close()
    if fila is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return perfil_propio(fila)

@app.put("/clients/me", dependencies=[Depends(llave)])
def actualizar_perfil(datos: PerfilUpdate, request: Request):
    usuario = identidad(request)
    con = conectar(DB)
    cambio = con.execute(
        "UPDATE perfiles SET nombre = ?, direccion = ?, telefono = ? WHERE user_id = ?",
        (datos.nombre, datos.direccion, datos.telefono, usuario["user_id"])
    )
    con.commit()
    fila = con.execute("SELECT * FROM perfiles WHERE user_id = ?", (usuario["user_id"],)).fetchone()
    con.close()
    if cambio.rowcount == 0:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return perfil_propio(fila)

@app.get("/clients", dependencies=[Depends(llave)])
def listar_clientes(request: Request):
    exigir_rol(identidad(request), "operador")
    con = conectar(DB)
    filas = con.execute("SELECT user_id, nombre, email FROM perfiles ORDER BY creado_en").fetchall()
    con.close()

    return [{"id": f["user_id"], "nombre": f["nombre"], "email": f["email"]} for f in filas]

@app.get("/internal/clients/{user_id}", dependencies=[Depends(llave)])
def datos_entrega(user_id: str):
    con = conectar(DB)
    fila = con.execute("SELECT nombre, direccion FROM perfiles WHERE user_id = ?", (user_id,)).fetchone()
    con.close()
    if fila is None:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")
    return {"nombre": fila["nombre"], "direccion": fila["direccion"]}
