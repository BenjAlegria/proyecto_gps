import math
import os
import threading
import time
import traceback
import uuid
from datetime import datetime

from kivy.animation import Animation
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             ObjectProperty, StringProperty)
from kivy.uix.screenmanager import Screen
from kivy.utils import platform
from kivy_garden.mapview import MapLayer, MapMarker, MapMarkerPopup, MapView  # noqa: F401
try:
    from plyer import gps
except Exception:
    gps = None

from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import (MDDialog, MDDialogButtonContainer,
                               MDDialogHeadlineText, MDDialogSupportingText)
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

from config import (CONFIG_REMOTA_DEFECTO, HISTORIAL_S, ICONO_BUS, LOG_ERRORES,
                    OPCIONES_ATRASO)
try:
    from config import API_URL  # https://tu-dominio/api/index.php
except ImportError:
    API_URL = ""
from datos_rutas import COORDENADAS, GRIS, NARANJA, ROJO, TIPOS_AVISO, VERDE
from servicios import almacenamiento, analitica, config_remota, ubicacion
from servicios.geo import largo_m, tramo_restante
from servicios.api_cliente import (ClienteApi, ErrorApi, normalizar_patente,
                                   patente_valida)
from servicios.notificaciones import notificar as enviar_notificacion
from tema import PaletaVisual
from servicios.ruteo import RuteadorCalles
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICONOS_NIVEL = {"Novato": "account-outline", "Colaborador": "account-check-outline",
                "Confiable": "shield-check-outline", "Verificador": "shield-star-outline"}


# ------------------------------------------------------------
# Registro de errores: si algo falla dentro de la app, en vez de cerrarse
# se guarda el detalle completo en crash_log.txt y la app sigue funcionando.
# ------------------------------------------------------------
def registrar_error(exc):
    texto = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(texto)
    try:
        with open(LOG_ERRORES, "a", encoding="utf-8") as f:
            f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n{texto}\n")
    except OSError:
        pass


class ManejadorErrores(ExceptionHandler):
    def handle_exception(self, inst):
        if not isinstance(inst, Exception):  # Ctrl+C, cerrar la ventana, etc.
            return ExceptionManager.RAISE
        registrar_error(inst)
        return ExceptionManager.PASS


ExceptionManager.add_handler(ManejadorErrores())


# ------------------------------------------------------------
# Widgets propios (su diseño está en root.kv; HomeBusCard en componentes.kv)
# ------------------------------------------------------------
class LineaCard(MDCard):
    ruta = StringProperty("")
    detalle = StringProperty("")
    minutos = StringProperty("")
    aviso = StringProperty("")
    aviso_color = ListProperty(GRIS)
    rid = NumericProperty(0)


class HomeBusCard(MDCard):
    ruta = StringProperty("")
    detalle = StringProperty("")
    minutos = StringProperty("")
    aviso = StringProperty("")
    aviso_color = ListProperty(GRIS)
    ocupacion = StringProperty("Sin dato")
    actualizacion = StringProperty("Sin reportes recientes")
    estado_icono = StringProperty("information-outline")
    rid = NumericProperty(0)


class AvisoCard(MDCard):
    aviso_id = StringProperty("")
    icono = StringProperty("bell")
    titulo = StringProperty("")
    detalle = StringProperty("")
    color = ListProperty(GRIS)
    antiguedad = StringProperty("")
    vencido = BooleanProperty(False)
    autor = StringProperty("")
    nivel = StringProperty("")
    votos_ok = NumericProperty(0)
    votos_mal = NumericProperty(0)
    mi_voto = NumericProperty(0)
    propio = BooleanProperty(False)


class CargaScreen(Screen):
    pass


class LoginScreen(Screen):
    pass


class RegistroScreen(Screen):
    pass


class HomeScreen(Screen):
    pass


class RecorridosScreen(Screen):
    pass


class DetalleScreen(Screen):
    pass


class CompartirScreen(Screen):
    pass


class AvisosScreen(Screen):
    pass


class PerfilScreen(Screen):
    pass


class AjustesScreen(Screen):
    pass


class AvisoSnackbar(MDSnackbar):
    """MDSnackbar que no revienta al crearse (FBO de alto 0 en KivyMD 2.0.0)."""

    def init_fbos(self):
        self.size = self._clamp_size(*self.size)
        super().init_fbos()


