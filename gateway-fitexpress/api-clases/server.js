const express = require("express");
const app = express();
app.use(express.json());

// Datos en memoria (se pierden al reiniciar el servidor, no hay base de datos)
let clases = [
    { id: 1, nombre: "Spinning", horario: "Lunes 18:00", cupo: 20, instructor: "Marcela" },
    { id: 2, nombre: "Funcional", horario: "Martes 19:00", cupo: 15, instructor: "Diego" },
    { id: 3, nombre: "Yoga", horario: "Miércoles 08:00", cupo: 12, instructor: "Camila" }
];
let siguienteId = 4;

// Listar todas las clases
app.get("/clases", (req, res) => {
    res.json(clases);
});

// Obtener una clase por id
app.get("/clases/:id", (req, res) => {
    const clase = clases.find(c => c.id === Number(req.params.id));
    if (!clase) return res.status(404).json({ error: "Clase no encontrada" });
    res.json(clase);
});

// Crear una clase nueva
app.post("/clases", (req, res) => {
    const { nombre, horario, cupo, instructor } = req.body;
    if (!nombre || !horario) {
        return res.status(400).json({ error: "Nombre y horario son obligatorios" });
    }
    const nuevaClase = { id: siguienteId++, nombre, horario, cupo, instructor };
    clases.push(nuevaClase);
    res.status(201).json(nuevaClase);
});

// Modificar una clase existente
app.put("/clases/:id", (req, res) => {
    const clase = clases.find(c => c.id === Number(req.params.id));
    if (!clase) return res.status(404).json({ error: "Clase no encontrada" });
    const { nombre, horario, cupo, instructor } = req.body;
    if (nombre) clase.nombre = nombre;
    if (horario) clase.horario = horario;
    if (cupo !== undefined) clase.cupo = cupo;
    if (instructor) clase.instructor = instructor;
    res.json(clase);
});

// Eliminar una clase
app.delete("/clases/:id", (req, res) => {
    const existe = clases.some(c => c.id === Number(req.params.id));
    if (!existe) return res.status(404).json({ error: "Clase no encontrada" });
    clases = clases.filter(c => c.id !== Number(req.params.id));
    res.status(204).send();
});

app.listen(3001, () => {
    console.log("API normal (clases) corriendo en http://localhost:3001");
});
