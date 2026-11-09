# Solemne 2 - Backend seguro de Fit Express (Caso 21)

Backend del caso Fit Express hecho con FastAPI, usando los mismos datos del frontend del Taller 1 (menú, pedido y registro). El frontend va en `frontend/`, mejorado (v2) para conectarse al backend: menú desde la API, registro con contraseña, login, confirmación real del pedido, Mis pedidos (GraphQL), pago y un panel simple para el operador.

```
solemne2-fitexpress/
├── frontend/            frontend del Taller 1 mejorado (v2), conectado al gateway
├── backend/
│   ├── api_gateway/     puerta de entrada única (puerto 8000)
│   ├── auth_service/    login, sesiones y contraseñas con hash (8100)
│   ├── inventory/       catálogo, precios y stock (9001)
│   ├── orders/          pedidos y estados (9002)
│   ├── clients/         perfiles de clientes (9003)
│   ├── payments/        pagos y avisos del proveedor (9004)
│   ├── graphql_gateway/ resumen de pedidos con GraphQL (9005)
│   ├── comun/           funciones compartidas (Vault, llaves, logs, SQLite)
│   ├── pruebas/         pruebas automáticas, proveedor de pagos simulado y prueba de carga
│   ├── iniciar.py       levanta todos los servicios
│   └── cargar_secretos.py  genera las llaves y las guarda en Vault
└── docs/                informe, diagramas (.puml editables + .png) y evidencias
```

Cada servicio tiene su propia base SQLite (`<servicio>/data/*.db`), que se crea sola con su `schema.sql` la primera vez. Solo el gateway se usa desde afuera; los demás servicios rechazan con 403 cualquier llamada que no traiga su llave interna.

## Cómo levantarlo (Windows / PowerShell)

1. Levantar Vault con Docker (modo desarrollo):

```
docker run --name vault-dev -p 8200:8200 -e VAULT_DEV_ROOT_TOKEN_ID=elige-un-token -d hashicorp/vault
```

Si el contenedor ya existe: `docker start vault-dev`.

2. Preparar el backend:

```
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Editar `.env` y poner el token de Vault y una clave para el operador.

3. Cargar los secretos en Vault (hay que repetirlo cada vez que se reinicia Vault, porque en modo dev parte vacío):

```
python cargar_secretos.py
```

4. Levantar todo:

```
python iniciar.py
```

Abrir el frontend en **http://127.0.0.1:5500** (`iniciar.py` también lo sirve; hay que usar esa dirección y no abrir el index.html con doble clic, porque el gateway solo acepta ese origen). Para entrar como operador se usan el `ADMIN_EMAIL` y `ADMIN_PASSWORD` del `.env`.

Para detener: `Ctrl+C`. La API es `http://127.0.0.1:8000/api/v1/...` y el health check está en `http://127.0.0.1:8000/health`.

Para probar un pago desde el frontend: apretar Pagar, copiar la referencia `PRV-...` y el monto que aparecen en el aviso, y simular la respuesta del proveedor:

```
python pruebas/proveedor_simulado.py PRV-xxxxxxxx 15000 aprobado
```

Luego apretar Actualizar en Mis pedidos.

## Pruebas

Con el backend corriendo, en otra terminal (dentro de `backend` y con el venv activado):

```
python -m pytest pruebas -v
```

La última prueba bloquea el login por un minuto (prueba el límite de intentos), así que hay que esperar un minuto antes de volver a correr todo.

Pruebas con servicios caídos:

```
python iniciar.py --excepto inventory
$env:CAIDA="inventory"; python -m pytest pruebas/test_6_caidas.py -v

python iniciar.py --excepto payments
$env:CAIDA="payments"; python -m pytest pruebas/test_6_caidas.py -v
```

Prueba de carga: subir `LIMITE_POR_MINUTO=100000` y `LIMITE_LOGIN_POR_MINUTO=1000` en el `.env`, reiniciar y correr `python pruebas/carga.py` (después dejar los límites como estaban).

Rotación de llaves: `python cargar_secretos.py --rotar` (los servicios toman las llaves nuevas en máximo 60 segundos, sin tocar código).

## Rutas principales

| Verbo | Ruta | Acceso |
|---|---|---|
| GET | /api/v1/products, /api/v1/products/{id} | público |
| POST | /api/v1/auth/registro, /api/v1/auth/login | público |
| POST | /api/v1/auth/logout | con sesión |
| GET, PUT | /api/v1/clients/me | con sesión |
| POST | /api/v1/orders (con cabecera Idempotency-Key) | cliente |
| GET | /api/v1/orders, /api/v1/orders/{id} | con sesión (solo los propios) |
| PATCH | /api/v1/orders/{id}/cancelar | con sesión (solo los propios) |
| POST | /api/v1/payments | cliente |
| GET | /api/v1/payments/{id} | con sesión (solo los propios) |
| POST | /api/v1/payments/webhook | proveedor (firma HMAC) |
| POST | /api/v1/graphql | con sesión |
| GET, POST, PUT, PATCH, DELETE | /api/v1/admin/products, /api/v1/products/... , /api/v1/orders/{id}/estado, /api/v1/clients, /api/v1/orders/reporte/diario | operador |

El detalle completo de servicios, permisos, secretos y pruebas está en `docs/Informe_Solemne2_FitExpress.docx`.
