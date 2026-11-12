import os
import random
import threading
import time
import traceback

from kivy.animation import Animation
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.utils import platform
from kivy_garden.mapview import MapView, MapMarker, MapMarkerPopup  # noqa: F401
try:
    from plyer import gps
except Exception:

    gps = None

from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText

from config import (CONFIG_REMOTA_DEFECTO, HISTORIAL_S, ICONO_BUS, LOG_ERRORES,
                    OPCIONES_ATRASO)
from datos_rutas import (COORDENADAS, GRIS, LOCALIDADES, NARANJA, ROJO, RUTAS,
                         TIPOS_AVISO, VERDE)
from servicios import almacenamiento, autenticacion, config_remota, avisos_service, recorridos, ubicacion
from servicios.autenticacion import ErrorAutenticacion
from servicios.notificaciones import notificar as enviar_notificacion
from tema import PaletaVisual

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------
# Registro de errores: si algo falla dentro de la app, en vez de cerrarse
# se guarda el detalle completo en crash_log.txt (junto a main.py) y la
# app sigue funcionando.
# ------------------------------------------------------------
def registrar_error(exc):
    """Imprime el error en la consola y lo guarda con su traza completa."""
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
# Widgets propios (su diseño está en root.kv)
# ------------------------------------------------------------
class LineaCard(MDCard):
    ruta = StringProperty("")
    detalle = StringProperty("")
    minutos = StringProperty("")
    aviso = StringProperty("")
    aviso_color = ListProperty(GRIS)


class HomeBusCard(MDCard):
    """Variante de Inicio; conserva intactas las tarjetas de otras pantallas."""
    ruta = StringProperty("")
    detalle = StringProperty("")
    minutos = StringProperty("")
    aviso = StringProperty("")
    aviso_color = ListProperty(GRIS)
    ocupacion = StringProperty("Sin dato")
    actualizacion = StringProperty("Sin reportes recientes")
    estado_icono = StringProperty("information-outline")


class AvisoCard(MDCard):
    icono = StringProperty("bell")
    titulo = StringProperty("")
    detalle = StringProperty("")
    color = ListProperty(GRIS)
    antiguedad = StringProperty("")
    vencido = BooleanProperty(False)


class LoginScreen(Screen):
    pass


class RegistroScreen(Screen):
    pass


class HomeScreen(Screen):
    pass


class RecorridosScreen(Screen):
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
    """MDSnackbar que no revienta al crearse.

    En KivyMD 2.0.0 el snackbar nace con altura 0 (su alto es
    'minimum_height' y aún no tiene hijos cuando RippleBehavior crea su FBO).
    Un FBO de alto 0 es inválido y en Windows/ANGLE lanza
    'FBO Initialization failed: Incomplete attachment (36054)'.
    Aquí forzamos un tamaño mínimo de 1x1 antes de crear el FBO; después el
    alto real se recalcula solo al agregar el texto."""

    def init_fbos(self):
        self.size = self._clamp_size(*self.size)
        super().init_fbos()


