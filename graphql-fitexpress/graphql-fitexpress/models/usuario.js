const mongoose = require("mongoose");

const usuarioSchema = new mongoose.Schema({
    nombre: String,
    email: String,
    pass: String
});

module.exports = mongoose.model("Usuario", usuarioSchema);
