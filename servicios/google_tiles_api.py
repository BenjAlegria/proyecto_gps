"""Cliente oficial de Google Map Tiles API, sin dependencias de Kivy.

Solicita mosaicos para visualización inmediata. No se guardan en disco
ni se mezclan con tiles OpenStreetMap. El uso requiere una clave de API
para Map Tiles y facturación activa en Google Cloud.

https://developers.google.com/maps/documentation/tile/roadmap
https://developers.google.com/maps/documentation/tile/policies
"""
from __future__ import annotations

import os
import threading
import time

import requests

VARIABLE_CLAVE = "ENRUTA_GOOGLE_TILES_API_KEY"
BASE = "https://tile.googleapis.com"
TIPOS_MAPA = {"roadmap", "satellite"}
LIMITE_IMAGEN_BYTES = 3 * 1024 * 1024
MAX_MOSAICOS_POR_ACTIVACION = 180  # Límite preventivo; no equivale a una cuota Google Cloud


class ErrorMapTiles(RuntimeError):
    """Error legible sin imprimir la URL ni la clave privada del usuario."""


def clave_configurada(entorno=None):
    """Valida solo que exista una clave; Google validará sus restricciones."""
    if entorno is None:
        entorno = os.environ
    clave = entorno.get(VARIABLE_CLAVE, "").strip()
    if not clave or len(clave) > 256 or any(c.isspace() for c in clave):
        raise ErrorMapTiles(
            "Configura ENRUTA_GOOGLE_TILES_API_KEY con una clave de Map Tiles API."
        )
    return clave


class ClienteMapTiles:
    """Cliente por sesión. No tiene caché persistente y no almacena GPS."""

    def __init__(self, clave, tipo="roadmap", transporte=None):
        if not clave or len(clave) > 256:
            raise ErrorMapTiles("La clave de Map Tiles API no es válida.")
        if tipo not in TIPOS_MAPA:
            raise ValueError("Tipo de mapa no admitido")
        self._clave = clave
        self.tipo = tipo
        self.transporte = transporte if transporte is not None else requests
        self.session = None
        self.expiry = 0
        self.formato = "png"
        self._mosaicos_pedidos = 0
        self._bloqueo = threading.Lock()

    def _verificar(self, respuesta, etapa):
        # No propagar requests.HTTPError: su mensaje puede incluir la API key.
        if respuesta.status_code != 200:
            raise ErrorMapTiles(
                f"Google Map Tiles falló en {etapa} (HTTP {respuesta.status_code}). "
                "Revisa Map Tiles API, restricciones, cuotas y facturación."
            )
        return respuesta

    def iniciar(self):
        try:
            respuesta = self.transporte.post(
                BASE + "/v1/createSession",
                params={"key": self._clave},
                json={"mapType": self.tipo, "language": "es-CL", "region": "CL"},
                timeout=10,
            )
            info = self._verificar(respuesta, "crear sesión").json()
            token = info.get("session") if isinstance(info, dict) else None
            if not isinstance(token, str) or not token:
                raise ErrorMapTiles("Google Map Tiles no devolvió una sesión válida.")
            self.session = token
            self.expiry = float(info.get("expiry", 0))
            formato = str(info.get("imageFormat", "png")).lower()
            self.formato = "jpg" if formato in ("jpeg", "jpg") else "png"
            return self
        except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
            # La causa puede contener una URL con clave: no se encadena.
            if isinstance(exc, ErrorMapTiles):
                raise
            raise ErrorMapTiles("No se pudo conectar con Google Map Tiles API.") from None

    def _asegurar_sesion(self):
        if not self.session:
            raise ErrorMapTiles("La sesión Google Maps aún no está preparada.")
        if self.expiry and time.time() >= self.expiry:
            raise ErrorMapTiles("La sesión del mapa caducó. Vuelve a activarlo.")

    def mosaico(self, zoom, x, y):
        """Devuelve bytes de imagen de una sola tesela, sin guardar caché."""
        self._asegurar_sesion()
        with self._bloqueo:
            if self._mosaicos_pedidos >= MAX_MOSAICOS_POR_ACTIVACION:
                raise ErrorMapTiles(
                    "Se alcanzó el límite de mosaicos de esta prueba. "
                    "Se volverá al mapa original."
                )
            self._mosaicos_pedidos += 1
        try:
            respuesta = self.transporte.get(
                f"{BASE}/v1/2dtiles/{int(zoom)}/{int(x)}/{int(y)}",
                params={"session": self.session, "key": self._clave},
                timeout=8,
            )
            datos = self._verificar(respuesta, "descargar mosaico").content
            if not datos or len(datos) > LIMITE_IMAGEN_BYTES:
                raise ErrorMapTiles("Google Map Tiles devolvió una imagen inválida.")
            return datos
        except requests.RequestException:
            raise ErrorMapTiles("No se pudo descargar una tesela de Google Maps.") from None

    def atribucion(self, zoom, norte, sur, este, oeste):
        """Recupera créditos variables para la extensión de mapa visible."""
        self._asegurar_sesion()
        try:
            respuesta = self.transporte.get(
                BASE + "/tile/v1/viewport",
                params={
                    "session": self.session, "key": self._clave,
                    "zoom": int(zoom), "north": float(norte),
                    "south": float(sur), "east": float(este),
                    "west": float(oeste),
                },
                timeout=8,
            )
            info = self._verificar(respuesta, "consultar atribución").json()
            copyright_texto = info.get("copyright", "") if isinstance(info, dict) else ""
            if not isinstance(copyright_texto, str) or not copyright_texto.strip():
                raise ErrorMapTiles("Google Maps no devolvió la atribución de datos.")
            return copyright_texto.strip()
        except (requests.RequestException, ValueError, TypeError):
            raise ErrorMapTiles("No se pudo consultar la atribución de Google Maps.") from None
