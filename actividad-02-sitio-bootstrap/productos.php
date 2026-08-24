<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Productos</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body onload="mostrarProductos()">

    <!-- Navbar -->
    <nav class="navbar navbar-expand-sm bg-dark navbar-dark">
        <div class="container-fluid">
            <a class="navbar-brand" href="index.php">Logo</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">Empresa</a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="empresa.php">Sobre Nosotros</a></li>
                        </ul>
                    </li>
                    <li class="nav-item"><a class="nav-link" href="productos.php">Productos</a></li>
                    <li class="nav-item"><a class="nav-link" href="servicios.php">Servicios</a></li>
                    <li class="nav-item"><a class="nav-link" href="contacto.php">Contacto</a></li>
                </ul>
                <a href="#" class="btn btn-outline-light ms-auto">Acceder</a>
            </div>
        </div>
    </nav>

    <!-- Container -->
    <div class="container-fluid bg-warning py-4">
        <h2>Nuestros Productos</h2>
        <div id="lista-productos" class="row"></div>
        <button class="btn btn-dark mt-2" onclick="agregarProducto()">Agregar producto</button>
    </div>

    <!-- Footer -->
    <div class="container-fluid bg-dark">
        <div class="row">
            <div class="col-4"></div>
            <div class="col-4 d-flex justify-content-center" style="color:white"><strong>MiEmpresa@2026</strong></div>
            <div class="col-4"></div>
        </div>
    </div>

    <script>
        // Array de objetos con los productos
        let productos = [
            {nombre: "Producto 1", precio: 1000},
            {nombre: "Producto 2", precio: 2000},
            {nombre: "Producto 3", precio: 3000}
        ];

        function mostrarProductos() {
            let contenedor = document.getElementById("lista-productos");
            contenedor.innerHTML = "";

            productos.forEach(function(p) {
                let div = document.createElement("div");
                div.className = "col-md-4";
                div.innerHTML = `<div class="card mb-3">
                                    <div class="card-body">
                                        <h5 class="card-title">${p.nombre}</h5>
                                        <p class="card-text">$${p.precio}</p>
                                    </div>
                                  </div>`;
                contenedor.appendChild(div);
            });
        }

        function agregarProducto() {
            let numero = productos.length + 1;
            let nuevo = {nombre: "Producto " + numero, precio: numero * 1000};
            productos.push(nuevo);
            mostrarProductos();
        }
    </script>

</body>
</html>
