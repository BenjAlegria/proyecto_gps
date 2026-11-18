"""Geometría de recorridos (servicios/geo.py). Sin Kivy: se puede probar sola.

Los puntos son tuplas (lat, lon). Las distancias usan una aproximación plana
local, más que suficiente para tramos de pocos kilómetros.
"""
import math

_METROS_POR_GRADO_LAT = 110540.0


def _metros_por_grado_lon(lat):
    return 111320.0 * math.cos(math.radians(lat))


def distancia_m(a, b):
    kx = _metros_por_grado_lon((a[0] + b[0]) / 2)
    return math.hypot((b[1] - a[1]) * kx, (b[0] - a[0]) * _METROS_POR_GRADO_LAT)


def largo_m(linea):
    return sum(distancia_m(linea[i], linea[i + 1]) for i in range(len(linea) - 1))


def proyectar_en_linea(linea, pos):
    """Punto de la línea más cercano a `pos`.

    Devuelve (indice_del_tramo, punto, distancia_en_metros), o None si la
    línea tiene menos de 2 puntos."""
    if len(linea) < 2:
        return None
    kx = _metros_por_grado_lon(pos[0])
    ky = _METROS_POR_GRADO_LAT
    mejor = None
    for i in range(len(linea) - 1):
        ax, ay = (linea[i][1] - pos[1]) * kx, (linea[i][0] - pos[0]) * ky
        bx, by = (linea[i + 1][1] - pos[1]) * kx, (linea[i + 1][0] - pos[0]) * ky
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / l2))
        cx, cy = ax + t * dx, ay + t * dy
        d = math.hypot(cx, cy)
        if mejor is None or d < mejor[2]:
            mejor = (i, (pos[0] + cy / ky, pos[1] + cx / kx), d)
    return mejor


def tramo_restante(linea, pos, tolerancia_m=500):
    """Lo que falta de la línea desde `pos` hasta el punto B.

    Devuelve (restante, distancia_a_la_linea_m). Si estás a más de
    `tolerancia_m` de la línea, restante es None (fuera de ruta)."""
    res = proyectar_en_linea(linea, pos)
    if res is None:
        return None, 0.0
    i, punto, dist = res
    if dist > tolerancia_m:
        return None, dist
    return [punto] + list(linea[i + 1:]), dist
