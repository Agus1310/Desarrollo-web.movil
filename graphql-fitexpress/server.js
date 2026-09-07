require("dotenv").config();
const express = require("express");
const cors = require("cors");
const mongoose = require("mongoose");
const { ApolloServer, gql } = require("apollo-server-express");
const Usuario = require("./models/usuario");

const MONGO_URI = process.env.MONGO_URI || "mongodb://localhost:27017/fitexpress";

mongoose.connect(MONGO_URI)
    .then(() => console.log("Conectado a MongoDB"))
    .catch((err) => console.log(err));

const typeDefs = gql`
    type Usuario {
        id: ID
        nombre: String
        email: String
    }

    input UsuarioInput {
        nombre: String
        email: String
        pass: String
    }

    type Alert {
        message: String
    }

    type Query {
        getUsuarios: [Usuario]
        getUsuariosById(id: ID!): Usuario
    }

    type Mutation {
        addUsuario(input: UsuarioInput): Usuario
        updUsuario(id: ID!, input: UsuarioInput): Usuario
        delUsuario(id: ID!): Alert
    }
`;

const resolvers = {
    Query: {
        getUsuarios: async () => {
            const usuarios = await Usuario.find();
            return usuarios;
        },
        getUsuariosById: async (_, { id }) => {
            const usuario = await Usuario.findById(id);
            return usuario;
        }
    },
    Mutation: {
        addUsuario: async (_, { input }) => {
            const nuevoUsuario = new Usuario(input);
            await nuevoUsuario.save();
            return nuevoUsuario;
        },
        updUsuario: async (_, { id, input }) => {
            const usuario = await Usuario.findByIdAndUpdate(id, input, { new: true });
            return usuario;
        },
        delUsuario: async (_, { id }) => {
            await Usuario.findByIdAndDelete(id);
            return { message: "Usuario eliminado" };
        }
    }
};

async function iniciar() {
    const app = express();
    app.use(cors());

    const server = new ApolloServer({ typeDefs, resolvers });
    await server.start();
    server.applyMiddleware({ app });

    app.listen(4000, () => {
        console.log("Graphql Iniciado en http://localhost:4000" + server.graphqlPath);
    });
}

iniciar();
