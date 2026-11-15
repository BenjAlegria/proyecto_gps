<?php

// ==========================
// Configuración Base Datos
// ==========================

define("DB_HOST", "localhost");

define("DB_USER", "fcaullan");

define("DB_PASS", "FxT82mQp#");

define("DB_NAME", "fcaullan_db2");


// ==========================
// Crear conexión
// ==========================

function conectarDB(){

    $conn = new mysqli(
        DB_HOST,
        DB_USER,
        DB_PASS,
        DB_NAME
    );


    if($conn->connect_error){

        die(
            "Error conexión BD: "
            .$conn->connect_error
        );

    }


    // soporte UTF-8

    $conn->set_charset("utf8mb4");


    return $conn;

}


?>