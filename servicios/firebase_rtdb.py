"""Firebase Realtime Database opcional por REST; sin dependencias Android.

La sesión anónima de Firebase es independiente del login local. Se usa
SOLO para compartir avisos sin nombre, IP ni GPS. Credenciales de
servicio/admin NUNCA deben distribuirse con la aplicación.

Para habilitar: ENRUTA_FIREBASE_API_KEY y ENRUTA_FIREBASE_DATABASE_URL.
"""
from __future__ import annotations

import os
import re
import threading
import time
from urllib.parse import urlparse

import requests


class FirebaseError(RuntimeError):
    """Error resumido, sin URL con token ni información sensible."""


def configuracion(entorno=None):
    if entorno is None:
        entorno = os.environ
    api_key = entorno.get("ENRUTA_FIREBASE_API_KEY", "").strip()
    url = entorno.get("ENRUTA_FIREBASE_DATABASE_URL", "").strip().rstrip("/")
    if not api_key or not url:
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.port is not None
            or parsed.username or parsed.password or parsed.path
            or parsed.query or parsed.fragment
            or not (host.endswith(".firebasedatabase.app")
                    or host.endswith(".firebaseio.com"))):
        raise FirebaseError("La URL de Firebase debe ser la URL HTTPS oficial de Realtime Database.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{15,200}", api_key):
        raise FirebaseError("La clave web de Firebase no tiene un formato válido.")
    return api_key, url


class FirebaseReportes:
    def __init__(self, api_key, database_url, transporte=None, reloj=None):
        self.api_key = api_key
        self.url = database_url.rstrip("/")
        self.transporte = transporte or requests
        self.reloj = reloj or time.time
        self.uid = None
        self.id_token = None
        self.refresh_token = None
        self.expira = 0
        self._lock = threading.RLock()

    def _json(self, respuesta, etapa):
        try:
            respuesta.raise_for_status()
            return respuesta.json()
        except (requests.RequestException, ValueError):
            # Nunca propagar la URL: contiene auth=<ID_TOKEN>.
            raise FirebaseError("Firebase no respondió en " + etapa + ". Verifica reglas y red.") from None

    def _autenticar(self):
        with self._lock:
            if self.id_token and self.expira > self.reloj() + 60:
                return self.id_token
            try:
                if self.refresh_token:
                    res = self.transporte.post(
                        "https://securetoken.googleapis.com/v1/token",
                        params={"key": self.api_key},
                        data={"grant_type": "refresh_token",
                              "refresh_token": self.refresh_token},
                        timeout=8,
                    )
                    data = self._json(res, "renovar sesión")
                    token, refresh, uid = (data.get("id_token"),
                                          data.get("refresh_token"), data.get("user_id"))
                    segundos = data.get("expires_in", 3600)
                else:
                    res = self.transporte.post(
                        "https://identitytoolkit.googleapis.com/v1/accounts:signUp",
                        params={"key": self.api_key},
                        json={"returnSecureToken": True},
                        timeout=8,
                    )
                    data = self._json(res, "autenticación anónima")
                    token, refresh, uid = (data.get("idToken"),
                                          data.get("refreshToken"), data.get("localId"))
                    segundos = data.get("expiresIn", 3600)
            except requests.RequestException:
                raise FirebaseError("Sin conexión con Firebase Authentication.") from None
            if not all(isinstance(x, str) and x for x in (token, refresh, uid)):
                raise FirebaseError("Firebase no devolvió credenciales válidas.")
            self.uid = uid
            self.id_token = token
            self.refresh_token = refresh
            self.expira = self.reloj() + int(segundos)
            return token

    def publicar(self, aviso):
        """Crea registro una vez. No se publica identidad ni lat/lon."""
        identificador = aviso.get("id", "")
        if not isinstance(identificador, str) or not re.fullmatch(r"[a-f0-9]{32}", identificador):
            raise FirebaseError("Identificador de aviso inválido.")
        ruta, tipo, ts, minutos = [aviso.get(k) for k in ("ruta", "tipo", "ts", "minutos")]
        if (not isinstance(ruta, str) or len(ruta) > 100 or not ruta
                or tipo not in ("lleno", "asientos", "atrasado", "cambio_ruta")
                or type(minutos) is not int or not 0 <= minutos <= 180
                or isinstance(ts, bool) or not isinstance(ts, (int, float))):
            raise FirebaseError("Datos de aviso no válidos.")
        token = self._autenticar()
        datos = {"uid": self.uid, "ruta": ruta, "tipo": tipo,
                 "minutos": minutos, "ts": int(ts)}
        try:
            res = self.transporte.put(
                f"{self.url}/reportes/{identificador}.json",
                params={"auth": token}, json=datos, timeout=8)
            return self._json(res, "publicar aviso")
        except requests.RequestException:
            raise FirebaseError("Sin conexión al guardar aviso remoto.") from None

    def recientes(self, limite=100):
        token = self._autenticar()
        try:
            res = self.transporte.get(
                f"{self.url}/reportes.json",
                params={"auth": token, "orderBy": '"ts"',
                        "limitToLast": min(100, max(1, int(limite)))},
                timeout=8)
            data = self._json(res, "consultar avisos")
        except requests.RequestException:
            raise FirebaseError("Sin conexión al consultar avisos remotos.") from None
        if not isinstance(data, dict):
            return []
        ahora = self.reloj()
        salida = []
        for id_aviso, a in data.items():
            if not isinstance(a, dict) or not isinstance(id_aviso, str):
                continue
            if not re.fullmatch(r"[a-f0-9]{32}", id_aviso):
                continue
            if (not isinstance(a.get("ruta"), str)
                    or a.get("tipo") not in ("lleno", "asientos", "atrasado", "cambio_ruta")
                    or type(a.get("minutos")) is not int
                    or type(a.get("ts")) not in (int, float)):
                continue
            if not 0 <= ahora - a["ts"] <= 7200:
                continue
            salida.append({"id": id_aviso, "ruta": a["ruta"], "tipo": a["tipo"],
                           "minutos": a["minutos"], "ts": a["ts"],
                           "fuente": "firebase", "propio": False, "autor": ""})
        return sorted(salida, key=lambda x: x["ts"], reverse=True)
