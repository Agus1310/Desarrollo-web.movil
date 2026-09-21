const productos = [
    {
        id: "bowl-pollo",
        nombre: "Bowl de Pollo",
        tag: "Alto en proteína",
        precio: 5900,
        descripcion: "Pollo a la plancha, quinoa, palta y verduras salteadas.",
        ingredientes: ["Pechuga de pollo", "Quinoa", "Palta", "Zanahoria", "Brócoli"],
        calorias: 520
    },
    {
        id: "bowl-vegano",
        nombre: "Bowl Vegano",
        tag: "Vegano",
        precio: 5500,
        descripcion: "Garbanzos especiados, tofu grillado y espinaca fresca.",
        ingredientes: ["Garbanzos", "Tofu", "Espinaca", "Quinoa", "Limón"],
        calorias: 470
    },
    {
        id: "snack-energetico",
        nombre: "Snack Energético",
        tag: "Para llevar",
        precio: 2500,
        descripcion: "Mix de frutos secos, avena y miel, ideal antes de entrenar.",
        ingredientes: ["Avena", "Almendras", "Pasas", "Miel"],
        calorias: 310
    },
    {
        id: "bowl-vegetariano",
        nombre: "Bowl Vegetariano",
        tag: "Vegetariano",
        precio: 5300,
        descripcion: "Huevo pochado, batata asada, kale y semillas de zapallo.",
        ingredientes: ["Huevo", "Batata", "Kale", "Semillas de zapallo"],
        calorias: 480
    },
    {
        id: "batido-proteico",
        nombre: "Batido Proteico",
        tag: "Post-entreno",
        precio: 3200,
        descripcion: "Plátano, proteína en polvo, leche de almendras y avena.",
        ingredientes: ["Plátano", "Proteína en polvo", "Leche de almendras", "Avena"],
        calorias: 340
    },
    {
        id: "ensalada-fit",
        nombre: "Ensalada César Fit",
        tag: "Bajo en calorías",
        precio: 4800,
        descripcion: "Versión liviana de la clásica, con aderezo yogur y pollo grillado.",
        ingredientes: ["Lechuga", "Pollo grillado", "Parmesano", "Aderezo de yogur"],
        calorias: 380
    }
];

let pedido = [];

const menuGrid = document.getElementById("menuGrid");
const detalleSection = document.getElementById("detalle");
const detalleContenido = document.getElementById("detalleContenido");

const pedidoVacio = document.getElementById("pedidoVacio");
const pedidoTabla = document.getElementById("pedidoTabla");
const pedidoBody = document.getElementById("pedidoBody");
const pedidoTotal = document.getElementById("pedidoTotal");
const pedidoAcciones = document.getElementById("pedidoAcciones");
const pedidoConfirmado = document.getElementById("pedidoConfirmado");
const pedidoConfirmadoTexto = document.getElementById("pedidoConfirmadoTexto");
const navCartCount = document.getElementById("navCartCount");

const btnVaciarPedido = document.getElementById("btnVaciarPedido");
const btnConfirmarPedido = document.getElementById("btnConfirmarPedido");

const navToggle = document.getElementById("navToggle");
const mainNav = document.getElementById("mainNav");

const formRegistro = document.getElementById("formRegistro");
const registroConfirmado = document.getElementById("registroConfirmado");
const btnNuevoRegistro = document.getElementById("btnNuevoRegistro");

function formatearPrecio(numero) {
    return "$" + numero.toLocaleString("es-CL");
}

function buscarProducto(id) {
    return productos.find(p => p.id === id);
}

function renderizarMenu() {
    menuGrid.innerHTML = "";

    productos.forEach(producto => {
        const card = document.createElement("article");
        card.className = "menu-card";

        card.innerHTML = `
            <img src="images/${producto.id}.jpg" alt="${producto.nombre}" class="menu-img" loading="lazy">
            <span class="tag">${producto.tag}</span>
            <h3>${producto.nombre}</h3>
            <p>${producto.descripcion}</p>
            <span class="precio">${formatearPrecio(producto.precio)}</span>
            <div class="acciones">
                <button type="button" class="btn-chip" data-ver-detalle="${producto.id}">Ver detalle</button>
                <button type="button" class="btn btn-primary" data-agregar="${producto.id}">Agregar</button>
            </div>
        `;

        menuGrid.appendChild(card);
    });
}

function mostrarDetalle(id) {
    const producto = buscarProducto(id);
    if (!producto) return;

    detalleContenido.innerHTML = `
        <img src="images/${producto.id}.jpg" alt="${producto.nombre}" class="detalle-img" loading="lazy">
        <span class="tag">${producto.tag}</span>
        <h3>${producto.nombre}</h3>
        <p>${producto.descripcion}</p>
        <p><strong>${producto.calorias} kcal</strong> aproximadas por porción</p>
        <ul>
            ${producto.ingredientes.map(ing => `<li>${ing}</li>`).join("")}
        </ul>
        <p class="precio">${formatearPrecio(producto.precio)}</p>
        <button type="button" class="btn btn-primary" data-agregar="${producto.id}">Agregar al pedido</button>
    `;

    detalleSection.hidden = false;
    detalleSection.scrollIntoView({ behavior: "smooth" });
}

