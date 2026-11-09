const API = "http://127.0.0.1:8000/api/v1";

let productos = [];
let pedido = [];
let sesion = null;
let claveIdempotencia = null;
let filtroTag = "Todos";
let ultimoPedidoId = null;

const ESTADOS = {
    pendiente_pago: "Pendiente de pago",
    pagado: "Pagado",
    en_preparacion: "En preparación",
    despachado: "En camino",
    entregado: "Entregado",
    cancelado: "Anulado"
};

const SIGUIENTE_ESTADO = {
    pagado: "en_preparacion",
    en_preparacion: "despachado",
    despachado: "entregado"
};

const $ = id => document.getElementById(id);

function esc(texto) {
    const div = document.createElement("div");
    div.textContent = texto == null ? "" : String(texto);
    return div.innerHTML;
}

function formatearPrecio(numero) {
    return "$" + Number(numero).toLocaleString("es-CL");
}

function formatearFecha(iso) {
    return new Date(iso).toLocaleString("es-CL", { dateStyle: "short", timeStyle: "short" });
}

function nuevaClave() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return Date.now() + "-" + Math.random().toString(16).slice(2);
}

let temporizadorAviso = null;
function avisar(mensaje, tipo = "ok") {
    const aviso = $("aviso");
    aviso.textContent = mensaje;
    aviso.className = "aviso " + tipo;
    aviso.hidden = false;
    clearTimeout(temporizadorAviso);
    temporizadorAviso = setTimeout(() => { aviso.hidden = true; }, 4500);
}

async function api(metodo, ruta, cuerpo, headersExtra = {}) {
    const headers = { ...headersExtra };
    if (cuerpo !== undefined) headers["Content-Type"] = "application/json";
    if (sesion) headers["Authorization"] = "Bearer " + sesion.token;

    let respuesta;
    try {
        respuesta = await fetch(API + ruta, {
            method: metodo,
            headers,
            body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined
        });
    } catch (e) {
        throw new Error("No hay conexión con el servidor. Intenta de nuevo en un momento.");
    }

    if (respuesta.status === 204) return null;
    const datos = await respuesta.json().catch(() => ({}));

    if (respuesta.status === 401 && sesion) {
        cerrarSesionLocal();
        throw new Error("Tu sesión expiró, vuelve a entrar.");
    }
    if (!respuesta.ok) {
        const detalle = Array.isArray(datos.detail) ? "Revisa los datos ingresados." : datos.detail;
        throw new Error(detalle || "Ocurrió un error (" + respuesta.status + ")");
    }
    return datos;
}

async function cargarMenu() {
    $("menuEstado").hidden = false;
    $("menuEstado").textContent = "Cargando el menú...";
    try {
        productos = await api("GET", "/products");
        $("menuEstado").hidden = true;
        $("statProductos").textContent = productos.filter(p => p.disponible).length;
        renderizarFiltros();
        renderizarMenu();
        renderizarPedido();
    } catch (error) {
        $("menuEstado").innerHTML = esc(error.message) +
            ' <button type="button" class="btn-chip" id="btnReintentarMenu">Reintentar</button>';
        $("btnReintentarMenu").addEventListener("click", cargarMenu);
    }
}

function buscarProducto(id) {
    return productos.find(p => p.id === id);
}

function renderizarFiltros() {
    const tags = ["Todos", ...new Set(productos.map(p => p.tag))];
    $("filtros").innerHTML = tags.map(tag =>
        `<button type="button" class="btn-chip ${tag === filtroTag ? "activo" : ""}" data-filtro="${esc(tag)}">${esc(tag)}</button>`
    ).join("");
}

function renderizarMenu() {
    const lista = filtroTag === "Todos" ? productos : productos.filter(p => p.tag === filtroTag);
    $("menuGrid").innerHTML = lista.map(p => `
        <article class="menu-card ${p.disponible ? "" : "agotado"}">
            <img src="images/${esc(p.id)}.jpg" alt="${esc(p.nombre)}" class="menu-img" loading="lazy"
                 onerror="this.src='images/hero-fitexpress.jpg'">
            <span class="tag">${esc(p.tag)}</span>
            <h3>${esc(p.nombre)}</h3>
            <p>${esc(p.descripcion)}</p>
            <span class="precio">${formatearPrecio(p.precio)}</span>
            <div class="acciones">
                <button type="button" class="btn-chip" data-ver-detalle="${esc(p.id)}">Ver detalle</button>
                ${p.disponible
                    ? `<button type="button" class="btn btn-primary" data-agregar="${esc(p.id)}">Agregar</button>`
                    : `<span class="etiqueta-agotado">Agotado por hoy</span>`}
            </div>
        </article>
    `).join("");
}