class MarcadorBus(MapMarker):
    """MapMarker cuyo tamaño depende del zoom del mapa.

    Los marcadores de MapView viven en una capa sin escala y por defecto
    miden 100x100 px siempre; al alejar el mapa el icono quedaba enorme
    comparado con el mapa y tapaba todo. Aquí va de dp(16) (mapa lejos)
    a dp(44) (mapa cerca)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.fit_mode = "contain"

    def ajustar_zoom(self, zoom):
        lado = dp(min(44, max(16, 24 + (zoom - 10) * 4)))
        self.size = (lado, lado)
        capa = self._layer
        if capa is not None and capa.parent is not None:
            capa.set_marker_position(capa.parent, self)


# ------------------------------------------------------------
# Aplicación
# ------------------------------------------------------------
class InterurbanoApp(MDApp):
    ui = ObjectProperty(None)
    safe_bottom = NumericProperty(0)
    menu_origen = None
    menu_linea = None
    dialogo = None
    _marcadores = []
    marcador_yo = None
    gps_activo = False
    panel_expandido = False
    consentimiento = False   # ¿el usuario aceptó compartir ubicación?
    compartiendo = BooleanProperty(False)
    linea_actual = ""
    favoritas = []
    viajes = 0
    avisos = []               # más nuevo primero: {ruta, tipo, minutos, ts, propio, autor}
    recorrido_home = ""
    menu_recorrido_home = None
    origen_actual = ""
    menu_atraso = None
    notificar_favoritas = True
    solo_favoritas = False
    _ultimo_aviso = {}

    usuario_actual = ""       # "" = nadie ha iniciado sesión
    nombre_visible = ""
    _cargando = False         # True mientras se aplica el perfil a la interfaz
    config = {}               # valores de la configuración remota
    fuente_config = ""        # "remota" | "caché" | "valor por defecto"

    def build(self):
        self.ui = PaletaVisual()
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.theme_cls.bind(theme_style=self._aplicar_tema_visual)
        self._aplicar_tema_visual()
        self.title = "EnRuta Ya!"
        self.favoritas = []
        self.avisos = []
        self._ultimo_aviso = {}
        # Configuración inmediata (caché o valores por defecto); la remota
        # llega después, en on_start, sin bloquear la interfaz.
        self.config, self.fuente_config = config_remota.cargar_local()
        Builder.load_file(os.path.join(BASE_DIR, "componentes.kv"))
        return Builder.load_file(os.path.join(BASE_DIR, "root.kv"))

    def _aplicar_tema_visual(self, *args):
        self.ui.aplicar(self.theme_cls.theme_style == "Dark")
        # Los controles MD conservados (campos, switches, menús y diálogos)
        # usan el mismo esquema que los componentes KV, incluso al cambiar tema.
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

    def on_start(self):
        Window.softinput_mode = "below_target"
        Window.bind(size=self._actualizar_zona_segura)
        self._actualizar_zona_segura()
        self.root.ids.sm.get_screen("home").ids.mapa.bind(zoom=self._ajustar_marcadores)
        self.cargar_avisos()
        self._aplicar_config(self.config, self.fuente_config)
        self.actualizar_config_remota()
        # Cada minuto se actualizan los "hace X min" y se descartan avisos vencidos.
        Clock.schedule_interval(lambda dt: self.refrescar_avisos(), 60)

    def _actualizar_zona_segura(self, *args):
        """Reserva el borde inferior solo si la ventana invade barras Android.

        En escritorio y ventanas donde Android ya reserva las barras, vale 0.
        Pyjnius lo aporta el empaquetado Android; no se exige en escritorio.
        """
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
            # Android antiguo o proveedor sin insets: se mantiene el área que
            # el sistema ya entrega a SDL, sin inventar una altura de barra.
            pass

    def _ajustar_marcadores(self, *args):
        """Achica/agranda los iconos de bus según el zoom actual del mapa."""
        try:
            zoom = self.root.ids.sm.get_screen("home").ids.mapa.zoom
        except Exception:
            return
        buses = [m for m in self._marcadores if isinstance(m, MarcadorBus)]
        if isinstance(self.marcador_yo, MarcadorBus):
            buses.append(self.marcador_yo)
        for m in buses:
            m.ajustar_zoom(zoom)

    def cambiar_pantalla(self, nombre):
        self.root.ids.sm.current = nombre

    def _pantalla(self, nombre):
        return self.root.ids.sm.get_screen(nombre)

    def _tarjeta(self, ruta):
        d = RUTAS[ruta]
        texto, color = self._texto_estado(ruta)
        return LineaCard(
            ruta=ruta,
            detalle=f'{d["parada"]} · {d["frecuencia"]}',
            minutos=d["minutos"],
            aviso=texto,
            aviso_color=list(color),
        )

    # --------------------------------------------------------
    # Autenticación: registro, login y cierre de sesión
    # (la validación y el hash viven en servicios/autenticacion.py)
    # --------------------------------------------------------
    def _mostrar_errores_auth(self, pantalla, error):
        """Muestra el mensaje bajo el campo que corresponde."""
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
            for campo in ("usuario", "clave", "repetir"):
                if campo in p.ids:
                    p.ids[campo].text = ""
            for err in ("err_usuario", "err_clave", "err_repetir", "err_general"):
                if err in p.ids:
                    p.ids[err].text = ""

    def hacer_login(self):
        p = self._pantalla("login")
        try:
            usuario = autenticacion.iniciar_sesion(p.ids.usuario.text, p.ids.clave.text)
        except ErrorAutenticacion as e:
            self._mostrar_errores_auth(p, e)
            return
        self._entrar(usuario)

    def hacer_registro(self):
        p = self._pantalla("registro")
        try:
            usuario = autenticacion.registrar(
                p.ids.usuario.text, p.ids.clave.text, p.ids.repetir.text)
        except ErrorAutenticacion as e:
            self._mostrar_errores_auth(p, e)
            return
        self._entrar(usuario, nuevo=True)

    def _entrar(self, usuario, nuevo=False):
        """Sesión iniciada: se carga el perfil guardado en perfiles.json y se
        aplica a la interfaz."""
        self.usuario_actual = usuario
        perfil = almacenamiento.cargar_perfil(usuario)
        self._cargando = True
        try:
            self.nombre_visible = perfil["nombre"]
            self.favoritas = list(perfil["favoritas"])
            self.viajes = perfil["viajes"]
            self.notificar_favoritas = perfil["notificar_favoritas"]
            self.consentimiento = perfil["consentimiento"]
            self.theme_cls.theme_style = "Dark" if perfil["tema_oscuro"] else "Light"
            aj = self._pantalla("ajustes").ids
            aj.switch_tema.active = perfil["tema_oscuro"]
            aj.switch_notif.active = perfil["notificar_favoritas"]
            pf = self._pantalla("perfil").ids
            pf.nombre_label.text = self.nombre_visible
            pf.usuario_label.text = f"@{usuario}"
            pf.viajes_num.text = str(self.viajes)
            pf.switch_consent.active = self.consentimiento
        finally:
            self._cargando = False
        self._limpiar_formularios()
        self.refrescar_avisos()
        self.cambiar_pantalla("home")
        self._snack(f"¡Cuenta creada! Hola, {self.nombre_visible}" if nuevo
                    else f"Hola de nuevo, {self.nombre_visible}")

    def cerrar_sesion(self):
        if self.compartiendo:
            self.detener_compartir()
        self._guardar_perfil()
        self.usuario_actual = ""
        self.linea_actual = ""
        p = self._pantalla("compartir").ids
        p.linea_text.text = "Elegir mi línea"
        self.cambiar_pantalla("login")

    # --------------------------------------------------------
    # Persistencia (servicios/almacenamiento.py -> data/*.json)
    # --------------------------------------------------------
    def _guardar_perfil(self):
        """Guarda en perfiles.json lo que cambió del usuario actual."""
        if not self.usuario_actual or self._cargando:
            return
        try:
            almacenamiento.guardar_perfil(self.usuario_actual, {
                "nombre": self.nombre_visible,
                "favoritas": list(self.favoritas),
                "viajes": self.viajes,
                "tema_oscuro": self.theme_cls.theme_style == "Dark",
                "notificar_favoritas": self.notificar_favoritas,
                "consentimiento": self.consentimiento,
            })
        except OSError as e:
            registrar_error(e)

    def cargar_avisos(self):
        """Recupera los avisos guardados; la primera vez (no existe
        avisos.json) crea unos de ejemplo para la demo."""
        guardados = almacenamiento.cargar_avisos()
        if guardados is None:
            self.avisos = almacenamiento.avisos_de_ejemplo([
                ("Temuco -> Nueva Imperial", "asientos", 0, 3),
                ("Nueva Imperial -> Temuco", "lleno", 0, 6),
                ("Lautaro -> Temuco", "atrasado", 10, 12),
            ])
            self._guardar_avisos()
        else:
            self.avisos = avisos_service.sanear_avisos(guardados)

    def _guardar_avisos(self):
        try:
            almacenamiento.guardar_avisos(self.avisos)
        except OSError as e:
            registrar_error(e)

    # --------------------------------------------------------
    # Configuración remota (servicios/config_remota.py)
    # --------------------------------------------------------
    @property
    def antispam_s(self):
        return self.config.get("antispam_segundos", CONFIG_REMOTA_DEFECTO["antispam_segundos"])

    @property
    def vigencia_s(self):
        return self.config.get("vigencia_aviso_min", CONFIG_REMOTA_DEFECTO["vigencia_aviso_min"]) * 60

    def actualizar_config_remota(self):
        """Pide la configuración a internet en segundo plano."""
        self._pantalla("ajustes").ids.cfg_estado.text = "Consultando configuración remota…"
        config_remota.descargar_en_hilo(
            lambda cfg, fuente: Clock.schedule_once(
                lambda dt: self._aplicar_config(cfg, fuente)))

    def _aplicar_config(self, cfg, fuente):
        """Refleja los valores remotos en la app: banner de Inicio, reglas
        de avisos y el resumen de Ajustes."""
        self.config, self.fuente_config = cfg, fuente
        mensaje = cfg["mensaje_inicio"]
        home = self._pantalla("home").ids
        home.banner_texto.text = mensaje
        home.banner.opacity = 1 if mensaje else 0
        self._pantalla("ajustes").ids.cfg_estado.text = (
            f'Fuente: {fuente}\n'
            f'Mensaje de Inicio: "{mensaje}"\n'
            f'Anti-spam de avisos: {cfg["antispam_segundos"]} s · '
            f'Vigencia de un aviso: {cfg["vigencia_aviso_min"]} min'
        )
        if self.root:
            self.refrescar_avisos()

    # --------------------------------------------------------
    # Ajustes
    # --------------------------------------------------------
    def cambiar_tema(self, oscuro):
        self.theme_cls.theme_style = "Dark" if oscuro else "Light"
        self._guardar_perfil()

    def cambiar_notificaciones(self, activo):
        self.notificar_favoritas = activo
        self._guardar_perfil()

    # --------------------------------------------------------
    # Inicio: localidad + mapa
    # --------------------------------------------------------
    def abrir_menu_origen(self, boton):
        items = [
            {"text": lugar, "on_release": lambda x=lugar: self.seleccionar_origen(x)}
            for lugar in LOCALIDADES
        ]
        self.menu_origen = MDDropdownMenu(caller=boton, items=items)
        self.menu_origen.open()

    def seleccionar_origen(self, lugar):
        if self.menu_origen:
            self.menu_origen.dismiss()
        home = self._pantalla("home")
        home.ids.origen_text.text = lugar
        self.recorrido_home = ""
        home.ids.recorrido_text.text = "Todos los destinos"
        self.origen_actual = lugar
        self._llenar_lineas_home()
        self.actualizar_mapa(home.ids.mapa, lugar)
        self.panel_expandido = False
        self.alternar_panel_buses()  # se abre mostrando los buses recién cargados

    def _llenar_lineas_home(self):
        """Redibuja las tarjetas del panel 'Buses desde...' de Inicio."""
        if not self.origen_actual:
            return
        home = self._pantalla("home")
        caja = home.ids.lineas_box
        caja.clear_widgets()
        for d in LOCALIDADES[self.origen_actual]:
            if self.recorrido_home and d["ruta"] != self.recorrido_home:
                continue
            texto, color = self._texto_estado(d["ruta"])
            recientes = [a for a in self.avisos if a["ruta"] == d["ruta"]]
            if not any(time.time() - a["ts"] < self.vigencia_s for a in recientes):
                texto = "Reporte desactualizado" if recientes else "Sin reportes recientes"
                color = GRIS
            ocupacion, atraso, cambio = self._estado_ruta(d["ruta"])
            ultimo = max((a["ts"] for a in recientes), default=None)
            icono = ("map-marker-alert-outline" if cambio else "clock-alert-outline" if atraso
                     else TIPOS_AVISO[ocupacion["tipo"]]["icono"] if ocupacion
                     else "information-outline")
            color = ((0.075, 0.60, 0.435, 1) if color == VERDE else color)
            caja.add_widget(HomeBusCard(
                ruta=d["ruta"], detalle=d["parada"], minutos=d.get("minutos") or "Sin ETA",
                aviso=texto, aviso_color=list(color), estado_icono=icono,
                ocupacion=TIPOS_AVISO[ocupacion["tipo"]]["texto"] if ocupacion else "Sin dato",
                actualizacion=f"Reporte local · {self._hace(ultimo)}" if ultimo else "Sin actualización real"))

    def abrir_recorrido_home(self, boton):
        if not self.origen_actual:
            self._snack("Primero elige una localidad")
            return
        rutas = [""] + [d["ruta"] for d in LOCALIDADES[self.origen_actual]]
        self.menu_recorrido_home = MDDropdownMenu(caller=boton, items=[
            {"text": ruta or "Todos los recorridos",
             "on_release": lambda r=ruta: self.seleccionar_recorrido_home(r)}
            for ruta in rutas])
        self.menu_recorrido_home.open()

    def seleccionar_recorrido_home(self, ruta):
        if self.menu_recorrido_home:
            self.menu_recorrido_home.dismiss()
        self.recorrido_home = ruta
        home = self._pantalla("home")
        home.ids.recorrido_text.text = ruta.split("->")[-1].strip() if ruta else "Todos los destinos"
        self._llenar_lineas_home()
        self.actualizar_mapa(home.ids.mapa, self.origen_actual)

    def ajustar_panel_home(self, *args):
        home = self._pantalla("home")
        Animation.cancel_all(home.ids.panel_buses, "height")
        home.ids.panel_buses.height = self._alto_panel_home(home)
        home.ids.panel_icono.icon = "chevron-down" if self.panel_expandido else "chevron-up"

    def _alto_panel_home(self, home):
        fijo = (home.ids.home_header.height + home.ids.home_selectors.height
                + home.ids.banner.height)
        return min(dp(248), max(dp(48), (home.height - fijo) * .38)) if self.panel_expandido else dp(48)

    def alternar_panel_buses(self):
        """Expande o colapsa el panel de 'Buses desde...' para estorbar
        menos la vista del mapa."""
        home = self._pantalla("home")
        self.panel_expandido = not self.panel_expandido
        alto = self._alto_panel_home(home)
        Animation.cancel_all(home.ids.panel_buses, "height")
        Animation(height=alto, d=0.18, t="out_quad").start(home.ids.panel_buses)
        home.ids.panel_icono.icon = "chevron-down" if self.panel_expandido else "chevron-up"

    @staticmethod
    def _minutos(texto):
        """Compatibilidad con llamadas existentes; el cálculo vive en recorridos."""
        return recorridos.minutos_desde_texto(texto)

    def actualizar_mapa(self, mapa, lugar):
        """Centra el mapa en la localidad, dibuja la parada y un bus (simulado)
        por cada línea que sale de ahí. Cada bus se ubica sobre el recorrido
        hacia su destino, más cerca de la parada mientras menos minutos falten."""
        lat, lon = COORDENADAS[lugar]
        for m in self._marcadores:
            mapa.remove_marker(m)
        self._marcadores = []

        parada = MapMarkerPopup(lat=lat, lon=lon)
        mapa.add_marker(parada)
        self._marcadores.append(parada)

        for d in LOCALIDADES[lugar]:
            if self.recorrido_home and d["ruta"] != self.recorrido_home:
                continue
            destino = d["ruta"].split("->")[-1].strip()
            if destino not in COORDENADAS:
                continue
            dlat, dlon = COORDENADAS[destino]
            bus_lat, bus_lon = recorridos.posicion_bus_demo(
                (lat, lon), (dlat, dlon), d["duracion"], d["minutos"]
            )
            bus = MarcadorBus(
                lat=bus_lat,
                lon=bus_lon,
                source=ICONO_BUS if os.path.exists(ICONO_BUS)
                       else "atlas://data/images/defaulttheme/checkbox_on",
                anchor_x=0.5, anchor_y=0.5,
            )
            mapa.add_marker(bus)
            self._marcadores.append(bus)

        mapa.zoom = 10
        mapa.center_on(lat, lon)
        self._ajustar_marcadores()

    # --------------------------------------------------------
    # Botón "reubicarme": identifica GPS o aproximación por IP y
    # dibuja al usuario con un marcador distinto del bus de demostración.
    # --------------------------------------------------------
    def localizarme(self):
        """Botón de reubicarme: usa el GPS del dispositivo si existe
        (celular/tablet); en un PC de escritorio, que normalmente no
        tiene GPS, calcula una posición aproximada por IP en segundo
        plano para no congelar la interfaz."""
        if self.marcador_yo:
            self._pantalla("home").ids.mapa.center_on(self.marcador_yo.lat, self.marcador_yo.lon)
        if self.gps_activo:
            return
        if gps is not None:
            try:
                gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
                gps.start(minTime=2000, minDistance=5)
                self.gps_activo = True
                return
            except (NotImplementedError, PermissionError):
                pass  # sin proveedor de GPS en este dispositivo -> sigue abajo
        threading.Thread(target=self._localizar_por_ip, daemon=True).start()

    def _localizar_por_ip(self):
        """Se ejecuta en un hilo aparte para no bloquear la app."""
        lat = lon = None
        try:
            import requests
            r = requests.get("http://ip-api.com/json/", timeout=4)
            datos = r.json()
            if datos.get("status") == "success":
                lat, lon = datos["lat"], datos["lon"]
        except Exception as e:
            print("No se pudo obtener ubicación aproximada por IP:", e)
        if lat is not None and lon is not None:
            Clock.schedule_once(lambda dt: self.actualizar_mi_ubicacion(lat, lon, "Aproximada por IP"))
        else:
            Clock.schedule_once(lambda dt: setattr(self._pantalla("home").ids.ubicacion_estado, "text", "Ubicación no disponible"))

    def on_gps_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is not None and lon is not None:
            Clock.schedule_once(lambda dt: self.actualizar_mi_ubicacion(lat, lon))

    def on_gps_status(self, stype, status):
        print(f"GPS [{stype}]: {status}")

    def actualizar_mi_ubicacion(self, lat, lon, fuente="GPS del dispositivo"):
        self._pantalla("home").ids.ubicacion_estado.text = fuente
        home = self._pantalla("home")
        mapa = home.ids.mapa
        if self.marcador_yo:
            mapa.remove_marker(self.marcador_yo)
        self.marcador_yo = MapMarker(
            lat=lat, lon=lon,
            anchor_x=0.5, anchor_y=0.5,
        )
        mapa.add_marker(self.marcador_yo)
        mapa.center_on(lat, lon)
        mapa.zoom = 15
        self._ajustar_marcadores()

    def detener_gps(self):
        if self.gps_activo and gps is not None:
            gps.stop()
        self.gps_activo = False

    def on_stop(self):
        Window.unbind(size=self._actualizar_zona_segura)
        self.detener_gps()
        self._guardar_perfil()
        self._guardar_avisos()

    # --------------------------------------------------------
    # Detalle de una línea (al tocar cualquier tarjeta)
    # --------------------------------------------------------
    def mostrar_detalle(self, ruta):
        d = RUTAS[ruta]
        es_fav = ruta in self.favoritas
        ocup, atraso, cambio = self._estado_ruta(ruta)
        ocup_txt = (f'{TIPOS_AVISO[ocup["tipo"]]["texto"]} ({self._hace(ocup["ts"])})'
                    if ocup else "sin avisos recientes")
        atraso_txt = (f'~{atraso["minutos"]} min ({self._hace(atraso["ts"])})'
                      if atraso else "sin atraso reportado")
        extra = f'\nAviso: cambio de ruta ({self._hace(cambio["ts"])})' if cambio else ""
        self.dialogo = MDDialog(
            MDDialogHeadlineText(text=ruta),
            MDDialogSupportingText(
                text=(
                    f'Parada: {d["parada"]}\n'
                    f'Próximo bus: {d["minutos"]}\n'
                    f'Frecuencia: {d["frecuencia"]}\n'
                    f'Duración del viaje: {d["duracion"]}\n'
                    f'Tarifa: {d["tarifa"]}\n'
                    f'Ocupación: {ocup_txt}\n'
                    f'Atraso: {atraso_txt}'
                    f'{extra}'
                )
            ),
            MDDialogButtonContainer(
                MDButton(
                    MDButtonText(text="Quitar favorita" if es_fav else "Agregar a favoritas"),
                    style="text",
                    on_release=lambda *a: self.alternar_favorita(ruta),
                ),
                MDButton(
                    MDButtonText(text="Cerrar"),
                    style="text",
                    on_release=lambda *a: self.dialogo.dismiss(),
                ),
                spacing="8dp",
            ),
        )
        self.dialogo.open()

    def alternar_favorita(self, ruta):
        if ruta in self.favoritas:
            self.favoritas.remove(ruta)
        else:
            self.favoritas.append(ruta)
        self.dialogo.dismiss()
        self._guardar_perfil()
        self.refrescar_favoritos()
        self.poblar_avisos()

    # --------------------------------------------------------
    # Recorridos y Perfil
    # --------------------------------------------------------
    def poblar_recorridos(self):
        pantalla = self._pantalla("recorridos")
        caja = pantalla.ids.recorridos_box
        caja.clear_widgets()
        for ruta in RUTAS:
            caja.add_widget(self._tarjeta(ruta))
        pantalla.ids.recorridos_resumen.text = (
            f"{len(RUTAS)} recorridos en {len(LOCALIDADES)} localidades"
        )

    def refrescar_favoritos(self):
        p = self._pantalla("perfil")
        p.ids.fav_box.clear_widgets()
        for ruta in self.favoritas:
            p.ids.fav_box.add_widget(self._tarjeta(ruta))
        hay = bool(self.favoritas)
        p.ids.fav_vacio.opacity = 0 if hay else 1
        p.ids.fav_vacio.height = 0 if hay else dp(40)
        p.ids.fav_num.text = str(len(self.favoritas))

    def guardar_nombre(self, campo):
        """Validación: el nombre no puede estar vacío ni pasar de 30 caracteres."""
        texto = campo.text.strip()
        if texto == "" or len(texto) > 30:
            campo.error = True
            return
        campo.error = False
        self.nombre_visible = texto
        self._pantalla("perfil").ids.nombre_label.text = texto
        campo.text = ""
        self._guardar_perfil()

    def cambiar_consentimiento(self, activo):
        self.consentimiento = activo
        if not activo and self.compartiendo:
            self.detener_compartir()
        self._guardar_perfil()

    # --------------------------------------------------------
    # Compartir ubicación (el usuario "es" el bus en el mapa)
    # --------------------------------------------------------
    def abrir_menu_linea(self, boton):
        items = [
            {"text": r, "on_release": lambda x=r: self.seleccionar_linea(x)}
            for r in RUTAS
        ]
        self.menu_linea = MDDropdownMenu(caller=boton, items=items)
        self.menu_linea.open()

    def seleccionar_linea(self, ruta):
        if self.menu_linea:
            self.menu_linea.dismiss()
        pantalla = self._pantalla("compartir")
        self.linea_actual = ruta
        pantalla.ids.linea_text.text = ruta
        pantalla.ids.linea_error.text = ""

    def alternar_compartir(self):
        pantalla = self._pantalla("compartir")
        if self.compartiendo:
            self.detener_compartir()
            return
        if not self.linea_actual:
            pantalla.ids.linea_error.text = "Primero elige la línea en la que vas"
            return
        if not self.consentimiento:
            self.mostrar_dialogo_consentimiento()
            return
        self.iniciar_compartir()

    def mostrar_dialogo_consentimiento(self):
        self.dialogo = MDDialog(
            MDDialogHeadlineText(text="¿Compartir tu ubicación?"),
            MDDialogSupportingText(
                text="En esta versión la posición se muestra solo en tu mapa; "
                     "todavía no se sincroniza con otros teléfonos. Se utiliza "
                     "durante el viaje y puedes detenerla cuando quieras."
            ),
            MDDialogButtonContainer(
                MDButton(MDButtonText(text="Cancelar"), style="text",
                         on_release=lambda *a: self.dialogo.dismiss()),
                MDButton(MDButtonText(text="Aceptar"), style="text",
                         on_release=self.aceptar_consentimiento),
                spacing="8dp",
            ),
        )
        self.dialogo.open()

    def aceptar_consentimiento(self, *args):
        self.consentimiento = True
        self._pantalla("perfil").ids.switch_consent.active = True
        self.dialogo.dismiss()
        self.iniciar_compartir()

    def iniciar_compartir(self):
        # TODO: además de mostrar mi posición local, enviarla a un servidor
        # para que otros usuarios la vean en su propio mapa.
        self.compartiendo = True
        self.localizarme()
        p = self._pantalla("compartir")
        p.ids.compartir_btn_text.text = "DETENER VIAJE"
        p.ids.estado_label.text = f"Ubicación local activa en {self.linea_actual}"

    def detener_compartir(self):
        self.compartiendo = False
        self.detener_gps()
        home = self._pantalla("home")
        if self.marcador_yo:
            home.ids.mapa.remove_marker(self.marcador_yo)
            self.marcador_yo = None
        self.viajes += 1
        self._pantalla("perfil").ids.viajes_num.text = str(self.viajes)
        self._guardar_perfil()
        p = self._pantalla("compartir")
        p.ids.compartir_btn_text.text = "INICIAR VIAJE"
        p.ids.estado_label.text = "Tu ubicación no se está compartiendo."
        # Evento de la app -> notificación
        self.notificar("Viaje finalizado", f"Llevas {self.viajes} viaje(s) compartido(s). ¡Gracias!")

    # --------------------------------------------------------
    # Avisos de pasajeros: bus lleno / con asientos / atrasado /
    # cambio de ruta. Se ven en las tarjetas de cada línea, en el
    # detalle y en la pantalla Avisos; los de rutas favoritas además
    # generan una notificación.
    # --------------------------------------------------------
    def _hace(self, ts):
        minutos = int((time.time() - ts) // 60)
        if minutos < 1:
            return "recién"
        if minutos < 60:
            return f"hace {minutos} min"
        return f"hace {minutos // 60} h"

    def _titulo_aviso(self, aviso):
        if aviso["tipo"] == "atrasado":
            return f'Bus atrasado ~{aviso["minutos"]} min'
        return TIPOS_AVISO[aviso["tipo"]]["texto"]

    def _estado_ruta(self, ruta):
        """Últimos reportes vigentes; sin dependencias de widgets Kivy."""
        return avisos_service.estado_ruta(self.avisos, ruta, self.vigencia_s)

    def _texto_estado(self, ruta):
        """Texto corto + color para la tarjeta de la línea."""
        ocupacion, atraso, cambio = self._estado_ruta(ruta)
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

    def _snack(self, texto):
        try:
            AvisoSnackbar(
                MDSnackbarText(text=texto),
                y=dp(80),  # por encima de la barra de navegación
                pos_hint={"center_x": 0.5},
                size_hint_x=0.9,
            ).open()
        except Exception as e:  # un aviso visual nunca debe tumbar la app
            registrar_error(e)

    def notificar(self, titulo, mensaje):
        """QUÉ DISPARA LA NOTIFICACIÓN: este método lo llaman los eventos de
        la app (aviso en una ruta favorita, viaje finalizado, aviso simulado).
        Delega en servicios/notificaciones.py: snackbar dentro de la app y,
        si el dispositivo lo permite, notificación del sistema (plyer)."""
        enviar_notificacion(titulo, mensaje, mostrar_en_app=self._snack)

    def abrir_menu_atraso(self, boton):
        """Botón 'Bus atrasado': pregunta cuántos minutos."""
        items = [
            {"text": f"{m} min" if m < OPCIONES_ATRASO[-1] else f"{m} min o más",
             "on_release": lambda x=m: self._elegir_atraso(x)}
            for m in OPCIONES_ATRASO
        ]
        self.menu_atraso = MDDropdownMenu(caller=boton, items=items)
        self.menu_atraso.open()

    def _elegir_atraso(self, minutos):
        if self.menu_atraso:
            self.menu_atraso.dismiss()
        self.enviar_aviso("atrasado", minutos)

    def enviar_aviso(self, tipo, minutos=0):
        """Un pasajero avisa el estado de su línea (validaciones: línea
        elegida y no repetir el mismo aviso antes del tiempo anti-spam, que
        viene de la configuración remota)."""
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
        self.publicar_aviso(self.linea_actual, tipo, minutos, propio=True)
        self._snack("¡Aviso enviado! Gracias por ayudar a otros pasajeros.")

    def publicar_aviso(self, ruta, tipo, minutos=0, propio=True):
        # TODO: enviar el aviso a un servidor y recibir los de otros usuarios
        # (hoy queda solo en este dispositivo, guardado en data/avisos.json).
        aviso = {"ruta": ruta, "tipo": tipo, "minutos": minutos,
                 "ts": time.time(), "propio": propio,
                 "autor": self.usuario_actual if propio else ""}
        self.avisos.insert(0, aviso)
        self._guardar_avisos()
        self.refrescar_avisos()
        if not propio and self.notificar_favoritas and ruta in self.favoritas:
            self.notificar(ruta, self._titulo_aviso(aviso))

    def refrescar_avisos(self):
        """Redibuja todo lo que muestra el estado de las líneas. Cada paso
        va aparte: si uno falla, los demás igual se actualizan."""
        for paso in (self._llenar_lineas_home, self.poblar_recorridos,
                     self.refrescar_favoritos, self.poblar_avisos):
            try:
                paso()
            except Exception as e:
                registrar_error(e)

    def poblar_avisos(self):
        pantalla = self._pantalla("avisos")
        caja = pantalla.ids.avisos_box
        caja.clear_widgets()
        ahora = time.time()
        anteriores = self.avisos
        self.avisos = avisos_service.historial_reciente(
            anteriores, HISTORIAL_S, ahora
        )
        if self.avisos != anteriores:
            self._guardar_avisos()
        visibles = [a for a in self.avisos
                    if not self.solo_favoritas or a["ruta"] in self.favoritas]
        for a in visibles:
            t = TIPOS_AVISO[a["tipo"]]
            caja.add_widget(AvisoCard(
                icono=t["icono"],
                titulo=self._titulo_aviso(a),
                detalle=f'{a["ruta"]} · {self._hace(a["ts"])}',
                color=list(t["color"]),
                antiguedad=f'{time.strftime("%H:%M", time.localtime(a["ts"]))} · {self._hace(a["ts"])}',
                vencido=ahora - a["ts"] > self.vigencia_s,
            ))
        pantalla.ids.avisos_vacio.text = (
            "No hay avisos en tus rutas favoritas." if self.solo_favoritas
            else "Aún no hay avisos. Cuando alguien avise, aparecerá aquí."
        )
        pantalla.ids.avisos_vacio.opacity = 0 if visibles else 1
        pantalla.ids.avisos_vacio.height = 0 if visibles else dp(40)

    def alternar_solo_favoritas(self, activo):
        self.solo_favoritas = activo
        self.poblar_avisos()

    def simular_aviso(self):
        """Solo para la demo: simula que otro pasajero envió un aviso
        (prefiere una ruta favorita) y dispara la notificación siempre
        que el interruptor de Ajustes esté activo."""
        ruta = random.choice(self.favoritas or list(RUTAS))
        tipo = random.choice(list(TIPOS_AVISO))
        minutos = random.choice(OPCIONES_ATRASO) if tipo == "atrasado" else 0
        self.publicar_aviso(ruta, tipo, minutos, propio=False)
        if ruta not in self.favoritas:
            if self.notificar_favoritas:
                self.notificar(f"{ruta} (demo)", self._titulo_aviso(self.avisos[0]))
            else:
                self._snack("Aviso simulado agregado en la pantalla Avisos.")


if __name__ == "__main__":
    InterurbanoApp().run()
