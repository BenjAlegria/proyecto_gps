"""Configuración remota (remote config).

Valores que NO están fijos en el código sino que se leen de un JSON en
internet (config.URL_CONFIG_REMOTA). Orden de prioridad:
  1. valor remoto recién descargado        -> fuente "remota"
  2. última copia guardada en data/ (caché) -> fuente "caché"
  3. config.CONFIG_REMOTA_DEFECTO           -> fuente "valor por defecto"
La descarga se hace en un hilo para no congelar la interfaz.
"""

import threading

from config import (ARCHIVO_CACHE_REMOTA, CONFIG_REMOTA_DEFECTO,
                    TIMEOUT_CONFIG_REMOTA_S, URL_CONFIG_REMOTA)
from servicios.almacenamiento import guardar_json, leer_json

FUENTE_REMOTA = "remota"
FUENTE_CACHE = "caché"
FUENTE_DEFECTO = "valor por defecto"


def _sanear(datos):
    """Se queda solo con las claves conocidas y del tipo correcto, así un
    JSON remoto mal escrito no puede romper la app."""
    limpio = {}
    if not isinstance(datos, dict):
        return limpio
    for clave, defecto in CONFIG_REMOTA_DEFECTO.items():
        valor = datos.get(clave)
        if isinstance(defecto, bool) or not isinstance(valor, type(defecto)):
            continue
        if isinstance(defecto, int) and valor <= 0:
            continue
        limpio[clave] = valor
    return limpio


def cargar_local():
    """Configuración inmediata (sin internet): caché o valores por defecto.
    Devuelve (configuracion, fuente)."""
    cache = _sanear(leer_json(ARCHIVO_CACHE_REMOTA, {}))
    if cache:
        return {**CONFIG_REMOTA_DEFECTO, **cache}, FUENTE_CACHE
    return dict(CONFIG_REMOTA_DEFECTO), FUENTE_DEFECTO


def descargar(url=None, timeout=None):
    """Descarga y valida el JSON remoto; lo guarda como caché. Devuelve
    (configuracion, fuente). Si falla, devuelve lo local."""
    try:
        import requests
        r = requests.get(url or URL_CONFIG_REMOTA,
                         timeout=timeout or TIMEOUT_CONFIG_REMOTA_S)
        r.raise_for_status()
        remoto = _sanear(r.json())
        if not remoto:
            raise ValueError("el JSON remoto no trae valores válidos")
        guardar_json(ARCHIVO_CACHE_REMOTA, remoto)
        return {**CONFIG_REMOTA_DEFECTO, **remoto}, FUENTE_REMOTA
    except Exception as e:
        print("Configuración remota no disponible, se usa la local:", e)
        return cargar_local()


def descargar_en_hilo(al_terminar):
    """Ejecuta `descargar` en segundo plano y llama a
    al_terminar(configuracion, fuente) al terminar (desde el hilo; quien
    llama debe pasarla al hilo de la interfaz, ej. con Clock)."""
    def trabajo():
        al_terminar(*descargar())
    threading.Thread(target=trabajo, daemon=True).start()
