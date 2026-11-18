"""Cliente de la API de EnRuta Ya! (servicios/api_cliente.py).

La app nunca toca la base de datos: solo habla con la API PHP.

Funcionamiento sin conexión:
  * Todo lo que se lee (recorridos, avisos) se guarda en cache_api.json; si no hay
    red, la app sigue mostrando la última copia.
  * Los votos, avisos y cierres de viaje que no se pudieron enviar quedan en una
    cola y se reenvían solos cuando vuelve la conexión (vaciar_cola).
  * Los recorridos se sincronizan de forma incremental (solo lo que cambió).

Este módulo no importa Kivy: las llamadas son bloqueantes y deben hacerse en un
hilo (main.py lo hace con _en_hilo).
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

try:  # certificados confiables también en Android
    import ssl
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # pragma: no cover
    _CTX = None


class ErrorApi(Exception):
    """Error de la API o de la red.

    sin_red=True  -> no hubo respuesta útil (sin internet, timeout, servidor caído):
                     la acción se puede reintentar más tarde.
    campo         -> campo del formulario al que corresponde el mensaje.
    """

    def __init__(self, mensaje, campo="general", estado=0, sin_red=False):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.campo = campo
        self.estado = estado
        self.sin_red = sin_red


def normalizar_patente(texto):
    return re.sub(r"[\s\-.]", "", str(texto or "")).upper()


def patente_valida(patente):
    """Patentes chilenas: AB1234 (antigua) o BCDF12 (nueva, sin vocales)."""
    return bool(re.fullmatch(r"[A-Z]{2}\d{4}|[BCDFGHJKLPRSTVWXYZ]{4}\d{2}", patente or ""))


_VACIO = {"token": "", "usuario": None, "recorridos": {}, "recorridos_ts": 0,
          "avisos": [], "sync_ts": 0, "cola": []}


class ClienteApi:
    def __init__(self, base_url, carpeta, timeout=8):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout
        self._lock = threading.RLock()
        os.makedirs(carpeta, exist_ok=True)
        self._archivo = os.path.join(carpeta, "cache_api.json")
        self._d = self._leer()

    # ---------------- persistencia local ----------------
    def _leer(self):
        datos = json.loads(json.dumps(_VACIO))
        try:
            with open(self._archivo, encoding="utf-8") as f:
                datos.update(json.load(f))
        except (OSError, ValueError):
            pass
        return datos

    def _guardar(self):
        try:
            tmp = self._archivo + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._d, f, ensure_ascii=False)
            os.replace(tmp, self._archivo)
        except OSError:
            pass  # la caché es un extra: nunca debe romper la app

    # ---------------- HTTP ----------------
    def _peticion(self, metodo, ruta, params=None, cuerpo=None, token=None):
        if not self.base_url:
            raise ErrorApi("Servidor no configurado.", sin_red=True)
        url = f"{self.base_url}?r={ruta}"
        if params:
            url += "&" + urllib.parse.urlencode(params)
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        cab = {"Accept": "application/json"}
        if datos is not None:
            cab["Content-Type"] = "application/json"
        tk = self.token if token is None else token
        if tk:
            cab["X-Token"] = tk
        req = urllib.request.Request(url, data=datos, headers=cab, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=_CTX) as r:
                crudo = r.read()
                return json.loads(crudo) if crudo else {}
        except urllib.error.HTTPError as e:
            try:
                info = json.loads(e.read() or b"{}")
            except ValueError:
                info = {}
            if e.code >= 500:
                raise ErrorApi("Servidor no disponible. Reintenta en un momento.",
                               estado=e.code, sin_red=True)
            raise ErrorApi(info.get("error") or "No se pudo completar la acción.",
                           info.get("campo", "general"), e.code)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            raise ErrorApi("Sin conexión con el servidor.", sin_red=True)

    # ---------------- sesión ----------------
    @property
    def token(self):
        return self._d.get("token", "")

    @property
    def usuario_guardado(self):
        return self._d.get("usuario")

    def _nueva_sesion(self, r):
        with self._lock:
            self._d["token"] = r["token"]
            self._d["usuario"] = r["usuario"]
            self._d["cola"] = []          # la cola pertenece a una sola persona
            self._reiniciar_votos()
            self._guardar()
        return r["usuario"]

    def _reiniciar_votos(self):
        for r in self._d["recorridos"].values():
            r["mi_voto"] = 0
        for a in self._d["avisos"]:
            a["mi_voto"] = 0
            a["es_mio"] = False

    def registrar(self, correo, clave, nombre=""):
        return self._nueva_sesion(self._peticion(
            "POST", "auth_registro", cuerpo={"correo": correo, "clave": clave, "nombre": nombre}))

    def login(self, correo, clave):
        return self._nueva_sesion(self._peticion(
            "POST", "auth_login", cuerpo={"correo": correo, "clave": clave}))

    def perfil(self):
        u = self._peticion("GET", "perfil")["usuario"]
        with self._lock:
            self._d["usuario"] = u
            self._guardar()
        return u

    def cambiar_nombre(self, nombre):
        u = self._peticion("POST", "perfil_nombre", cuerpo={"nombre": nombre})["usuario"]
        with self._lock:
            self._d["usuario"] = u
            self._guardar()
        return u

    def olvidar_sesion(self):
        """Cierra la sesión solo en el teléfono (p. ej. token vencido)."""
        with self._lock:
            self._d["token"], self._d["usuario"], self._d["cola"] = "", None, []
            self._reiniciar_votos()
            self._guardar()

    def cerrar_sesion(self):
        """Cierra la sesión local y avisa al servidor (si hay red)."""
        viejo = self.token
        self.olvidar_sesion()
        if viejo:
            try:
                self._peticion("POST", "auth_logout", token=viejo)
            except ErrorApi:
                pass

    # ---------------- lecturas con caché ----------------
    def recorridos_cache(self):
        with self._lock:
            return list(self._d["recorridos"].values())

    def avisos_cache(self):
        with self._lock:
            return list(self._d["avisos"])

    def ultima_sync(self):
        return self._d.get("sync_ts", 0)

    def recorridos(self, completo=False):
        """Sincroniza y devuelve todos los recorridos. completo=True vuelve a
        bajar todo (así desaparecen los que el admin borró)."""
        with self._lock:
            tiene = bool(self._d["recorridos"])
            desde = 0 if (completo or not tiene) else max(0, int(self._d["recorridos_ts"]) - 5)
        r = self._peticion("GET", "recorridos", {"desde": desde})
        with self._lock:
            if desde == 0:
                self._d["recorridos"] = {}
            for x in r["recorridos"]:
                if x["estado"] == "oculto":
                    self._d["recorridos"].pop(str(x["id"]), None)
                else:
                    self._d["recorridos"][str(x["id"])] = x
            self._d["recorridos_ts"] = r["servidor_ts"]
            self._d["sync_ts"] = time.time()
            self._guardar()
        return self.recorridos_cache()

    def avisos(self):
        r = self._peticion("GET", "avisos")
        with self._lock:
            self._d["avisos"] = r["avisos"]
            self._guardar()
        return self.avisos_cache()

    def recorrido(self, rid):
        """Detalle de un recorrido (con sus avisos); actualiza la caché."""
        r = self._peticion("GET", "recorrido", {"id": rid})["recorrido"]
        with self._lock:
            avisos = r.pop("avisos", [])
            self._d["recorridos"][str(rid)] = {**self._d["recorridos"].get(str(rid), {}), **r}
            self._d["avisos"] = [a for a in self._d["avisos"] if a["recorrido_id"] != rid] + avisos
            self._guardar()
        return r, avisos

    # ---------------- acciones con cola ----------------
    def _accion(self, ruta, cuerpo, unico=None):
        """Envía una acción; si no hay red la deja en cola y devuelve {'en_cola': True}.
        unico: clave del cuerpo que identifica el objetivo (el último voto reemplaza al anterior)."""
        try:
            return self._peticion("POST", ruta, cuerpo=cuerpo)
        except ErrorApi as e:
            if not e.sin_red:
                raise
        with self._lock:
            if unico:
                self._d["cola"] = [c for c in self._d["cola"]
                                   if not (c["ruta"] == ruta and c["cuerpo"].get(unico) == cuerpo.get(unico))]
            self._d["cola"].append({"ruta": ruta, "cuerpo": cuerpo})
            self._guardar()
        return {"en_cola": True}

    def pendientes(self):
        with self._lock:
            return len(self._d["cola"])

    def vaciar_cola(self):
        """Reenvía en orden lo pendiente. Se detiene si no hay red o la sesión
        caducó; descarta lo que el servidor rechace de forma definitiva."""
        enviados = 0
        while True:
            with self._lock:
                item = self._d["cola"][0] if self._d["cola"] else None
            if item is None:
                return enviados
            try:
                self._peticion("POST", item["ruta"], cuerpo=item["cuerpo"])
            except ErrorApi as e:
                if e.sin_red or e.estado == 401:
                    raise
            with self._lock:
                if self._d["cola"] and self._d["cola"][0] == item:
                    self._d["cola"].pop(0)
                    self._guardar()
            enviados += 1

    def votar(self, ruta, objetivo, valor):
        return self._accion(ruta, {"id": objetivo, "valor": valor}, unico="id")

    def crear_aviso(self, aviso_id, recorrido_id, tipo, minutos=0):
        return self._accion("aviso_crear", {"id": aviso_id, "recorrido_id": recorrido_id,
                                            "tipo": tipo, "minutos": minutos})

    def iniciar_viaje(self, recorrido_id, patente="", agendado_para=None):
        """Requiere conexión: el servidor valida la patente o la agenda."""
        cuerpo = {"recorrido_id": recorrido_id, "patente": patente}
        if agendado_para:
            cuerpo["agendado_para"] = agendado_para
        return self._peticion("POST", "viaje_iniciar", cuerpo=cuerpo)

    def terminar_viaje(self, viaje_id):
        return self._accion("viaje_fin", {"id": viaje_id})

    def evento(self, tipo, sesion):
        """Métrica anónima; si falla se descarta."""
        try:
            self._peticion("POST", "evento", cuerpo={"tipo": tipo, "sesion": sesion})
        except ErrorApi:
            pass
