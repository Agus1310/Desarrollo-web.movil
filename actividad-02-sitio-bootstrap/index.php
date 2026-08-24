<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Página Principal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body onload="saludar()">

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

    <?php
        $fecha = date("d-m-Y");
    ?>

    <!-- Container -->
    <div class="container-fluid bg-warning">
        Página Principal<br>
        Fecha de hoy: <?php echo $fecha; ?><br>
        <a href="index.php">Ir a Principal</a><br>
        <a href="empresa.php">Ir a Empresa</a><br>
        <a href="productos.php">Ir a Productos</a><br>
        <a href="servicios.php">Ir a Servicios</a><br>
        <a href="contacto.php">Ir a Contacto</a>

        <p id="mensaje" class="mt-3"></p>
        <button class="btn btn-primary" onclick="cambiarColor()">Cambiar color de fondo</button>
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
        function saludar() {
            let mensaje = document.getElementById("mensaje");
            mensaje.textContent = "Bienvenido a MiEmpresa";
        }

        function cambiarColor() {
            let contenedor = document.querySelector(".bg-warning");
            if (contenedor.style.backgroundColor === "lightblue") {
                contenedor.style.backgroundColor = "";
            } else {
                contenedor.style.backgroundColor = "lightblue";
            }
        }
    </script>

</body>
</html>
