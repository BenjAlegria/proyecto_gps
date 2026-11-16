"""Firebase Authentication (correo y contraseña) para la app Kivy.

Usa Identity Toolkit REST desde hilos de trabajo, sin SDK administrativo.
Las claves de API de Firebase son públicas; jamás guardar contraseñas o
refresh tokens en JSON/ Git. La sesión vive solamente en memoria.
"""
from __future__ import annotations

import re
import threading
import time
import requests


class ErrorFirebaseAuth(Exception):
    def __init__(self, mensaje, campo="general"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo


def validar_correo(correo):
    correo = (correo or "").strip().lower()
    if not re.fullmatch(r"[^\s@]{1,64}@[^\s@]+\.[^\s@]{2,}", correo) or len(correo) > 254:
        raise ErrorFirebaseAuth("Ingresa un correo electrónico válido.", "usuario")
    return correo


def validar_clave(clave, repetir=None):
    if not isinstance(clave, str) or len(clave) < 8:
        raise ErrorFirebaseAuth("La contraseña debe tener al menos 8 caracteres.", "clave")
    if repetir is not None and clave != repetir:
        raise ErrorFirebaseAuth("Las contraseñas no coinciden.", "repetir")


_ERRORES = {
    "EMAIL_EXISTS": ("Este correo ya está registrado.", "usuario"),
    "INVALID_EMAIL": ("Ingresa un correo electrónico válido.", "usuario"),
    "EMAIL_NOT_FOUND": ("Correo o contraseña incorrectos.", "general"),
    "INVALID_PASSWORD": ("Correo o contraseña incorrectos.", "general"),
    "INVALID_LOGIN_CREDENTIALS": ("Correo o contraseña incorrectos.", "general"),
    "USER_DISABLED": ("Esta cuenta fue deshabilitada.", "general"),
    "WEAK_PASSWORD": ("La contraseña no cumple los requisitos de seguridad.", "clave"),
    "TOO_MANY_ATTEMPTS_TRY_LATER": ("Demasiados intentos. Intenta más tarde.", "general"),
    "OPERATION_NOT_ALLOWED": ("Activa el proveedor Correo/Contraseña en Firebase Authentication.", "general"),
    "INVALID_REFRESH_TOKEN": ("La sesión caducó. Inicia sesión de nuevo.", "general"),
    "TOKEN_EXPIRED": ("La sesión caducó. Inicia sesión de nuevo.", "general"),
}


def _leer(respuesta):
    """Sanitiza los errores: nunca mostrar URL con API key/token ni contraseña."""
    codigo = getattr(respuesta, "status_code", 200)
    try:
        data = respuesta.json()
    except (ValueError, TypeError):
        raise ErrorFirebaseAuth("Respuesta inválida de Firebase.") from None
    if isinstance(codigo, int) and codigo >= 400:
        clave = str((data.get("error") or {}).get("message", "")) if isinstance(data.get("error"), dict) else ""
        clave = clave.split(" : ")[0].strip()
        mensaje, campo = _ERRORES.get(clave, ("No se pudo autenticar. Revisa tu conexión y Firebase.", "general"))
        raise ErrorFirebaseAuth(mensaje, campo)
    if not isinstance(data, dict):
        raise ErrorFirebaseAuth("Respuesta inválida de Firebase.")
    return data


class SesionFirebase:
    """Una sola identidad por login; refresh en memoria y protegido por lock."""

    def __init__(self, api_key, transporte=None, reloj=None):
        self.api_key = api_key
        self.http = transporte or requests
        self.reloj = reloj or time.time
        self._lock = threading.RLock()
        self.uid = None
        self.email = None
        self.id_token = None
        self.refresh_token = None
        self.expira = 0

    def _post(self, endpoint, *, datos=None, formulario=None):
        try:
            respuesta = self.http.post(endpoint, params={"key": self.api_key},
                                      json=datos, data=formulario, timeout=12)
            return _leer(respuesta)
        except requests.RequestException:
            raise ErrorFirebaseAuth("No se pudo conectar con Firebase. Comprueba internet.") from None

    def _guardar(self, resultado):
        token = resultado.get("idToken") or resultado.get("id_token")
        refresh = resultado.get("refreshToken") or resultado.get("refresh_token")
        uid = resultado.get("localId") or resultado.get("user_id")
        expira = resultado.get("expiresIn") or resultado.get("expires_in") or "3600"
        if not all(isinstance(v, str) and v for v in (token, refresh, uid)):
            raise ErrorFirebaseAuth("Firebase devolvió una sesión inválida.")
        self.id_token, self.refresh_token, self.uid = token, refresh, uid
        self.expira = self.reloj() + int(expira)
        return uid

    def login(self, correo, clave):
        correo = validar_correo(correo)
        if not clave:
            raise ErrorFirebaseAuth("Escribe tu contraseña.", "clave")
        datos = self._post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
            datos={"email": correo, "password": clave, "returnSecureToken": True})
        with self._lock:
            self._guardar(datos)
            self.email = correo
        return self.uid

    def registrar(self, correo, clave, repetir):
        correo = validar_correo(correo)
        validar_clave(clave, repetir)
        datos = self._post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signUp",
            datos={"email": correo, "password": clave, "returnSecureToken": True})
        with self._lock:
            self._guardar(datos)
            self.email = correo
        return self.uid

    def token(self):
        with self._lock:
            if not self.uid or not self.refresh_token:
                raise ErrorFirebaseAuth("Inicia sesión para sincronizar.")
            if self.id_token and self.expira > self.reloj() + 60:
                return self.id_token
            datos = self._post("https://securetoken.googleapis.com/v1/token",
                               formulario={"grant_type": "refresh_token",
                                           "refresh_token": self.refresh_token})
            self._guardar(datos)
            return self.id_token

    def cerrar(self):
        with self._lock:
            self.uid = self.email = self.id_token = self.refresh_token = None
            self.expira = 0