async function mostrarDetalle(id) {
    $("detalle").hidden = false;
    $("detalleContenido").innerHTML = "<p>Cargando...</p>";
    $("detalle").scrollIntoView({ behavior: "smooth" });
    try {
        const p = await api("GET", "/products/" + encodeURIComponent(id));
        $("detalleContenido").innerHTML = `
            <img src="images/${esc(p.id)}.jpg" alt="${esc(p.nombre)}" class="detalle-img" loading="lazy"
                 onerror="this.src='images/hero-fitexpress.jpg'">
            <span class="tag">${esc(p.tag)}</span>
            <h3>${esc(p.nombre)}</h3>
            <p>${esc(p.descripcion)}</p>
            <p><strong>${esc(p.calorias)} kcal</strong> aproximadas por porción</p>
            <ul>${p.ingredientes.map(i => `<li>${esc(i)}</li>`).join("")}</ul>
            <p class="precio">${formatearPrecio(p.precio)}</p>
            ${p.disponible
                ? `<button type="button" class="btn btn-primary" data-agregar="${esc(p.id)}">Agregar al pedido</button>`
                : `<span class="etiqueta-agotado">Agotado por hoy</span>`}
        `;
    } catch (error) {
        $("detalleContenido").innerHTML = `<p class="error">${esc(error.message)}</p>`;
    }
}

function cambioEnCarrito() {
    claveIdempotencia = null;
    $("pedidoConfirmado").hidden = true;
    renderizarPedido();
}

function agregarAlPedido(id) {
    const item = pedido.find(p => p.id === id);
    if (item) {
        if (item.cantidad >= 10) return avisar("Máximo 10 unidades por preparación.", "error");
        item.cantidad += 1;
    } else {
        pedido.push({ id, cantidad: 1 });
    }
    cambioEnCarrito();
    avisar("Agregado a tu pedido");
}

function cambiarCantidad(id, delta) {
    const item = pedido.find(p => p.id === id);
    if (!item) return;
    item.cantidad = Math.min(10, item.cantidad + delta);
    if (item.cantidad <= 0) pedido = pedido.filter(p => p.id !== id);
    cambioEnCarrito();
}

function vaciarPedido() {
    pedido = [];
    cambioEnCarrito();
}

function renderizarPedido() {
    const totalItems = pedido.reduce((acc, item) => acc + item.cantidad, 0);
    $("navCartCount").textContent = totalItems;

    const vacio = pedido.length === 0;
    $("pedidoVacio").hidden = !vacio;
    $("pedidoTabla").hidden = vacio;
    $("pedidoAcciones").hidden = vacio;
    if (vacio) return;

    let total = 0;
    $("pedidoBody").innerHTML = pedido.map(item => {
        const producto = buscarProducto(item.id);
        if (!producto) return "";
        const subtotal = producto.precio * item.cantidad;
        total += subtotal;
        return `
            <tr>
                <td>${esc(producto.nombre)}</td>
                <td class="cantidad">
                    <button type="button" class="btn-cantidad" data-menos="${esc(item.id)}" aria-label="Quitar uno">−</button>
                    <span>${item.cantidad}</span>
                    <button type="button" class="btn-cantidad" data-mas="${esc(item.id)}" aria-label="Agregar uno">+</button>
                </td>
                <td>${formatearPrecio(subtotal)}</td>
                <td><button type="button" class="btn-quitar" data-quitar="${esc(item.id)}">Quitar</button></td>
            </tr>`;
    }).join("");
    $("pedidoTotal").textContent = formatearPrecio(total);
}

