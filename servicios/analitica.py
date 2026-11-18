"""Medición MJV App local: sin cuentas, coordenadas, IP ni contraseñas.

Los eventos se guardan en data/analitica_eventos.jsonl; no se suben a
Firebase. Permite reconstruir la procedencia de los KPIs de la defensa.
"""
from __future__ import annotations

import json
import os
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

from config import DATA_DIR

RUTA_EVENTOS = os.path.join(DATA_DIR, "analitica_eventos.jsonl")
EVENTOS = frozenset({
    "aplicacion_iniciada", "aplicacion_cerrada", "login_exitoso",
    "login_fallido", "registro_exitoso", "pantalla_abierta",
    "busqueda_iniciada", "recorrido_consultado", "favorito_agregado",
    "favorito_eliminado", "aviso_publicado", "error_ubicacion",
})
PANTALLAS = frozenset({
    "home", "recorridos", "compartir", "avisos", "perfil", "ajustes", "analitica"
})
_BLOQUEO = threading.Lock()


class Registrador:
    """Eventos pseudónimos por ejecución. Nunca identifica al usuario."""

    def __init__(self, archivo=RUTA_EVENTOS, reloj=None, cronometro=None, activo=True):
        self.archivo = archivo
        self.sesion = uuid.uuid4().hex
        self.activo = activo
        self.reloj = reloj or time.time
        self.cronometro = cronometro or time.monotonic
        self._intentos = {}

    def registrar(self, nombre, *, pantalla=None, intento=None, duracion_ms=None):
        if not self.activo:
            return False
        if nombre not in EVENTOS:
            raise ValueError("Evento no permitido")
        evento = {
            "id": uuid.uuid4().hex,
            "sesion": self.sesion,
            "evento": nombre,
            "ts": datetime.fromtimestamp(self.reloj(), timezone.utc).isoformat(),
        }
        if pantalla in PANTALLAS:
            evento["pantalla"] = pantalla
        if isinstance(intento, str) and len(intento) == 32:
            evento["intento"] = intento
        if isinstance(duracion_ms, (int, float)) and not isinstance(duracion_ms, bool):
            if 0 <= duracion_ms <= 900_000:
                evento["duracion_ms"] = int(duracion_ms)
        try:
            with _BLOQUEO:
                os.makedirs(os.path.dirname(self.archivo), exist_ok=True)
                with open(self.archivo, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
            return True
        except OSError:
            return False

    def iniciar_busqueda(self):
        if not self.activo:
            return None
        intento = uuid.uuid4().hex
        self._intentos[intento] = self.cronometro()
        self.registrar("busqueda_iniciada", intento=intento, pantalla="recorridos")
        return intento

    def completar_busqueda(self, intento):
        inicio = self._intentos.pop(intento, None)
        if inicio is None:
            return False
        ms = max(0, round((self.cronometro() - inicio) * 1000))
        return self.registrar("recorrido_consultado", intento=intento,
                             duracion_ms=ms, pantalla="recorridos")


def leer_eventos(archivo=RUTA_EVENTOS):
    eventos = []
    try:
        with open(archivo, encoding="utf-8") as fh:
            for i, linea in enumerate(fh):
                if i >= 100_000:
                    break
                try:
                    e = json.loads(linea)
                except (ValueError, TypeError):
                    continue
                if (isinstance(e, dict) and e.get("evento") in EVENTOS
                        and isinstance(e.get("sesion"), str)
                        and isinstance(e.get("ts"), str)):
                    eventos.append(e)
    except OSError:
        pass
    return eventos


def resumen(eventos):
    """KPIs con denominadores explícitos y None si no hay evidencia."""
    sesiones = set()
    intentos = set()
    exitos = set()
    duraciones = {}
    avisos = 0
    favoritos = 0
    fechas = []
    for e in eventos:
        if not isinstance(e, dict):
            continue
        evento = e.get("evento")
        sesion = e.get("sesion")
        if isinstance(sesion, str) and sesion:
            sesiones.add(sesion)
        fecha = e.get("ts")
        if isinstance(fecha, str) and fecha:
            fechas.append(fecha)
        intento = e.get("intento")
        if evento == "busqueda_iniciada" and isinstance(intento, str):
            intentos.add(intento)
        elif evento == "recorrido_consultado" and isinstance(intento, str):
            exitos.add(intento)
            ms = e.get("duracion_ms")
            if type(ms) is int and 0 <= ms <= 900_000:
                duraciones[intento] = ms / 1000
        elif evento == "aviso_publicado":
            avisos += 1
        elif evento == "favorito_agregado":
            favoritos += 1
    aciertos = len(intentos & exitos)
    # Un tiempo sin evento de entrada correspondiente no es un dato
    # válido de la tarea; jamás contaminar la mediana con registros sueltos.
    tiempos = [v for k, v in duraciones.items() if k in intentos]
    return {
        "sesiones": len(sesiones),
        "eventos": len(eventos),
        "busquedas": len(intentos),
        "consultas_exitosas": aciertos,
        "exito_busqueda_pct": round(aciertos / len(intentos) * 100, 1)
        if intentos else None,
        "mediana_busqueda_s": round(statistics.median(tiempos), 2)
        if tiempos else None,
        "avisos_publicados": avisos,
        "favoritos_agregados": favoritos,
        "periodo_inicio_utc": min(fechas) if fechas else None,
        "periodo_fin_utc": max(fechas) if fechas else None,
    }
