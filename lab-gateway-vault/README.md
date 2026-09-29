# Lab Gateway seguro con Vault - Fit Express

Este es el laboratorio de la guia sobre API Gateway seguro, usando Vault para manejar los secretos. Se simulan dos hosts con dos puertos distintos en la misma maquina.

## Como esta armado

- api-gateway (puerto 8000): es la unica puerta de entrada. El cliente le manda un Bearer token, el gateway valida ese token contra lo que tiene guardado Vault, y si esta bien reenvia la peticion al backend agregando un header secreto que tambien saca de Vault.
- backend-api (puerto 9000): tiene los datos reales. Solo responde si la peticion viene con el header secreto correcto, si alguien intenta entrar directo sin pasar por el gateway le tira 403.
- Vault (puerto 8200, corriendo en Docker modo dev): tiene guardados dos secretos en secret/gateway: el token que usa el cliente y el secreto que usa el gateway para hablar con el backend.

El gateway le pregunta a Vault cada vez que llega una peticion, no se guarda los secretos en ningun lado fijo, por eso si se cambia el token en Vault el gateway ya usa el nuevo sin tener que tocar nada del codigo.

## Como levantarlo

1. Levantar Vault: docker run --name vault-dev -p 8200:8200 -e VAULT_DEV_ROOT_TOKEN_ID=dev-only-token -d hashicorp/vault

2. Cargar los secretos en Vault: docker exec -e VAULT_ADDR=http://127.0.0.1:8200 -e VAULT_TOKEN=dev-only-token vault-dev vault kv put secret/gateway client_token="student-token-123" backend_shared_secret="gateway-api-secret-456"

3. Backend api (carpeta backend-api, con su venv y requirements instalados): uvicorn backend_api:app --host 0.0.0.0 --port 9000

4. Gateway (carpeta api-gateway, con su venv y requirements instalados): uvicorn gateway:app --host 0.0.0.0 --port 8000

Las variables de entorno de cada uno estan en su .env.example.

## Pruebas que se hicieron

- Sin token: 401
- Token malo: 401
- Token bueno: 200, devuelve los productos
- Entrar directo al backend sin pasar por el gateway: 403
- Vault apagado: 500
- Backend apagado: 502
- Cambiar el token en Vault sin tocar codigo: el token viejo deja de servir y el nuevo funciona al toque

Todo probado con curl desde PowerShell.