async function confirmarPedido() {
    if (pedido.length === 0) return;
    if (!sesion) {
        avisar("Entra a tu cuenta para confirmar el pedido.", "error");
        $("cuenta").scrollIntoView({ behavior: "smooth" });
        return;
    }
    if (sesion.rol !== "cliente") {
        return avisar("El operador no puede hacer pedidos.", "error");
    }
    if (!claveIdempotencia) claveIdempotencia = nuevaClave();

    const boton = $("btnConfirmarPedido");
    boton.disabled = true;
    boton.textContent = "Confirmando...";
    try {
        const items = pedido.map(item => ({ product_id: item.id, cantidad: item.cantidad }));
        const creado = await api("POST", "/orders", { items }, { "Idempotency-Key": claveIdempotencia });
        ultimoPedidoId = creado.id;
        const unidades = creado.items.reduce((acc, i) => acc + i.cantidad, 0);
        pedido = [];
        claveIdempotencia = null;
        renderizarPedido();
        $("pedidoConfirmadoTexto").textContent =
            `Pedido ${creado.id}: ${unidades} preparación(es) por ${formatearPrecio(creado.total)}. ` +
            `Se despacha a ${creado.direccion_entrega} cuando se confirme el pago.`;
        $("pedidoConfirmado").hidden = false;
        cargarMenu();
    } catch (error) {
        avisar(error.message, "error");
    } finally {
        boton.disabled = false;
        boton.textContent = "Confirmar pedido";
    }
}

async function pagarPedido(id) {
    try {
        const pago = await api("POST", "/payments", { order_id: id });
        avisar(`Pago de ${formatearPrecio(pago.monto)} enviado al proveedor (ref. ${pago.provider_ref}). Esperando su confirmación.`);
        cargarMisPedidos();
    } catch (error) {
        avisar(error.message, "error");
    }
}

async function anularPedido(id) {
    if (!confirm("¿Seguro que quieres anular el pedido " + id + "?")) return;
    try {
        await api("PATCH", `/orders/${encodeURIComponent(id)}/cancelar`);
        avisar("Pedido anulado.");
        cargarMisPedidos();
        cargarMenu();
    } catch (error) {
        avisar(error.message, "error");
    }
}

const CONSULTA_MIS_PEDIDOS = `{
  misPedidos(limite: 10) {
    id estado total creadoEn
    items { nombre cantidad subtotal }
    pago { estado monto }
  }
}`;

function tarjetaPedido(p, acciones) {
    const pagoTexto = p.pago ? `Pago: ${esc(p.pago.estado)}` : (p.pagoNoDisponible ? "Pago: sin información por ahora" : "");
    return `
        <article class="pedido-card">
            <div class="pedido-card-top">
                <strong>${esc(p.id)}</strong>
                <span class="estado estado-${esc(p.estado)}">${esc(ESTADOS[p.estado] || p.estado)}</span>
            </div>
            <p class="pedido-meta">${formatearFecha(p.creadoEn || p.creado_en)} · ${formatearPrecio(p.total)}</p>
            <ul class="pedido-items">
                ${p.items.map(i => `<li>${esc(i.cantidad)} × ${esc(i.nombre)}</li>`).join("")}
            </ul>
            ${pagoTexto ? `<p class="pedido-meta">${pagoTexto}</p>` : ""}
            <div class="pedido-acciones">${acciones}</div>
        </article>`;
}

async function cargarMisPedidos() {
    if (!sesion || sesion.rol !== "cliente") return;
    $("misPedidosEstado").textContent = "Cargando...";
    try {
        const respuesta = await api("POST", "/graphql", { query: CONSULTA_MIS_PEDIDOS });
        const lista = (respuesta.data && respuesta.data.misPedidos) || [];
        if (respuesta.errors) {
            lista.forEach(p => { if (!p.pago) p.pagoNoDisponible = true; });
        }
        $("misPedidosEstado").textContent = lista.length ? "" : "Aún no tienes pedidos.";
        $("misPedidosLista").innerHTML = lista.map(p => {
            let acciones = "";
            if (p.estado === "pendiente_pago") {
                const pagoAbierto = p.pago && p.pago.estado === "iniciado";
                acciones = (pagoAbierto
                    ? `<span class="pedido-meta">Esperando confirmación del pago...</span>`
                    : `<button type="button" class="btn btn-primary" data-pagar="${esc(p.id)}">Pagar</button>`) +
                    `<button type="button" class="btn btn-outline" data-anular="${esc(p.id)}">Anular</button>`;
            }
            return tarjetaPedido(p, acciones);
        }).join("");
    } catch (error) {
        $("misPedidosEstado").textContent = error.message;
    }
}

