"""Datos de ejemplo de la app: localidades, recorridos y tipos de aviso.

Frecuencias, tarifas y horarios son referenciales (reemplazar por los
datos reales del socio comunitario).
"""

COORDENADAS = {
    "Nueva Imperial": (-38.7442, -72.9503),
    "Lautaro": (-38.5285, -72.4318),
    "Carahue": (-38.7103, -73.1561),
    "Padre Las Casas": (-38.7683, -72.5975),
    "Temuco": (-38.7359, -72.5904),
    "Victoria": (-38.2333, -72.3333),
}

LOCALIDADES = {
    "Nueva Imperial": [
        {"ruta": "Nueva Imperial -> Temuco", "parada": "Terminal Nueva Imperial",
         "minutos": "15 min", "frecuencia": "Cada 20 min", "tarifa": "$1.500", "duracion": "50 min"},
        {"ruta": "Nueva Imperial -> Carahue", "parada": "Terminal Nueva Imperial",
         "minutos": "40 min", "frecuencia": "Cada 45 min", "tarifa": "$1.200", "duracion": "35 min"},
    ],
    "Lautaro": [
        {"ruta": "Lautaro -> Temuco", "parada": "Parada Balmaceda",
         "minutos": "50 min", "frecuencia": "Cada 30 min", "tarifa": "$1.800", "duracion": "1 h"},
        {"ruta": "Lautaro -> Victoria", "parada": "Terminal Lautaro",
         "minutos": "25 min", "frecuencia": "Cada 40 min", "tarifa": "$1.000", "duracion": "35 min"},
    ],
    "Carahue": [
        {"ruta": "Carahue -> Temuco", "parada": "Terminal Carahue",
         "minutos": "30 min", "frecuencia": "Cada 30 min", "tarifa": "$2.500", "duracion": "1 h 20 min"},
        {"ruta": "Carahue -> Nueva Imperial", "parada": "Terminal Carahue",
         "minutos": "10 min", "frecuencia": "Cada 45 min", "tarifa": "$1.200", "duracion": "35 min"},
    ],
    "Padre Las Casas": [
        {"ruta": "Padre Las Casas -> Temuco", "parada": "Parada Balmaceda",
         "minutos": "20 min", "frecuencia": "Cada 10 min", "tarifa": "$700", "duracion": "20 min"},
    ],
    "Temuco": [
        {"ruta": "Temuco -> Lautaro", "parada": "Terminal Rodoviario",
         "minutos": "5 min", "frecuencia": "Cada 30 min", "tarifa": "$1.800", "duracion": "1 h"},
        {"ruta": "Temuco -> Nueva Imperial", "parada": "Terminal Rodoviario",
         "minutos": "12 min", "frecuencia": "Cada 20 min", "tarifa": "$1.500", "duracion": "50 min"},
    ],
}

# Índice por nombre de ruta: {ruta: {..., "origen": localidad}}
RUTAS = {
    d["ruta"]: {**d, "origen": lugar}
    for lugar, lista in LOCALIDADES.items()
    for d in lista
}



# ------------------------------------------------------------
# Avisos de pasajeros (pedidos en la encuesta: 71% quedó sin poder subir
# por bus lleno, 41% sufrió buses que no pasaron a la hora, 59% quiere
# notificaciones de retrasos y 65% ver la capacidad de asientos).
# ------------------------------------------------------------
ROJO = (0.80, 0.18, 0.18, 1)
NARANJA = (0.90, 0.50, 0.05, 1)
VERDE = (0.05, 0.62, 0.43, 1)
GRIS = (0.50, 0.52, 0.58, 1)

TIPOS_AVISO = {
    "lleno": {"texto": "Bus lleno", "icono": "account-group", "color": ROJO},
    "asientos": {"texto": "Hay asientos", "icono": "seat-passenger", "color": VERDE},
    "atrasado": {"texto": "Bus atrasado", "icono": "clock-alert", "color": NARANJA},
    "cambio_ruta": {"texto": "Cambio de ruta", "icono": "map-marker-alert", "color": NARANJA},
}
