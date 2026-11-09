import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from comun.db import conectar, inicializar
from comun.seguridad import exigir_llave, agregar_logs

CARPETA = os.path.dirname(__file__)
DB = os.path.join(CARPETA, "data", "auth.db")
MINUTOS_SESION = 30
ITERACIONES = 200_000

app = FastAPI(title="Fit Express - Auth Service")
agregar_logs(app, "auth")
llave = exigir_llave("auth")

class NuevoUsuario(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    rol: str = "cliente"

class Login(BaseModel):
    email: str = Field(max_length=120)
    password: str = Field(max_length=72)

class TokenIn(BaseModel):
    token: str = Field(max_length=200)

def ahora():
    return datetime.now(timezone.utc)

def hashear(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERACIONES).hex()

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()

def crear_usuario(con, email, password, rol):
    salt = secrets.token_hex(16)
    user_id = "USR-" + uuid.uuid4().hex[:8]
    con.execute(
        "INSERT INTO usuarios (id, email, password_hash, salt, rol, creado_en) VALUES (?,?,?,?,?,?)",
        (user_id, email.lower(), hashear(password, salt), salt, rol, ahora().isoformat())
    )
    return user_id

@app.on_event("startup")
def iniciar():
    inicializar(DB, os.path.join(CARPETA, "schema.sql"))

    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if email and password:
        con = conectar(DB)
        existe = con.execute("SELECT id FROM usuarios WHERE email = ?", (email.lower(),)).fetchone()
        if not existe:
            crear_usuario(con, email, password, "operador")
            con.commit()
        con.close()

@app.get("/health")
def health():
    return {"status": "OK", "service": "auth"}

@app.post("/internal/usuarios", status_code=201, dependencies=[Depends(llave)])
def registrar_credencial(datos: NuevoUsuario):
    if datos.rol != "cliente":
        raise HTTPException(status_code=403, detail="Solo se pueden registrar clientes")
    con = conectar(DB)
    existe = con.execute("SELECT id FROM usuarios WHERE email = ?", (datos.email.lower(),)).fetchone()
    if existe:
        con.close()
        raise HTTPException(status_code=409, detail="Ese email ya esta registrado")
    user_id = crear_usuario(con, datos.email, datos.password, "cliente")
    con.commit()
    con.close()
    return {"user_id": user_id}

@app.post("/login", dependencies=[Depends(llave)])
def login(datos: Login):
    con = conectar(DB)
    usuario = con.execute(
        "SELECT * FROM usuarios WHERE email = ? AND activo = 1", (datos.email.lower(),)
    ).fetchone()

    if usuario is None or not secrets.compare_digest(
        hashear(datos.password, usuario["salt"]), usuario["password_hash"]
    ):
        con.close()
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = secrets.token_urlsafe(32)
    expira = ahora() + timedelta(minutes=MINUTOS_SESION)
    con.execute(
        "INSERT INTO sesiones (token_hash, user_id, expira_en) VALUES (?,?,?)",
        (hash_token(token), usuario["id"], expira.isoformat())
    )
    con.commit()
    con.close()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": MINUTOS_SESION * 60,
        "rol": usuario["rol"]
    }

@app.post("/introspect", dependencies=[Depends(llave)])
def introspect(datos: TokenIn):
    con = conectar(DB)
    fila = con.execute(
        """SELECT s.expira_en, s.revocada, u.id, u.email, u.rol, u.activo
           FROM sesiones s JOIN usuarios u ON u.id = s.user_id
           WHERE s.token_hash = ?""",
        (hash_token(datos.token),)
    ).fetchone()
    con.close()
    if fila is None or fila["revocada"] or not fila["activo"]:
        return {"active": False}
    if datetime.fromisoformat(fila["expira_en"]) < ahora():
        return {"active": False}
    return {"active": True, "user_id": fila["id"], "email": fila["email"], "rol": fila["rol"]}

@app.post("/logout", dependencies=[Depends(llave)])
def logout(datos: TokenIn):
    con = conectar(DB)
    con.execute("UPDATE sesiones SET revocada = 1 WHERE token_hash = ?", (hash_token(datos.token),))
    con.commit()
    con.close()
    return {"message": "Sesion cerrada"}
