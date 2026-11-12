"""Vista experimental Google Maps para EnRuta Ya!

No reemplaza MapView: levanta un servidor HTTP SOLO en 127.0.0.1 y abre
una vista web en el navegador predeterminado. No publica el GPS del
usuario: únicamente ofrece los recorridos simulados ya incluidos en
datos_rutas.py.

La clave de Maps JavaScript API se lee de la variable de entorno
ENRUTA_GOOGLE_MAPS_API_KEY. Debe restringirse en Google Cloud a la
Maps JavaScript API y al origen de prueba http://127.0.0.1:8765/*.
"""
from __future__ import annotations

import html
import json
import os
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from datos_rutas import COORDENADAS, LOCALIDADES
from servicios.recorridos import posicion_bus_demo

HTML_PATH = Path(__file__).resolve().parent.parent / "experimentos" / "google_maps.html"
CLAVE_ENV = "ENRUTA_GOOGLE_MAPS_API_KEY"
HOST = "127.0.0.1"
PUERTO = 8765

_lock = threading.Lock()
_servidor = None
_hilo = None


class ErrorGoogleMaps(RuntimeError):
    """Una configuración ausente no debe cerrar la aplicación Kivy."""


def validar_clave(clave):
    """Acepta solo caracteres habituales de una API key web de Google."""
    if not isinstance(clave, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,150}", clave):
        raise ErrorGoogleMaps(
            "Configura ENRUTA_GOOGLE_MAPS_API_KEY con una clave válida "
            "de Google Maps JavaScript API. No la escribas en Git."
        )
    return clave


def construir_datos_demo():
    """Devuelve únicamente datos de ejemplo (nunca ubicación del usuario)."""
    rutas = []
    for origen, lineas in LOCALIDADES.items():
        if origen not in COORDENADAS:
            continue
        for linea in lineas:
            destino = linea["ruta"].split("->")[-1].strip()
            if destino not in COORDENADAS:
                continue
            lat, lon = posicion_bus_demo(
                COORDENADAS[origen],
                COORDENADAS[destino],
                linea["duracion"],
                linea["minutos"],
            )
            rutas.append({
                "nombre": linea["ruta"],
                "origen": origen,
                "destino": destino,
                "inicio": {
                    "lat": COORDENADAS[origen][0],
                    "lng": COORDENADAS[origen][1],
                },
                "fin": {
                    "lat": COORDENADAS[destino][0],
                    "lng": COORDENADAS[destino][1],
                },
                "bus_demo": {"lat": lat, "lng": lon},
                "minutos": linea["minutos"],
                "frecuencia": linea["frecuencia"],
                "tarifa": linea["tarifa"],
                "duracion": linea["duracion"],
            })
    return {
        "demo": True,
        "aviso": (
            "Posiciones simuladas con interpolación lineal. "
            "No representan GPS real ni trayectorias por calles."
        ),
        "centro": {"lat": -38.7359, "lng": -72.5904},
        "rutas": rutas,
    }


def crear_servidor(clave, host=HOST, puerto=PUERTO):
    """Construye un servidor local sin iniciarlo; puerto=0 sirve para tests."""
    validar_clave(clave)
    html_base = HTML_PATH.read_text(encoding="utf-8")
    if "__GOOGLE_MAPS_API_KEY__" not in html_base:
        raise ErrorGoogleMaps("Falta el marcador de clave en google_maps.html")
    # El valor aparece en el navegador por diseño de Maps JS; hay que
    # restringir la clave, no tratarla como contraseña privada de backend.
    pagina = html_base.replace(
        "__GOOGLE_MAPS_API_KEY__", html.escape(clave, quote=True)
    ).encode("utf-8")
    datos = json.dumps(construir_datos_demo(), ensure_ascii=False).encode("utf-8")

    class Manejador(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            # Evita imprimir accidentalmente información de la vista.
            pass

        def do_GET(self):
            ruta = urlsplit(self.path).path
            if ruta in ("/", "/index.html"):
                cuerpo, tipo, estado = pagina, "text/html; charset=utf-8", 200
            elif ruta == "/api/rutas":
                cuerpo, tipo, estado = datos, "application/json; charset=utf-8", 200
            else:
                cuerpo, tipo, estado = b"No encontrado", "text/plain; charset=utf-8", 404
            self.send_response(estado)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(cuerpo)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.end_headers()
            self.wfile.write(cuerpo)

    try:
        return ThreadingHTTPServer((host, puerto), Manejador)
    except OSError as exc:
        raise ErrorGoogleMaps(
            f"No se pudo abrir el servidor local {host}:{puerto}: {exc}"
        ) from exc


def abrir_en_navegador(abrir=None):
    """Inicia vista local una vez y abre el navegador desde la app de Kivy.

    En esta primera prueba solo se admite Windows/Linux/macOS; una futura
    integración Android requiere WebView nativa + origen HTTPS controlado.
    """
    global _servidor, _hilo
    clave = validar_clave(os.getenv(CLAVE_ENV, ""))
    with _lock:
        if _servidor is None:
            _servidor = crear_servidor(clave)
            _hilo = threading.Thread(
                target=_servidor.serve_forever,
                name="google-maps-preview", daemon=True,
            )
            _hilo.start()
        url = f"http://{HOST}:{_servidor.server_address[1]}/"

    abrir = abrir or webbrowser.open
    if not abrir(url):
        raise ErrorGoogleMaps(
            "El navegador no se abrió automáticamente. Abre " + url
        )
    return url


def detener():
    """Cierra el servidor local al salir de la app y libera el puerto."""
    global _servidor, _hilo
    with _lock:
        servidor, hilo = _servidor, _hilo
        _servidor, _hilo = None, None
    if servidor is not None:
        servidor.shutdown()
        servidor.server_close()
    if hilo is not None and hilo.is_alive():
        hilo.join(timeout=2)
