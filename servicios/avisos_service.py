"""Reglas de negocio de los avisos, sin widgets ni acceso a red.

Estos avisos son registros locales. No están sincronizados ni verificados
por una empresa de transporte.
"""
import math
import time

TIPOS_VALIDOS = frozenset(("lleno", "asientos", "atrasado", "cambio_ruta"))


def sanear_avisos(registros):
    """Filtra entradas JSON dañadas o incompletas antes de mostrar tarjetas.

    Devuelve una lista nueva, ordenada del reporte más reciente al más viejo.
    Se mantienen campos opcionales compatibles con los JSON existentes.
    """
    if not isinstance(registros, list):
        return []
    resultado = []
    for aviso in registros:
        if not isinstance(aviso, dict):
            continue
        ruta, tipo, ts = aviso.get("ruta"), aviso.get("tipo"), aviso.get("ts")
        if not isinstance(ruta, str) or not ruta or not isinstance(tipo, str) or tipo not in TIPOS_VALIDOS:
            continue
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts):
            continue
        minutos = aviso.get("minutos", 0)
        if isinstance(minutos, bool) or not isinstance(minutos, int) or minutos < 0:
            continue
        resultado.append({
            "ruta": ruta,
            "tipo": tipo,
            "minutos": minutos,
            "ts": ts,
            "propio": aviso.get("propio") is True,
            "autor": aviso.get("autor") if isinstance(aviso.get("autor"), str) else "",
        })
    return sorted(resultado, key=lambda a: a["ts"], reverse=True)


def estado_ruta(avisos, ruta, vigencia_s, ahora=None):
    """(ocupación, atraso, desvío) vigentes, priorizando el más reciente."""
    if ahora is None:
        ahora = time.time()
    vigentes = [a for a in sanear_avisos(avisos)
                if a["ruta"] == ruta and 0 <= ahora - a["ts"] <= vigencia_s]
    ocupacion = next((a for a in vigentes if a["tipo"] in ("lleno", "asientos")), None)
    atraso = next((a for a in vigentes if a["tipo"] == "atrasado"), None)
    cambio = next((a for a in vigentes if a["tipo"] == "cambio_ruta"), None)
    return ocupacion, atraso, cambio


def historial_reciente(avisos, historial_s, ahora=None):
    """Descarta datos dañados, futuros y anteriores al límite de historial."""
    if ahora is None:
        ahora = time.time()
    return [a for a in sanear_avisos(avisos)
            if 0 <= ahora - a["ts"] <= historial_s]
