const express = require("express");
const axios = require("axios");
const app = express();
app.use(express.json());


const API_CLASES_URL = "http://localhost:3001";


app.get("/api/clases", async (req, res) => {
    try {
        const respuesta = await axios.get(`${API_CLASES_URL}/clases`);
        res.json(respuesta.data);
    } catch (err) {
        res.status(502).json({ error: "No se pudo contactar la API de clases" });
    }
});

app.get("/api/clases/:id", async (req, res) => {
    try {
        const respuesta = await axios.get(`${API_CLASES_URL}/clases/${req.params.id}`);
        res.json(respuesta.data);
    } catch (err) {
        if (err.response) return res.status(err.response.status).json(err.response.data);
        res.status(502).json({ error: "No se pudo contactar la API de clases" });
    }
});

app.post("/api/clases", async (req, res) => {
    try {
        const respuesta = await axios.post(`${API_CLASES_URL}/clases`, req.body);
        res.status(201).json(respuesta.data);
    } catch (err) {
        if (err.response) return res.status(err.response.status).json(err.response.data);
        res.status(502).json({ error: "No se pudo contactar la API de clases" });
    }
});

app.put("/api/clases/:id", async (req, res) => {
    try {
        const respuesta = await axios.put(`${API_CLASES_URL}/clases/${req.params.id}`, req.body);
        res.json(respuesta.data);
    } catch (err) {
        if (err.response) return res.status(err.response.status).json(err.response.data);
        res.status(502).json({ error: "No se pudo contactar la API de clases" });
    }
});

app.delete("/api/clases/:id", async (req, res) => {
    try {
        await axios.delete(`${API_CLASES_URL}/clases/${req.params.id}`);
        res.status(204).send();
    } catch (err) {
        if (err.response) return res.status(err.response.status).json(err.response.data);
        res.status(502).json({ error: "No se pudo contactar la API de clases" });
    }
});

app.listen(3000, () => {
    console.log("API Gateway corriendo en http://localhost:3000");
});
