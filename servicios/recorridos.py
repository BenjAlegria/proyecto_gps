"""Cálculos independientes de Kivy para recorridos y buses simulados.

La posición calculada NO procede del GPS de un bus; solo alimenta la demo.
Mantener estos cálculos separados permite reemplazar MapView más adelante.
"""
import re


def minutos_desde_texto(texto):
    """Convierte '1 h 20 min' en 80; tolera valores vacíos o inválidos."""
    if not isinstance(texto, str):
        return 0
    horas = re.search(r"(\d+)\s*h", texto)
    mins = re.search(r"(\d+)\s*min", texto)
    return (int(horas.group(1)) * 60 if horas else 0) + (
        int(mins.group(1)) if mins else 0
    )


def posicion_bus_demo(origen, destino, duracion, espera):
    """Posición lineal DEMOSTRATIVA entre (lat, lon) de origen y destino.

    La fracción se mantiene entre 0.15 y 0.8, igual que en la versión
    anterior. No debe emplearse como telemetría ni ubicación verificada.
    """
    lat, lon = origen
    dlat, dlon = destino
    dur = max(minutos_desde_texto(duracion), 1)
    fraccion = min(0.8, max(0.15, minutos_desde_texto(espera) / dur))
    return lat + (dlat - lat) * fraccion, lon + (dlon - lon) * fraccion
