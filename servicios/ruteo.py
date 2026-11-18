"""Rutas por calles con OSRM. Solo usa la biblioteca estándar.

Pide a OSRM el trazado A -> B (más los puntos intermedios, si la API los trae),
lo simplifica y lo guarda en disco: cada recorrido se consulta una sola vez y
luego funciona sin internet. Si OSRM falla, la app sigue con la línea de la API.
"""
import json
import math
import os
import queue
import threading
import time
import urllib.request

OSRM_URL = "https://router.project-osrm.org"   # servidor público de demostración
PERFIL = "driving"
TIMEOUT_S = 12
PAUSA_S = 1.2        # el servidor público pide como máximo ~1 petición por segundo
REINTENTO_S = 600    # tras un fallo, esperar 10 min antes de reintentar ese recorrido
MAX_PUNTOS = 25      # puntos de la API que se envían a OSRM
TOLERANCIA_M = 15    # simplificación del trazado devuelto (menos puntos = mapa más fluido)


def clave_linea(puntos):
    return ";".join(f"{la:.5f},{lo:.5f}" for la, lo in puntos)


def _muestrear(puntos, maximo):
    if len(puntos) <= maximo:
        return list(puntos)
    paso = (len(puntos) - 1) / (maximo - 1)
    return [puntos[round(i * paso)] for i in range(maximo)]


def simplificar(puntos, tolerancia_m=TOLERANCIA_M):
    """Douglas-Peucker (iterativo) sobre coordenadas aproximadas en metros."""
    if len(puntos) < 3:
        return list(puntos)
    kx, ky = 111320 * math.cos(math.radians(puntos[0][0])), 110540
    xy = [(lo * kx, la * ky) for la, lo in puntos]
    mantener = [False] * len(puntos)
    mantener[0] = mantener[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        i, j = pila.pop()
        (x1, y1), (x2, y2) = xy[i], xy[j]
        dx, dy = x2 - x1, y2 - y1
        largo2 = dx * dx + dy * dy
        lejano, mayor = None, tolerancia_m
        for k in range(i + 1, j):
            px, py = xy[k]
            if largo2 == 0:
                d = math.hypot(px - x1, py - y1)
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / largo2))
                d = math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
            if d > mayor:
                lejano, mayor = k, d
        if lejano is not None:
            mantener[lejano] = True
            pila.append((i, lejano))
            pila.append((lejano, j))
    return [p for p, m in zip(puntos, mantener) if m]


def pedir_ruta(puntos, base_url=OSRM_URL):
    """Devuelve [(lat, lon), ...] siguiendo las calles. Lanza excepción si falla."""
    puntos = _muestrear(puntos, MAX_PUNTOS)
    coords = ";".join(f"{lo:.6f},{la:.6f}" for la, lo in puntos)   # OSRM usa lon,lat
    url = (f"{base_url}/route/v1/{PERFIL}/{coords}"
           "?overview=full&geometries=geojson&steps=false")
    req = urllib.request.Request(url, headers={"User-Agent": "EnRutaYa/3.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    if datos.get("code") != "Ok" or not datos.get("routes"):
        raise ValueError(f"OSRM respondió: {datos.get('code')}")
    trazado = [(la, lo) for lo, la in datos["routes"][0]["geometry"]["coordinates"]]
    return simplificar(trazado)


class RuteadorCalles:
    """Caché en disco + cola de consultas a OSRM en un solo hilo en segundo plano."""

    def __init__(self, carpeta, base_url=OSRM_URL):
        self._archivo = os.path.join(carpeta, "rutas_calles.json")
        self._base = base_url
        self._lock = threading.Lock()
        self._cola = queue.Queue()
        self._en_cola = set()
        self._fallos = {}
        self._hilo = None
        self._cache = {}
        try:
            with open(self._archivo, encoding="utf-8") as f:
                self._cache = {k: [tuple(p) for p in v] for k, v in json.load(f).items()}
        except (OSError, ValueError, TypeError):
            self._cache = {}

    def cacheada(self, puntos):
        """Trazado por calles ya guardado para esta línea, o None."""
        with self._lock:
            return self._cache.get(clave_linea(puntos))

    def pedir(self, puntos, al_terminar):
        """Encola la consulta. `al_terminar(ruta)` se llama desde el hilo de fondo."""
        clave = clave_linea(puntos)
        with self._lock:
            if clave in self._cache or clave in self._en_cola:
                return
            if time.time() - self._fallos.get(clave, 0) < REINTENTO_S:
                return
            self._en_cola.add(clave)
            self._cola.put((clave, list(puntos), al_terminar))
            if self._hilo is None:
                self._hilo = threading.Thread(target=self._trabajar, daemon=True,
                                              name="enruta-osrm")
                self._hilo.start()

    def _trabajar(self):
        while True:
            with self._lock:
                try:
                    clave, puntos, al_terminar = self._cola.get_nowait()
                except queue.Empty:
                    self._hilo = None
                    return
            try:
                ruta = pedir_ruta(puntos, self._base)
            except Exception as e:
                print("OSRM no disponible:", e)
                ruta = None
            with self._lock:
                self._en_cola.discard(clave)
                if ruta:
                    self._cache[clave] = ruta
                else:
                    self._fallos[clave] = time.time()
            if ruta:
                self._guardar()
                try:
                    al_terminar(ruta)
                except Exception as e:
                    print("Error aplicando ruta por calles:", e)
            time.sleep(PAUSA_S)

    def _guardar(self):
        with self._lock:
            datos = {k: [[round(la, 5), round(lo, 5)] for la, lo in v]
                     for k, v in self._cache.items()}
        try:
            tmp = self._archivo + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(datos, f)
            os.replace(tmp, self._archivo)
        except OSError:
            pass