async function cargarPanel() {
    if (!sesion || sesion.rol !== "operador") return;
    try {
        const [pedidos, stock, ventas] = await Promise.all([
            api("GET", "/orders"),
            api("GET", "/admin/products"),
            api("GET", "/orders/reporte/diario")
        ]);

        $("panelPedidos").innerHTML = pedidos.length ? pedidos.map(p => {
            const siguiente = SIGUIENTE_ESTADO[p.estado];
            const acciones = siguiente
                ? `<button type="button" class="btn btn-primary" data-avanzar="${esc(p.id)}" data-estado="${siguiente}">Marcar ${esc(ESTADOS[siguiente].toLowerCase())}</button>`
                : "";
            return tarjetaPedido(p, acciones);
        }).join("") : "<p>No hay pedidos todavía.</p>";

        $("panelStock").innerHTML = stock.filter(p => p.activo).map(p => `
            <tr>
                <td>${esc(p.nombre)}</td>
                <td><input type="number" min="0" max="1000" value="${esc(p.stock)}" class="input-stock" id="stock-${esc(p.id)}"></td>
                <td><button type="button" class="btn-chip" data-guardar-stock="${esc(p.id)}">Guardar</button></td>
            </tr>`).join("");

        const ultimoDia = ventas.length ? ventas[0].dia : null;
        const hoy = ventas.filter(v => v.dia === ultimoDia);
        $("panelVentas").innerHTML = hoy.length ? hoy.map(v => `
            <tr><td>${esc(v.nombre)}</td><td>${esc(v.unidades)}</td><td>${formatearPrecio(v.ventas)}</td></tr>`).join("")
            : `<tr><td colspan="3">Sin ventas pagadas todavía.</td></tr>`;
    } catch (error) {
        avisar(error.message, "error");
    }
}

async function avanzarEstado(id, estado) {
    try {
        await api("PATCH", `/orders/${encodeURIComponent(id)}/estado`, { estado });
        avisar(`Pedido ${id}: ${ESTADOS[estado]}`);
        cargarPanel();
    } catch (error) {
        avisar(error.message, "error");
    }
}

async function guardarStock(id) {
    const valor = parseInt($("stock-" + id).value, 10);
    if (isNaN(valor) || valor < 0) return avisar("El stock debe ser un número mayor o igual a 0.", "error");
    try {
        await api("PATCH", `/products/${encodeURIComponent(id)}/stock`, { stock: valor });
        avisar("Stock actualizado.");
        cargarMenu();
    } catch (error) {
        avisar(error.message, "error");
    }
}

function actualizarVistaSesion() {
    const rol = sesion ? sesion.rol : null;
    document.querySelectorAll("[data-solo]").forEach(el => {
        const solo = el.dataset.solo;
        el.hidden = !((solo === "anonimo" && !rol) || (solo === "sesion" && rol) || (solo === "operador" && rol === "operador"));
    });
    $("mis-pedidos").hidden = rol !== "cliente";
    $("panel").hidden = rol !== "operador";
    $("formLogin").hidden = Boolean(rol) || pestanaActiva !== "login";
    $("formRegistro").hidden = Boolean(rol) || pestanaActiva !== "registro";
    document.querySelector(".tabs").hidden = Boolean(rol);
    $("sesionActiva").hidden = !rol;
    if (rol) {
        $("navUsuario").textContent = sesion.nombre;
        $("sesionNombre").textContent = sesion.nombre;
    }
}

async function iniciarSesion(email, password) {
    const datos = await api("POST", "/auth/login", { email, password });
    sesion = { token: datos.access_token, rol: datos.rol, nombre: email };
    if (sesion.rol === "cliente") {
        try {
            const perfil = await api("GET", "/clients/me");
            sesion.nombre = perfil.nombre.split(" ")[0];
        } catch (e) { }
    } else {
        sesion.nombre = "Operador";
    }
    actualizarVistaSesion();
    cargarMisPedidos();
    cargarPanel();
}

function cerrarSesionLocal() {
    sesion = null;
    cambiarPestana("login");
}

async function cerrarSesion() {
    try { await api("POST", "/auth/logout"); } catch (e) { }
    cerrarSesionLocal();
    avisar("Sesión cerrada.");
}

let pestanaActiva = "login";
function cambiarPestana(nombre) {
    pestanaActiva = nombre;
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("activa", t.dataset.tab === nombre));
    actualizarVistaSesion();
}

function mostrarError(inputId, errorId, mensaje) {
    $(inputId).classList.toggle("invalido", Boolean(mensaje));
    $(errorId).textContent = mensaje || "";
}

