import os

from config import DATA_DIR
from servicios.almacenamiento import guardar_json, leer_json

RUTA = os.path.join(DATA_DIR, "reputacion.json")


def _cargar():
    return leer_json(RUTA, {})


def _guardar(datos):
    guardar_json(RUTA, datos)

PTS_AVISO, PTS_OK, PTS_MAL = 1, 3, -2

# (puntos mínimos, nombre, icono)
NIVELES = [
    (0, "Novato", "account-outline"),
    (10, "Colaborador", "star-outline"),
    (30, "Confiable", "star-half-full"),
    (80, "Guía de ruta", "star"),
    (200, "Leyenda del camino", "trophy"),
]




def _ficha(datos, usuario):
    return datos.setdefault(usuario, {"avisos": 0, "ok": 0, "mal": 0})


def sumar_aviso(usuario):
    if not usuario:
        return
    datos = _cargar()
    _ficha(datos, usuario)["avisos"] += 1
    _guardar(datos)


def actualizar_voto(autor, previo, nuevo):
    """Ajusta los contadores del autor cuando alguien vota (1, -1 o 0 = sin voto)."""
    if not autor or previo == nuevo:
        return
    datos = _cargar()
    f = _ficha(datos, autor)
    if previo == 1:
        f["ok"] = max(0, f["ok"] - 1)
    elif previo == -1:
        f["mal"] = max(0, f["mal"] - 1)
    if nuevo == 1:
        f["ok"] += 1
    elif nuevo == -1:
        f["mal"] += 1
    _guardar(datos)


def puntos(usuario):
    f = _cargar().get(usuario, {"avisos": 0, "ok": 0, "mal": 0})
    return max(0, f["avisos"] * PTS_AVISO + f["ok"] * PTS_OK + f["mal"] * PTS_MAL)


def nivel(pts):
    """Devuelve (nombre, icono, puntos que faltan para el siguiente o None)."""
    actual = NIVELES[0]
    for n in NIVELES:
        if pts >= n[0]:
            actual = n
    idx = NIVELES.index(actual)
    faltan = NIVELES[idx + 1][0] - pts if idx + 1 < len(NIVELES) else None
    return actual[1], actual[2], faltan


def ranking(cuantos=5):
    datos = _cargar()
    tabla = [(u, puntos(u)) for u in datos]
    return sorted(tabla, key=lambda t: t[1], reverse=True)[:cuantos]