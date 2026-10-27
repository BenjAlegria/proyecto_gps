"""Persistencia en JSON.

Todo lo que la app guarda pasa por este módulo:
  - usuarios.json  -> credenciales (lo escribe autenticacion.py)
  - perfiles.json  -> datos de cada usuario (nombre, favoritas, viajes, ajustes)
  - avisos.json    -> los avisos de pasajeros (los "registros" de la app)
Los archivos viven en config.DATA_DIR y se leen al abrir la app.
"""

import json
import os
import time

from config import ARCHIVO_AVISOS, ARCHIVO_PERFILES, DATA_DIR

PERFIL_POR_DEFECTO = {
    "nombre": "",
    "favoritas": [],
    "viajes": 0,
    "tema_oscuro": False,
    "notificar_favoritas": True,
    "consentimiento": False,
}

def leer_json(ruta, por_defecto=None):
    """Lee un JSON. Si no existe devuelve `por_defecto`; si está corrupto lo
    aparta (.corrupto) para no perderlo y devuelve `por_defecto`."""
    if not os.path.exists(ruta):
        return por_defecto
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        try:
            os.replace(ruta, f"{ruta}.corrupto")
        except OSError:
            pass
        return por_defecto

def guardar_json(ruta, datos):
    """Escribe el JSON de forma segura: primero a un archivo temporal y luego
    lo reemplaza, así un cierre inesperado no deja el archivo a medias."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = f"{ruta}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)

# ------------------------------------------------------------
# Perfiles (uno por usuario)
# ------------------------------------------------------------
def cargar_perfil(usuario):
    """Devuelve el perfil del usuario, completando lo que falte con los
    valores por defecto."""
    todos = leer_json(ARCHIVO_PERFILES, {})
    perfil = dict(PERFIL_POR_DEFECTO)
    perfil["favoritas"] = []
    perfil.update(todos.get(usuario, {}))
    if not perfil["nombre"]:
        perfil["nombre"] = usuario
    return perfil

def guardar_perfil(usuario, perfil):
    todos = leer_json(ARCHIVO_PERFILES, {})
    todos[usuario] = perfil
    guardar_json(ARCHIVO_PERFILES, todos)

# ------------------------------------------------------------
# Avisos (registros compartidos por todos los usuarios del dispositivo)
# ------------------------------------------------------------
def cargar_avisos():
    """Lista de avisos (más nuevo primero) o None si nunca se han guardado."""
    return leer_json(ARCHIVO_AVISOS, None)

def guardar_avisos(avisos):
    guardar_json(ARCHIVO_AVISOS, avisos)

def avisos_de_ejemplo(rutas_ejemplo):
    """Avisos de demostración para la primera vez que se abre la app.
    `rutas_ejemplo`: lista de (ruta, tipo, minutos, hace_cuantos_min)."""
    ahora = time.time()
    return [
        {"ruta": r, "tipo": t, "minutos": m, "ts": ahora - hace * 60,
         "propio": False, "autor": ""}
        for r, t, m, hace in rutas_ejemplo
    ]

__all__ = ["DATA_DIR"]