class LineaMapLayer(MapLayer):
    """Dibuja una o varias líneas (punto A -> punto B) sobre el mapa."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lineas = []

    def fijar(self, lineas):
        self.lineas = [list(l) for l in lineas if len(l) >= 2]
        self.reposition()

    def reposition(self):
        mapa = self.parent
        self.canvas.clear()
        if mapa is None or not self.lineas:
            return
        with self.canvas:
            Color(0.16, 0.45, 0.87, 0.9)
            for linea in self.lineas:
                pts = []
                for lat, lon in linea:
                    x, y = mapa.get_window_xy_from(lat, lon, mapa.zoom)
                    pts.extend((x, y))
                Line(points=pts, width=dp(3), cap="round", joint="round")


# ------------------------------------------------------------
# Aplicación
# ------------------------------------------------------------
class InterurbanoApp(MDApp):
    ui = ObjectProperty(None)
    safe_bottom = NumericProperty(0)
    compartiendo = BooleanProperty(False)
    en_linea = BooleanProperty(True)
    texto_conexion = StringProperty("")
    id_detalle = NumericProperty(0)
    # "" = nadie · "invitado" · "registrado" · "admin"
    rol = StringProperty("")

    menu_origen = None
    menu_linea = None
    menu_atraso = None
    menu_recorrido_home = None
    dialogo = None
    marcador_yo = None
    gps_activo = False
    panel_expandido = False
    consentimiento = False
    notificar_favoritas = True
    solo_favoritas = False
    viajes = 0
    config = {}
    fuente_config = ""

    def build(self):
        self.ui = PaletaVisual()
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.bind(theme_style=self._aplicar_tema_visual)
        self._aplicar_tema_visual()
        self.title = "EnRuta Ya!"
        self.cliente = ClienteApi(API_URL, self.user_data_dir)
        self.ruteador = RuteadorCalles(self.user_data_dir)
        # Datos de la base de datos (llegan por la API; la caché local cubre los cortes).
        self.recorridos = {}          # id -> recorrido normalizado
        self.localidades = {}         # origen -> [recorridos]
        self.coords = dict(COORDENADAS)
        self.avisos = []              # más nuevo primero
        self._avisos_vistos = set()
        self._avisos_cargados = False
        self._marcadores = []
        self._marc_detalle = []
        self._capa_home = None
        self._capa_detalle = None
        # Sesión y perfil
        self.usuario_actual = ""
        self.nombre_visible = ""
        self.puntos = 0
        self.nivel = {"nombre": "Novato", "faltan": 0}
        self.favoritas = []           # ids de recorrido como texto
        self._cargando = False
        self._auth_generacion = 0
        self._auth_en_progreso = False
        # Estado de pantallas
        self.linea_actual = 0         # id del recorrido en el que voy
        self.recorrido_home = 0       # 0 = todos
        self.origen_actual = ""
        self.viaje_id = None
        self._viaje_pendiente = None
        self._pantalla_previa = "recorridos"
        self._ultimo_aviso = {}
        self._sync_ocupado = False
        self._sync_completo = False
        # Ubicación
        self.gps_activo = False
        self.marcador_yo = None
        self._solicitud_ubicacion = 0
        self._ip_consulta_pendiente = False
        # Métricas: nunca medir antes de pedir consentimiento explícito.
        self.medidor = analitica.Registrador(activo=False)
        self._medicion_intento = None
        self._sesion_metricas = uuid.uuid4().hex[:16]
        self.config, self.fuente_config = config_remota.cargar_local()
        Builder.load_file(os.path.join(BASE_DIR, "componentes.kv"))
        return Builder.load_file(os.path.join(BASE_DIR, "root.kv"))

    # --------------------------------------------------------
    # Tema
    # --------------------------------------------------------
    def _aplicar_tema_visual(self, *args):
        self.ui.aplicar(self.theme_cls.theme_style == "Dark")
        Clock.schedule_once(self._sincronizar_colores_md)

    def _sincronizar_colores_md(self, *args):
        colores = {"primaryColor": self.ui.azul, "surfaceColor": self.ui.fondo,
                   "surfaceContainerColor": self.ui.tarjeta,
                   "surfaceContainerHighColor": self.ui.tarjeta,
                   "onSurfaceColor": self.ui.texto,
                   "onSurfaceVariantColor": self.ui.secundario,
                   "outlineColor": self.ui.borde, "errorColor": self.ui.rojo}
        for nombre, color in colores.items():
            setattr(self.theme_cls, nombre, color)

    # --------------------------------------------------------
    # Ciclo de vida
    # --------------------------------------------------------
    def on_start(self):
        Window.softinput_mode = "below_target"
        Window.bind(size=self._actualizar_zona_segura)
        self._actualizar_zona_segura()
        try:
            self._capa_home = LineaMapLayer()
            self._pantalla("home").ids.mapa.add_layer(self._capa_home, mode="window")
            self._capa_detalle = LineaMapLayer()
            self._pantalla("detalle").ids.mapa_detalle.add_layer(self._capa_detalle, mode="window")
        except Exception as e:
            registrar_error(e)
        # 1) Se muestra de inmediato lo último guardado (funciona sin internet).
        self._aplicar_datos(self.cliente.recorridos_cache(), self.cliente.avisos_cache())
        self._aplicar_config(self.config, self.fuente_config)
        self.actualizar_config_remota()
        self._marcar_conexion(None)
        Clock.schedule_interval(lambda dt: self.refrescar_avisos(), 60)
        # 2) Cada 45 s se reenvía lo pendiente y se recarga desde la base de datos.
        Clock.schedule_interval(lambda dt: self.sincronizar(), 45)
        Clock.schedule_once(self._terminar_inicio, 0.4)

    def _terminar_inicio(self, *args):
        if self.root.ids.sm.current != "carga" or self._auth_en_progreso:
            return
        usuario = self.cliente.usuario_guardado
        if usuario and self.cliente.token:
            self._entrar(usuario, restaurada=True)
        else:
            self.cambiar_pantalla("login")
        self.sincronizar(completo=True)

    def on_pause(self):
        return True  # Android: mantener la app viva en segundo plano

    def on_resume(self):
        # Al volver (o al recuperar red) se recargan los datos.
        self.sincronizar()

    def on_stop(self):
        self._medir("aplicacion_cerrada")
        Window.unbind(size=self._actualizar_zona_segura)
        self.detener_gps()
        self._guardar_perfil()

    def _actualizar_zona_segura(self, *args):
        self.safe_bottom = 0
        if platform != "android":
            return
        try:
            from jnius import autoclass
            actividad = autoclass("org.kivy.android.PythonActivity").mActivity
            decor = actividad.getWindow().getDecorView()
            insets = decor.getRootWindowInsets()
            if insets is not None:
                visible = autoclass("android.graphics.Rect")()
                decor.getWindowVisibleDisplayFrame(visible)
                self.safe_bottom = max(0, min(insets.getStableInsetBottom(),
                                              Window.height - visible.height()))
        except Exception:
            pass

    def cambiar_pantalla(self, nombre):
        anterior = self.root.ids.sm.current
        self.root.ids.sm.current = nombre
        if nombre != anterior:
            self._medir("pantalla_abierta", pantalla=nombre)
            if nombre == "recorridos":
                self._medicion_intento = self.medidor.iniciar_busqueda()
            elif anterior == "recorridos":
                self._medicion_intento = None

    def _pantalla(self, nombre):
        return self.root.ids.sm.get_screen(nombre)

    @property
    def es_invitado(self):
        return self.rol == "invitado"

    # --------------------------------------------------------
    # Utilidades: hilos, diálogos, avisos en pantalla
    # --------------------------------------------------------
    def _en_hilo(self, tarea, listo):
        """Ejecuta `tarea` fuera del hilo de dibujo y llama a listo(resultado, error) dentro de él."""
        def trabajo():
            try:
                res, err = tarea(), None
            except ErrorApi as e:
                res, err = None, e
            except Exception as e:  # nunca dejar un hilo colgado
                registrar_error(e)
                res, err = None, ErrorApi("Ocurrió un error inesperado.")
            Clock.schedule_once(lambda dt: listo(res, err))
        threading.Thread(target=trabajo, daemon=True, name="enruta-api").start()

    def _dialogo(self, titulo, texto, botones):
        """botones: [(texto, accion o None)]; el diálogo siempre se cierra al tocar."""
        def cerrar_y(accion):
            def al_tocar(*a):
                self.dialogo.dismiss()
                if accion:
                    accion()
            return al_tocar
        self.dialogo = MDDialog(
            MDDialogHeadlineText(text=titulo),
            MDDialogSupportingText(text=texto),
            MDDialogButtonContainer(
                *[MDButton(MDButtonText(text=t), style="text", on_release=cerrar_y(a))
                  for t, a in botones], spacing="8dp"))
        self.dialogo.open()

    def _snack(self, texto):
        try:
            AvisoSnackbar(MDSnackbarText(text=texto), y=dp(80),
                          pos_hint={"center_x": 0.5}, size_hint_x=0.9).open()
        except Exception as e:
            registrar_error(e)

    def notificar(self, titulo, mensaje):
        enviar_notificacion(titulo, mensaje, mostrar_en_app=self._snack)

    def _medir(self, tipo, **datos):
        """Métrica anónima: solo si la persona aceptó (Ajustes) y sin datos personales."""
        self.medidor.registrar(tipo, **datos)
        if self.medidor.activo:
            threading.Thread(target=self.cliente.evento, args=(tipo, self._sesion_metricas),
                             daemon=True).start()

    def _hace(self, ts):
        if not ts:
            return "nunca"
        minutos = int((time.time() - ts) // 60)
        if minutos < 1:
            return "recién"
        if minutos < 60:
            return f"hace {minutos} min"
        if minutos < 1440:
            return f"hace {minutos // 60} h"
        return f"hace {minutos // 1440} d"

    def _requiere_cuenta(self, accion):
        """Solo las cuentas registradas pueden votar, avisar y compartir."""
        if self.rol in ("registrado", "admin"):
            return True
        self._dialogo("Necesitas una cuenta",
                      f"Como invitado puedes mirar recorridos y avisos. "
                      f"Crea una cuenta o inicia sesión para {accion}.",
                      [("Ahora no", None), ("Iniciar sesión", self.cerrar_sesion)])
        return False

    # --------------------------------------------------------
    # Datos desde la base de datos (con caché y recarga al volver la red)
    # --------------------------------------------------------
    def sincronizar(self, manual=False, completo=False):
        """Reenvía lo pendiente y recarga recorridos y avisos. Si no hay conexión,
        la app sigue con la última copia y reintenta sola."""
        if self._sync_ocupado:
            return
        self._sync_ocupado = True
        completo = completo or not self._sync_completo
        c = self.cliente

        def tarea():
            registrado = bool(c.token)
            enviados = c.vaciar_cola() if registrado else 0
            recs = c.recorridos(completo=completo)
            avisos = c.avisos()
            usuario = c.perfil() if registrado else None
            return {"recs": recs, "avisos": avisos, "usuario": usuario,
                    "enviados": enviados, "completo": completo}

        self._en_hilo(tarea, lambda res, err: self._sync_listo(res, err, manual))

    def _sync_listo(self, res, err, manual):
        self._sync_ocupado = False
        if err:
            if err.sin_red:
                self._marcar_conexion(False)
                if manual:
                    self._snack("Sin conexión: se muestran los últimos datos guardados.")
            elif err.estado == 401:
                self._sesion_caducada()
            elif manual:
                self._snack(err.mensaje)
            return
        self._sync_completo = self._sync_completo or res["completo"]
        self._marcar_conexion(True)
        if res["usuario"] and self.rol in ("registrado", "admin"):
            self._aplicar_usuario(res["usuario"])
        self._aplicar_datos(res["recs"], res["avisos"])
        if manual:
            self._snack("Datos actualizados.")

    def _marcar_conexion(self, ok):
        recuperada = ok is True and not self.en_linea
        if ok is not None:
            self.en_linea = ok
        pend = self.cliente.pendientes()
        extra = f" · {pend} acción(es) pendiente(s)" if pend else ""
        if self.en_linea:
            self.texto_conexion = "Conectado" + extra
        else:
            self.texto_conexion = f"Sin conexión · datos de {self._hace(self.cliente.ultima_sync())}" + extra
        try:
            self._pantalla("ajustes").ids.conexion_estado.text = (
                self.texto_conexion + (f"\nÚltima actualización: {self._hace(self.cliente.ultima_sync())}"
                                       if self.en_linea else ""))
        except Exception:
            pass
        if recuperada:
            self._snack("Conexión recuperada. Datos actualizados.")

    def _sesion_caducada(self):
        self._snack("Tu sesión caducó. Inicia sesión de nuevo.")
        self.cliente.olvidar_sesion()
        self.cerrar_sesion()

    def _normalizar(self, x):
        base = [(float(p[0]), float(p[1])) for p in x.get("linea", [])]
        calles = self.ruteador.cacheada(base) if len(base) >= 2 else None
        return {
            "id": int(x["id"]), "ruta": x["nombre"], "origen": x["origen"], "destino": x["destino"],
            "parada": x.get("parada") or "Parada no indicada",
            "frecuencia": x.get("frecuencia") or "No indicada",
            "duracion": f'{x["duracion_min"]} min' if x.get("duracion_min") else "No indicada",
            "tarifa": f'${int(x["tarifa"]):,}'.replace(",", ".") if x.get("tarifa") else "No indicada",
            "estado": x.get("estado", "pendiente"),
            "votos_ok": int(x.get("votos_ok", 0)), "votos_mal": int(x.get("votos_mal", 0)),
            "mi_voto": int(x.get("mi_voto", 0)),
            "linea_api": base, "linea": calles or base, "por_calles": bool(calles),
        }

    def _aplicar_datos(self, recs, avisos):
        self.recorridos = {}
        for x in recs:
            try:
                r = self._normalizar(x)
                self.recorridos[r["id"]] = r
            except (KeyError, TypeError, ValueError) as e:
                registrar_error(e)
        self.coords = dict(COORDENADAS)
        loc = {}
        for r in self.recorridos.values():
            loc.setdefault(r["origen"], []).append(r)
            if r["linea"]:
                self.coords.setdefault(r["origen"], r["linea"][0])
                self.coords.setdefault(r["destino"], r["linea"][-1])
        self.localidades = {k: sorted(v, key=lambda r: r["ruta"]) for k, v in sorted(loc.items())}
        self._aplicar_avisos(avisos)
        if self.origen_actual and self.origen_actual not in self.localidades:
            self.origen_actual = ""
        self._pintar_perfil()
        self.refrescar_avisos()

    def _aplicar_avisos(self, avisos):
        limite = time.time() - HISTORIAL_S
        lista = sorted((a for a in avisos if a.get("ts", 0) >= limite and a.get("tipo") in TIPOS_AVISO),
                       key=lambda a: a["ts"], reverse=True)
        if self._avisos_cargados and self.notificar_favoritas:
            for a in lista:
                if (a["id"] not in self._avisos_vistos and not a.get("es_mio")
                        and str(a["recorrido_id"]) in self.favoritas and time.time() - a["ts"] < 900):
                    self.notificar(a["ruta"], self._titulo_aviso(a))
        self._avisos_vistos |= {a["id"] for a in lista}
        self._avisos_cargados = True
        self.avisos = lista

    def _buscar_recorrido(self, ref):
        """Acepta el id (número o texto) o el nombre del recorrido."""
        if isinstance(ref, (int, float)):
            return self.recorridos.get(int(ref))
        if isinstance(ref, str):
            if ref.isdigit() and int(ref) in self.recorridos:
                return self.recorridos[int(ref)]
            return next((r for r in self.recorridos.values() if r["ruta"] == ref), None)
        return None

    # --------------------------------------------------------
    # Sesión: invitado, registro, login y cierre
    # --------------------------------------------------------
    def _mostrar_errores_auth(self, pantalla, error):
        etiquetas = {"usuario": "err_usuario", "clave": "err_clave",
                     "repetir": "err_repetir", "general": "err_general"}
        for nombre in etiquetas.values():
            if nombre in pantalla.ids:
                pantalla.ids[nombre].text = ""
        destino = etiquetas.get(error.campo, "err_general")
        if destino not in pantalla.ids:
            destino = "err_general"
        pantalla.ids[destino].text = error.mensaje

    def _limpiar_formularios(self):
        for nombre in ("login", "registro"):
            p = self._pantalla(nombre)
            for campo in ("usuario", "clave", "repetir", "err_usuario", "err_clave",
                          "err_repetir", "err_general"):
                if campo in p.ids:
                    p.ids[campo].text = ""

    def hacer_login(self):
        p = self._pantalla("login")
        correo, clave = p.ids.usuario.text.strip(), p.ids.clave.text
        if not correo or not clave:
            self._mostrar_errores_auth(p, ErrorApi("Escribe tu correo y tu contraseña."))
            return
        self._autenticar(lambda: self.cliente.login(correo, clave), p, "Iniciando sesión…", False)

    def hacer_registro(self):
        p = self._pantalla("registro")
        correo, clave, repetir = p.ids.usuario.text.strip(), p.ids.clave.text, p.ids.repetir.text
        if clave != repetir:
            self._mostrar_errores_auth(p, ErrorApi("Las contraseñas no coinciden.", "repetir"))
            return
        self._autenticar(lambda: self.cliente.registrar(correo, clave), p, "Creando tu cuenta…", True)

    def _autenticar(self, accion, pantalla, mensaje, nuevo):
        if self._auth_en_progreso:
            return
        self._auth_en_progreso = True
        self._auth_generacion += 1
        generacion = self._auth_generacion
        self.cambiar_pantalla("carga")
        self._pantalla("carga").ids.carga_estado.text = mensaje

        def listo(usuario, error):
            if generacion != self._auth_generacion:
                return
            self._auth_en_progreso = False
            if error:
                self._medir("login_fallido")
                self.cambiar_pantalla("registro" if nuevo else "login")
                self._mostrar_errores_auth(pantalla, error)
                return
            self._medir("registro_exitoso" if nuevo else "login_exitoso")
            self._entrar(usuario, nuevo=nuevo)

        self._en_hilo(accion, listo)

    def entrar_invitado(self):
        self.rol = "invitado"
        self.usuario_actual = "invitado"
        self.nombre_visible = "Invitado"
        self.puntos, self.nivel = 0, {"nombre": "Invitado", "faltan": 0}
        self.favoritas, self.viajes = [], 0
        self._finalizar_entrada("Estás como invitado: puedes mirar, pero no votar ni compartir.")

    def _entrar(self, usuario, nuevo=False, restaurada=False):
        """Sesión de una cuenta registrada: puntos y nombre vienen del servidor;
        las preferencias (tema, favoritas...) se guardan en el teléfono."""
        self.rol = usuario.get("rol", "registrado")
        self.usuario_actual = f'u{usuario["id"]}'
        self.nombre_visible = usuario["nombre"]
        self.correo = usuario["correo"]
        self._cargando = True
        try:
            perfil = almacenamiento.cargar_perfil(self.usuario_actual)
            self.favoritas = [str(f) for f in perfil.get("favoritas", [])]
            self.viajes = perfil.get("viajes", 0)
            self.notificar_favoritas = perfil.get("notificar_favoritas", True)
            self.consentimiento = perfil.get("consentimiento", False)
            self.theme_cls.theme_style = "Dark" if perfil.get("tema_oscuro") else "Light"
            aj = self._pantalla("ajustes").ids
            aj.switch_tema.active = bool(perfil.get("tema_oscuro"))
            aj.switch_notif.active = self.notificar_favoritas
            self._pantalla("perfil").ids.switch_consent.active = self.consentimiento
        finally:
            self._cargando = False
        self._aplicar_usuario(usuario)
        saludo = (f"¡Cuenta creada! Hola, {self.nombre_visible}" if nuevo
                  else f"Hola de nuevo, {self.nombre_visible}")
        self._finalizar_entrada(None if restaurada else saludo)

    def _finalizar_entrada(self, mensaje):
        self._limpiar_formularios()
        self._pintar_perfil()
        self._pantalla("ajustes").ids.cerrar_texto.text = (
            "Salir del modo invitado" if self.es_invitado else "Cerrar sesión")
        self.refrescar_avisos()
        self.cambiar_pantalla("home")
        self.sincronizar()
        if mensaje:
            self._snack(mensaje)

    def _aplicar_usuario(self, usuario):
        self.puntos = int(usuario.get("puntos", 0))
        self.nivel = usuario.get("nivel", {"nombre": "Novato", "faltan": 0})
        self.nombre_visible = usuario.get("nombre", self.nombre_visible)
        self.rol = usuario.get("rol", self.rol)
        self._pintar_perfil()

    def cerrar_sesion(self):
        self._guardar_perfil()
        self._auth_generacion += 1
        self._auth_en_progreso = False
        if self.rol in ("registrado", "admin"):
            threading.Thread(target=self.cliente.cerrar_sesion, daemon=True).start()
        if self.compartiendo:
            self.detener_compartir()
        self.detener_gps()
        if self.marcador_yo:
            self._pantalla("home").ids.mapa.remove_marker(self.marcador_yo)
            self.marcador_yo = None
        self._pantalla("home").ids.ubicacion_estado.text = "Tu ubicación: sin consultar"
        for r in self.recorridos.values():
            r["mi_voto"] = 0
        for a in self.avisos:
            a["mi_voto"], a["es_mio"] = 0, False
        self.rol, self.usuario_actual, self.linea_actual = "", "", 0
        self.favoritas = []
        p = self._pantalla("compartir").ids
        p.linea_text.text = "Elegir mi línea"
        self.refrescar_avisos()
        self.cambiar_pantalla("login")

    # --------------------------------------------------------
    # Perfil local (preferencias) y perfil público (nivel y puntos)
    # --------------------------------------------------------
    def _guardar_perfil(self):
        if self.rol not in ("registrado", "admin") or self._cargando:
            return
        try:
            almacenamiento.guardar_perfil(self.usuario_actual, {
                "nombre": self.nombre_visible,
                "favoritas": list(self.favoritas),
                "viajes": self.viajes,
                "tema_oscuro": self.theme_cls.theme_style == "Dark",
                "notificar_favoritas": self.notificar_favoritas,
                "consentimiento": self.consentimiento,
                "firebase_avisos": False,
            })
        except OSError as e:
            registrar_error(e)

    def _pintar_perfil(self):
        try:
            pf = self._pantalla("perfil").ids
        except Exception:
            return
        pf.nombre_label.text = self.nombre_visible or "Usuario"
        if self.es_invitado:
            pf.usuario_label.text = "Modo invitado"
            pf.nivel_icono.icon = "account-outline"
            pf.nivel_label.text = "Invitado"
            pf.nivel_falta.text = "Crea una cuenta para votar, avisar y ganar puntos."
            pf.perfil_editable.opacity = 0
            pf.perfil_editable.disabled = True
            pf.perfil_editable.height = 0
        else:
            pf.usuario_label.text = getattr(self, "correo", "")
            nombre = self.nivel.get("nombre", "Novato")
            faltan = int(self.nivel.get("faltan", 0))
            pf.nivel_icono.icon = ICONOS_NIVEL.get(nombre, "account-outline")
            pf.nivel_label.text = f"{nombre} · {self.puntos} puntos"
            pf.nivel_falta.text = (f"Te faltan {faltan} puntos para el siguiente nivel."
                                   if faltan else "¡Nivel máximo alcanzado!")
            pf.perfil_editable.opacity = 1
            pf.perfil_editable.disabled = False
            pf.perfil_editable.height = dp(112)
        pf.viajes_num.text = str(self.viajes)
        pf.fav_num.text = str(len(self.favoritas))

    def guardar_nombre(self, campo):
        if self.es_invitado:
            return
        texto = campo.text.strip()
        if texto == "" or len(texto) > 30:
            campo.error = True
            return
        campo.error = False

        def listo(usuario, error):
            if error:
                self._snack("Necesitas conexión para cambiar tu nombre." if error.sin_red else error.mensaje)
                return
            campo.text = ""
            self._aplicar_usuario(usuario)
            self._guardar_perfil()
        self._en_hilo(lambda: self.cliente.cambiar_nombre(texto), listo)

    def cambiar_tema(self, oscuro):
        self.theme_cls.theme_style = "Dark" if oscuro else "Light"
        self._guardar_perfil()

    def cambiar_notificaciones(self, activo):
        self.notificar_favoritas = activo
        self._guardar_perfil()

    def cambiar_consentimiento(self, activo):
        self.consentimiento = activo
        if not activo:
            if self.compartiendo:
                self.detener_compartir()
            else:
                self.detener_gps()
        self._guardar_perfil()

    def cambiar_analitica(self, activo):
        anterior = self.medidor.activo
        self.medidor.activo = bool(activo)
        if self.root:
            self._pantalla("ajustes").ids.mjv_estado.text = (
                "Métricas anónimas activadas (sin ubicación ni nombre)" if activo
                else "Métricas anónimas desactivadas")
        if activo and not anterior:
            self._medir("aplicacion_iniciada")
        if not activo:
            self._medicion_intento = None

    # --------------------------------------------------------
    # Configuración remota (banner de Inicio)
    # --------------------------------------------------------
    @property
    def antispam_s(self):
        return self.config.get("antispam_segundos", CONFIG_REMOTA_DEFECTO["antispam_segundos"])

    @property
    def vigencia_s(self):
        return self.config.get("vigencia_aviso_min", CONFIG_REMOTA_DEFECTO["vigencia_aviso_min"]) * 60

    def actualizar_config_remota(self):
        self._pantalla("ajustes").ids.cfg_estado.text = "Consultando configuración remota…"
        config_remota.descargar_en_hilo(
            lambda cfg, fuente: Clock.schedule_once(lambda dt: self._aplicar_config(cfg, fuente)))

    def _aplicar_config(self, cfg, fuente):
        self.config, self.fuente_config = cfg, fuente
        mensaje = cfg["mensaje_inicio"]
        home = self._pantalla("home").ids
        home.banner_texto.text = mensaje
        home.banner.opacity = 1 if mensaje else 0
        self._pantalla("ajustes").ids.cfg_estado.text = (
            f'Fuente: {fuente}\nMensaje de Inicio: "{mensaje}"\n'
            f'Anti-spam de avisos: {cfg["antispam_segundos"]} s · '
            f'Vigencia de un aviso: {cfg["vigencia_aviso_min"]} min')
        if self.root:
            self.refrescar_avisos()

    # --------------------------------------------------------
    # Estado de cada recorrido según los avisos vigentes
    # --------------------------------------------------------
    def _titulo_aviso(self, aviso):
        if aviso["tipo"] == "atrasado":
            return f'Bus atrasado ~{aviso["minutos"]} min'
        return TIPOS_AVISO[aviso["tipo"]]["texto"]

    def _estado_ruta(self, rid):
        """(ocupación, atraso, cambio de ruta): el aviso vigente más reciente de cada clase."""
        limite = time.time() - self.vigencia_s
        vigentes = [a for a in self.avisos if a["recorrido_id"] == rid and a["ts"] >= limite]

        def ultimo(tipos):
            return next((a for a in vigentes if a["tipo"] in tipos), None)
        return ultimo(("lleno", "asientos")), ultimo(("atrasado",)), ultimo(("cambio_ruta",))

    def _texto_estado(self, rid):
        ocupacion, atraso, cambio = self._estado_ruta(rid)
        partes = []
        if ocupacion:
            partes.append(TIPOS_AVISO[ocupacion["tipo"]]["texto"])
        if atraso:
            partes.append(f'Atraso ~{atraso["minutos"]} min')
        if cambio:
            partes.append("Cambio de ruta")
        if not partes:
            return "Sin avisos recientes", GRIS
        if ocupacion and ocupacion["tipo"] == "lleno":
            color = ROJO
        elif atraso or cambio:
            color = NARANJA
        else:
            color = VERDE
        return " · ".join(partes), color

    @staticmethod
    def _texto_verificacion(r):
        return "Verificado" if r["estado"] == "verificado" else "Por verificar"

    def _tarjeta(self, r):
        texto, color = self._texto_estado(r["id"])
        return LineaCard(
            ruta=r["ruta"], rid=r["id"],
            detalle=f'{r["parada"]} · {self._texto_verificacion(r)}',
            minutos=r["duracion"] if r["duracion"] != "No indicada" else "—",
            aviso=texto, aviso_color=list(color))

    # --------------------------------------------------------
    # Refrescos de pantalla
    # --------------------------------------------------------
    def refrescar_avisos(self):
        """Cada paso va aparte: si uno falla, los demás igual se actualizan."""
        if not self.root:
            return
        pasos = [self._llenar_lineas_home, self.poblar_recorridos,
                 self.refrescar_favoritos, self.poblar_avisos]
        if self.id_detalle and self.root.ids.sm.current == "detalle":
            pasos.append(self._pintar_detalle)
        for paso in pasos:
            try:
                paso()
            except Exception as e:
                registrar_error(e)

    def poblar_recorridos(self):
        pantalla = self._pantalla("recorridos")
        caja = pantalla.ids.recorridos_box
        caja.clear_widgets()
        for r in sorted(self.recorridos.values(), key=lambda r: r["ruta"]):
            caja.add_widget(self._tarjeta(r))
        pantalla.ids.recorridos_resumen.text = (
            f"{len(self.recorridos)} recorridos en {len(self.localidades)} localidades"
            if self.recorridos else "Aún no hay recorridos cargados. Conéctate para descargarlos.")

    def refrescar_favoritos(self):
        p = self._pantalla("perfil")
        p.ids.fav_box.clear_widgets()
        for f in self.favoritas:
            r = self.recorridos.get(int(f)) if f.isdigit() else None
            if r:
                p.ids.fav_box.add_widget(self._tarjeta(r))
        hay = bool(self.favoritas)
        p.ids.fav_vacio.opacity = 0 if hay else 1
        p.ids.fav_vacio.height = 0 if hay else dp(40)
        p.ids.fav_num.text = str(len(self.favoritas))

    def _crear_tarjeta_aviso(self, a, ahora):
        t = TIPOS_AVISO[a["tipo"]]
        return AvisoCard(
            aviso_id=a["id"], icono=t["icono"], titulo=self._titulo_aviso(a),
            detalle=f'{a["ruta"]} · {self._hace(a["ts"])}', color=list(t["color"]),
            antiguedad=f'{time.strftime("%H:%M", time.localtime(a["ts"]))} · {self._hace(a["ts"])}',
            vencido=ahora - a["ts"] > self.vigencia_s,
            autor=a.get("autor", ""), nivel=a.get("autor_nivel", ""),
            votos_ok=a.get("votos_ok", 0), votos_mal=a.get("votos_mal", 0),
            mi_voto=a.get("mi_voto", 0), propio=bool(a.get("es_mio")))

    def poblar_avisos(self):
        pantalla = self._pantalla("avisos")
        caja = pantalla.ids.avisos_box
        caja.clear_widgets()
        ahora = time.time()
        visibles = [a for a in self.avisos
                    if not self.solo_favoritas or str(a["recorrido_id"]) in self.favoritas]
        for a in visibles:
            caja.add_widget(self._crear_tarjeta_aviso(a, ahora))
        pantalla.ids.avisos_vacio.text = (
            "No hay avisos en tus rutas favoritas." if self.solo_favoritas
            else "Aún no hay avisos. Cuando alguien avise, aparecerá aquí.")
        pantalla.ids.avisos_vacio.opacity = 0 if visibles else 1
        pantalla.ids.avisos_vacio.height = 0 if visibles else dp(40)

    def alternar_solo_favoritas(self, activo):
        self.solo_favoritas = activo
        self.poblar_avisos()

    # --------------------------------------------------------
    # Inicio: localidad, recorrido y mapa con la línea A -> B
    # --------------------------------------------------------
    def abrir_menu_origen(self, boton):
        items = [{"text": lugar, "on_release": lambda x=lugar: self.seleccionar_origen(x)}
                 for lugar in self.localidades]
        if not items:
            self._snack("Aún no hay recorridos cargados.")
            return
        self.menu_origen = MDDropdownMenu(caller=boton, items=items)
        self.menu_origen.open()

    def seleccionar_origen(self, lugar):
        if self.menu_origen:
            self.menu_origen.dismiss()
        home = self._pantalla("home")
        home.ids.origen_text.text = lugar
        self.recorrido_home = 0
        home.ids.recorrido_text.text = "Todos los destinos"
        self.origen_actual = lugar
        self._llenar_lineas_home()
        self.actualizar_mapa(home.ids.mapa, lugar)
        self.panel_expandido = False
        self.alternar_panel_buses()

    def abrir_recorrido_home(self, boton):
        if not self.origen_actual:
            self._snack("Primero elige una localidad")
            return
        opciones = [(0, "Todos los recorridos")] + [(r["id"], r["ruta"]) for r in self.localidades[self.origen_actual]]
        self.menu_recorrido_home = MDDropdownMenu(caller=boton, items=[
            {"text": txt, "on_release": lambda i=rid: self.seleccionar_recorrido_home(i)}
            for rid, txt in opciones])
        self.menu_recorrido_home.open()

    def seleccionar_recorrido_home(self, rid):
        if self.menu_recorrido_home:
            self.menu_recorrido_home.dismiss()
        self.recorrido_home = rid
        home = self._pantalla("home")
        r = self.recorridos.get(rid)
        home.ids.recorrido_text.text = r["destino"] if r else "Todos los destinos"
        self._llenar_lineas_home()
        self.actualizar_mapa(home.ids.mapa, self.origen_actual)

    def _llenar_lineas_home(self):
        if not self.origen_actual or self.origen_actual not in self.localidades:
            return
        caja = self._pantalla("home").ids.lineas_box
        caja.clear_widgets()
        for r in self.localidades[self.origen_actual]:
            if self.recorrido_home and r["id"] != self.recorrido_home:
                continue
            texto, color = self._texto_estado(r["id"])
            recientes = [a for a in self.avisos if a["recorrido_id"] == r["id"]]
            if not any(time.time() - a["ts"] < self.vigencia_s for a in recientes):
                texto = "Reporte desactualizado" if recientes else "Sin reportes recientes"
                color = GRIS
            ocupacion, atraso, cambio = self._estado_ruta(r["id"])
            ultimo = max((a["ts"] for a in recientes), default=None)
            icono = ("map-marker-alert-outline" if cambio else "clock-alert-outline" if atraso
                     else TIPOS_AVISO[ocupacion["tipo"]]["icono"] if ocupacion
                     else "information-outline")
            color = ((0.075, 0.60, 0.435, 1) if color == VERDE else color)
            caja.add_widget(HomeBusCard(
                ruta=r["ruta"], rid=r["id"], detalle=r["parada"], minutos="Sin ETA",
                aviso=texto, aviso_color=list(color), estado_icono=icono,
                ocupacion=TIPOS_AVISO[ocupacion["tipo"]]["texto"] if ocupacion else "Sin dato",
                actualizacion=f"{self._texto_verificacion(r)} · {self._hace(ultimo)}" if ultimo
                else f"{self._texto_verificacion(r)} · sin avisos"))

    def ajustar_panel_home(self, *args):
        if not self.root:
            return
        home = self._pantalla("home")
        Animation.cancel_all(home.ids.panel_buses, "height")
        home.ids.panel_buses.height = self._alto_panel_home(home)
        home.ids.panel_icono.icon = "chevron-down" if self.panel_expandido else "chevron-up"

    def _alto_panel_home(self, home):
        fijo = (home.ids.home_header.height + home.ids.home_selectors.height
                + home.ids.banner.height)
        return (min(dp(248), max(dp(48), (home.height - fijo) * .38))
                if self.panel_expandido else dp(48))

    def alternar_panel_buses(self):
        home = self._pantalla("home")
        self.panel_expandido = not self.panel_expandido
        Animation.cancel_all(home.ids.panel_buses, "height")
        Animation(height=self._alto_panel_home(home), d=0.18, t="out_quad").start(home.ids.panel_buses)
        home.ids.panel_icono.icon = "chevron-down" if self.panel_expandido else "chevron-up"

    @staticmethod
    def _encuadrar(mapa, puntos):
        """Centra el mapa y ajusta el zoom para que se vea toda la línea."""
        if not puntos:
            return
        lats, lons = [p[0] for p in puntos], [p[1] for p in puntos]
        span = max(max(lats) - min(lats), max(lons) - min(lons), 0.01)
        ancho = max(mapa.width, 300)
        mapa.zoom = max(5, min(16, int(math.log2(360 * ancho / (256 * span * 1.4)))))
        mapa.center_on((min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2)

    def actualizar_mapa(self, mapa, lugar):
        """Dibuja la parada y la línea A -> B de cada recorrido que sale de ahí."""
        try:
            for m in self._marcadores:
                mapa.remove_marker(m)
            self._marcadores = []
            centro = self.coords.get(lugar)
            lineas, puntos = [], []
            if centro:
                parada = MapMarkerPopup(lat=centro[0], lon=centro[1])
                mapa.add_marker(parada)
                self._marcadores.append(parada)
                puntos.append(centro)
            for r in self.localidades.get(lugar, []):
                if self.recorrido_home and r["id"] != self.recorrido_home:
                    continue
                if len(r["linea"]) >= 2:
                    lineas.append(r["linea"])
                    puntos.extend(r["linea"])
                    destino = MapMarker(lat=r["linea"][-1][0], lon=r["linea"][-1][1])
                    mapa.add_marker(destino)
                    self._marcadores.append(destino)
            if self._capa_home:
                self._capa_home.fijar(lineas)
            if self.recorrido_home and puntos:
                self._encuadrar(mapa, puntos)
            elif centro:
                mapa.zoom = 10
                mapa.center_on(*centro)
        except Exception as e:
            registrar_error(e)

    # --------------------------------------------------------
    # Detalle de un recorrido: línea A -> B, votos y avisos
    # --------------------------------------------------------
    def mostrar_detalle(self, ref):
        r = self._buscar_recorrido(ref)
        if not r:
            return
        if self._medicion_intento:
            self.medidor.completar_busqueda(self._medicion_intento)
            self._medicion_intento = None
        actual = self.root.ids.sm.current
        if actual != "detalle":
            self._pantalla_previa = actual
        self.id_detalle = r["id"]
        self._pintar_detalle()
        self.cambiar_pantalla("detalle")
        Clock.schedule_once(lambda dt: self._dibujar_mapa_detalle(), 0.25)
        # Se refresca desde la base de datos; sin red se queda con lo guardado.
        rid = r["id"]
        self._en_hilo(lambda: self.cliente.recorrido(rid), lambda res, err: self._detalle_listo(rid, res, err))

    def _detalle_listo(self, rid, res, err):
        if err or not res:
            return
        datos, avisos = res
        self.recorridos[rid] = self._normalizar({**datos, "id": rid})
        otros = [a for a in self.avisos if a["recorrido_id"] != rid]
        self._aplicar_avisos(otros + avisos)
        if self.id_detalle == rid:
            self._pintar_detalle()
            self._dibujar_mapa_detalle()

    def cerrar_detalle(self):
        self.id_detalle = 0
        self.cambiar_pantalla(self._pantalla_previa or "recorridos")

    def _pintar_detalle(self):
        r = self.recorridos.get(self.id_detalle)
        if not r:
            return
        d = self._pantalla("detalle").ids
        d.det_titulo.text = r["ruta"]
        d.det_parada.text = r["parada"]
        d.det_ruta_texto.text = f'A: {r["origen"]}   →   B: {r["destino"]}'
        d.det_ver.text = self._texto_verificacion(r)
        d.det_ver.text_color = [0.075, 0.60, 0.435, 1] if r["estado"] == "verificado" else [1, 1, 1, 0.85]
        d.det_frecuencia.valor = r["frecuencia"]
        d.det_duracion.valor = r["duracion"]
        d.det_tarifa.valor = r["tarifa"]
        texto, color = self._texto_estado(r["id"])
        d.det_estado.text = texto
        d.det_estado.text_color = list(color)
        # Votación: ¿este recorrido es real?
        d.det_like.icon = "thumb-up" if r["mi_voto"] == 1 else "thumb-up-outline"
        d.det_dislike.icon = "thumb-down" if r["mi_voto"] == -1 else "thumb-down-outline"
        d.det_n_ok.text, d.det_n_mal.text = str(r["votos_ok"]), str(r["votos_mal"])
        total = r["votos_ok"] + r["votos_mal"]
        d.det_confianza.text = (
            f'{round(100 * r["votos_ok"] / total)}% de {total} voto(s) dice que es real'
            if total else "Aún nadie ha votado. ¡Sé el primero!")
        es_fav = str(r["id"]) in self.favoritas
        d.det_fav_icono.icon = "star" if es_fav else "star-outline"
        d.det_fav_texto.text = "Quitar de favoritas" if es_fav else "Agregar a favoritas"
        # Avisos de esta línea (con votos)
        caja = d.det_avisos_box
        caja.clear_widgets()
        ahora = time.time()
        propios = [a for a in self.avisos if a["recorrido_id"] == r["id"]]
        for a in propios:
            caja.add_widget(self._crear_tarjeta_aviso(a, ahora))
        d.det_vacio.opacity = 0 if propios else 1
        d.det_vacio.height = 0 if propios else dp(40)

    def _dibujar_mapa_detalle(self):
        r = self.recorridos.get(self.id_detalle)
        if not r or not self._capa_detalle:
            return
        try:
            mapa = self._pantalla("detalle").ids.mapa_detalle
            for m in self._marc_detalle:
                mapa.remove_marker(m)
            self._marc_detalle = []
            for lat, lon in (r["linea"][:1] + r["linea"][-1:]) if len(r["linea"]) >= 2 else []:
                m = MapMarker(lat=lat, lon=lon)
                mapa.add_marker(m)
                self._marc_detalle.append(m)
            self._capa_detalle.fijar([r["linea"]])
            self._encuadrar(mapa, r["linea"])
        except Exception as e:
            registrar_error(e)

    def alternar_favorita(self, ref):
        r = self._buscar_recorrido(ref)
        if not r:
            return
        clave = str(r["id"])
        if clave in self.favoritas:
            self.favoritas.remove(clave)
            self._medir("favorito_eliminado")
        else:
            self.favoritas.append(clave)
            self._medir("favorito_agregado")
        self._guardar_perfil()
        self.refrescar_avisos()
        if self.es_invitado:
            self._snack("Como invitado, tus favoritas se borran al salir.")

    # --------------------------------------------------------
    # Votos (recorridos y avisos): un voto por persona; los puntos los calcula el servidor
    # --------------------------------------------------------
    @staticmethod
    def _ajustar_voto(obj, valor):
        previo = obj.get("mi_voto", 0)
        if previo == valor:
            return False
        if previo == 1:
            obj["votos_ok"] -= 1
        elif previo == -1:
            obj["votos_mal"] -= 1
        obj["votos_ok" if valor == 1 else "votos_mal"] += 1
        obj["mi_voto"] = valor
        return True

    def votar_recorrido(self, valor):
        if not self._requiere_cuenta("votar si un recorrido es real"):
            return
        r = self.recorridos.get(self.id_detalle)
        if r and self._ajustar_voto(r, valor):
            self._enviar_voto("voto_recorrido", r["id"], valor)
            self._pintar_detalle()

    def votar_aviso(self, aviso_id, valor):
        if not self._requiere_cuenta("votar si un aviso es correcto"):
            return
        a = next((x for x in self.avisos if x["id"] == aviso_id), None)
        if not a:
            return
        if a.get("es_mio"):
            self._snack("No puedes votar tu propio aviso.")
            return
        if self._ajustar_voto(a, valor):
            self._enviar_voto("voto_aviso", aviso_id, valor)
            self.refrescar_avisos()

    def _enviar_voto(self, ruta, objetivo, valor):
        """Se muestra al instante; si no hay red, el voto queda en cola y se envía al volver."""
        def listo(res, err):
            if err:
                if err.estado == 401:
                    self._sesion_caducada()
                else:
                    self._snack(err.mensaje)
                    self.sincronizar()   # recupera el estado real
                return
            if res.get("en_cola"):
                self._marcar_conexion(False)
                self._snack("Sin conexión: tu voto se enviará cuando vuelva la red.")
                return
            if ruta == "voto_recorrido" and objetivo in self.recorridos:
                self.recorridos[objetivo].update(votos_ok=res["votos_ok"], votos_mal=res["votos_mal"],
                                                 mi_voto=res["mi_voto"], estado=res.get("estado", "pendiente"))
            else:
                for a in self.avisos:
                    if a["id"] == objetivo:
                        a.update(votos_ok=res["votos_ok"], votos_mal=res["votos_mal"], mi_voto=res["mi_voto"])
            self.refrescar_avisos()
        self._en_hilo(lambda: self.cliente.votar(ruta, objetivo, valor), listo)

    # --------------------------------------------------------
    # Ubicación: GPS o aproximación por IP (solo desde el botón de Inicio)
    # --------------------------------------------------------
    def localizarme(self, permitir_ip=True):
        if self.marcador_yo:
            self._pantalla("home").ids.mapa.center_on(self.marcador_yo.lat, self.marcador_yo.lon)
        if self.gps_activo:
            return True
        if self._ip_consulta_pendiente:
            return False
        self._solicitud_ubicacion += 1
        solicitud = self._solicitud_ubicacion
        if gps is not None:
            try:
                gps.configure(on_location=lambda **kw: self.on_gps_location(_solicitud=solicitud, **kw),
                              on_status=self.on_gps_status)
                gps.start(minTime=2000, minDistance=5)
                self.gps_activo = True
                return True
            except (NotImplementedError, PermissionError, RuntimeError, OSError):
                pass
        if permitir_ip and not self.compartiendo and platform != "android":
            self._ip_consulta_pendiente = True
            self._dialogo(
                "Ubicación aproximada por IP",
                "Este equipo no tiene GPS disponible. Si continúas, se consultará al proveedor "
                "externo ipwho.is por HTTPS usando tu IP pública para estimar la ubicación. "
                "No es una ubicación precisa ni se usará para viajes.",
                [("Cancelar", lambda: self._cancelar_ubicacion_ip(solicitud)),
                 ("Continuar", lambda: self._autorizar_ubicacion_ip(solicitud))])
        else:
            self._pantalla("home").ids.ubicacion_estado.text = "GPS no disponible o sin permisos"
        return False

    def _cancelar_ubicacion_ip(self, solicitud):
        if solicitud == self._solicitud_ubicacion:
            self._ip_consulta_pendiente = False
            self._solicitud_ubicacion += 1

    def _autorizar_ubicacion_ip(self, solicitud):
        if solicitud != self._solicitud_ubicacion or self.compartiendo:
            self._ip_consulta_pendiente = False
            return
        threading.Thread(target=self._localizar_por_ip, args=(solicitud,), daemon=True).start()

    def _localizar_por_ip(self, solicitud=None):
        coordenadas = None
        try:
            coordenadas = ubicacion.aproximacion_por_ip()
        except Exception as e:
            print("No se pudo obtener ubicación aproximada por IP:", e)

        def aplicar(_dt):
            if solicitud is not None and solicitud != self._solicitud_ubicacion:
                return
            self._ip_consulta_pendiente = False
            if coordenadas is not None and not self.compartiendo:
                self.actualizar_mi_ubicacion(*coordenadas, fuente="Aproximada por IP")
            else:
                self._pantalla("home").ids.ubicacion_estado.text = "Ubicación no disponible"
        Clock.schedule_once(aplicar)

    def on_gps_location(self, _solicitud=None, **kwargs):
        lat, lon = kwargs.get("lat"), kwargs.get("lon")
        if not ubicacion.coordenadas_validas(lat, lon):
            return

        def aplicar(_dt):
            if _solicitud is not None and _solicitud != self._solicitud_ubicacion:
                return
            self.actualizar_mi_ubicacion(lat, lon)
            if not self.compartiendo:
                self.detener_gps()   # «localizarme» solo necesita una posición
            else:
                self._actualizar_progreso(lat, lon)
        Clock.schedule_once(aplicar)

    def on_gps_status(self, stype, status):
        print(f"GPS [{stype}]: {status}")

    def actualizar_mi_ubicacion(self, lat, lon, fuente="GPS del dispositivo"):
        home = self._pantalla("home")
        if not ubicacion.coordenadas_validas(lat, lon):
            home.ids.ubicacion_estado.text = "Coordenadas de ubicación inválidas"
            return
        home.ids.ubicacion_estado.text = fuente
        mapa = home.ids.mapa
        if self.marcador_yo:
            mapa.remove_marker(self.marcador_yo)
        self.marcador_yo = MapMarker(lat=lat, lon=lon, anchor_x=0.5, anchor_y=0.5)
        mapa.add_marker(self.marcador_yo)
        mapa.center_on(lat, lon)
        mapa.zoom = 15

    def detener_gps(self):
        self._solicitud_ubicacion += 1
        self._ip_consulta_pendiente = False
        if self.gps_activo and gps is not None:
            try:
                gps.stop()
            except (NotImplementedError, PermissionError, RuntimeError, OSError) as e:
                registrar_error(e)
        self.gps_activo = False

    # --------------------------------------------------------
    # Compartir viaje: exige la patente del bus o un viaje agendado
    # --------------------------------------------------------
    def _nombre_linea(self):
        r = self.recorridos.get(self.linea_actual)
        return r["ruta"] if r else ""

    def abrir_menu_linea(self, boton):
        items = [{"text": r["ruta"], "on_release": lambda x=r["id"]: self.seleccionar_linea(x)}
                 for r in sorted(self.recorridos.values(), key=lambda r: r["ruta"])]
        if not items:
            self._snack("Aún no hay recorridos cargados.")
            return
        self.menu_linea = MDDropdownMenu(caller=boton, items=items)
        self.menu_linea.open()

    def seleccionar_linea(self, rid):
        if self.menu_linea:
            self.menu_linea.dismiss()
        pantalla = self._pantalla("compartir")
        self.linea_actual = rid
        pantalla.ids.linea_text.text = self._nombre_linea()
        pantalla.ids.linea_error.text = ""

    @staticmethod
    def _parsear_agenda(texto):
        """'DD/MM HH:MM' (o con año) en hora local -> texto ISO con zona horaria."""
        for formato in ("%d/%m %H:%M", "%d/%m/%Y %H:%M"):
            try:
                d = datetime.strptime(texto, formato)
                if formato == "%d/%m %H:%M":
                    d = d.replace(year=datetime.now().year)
                return d.astimezone().isoformat()
            except ValueError:
                continue
        return None

    def alternar_compartir(self):
        if not self._requiere_cuenta("compartir tu viaje"):
            return
        if self.compartiendo:
            self.detener_compartir()
            return
        p = self._pantalla("compartir").ids
        p.patente_error.text = ""
        if not self.linea_actual:
            p.linea_error.text = "Primero elige la línea en la que vas"
            return
        patente = normalizar_patente(p.patente_field.text)
        agenda_txt = p.agenda_field.text.strip()
        if not patente and not agenda_txt:
            p.patente_error.text = "Escribe la patente del bus o agenda el viaje para poder compartir."
            return
        if patente and not patente_valida(patente):
            p.patente_error.text = "Patente inválida (ejemplos: AB1234 o BCDF12)."
            return
        agenda = None
        if agenda_txt:
            agenda = self._parsear_agenda(agenda_txt)
            if agenda is None:
                p.patente_error.text = "Agenda con el formato DD/MM HH:MM (ej.: 20/11 07:30)."
                return
        self._viaje_pendiente = (patente, agenda)
        if not self.consentimiento:
            self.mostrar_dialogo_consentimiento()
            return
        self._comenzar_viaje()

    def mostrar_dialogo_consentimiento(self):
        self._dialogo(
            "¿Compartir tu ubicación?",
            "En esta versión la posición se muestra solo en tu mapa; todavía no se sincroniza "
            "con otros teléfonos. Se utiliza durante el viaje y puedes detenerla cuando quieras.",
            [("Cancelar", None), ("Aceptar", self.aceptar_consentimiento)])

    def aceptar_consentimiento(self, *args):
        self.consentimiento = True
        self._pantalla("perfil").ids.switch_consent.active = True
        self._comenzar_viaje()

    def _comenzar_viaje(self):
        """Registra el viaje en el servidor (valida patente/agenda) y recién entonces inicia el GPS."""
        if not self._viaje_pendiente:
            return
        patente, agenda = self._viaje_pendiente
        rid = self.linea_actual
        p = self._pantalla("compartir").ids
        p.estado_label.text = "Registrando el viaje…"

        def listo(res, err):
            if err:
                p.estado_label.text = "Tu ubicación no se está compartiendo."
                p.patente_error.text = ("Necesitas conexión para iniciar un viaje." if err.sin_red
                                        else err.mensaje)
                return
            self.viaje_id = res["id"]
            self._viaje_pendiente = None
            self.iniciar_compartir()
        self._en_hilo(lambda: self.cliente.iniciar_viaje(rid, patente, agenda), listo)

    def _actualizar_progreso(self, lat, lon):
        """Mientras compartes el viaje, la línea dibujada se acorta: solo queda
        lo que falta desde tu posición hasta el punto B."""
        estado = self._pantalla("compartir").ids.estado_label
        r = self.recorridos.get(self.linea_actual)
        if not r or len(r["linea"]) < 2:
            estado.text = f"GPS local activo en {self._nombre_linea()}"
            return
        restante, dist = tramo_restante(r["linea"], (lat, lon))
        if restante is None:
            estado.text = f'Estás a {int(dist)} m del recorrido {r["ruta"]}'
            restante = r["linea"]
        else:
            estado.text = f'{r["ruta"]}: faltan {largo_m(restante) / 1000:.1f} km hasta {r["destino"]}'
        if self._capa_home:
            self._capa_home.fijar([restante])
        if self._capa_detalle and self.id_detalle == r["id"]:
            self._capa_detalle.fijar([restante])

    def _restaurar_lineas(self):
        """Al terminar el viaje vuelven las líneas completas."""
        try:
            lineas = [r["linea"] for r in self.localidades.get(self.origen_actual, [])
                      if (not self.recorrido_home or r["id"] == self.recorrido_home) and len(r["linea"]) >= 2]
            if self._capa_home:
                self._capa_home.fijar(lineas)
            if self.id_detalle:
                self._dibujar_mapa_detalle()
        except Exception as e:
            registrar_error(e)

    def iniciar_compartir(self):
        # TODO: además de mostrar mi posición local, enviarla a la API para que
        # otros usuarios la vean en su propio mapa.
        if self._ip_consulta_pendiente:
            self.detener_gps()
        self.compartiendo = True
        gps_iniciado = self.localizarme(permitir_ip=False)   # una IP no sirve para seguir un bus
        p = self._pantalla("compartir").ids
        if not gps_iniciado:
            self.compartiendo = False
            p.compartir_btn_text.text = "INICIAR VIAJE"
            p.estado_label.text = "GPS no disponible. Verifica los permisos del dispositivo."
            self._cerrar_viaje_remoto()
            return
        p.compartir_btn_text.text = "DETENER VIAJE"
        p.estado_label.text = f"Esperando señal GPS local en {self._nombre_linea()}"

    def _cerrar_viaje_remoto(self):
        vid, self.viaje_id = self.viaje_id, None
        if not vid:
            return

        def listo(res, err):
            if err or not res or res.get("en_cola"):
                return
            if res.get("usuario"):
                self._aplicar_usuario(res["usuario"])
            if res.get("puntos_ganados"):
                self._snack(f'¡Viaje completado! +{res["puntos_ganados"]} puntos')
        self._en_hilo(lambda: self.cliente.terminar_viaje(vid), listo)

    def detener_compartir(self):
        self.compartiendo = False
        self.detener_gps()
        if self.marcador_yo:
            self._pantalla("home").ids.mapa.remove_marker(self.marcador_yo)
            self.marcador_yo = None
        self.viajes += 1
        self._guardar_perfil()
        self._pintar_perfil()
        p = self._pantalla("compartir").ids
        p.compartir_btn_text.text = "INICIAR VIAJE"
        p.estado_label.text = "Tu ubicación no se está compartiendo."
        self._cerrar_viaje_remoto()
        self._restaurar_lineas()
        self.notificar("Viaje finalizado", f"Llevas {self.viajes} viaje(s) compartido(s). ¡Gracias!")

    # --------------------------------------------------------
    # Avisos de pasajeros (solo cuentas registradas)
    # --------------------------------------------------------
    def abrir_menu_atraso(self, boton):
        items = [{"text": f"{m} min" if m < OPCIONES_ATRASO[-1] else f"{m} min o más",
                  "on_release": lambda x=m: self._elegir_atraso(x)} for m in OPCIONES_ATRASO]
        self.menu_atraso = MDDropdownMenu(caller=boton, items=items)
        self.menu_atraso.open()

    def _elegir_atraso(self, minutos):
        if self.menu_atraso:
            self.menu_atraso.dismiss()
        self.enviar_aviso("atrasado", minutos)

    def enviar_aviso(self, tipo, minutos=0):
        if not self._requiere_cuenta("avisar a otros pasajeros"):
            return
        pantalla = self._pantalla("compartir")
        if not self.linea_actual:
            pantalla.ids.linea_error.text = "Primero elige la línea en la que vas"
            return
        ahora = time.time()
        clave = (self.linea_actual, tipo)
        if ahora - self._ultimo_aviso.get(clave, 0) < self.antispam_s:
            self._snack("Ya enviaste este aviso hace un momento. ¡Gracias!")
            return
        self._ultimo_aviso[clave] = ahora
        aviso = {"id": uuid.uuid4().hex, "recorrido_id": self.linea_actual, "ruta": self._nombre_linea(),
                 "tipo": tipo, "minutos": minutos, "ts": ahora, "autor": self.nombre_visible,
                 "autor_nivel": self.nivel.get("nombre", ""), "votos_ok": 0, "votos_mal": 0,
                 "mi_voto": 0, "es_mio": True}
        self.avisos.insert(0, aviso)
        self._avisos_vistos.add(aviso["id"])
        self.refrescar_avisos()
        self._medir("aviso_publicado")

        def listo(res, err):
            if err:   # rechazado por el servidor (p. ej. anti-spam): se quita el aviso local
                self.avisos = [a for a in self.avisos if a["id"] != aviso["id"]]
                self.refrescar_avisos()
                if err.estado == 401:
                    self._sesion_caducada()
                else:
                    self._snack(err.mensaje)
            elif res.get("en_cola"):
                self._marcar_conexion(False)
                self._snack("Sin conexión: tu aviso se enviará cuando vuelva la red.")
            else:
                self._snack("¡Aviso enviado! Gracias por ayudar a otros pasajeros.")
        self._en_hilo(lambda: self.cliente.crear_aviso(
            aviso["id"], aviso["recorrido_id"], tipo, minutos), listo)
        def _pedir_calles(self):
            """Pide a OSRM el trazado por calles de los recorridos que aún no lo tienen."""
            for r in self.recorridos.values():
                if r["por_calles"] or len(r["linea_api"]) < 2:
                    continue
                self.ruteador.pedir(r["linea_api"], self._al_llegar_calles(r["id"], r["linea_api"]))

        def _al_llegar_calles(self, rid, base):
            def listo(ruta):   # corre en el hilo de fondo
                Clock.schedule_once(lambda dt: self._aplicar_calles(rid, base, ruta))
            return listo

        def _aplicar_calles(self, rid, base, ruta):
            r = self.recorridos.get(rid)
            if not r or r["linea_api"] != base:   # la línea cambió mientras tanto
                return
            r["linea"], r["por_calles"] = ruta, True
            if not self.compartiendo:             # en viaje, el progreso usa la línea nueva solo
                self._restaurar_lineas()

if __name__ == "__main__":
    InterurbanoApp().run()