function agregarAlPedido(id) {
    const item = pedido.find(p => p.id === id);
    if (item) {
        item.cantidad += 1;
    } else {
        pedido.push({ id, cantidad: 1 });
    }
    pedidoConfirmado.hidden = true;
    renderizarPedido();
}

function quitarDelPedido(id) {
    pedido = pedido.filter(p => p.id !== id);
    renderizarPedido();
}

function vaciarPedido() {
    pedido = [];
    renderizarPedido();
}

function renderizarPedido() {
    const totalItems = pedido.reduce((acc, item) => acc + item.cantidad, 0);
    navCartCount.textContent = totalItems;

    if (pedido.length === 0) {
        pedidoVacio.hidden = false;
        pedidoTabla.hidden = true;
        pedidoAcciones.hidden = true;
        return;
    }

    pedidoVacio.hidden = true;
    pedidoTabla.hidden = false;
    pedidoAcciones.hidden = false;

    pedidoBody.innerHTML = "";
    let total = 0;

    pedido.forEach(item => {
        const producto = buscarProducto(item.id);
        const subtotal = producto.precio * item.cantidad;
        total += subtotal;

        const fila = document.createElement("tr");
        fila.innerHTML = `
            <td>${producto.nombre}</td>
            <td>${item.cantidad}</td>
            <td>${formatearPrecio(subtotal)}</td>
            <td><button type="button" class="btn-quitar" data-quitar="${item.id}">Quitar</button></td>
        `;
        pedidoBody.appendChild(fila);
    });

    pedidoTotal.textContent = formatearPrecio(total);
}

function confirmarPedido() {
    if (pedido.length === 0) return;

    const totalItems = pedido.reduce((acc, item) => acc + item.cantidad, 0);
    pedidoConfirmadoTexto.textContent =
        `Recibimos tu pedido con ${totalItems} preparación(es). Te va a llegar en unos 25 minutos.`;
    pedidoConfirmado.hidden = false;

    vaciarPedido();
}

document.addEventListener("click", (evento) => {
    const botonAgregar = evento.target.closest("[data-agregar]");
    if (botonAgregar) {
        agregarAlPedido(botonAgregar.dataset.agregar);
        return;
    }

    const botonDetalle = evento.target.closest("[data-ver-detalle]");
    if (botonDetalle) {
        mostrarDetalle(botonDetalle.dataset.verDetalle);
        return;
    }

    const botonQuitar = evento.target.closest("[data-quitar]");
    if (botonQuitar) {
        quitarDelPedido(botonQuitar.dataset.quitar);
        return;
    }
});

btnVaciarPedido.addEventListener("click", vaciarPedido);
btnConfirmarPedido.addEventListener("click", confirmarPedido);

navToggle.addEventListener("click", () => {
    const abierto = mainNav.classList.toggle("abierto");
    navToggle.setAttribute("aria-expanded", abierto);
});

mainNav.addEventListener("click", (evento) => {
    if (evento.target.tagName === "A") {
        mainNav.classList.remove("abierto");
        navToggle.setAttribute("aria-expanded", "false");
    }
});

function mostrarError(inputId, errorId, mensaje) {
    document.getElementById(inputId).classList.toggle("invalido", Boolean(mensaje));
    document.getElementById(errorId).textContent = mensaje || "";
}

function validarRegistro() {
    let esValido = true;

    const nombre = document.getElementById("nombre").value.trim();
    const email = document.getElementById("email").value.trim();
    const direccion = document.getElementById("direccion").value.trim();
    const telefono = document.getElementById("telefono").value.trim();

    if (nombre.length < 2) {
        mostrarError("nombre", "errorNombre", "Ingresá tu nombre completo.");
        esValido = false;
    } else {
        mostrarError("nombre", "errorNombre", "");
    }

    const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!regexEmail.test(email)) {
        mostrarError("email", "errorEmail", "Ingresá un email válido.");
        esValido = false;
    } else {
        mostrarError("email", "errorEmail", "");
    }

    if (direccion.length < 5) {
        mostrarError("direccion", "errorDireccion", "Ingresá una dirección de entrega.");
        esValido = false;
    } else {
        mostrarError("direccion", "errorDireccion", "");
    }

    const regexTelefono = /^[0-9+\s]{7,15}$/;
    if (telefono !== "" && !regexTelefono.test(telefono)) {
        mostrarError("telefono", "errorTelefono", "Revisá el formato del teléfono.");
        esValido = false;
    } else {
        mostrarError("telefono", "errorTelefono", "");
    }

    return { esValido, nombre, email, direccion };
}

formRegistro.addEventListener("submit", (evento) => {
    evento.preventDefault();

    const { esValido, nombre, email, direccion } = validarRegistro();
    if (!esValido) return;

    document.getElementById("registroNombre").textContent = nombre;
    document.getElementById("registroEmail").textContent = email;
    document.getElementById("registroDireccion").textContent = direccion;

    formRegistro.hidden = true;
    registroConfirmado.hidden = false;
});

btnNuevoRegistro.addEventListener("click", () => {
    formRegistro.reset();
    ["nombre", "email", "direccion", "telefono"].forEach(id =>
        mostrarError(id, "error" + id.charAt(0).toUpperCase() + id.slice(1), "")
    );
    registroConfirmado.hidden = true;
    formRegistro.hidden = false;
});

renderizarMenu();
renderizarPedido();
