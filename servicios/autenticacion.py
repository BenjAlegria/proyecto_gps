"""Autenticación: registro y login de usuarios.

Las contraseñas NUNCA se guardan en texto plano: se guarda un hash
PBKDF2-SHA256 con una sal aleatoria distinta por usuario. Los usuarios
quedan en data/usuarios.json (ver almacenamiento.py).
"""

import hashlib
import hmac
import os
import re
import time

from config import ARCHIVO_USUARIOS
from servicios.almacenamiento import guardar_json, leer_json

ITERACIONES = 120_000
USUARIO_MIN, USUARIO_MAX = 3, 20
CLAVE_MIN = 6


class ErrorAutenticacion(Exception):
    """Error de validación con un mensaje listo para mostrar al usuario.
    `campo` indica en qué campo del formulario mostrarlo."""

    def __init__(self, mensaje, campo="general"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


def _hash(clave, sal_hex):
    return hashlib.pbkdf2_hmac(
        "sha256", clave.encode("utf-8"), bytes.fromhex(sal_hex), ITERACIONES
    ).hex()


def normalizar_usuario(usuario):
    return (usuario or "").strip().lower()


def validar_usuario(usuario):
    """Reglas del nombre de usuario (se muestra el error bajo el campo)."""
    if not usuario:
        raise ErrorAutenticacion("Escribe un nombre de usuario", "usuario")
    if not USUARIO_MIN <= len(usuario) <= USUARIO_MAX:
        raise ErrorAutenticacion(
            f"Debe tener entre {USUARIO_MIN} y {USUARIO_MAX} caracteres", "usuario")
    if not re.fullmatch(r"[a-z0-9_.]+", usuario):
        raise ErrorAutenticacion(
            "Solo letras, números, punto y guion bajo", "usuario")


def validar_contrasena(clave, repetir=None):
    """DÓNDE SE VALIDA LA CONTRASEÑA al registrarse:
    mínimo 6 caracteres, al menos una letra y un número, y que coincida
    con la repetición."""
    if len(clave) < CLAVE_MIN:
        raise ErrorAutenticacion(
            f"La contraseña debe tener al menos {CLAVE_MIN} caracteres", "clave")
    if not (re.search(r"[A-Za-z]", clave) and re.search(r"\d", clave)):
        raise ErrorAutenticacion(
            "Debe incluir al menos una letra y un número", "clave")
    if repetir is not None and clave != repetir:
        raise ErrorAutenticacion("Las contraseñas no coinciden", "repetir")


def registrar(usuario, clave, repetir):
    """Crea la cuenta y la guarda en usuarios.json. Devuelve el usuario
    normalizado. Lanza ErrorAutenticacion si algo no es válido."""
    usuario = normalizar_usuario(usuario)
    validar_usuario(usuario)
    validar_contrasena(clave, repetir)
    usuarios = leer_json(ARCHIVO_USUARIOS, {})
    if usuario in usuarios:
        raise ErrorAutenticacion("Ese usuario ya existe", "usuario")
    sal = os.urandom(16).hex()
    usuarios[usuario] = {
        "sal": sal,
        "hash": _hash(clave, sal),
        "creado": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    guardar_json(ARCHIVO_USUARIOS, usuarios)
    return usuario


def iniciar_sesion(usuario, clave):
    """Comprueba usuario y contraseña contra usuarios.json. Devuelve el
    usuario normalizado. El mensaje de error es el mismo si falla el
    usuario o la contraseña (no revela cuál de los dos)."""
    usuario = normalizar_usuario(usuario)
    if not usuario or not clave:
        raise ErrorAutenticacion("Completa usuario y contraseña")
    registro = leer_json(ARCHIVO_USUARIOS, {}).get(usuario)
    if registro is None or not hmac.compare_digest(
            registro["hash"], _hash(clave, registro["sal"])):
        raise ErrorAutenticacion("Usuario o contraseña incorrectos")
    return usuario
