<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Productos</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>
</head>
<body>

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

    <!-- Carrusel -->
    <div id="carouselProductos" class="carousel slide bg-dark" data-bs-ride="carousel">
        <div class="carousel-inner">
            <div class="carousel-item active">
                <img src="img/producto1.jpg" class="d-block w-100" alt="Producto 1" style="max-height:500px; object-fit:contain;">
            </div>
            <div class="carousel-item">
                <img src="img/producto2.jpg" class="d-block w-100" alt="Producto 2" style="max-height:500px; object-fit:contain;">
            </div>
            <div class="carousel-item">
                <img src="img/producto3.jpg" class="d-block w-100" alt="Producto 3" style="max-height:500px; object-fit:contain;">
            </div>
        </div>
        <button class="carousel-control-prev" type="button" data-bs-target="#carouselProductos" data-bs-slide="prev">
            <span class="carousel-control-prev-icon"></span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#carouselProductos" data-bs-slide="next">
            <span class="carousel-control-next-icon"></span>
        </button>
    </div>

    <!-- Footer -->
    <div class="container-fluid bg-dark">
        <div class="row">
            <div class="col-4"></div>
            <div class="col-4 d-flex justify-content-center" style="color:white"><strong>MiEmpresa@2026</strong></div>
            <div class="col-4"></div>
        </div>
    </div>

</body>
</html>