function validarRegistro() {
    let esValido = true;
    const datos = {
        nombre: $("nombre").value.trim(),
        email: $("email").value.trim(),
        direccion: $("direccion").value.trim(),
        telefono: $("telefono").value.trim(),
        password: $("password").value
    };

    const reglas = [
        ["nombre", "errorNombre", datos.nombre.length >= 2, "Ingresa tu nombre completo."],
        ["email", "errorEmail", /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(datos.email), "Ingresa un email válido."],
        ["direccion", "errorDireccion", datos.direccion.length >= 5, "Ingresa una dirección de entrega."],
        ["telefono", "errorTelefono", datos.telefono === "" || /^[0-9+\s]{7,15}$/.test(datos.telefono), "Revisa el formato del teléfono."],
        ["password", "errorPassword", datos.password.length >= 8, "La contraseña debe tener al menos 8 caracteres."]
    ];
    reglas.forEach(([input, error, ok, mensaje]) => {
        mostrarError(input, error, ok ? "" : mensaje);
        if (!ok) esValido = false;
    });
    return { esValido, datos };
}

document.addEventListener("click", (evento) => {
    const t = evento.target;
    const boton = selector => t.closest(selector);

    if (boton("[data-agregar]")) return agregarAlPedido(boton("[data-agregar]").dataset.agregar);
    if (boton("[data-ver-detalle]")) return mostrarDetalle(boton("[data-ver-detalle]").dataset.verDetalle);
    if (boton("[data-quitar]")) { pedido = pedido.filter(p => p.id !== boton("[data-quitar]").dataset.quitar); return cambioEnCarrito(); }
    if (boton("[data-mas]")) return cambiarCantidad(boton("[data-mas]").dataset.mas, 1);
    if (boton("[data-menos]")) return cambiarCantidad(boton("[data-menos]").dataset.menos, -1);
    if (boton("[data-filtro]")) { filtroTag = boton("[data-filtro]").dataset.filtro; renderizarFiltros(); return renderizarMenu(); }
    if (boton("[data-pagar]")) return pagarPedido(boton("[data-pagar]").dataset.pagar);
    if (boton("[data-anular]")) return anularPedido(boton("[data-anular]").dataset.anular);
    if (boton("[data-avanzar]")) return avanzarEstado(boton("[data-avanzar]").dataset.avanzar, boton("[data-avanzar]").dataset.estado);
    if (boton("[data-guardar-stock]")) return guardarStock(boton("[data-guardar-stock]").dataset.guardarStock);
    if (boton(".tab")) return cambiarPestana(boton(".tab").dataset.tab);
});

$("btnVaciarPedido").addEventListener("click", vaciarPedido);
$("btnConfirmarPedido").addEventListener("click", confirmarPedido);
$("btnPagarConfirmado").addEventListener("click", () => {
    if (ultimoPedidoId) pagarPedido(ultimoPedidoId);
    $("pedidoConfirmado").hidden = true;
    $("mis-pedidos").scrollIntoView({ behavior: "smooth" });
});
$("btnActualizarPedidos").addEventListener("click", cargarMisPedidos);
$("btnActualizarPanel").addEventListener("click", cargarPanel);
$("btnSalir").addEventListener("click", cerrarSesion);

$("navToggle").addEventListener("click", () => {
    const abierto = $("mainNav").classList.toggle("abierto");
    $("navToggle").setAttribute("aria-expanded", abierto);
});

$("mainNav").addEventListener("click", (evento) => {
    if (evento.target.tagName === "A") {
        $("mainNav").classList.remove("abierto");
        $("navToggle").setAttribute("aria-expanded", "false");
    }
});

$("formLogin").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    $("errorLogin").textContent = "";
    const email = $("loginEmail").value.trim();
    const password = $("loginPassword").value;
    if (!email || !password) {
        $("errorLogin").textContent = "Ingresa tu email y contraseña.";
        return;
    }
    try {
        await iniciarSesion(email, password);
        $("formLogin").reset();
        avisar("¡Bienvenido/a, " + sesion.nombre + "!");
    } catch (error) {
        $("errorLogin").textContent = error.message;
    }
});

$("formRegistro").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    $("errorRegistro").textContent = "";
    const { esValido, datos } = validarRegistro();
    if (!esValido) return;
    if (!datos.telefono) delete datos.telefono;
    try {
        await api("POST", "/auth/registro", datos);
        await iniciarSesion(datos.email, datos.password);
        $("formRegistro").reset();
        avisar("Cuenta creada. ¡Ya puedes pedir!");
    } catch (error) {
        $("errorRegistro").textContent = error.message;
    }
});

actualizarVistaSesion();
renderizarPedido();
cargarMenu();
