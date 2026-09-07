# graphql-fitexpress

API GraphQL para el registro de usuarios de Fit Express. Hecha con Node.js, Express, Apollo Server y Mongoose (MongoDB).

## Qué tiene

Un modelo Usuario (nombre, email, pass) con las operaciones básicas: listar usuarios, buscar por id, crear, actualizar y eliminar.

## Cómo correrlo

1. `npm install`
2. Crear un `.env` en la raíz con tu conexión de Mongo:
   MONGO_URI=tu_cadena_de_atlas
3. `npm start`
4. Entrar a `http://localhost:4000/graphql` y probar las queries/mutations.
