import math
import os
import random
import re
import threading
import time
import traceback
import uuid

from kivy.animation import Animation
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (BooleanProperty, ListProperty, NumericProperty,
                             StringProperty)
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapLayer, MapView, MapMarker, MapMarkerPopup  # noqa: F401
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

from config import (CONFIG_REMOTA_DEFECTO, DATA_DIR, HISTORIAL_S, ICONO_BUS,
                    LOG_ERRORES, OPCIONES_ATRASO)
from datos_rutas import (COORDENADAS, GRIS, LOCALIDADES, NARANJA, ROJO, RUTAS,
                         TIPOS_AVISO, VERDE)
from servicios import almacenamiento, autenticacion, config_remota, reputacion
from servicios.autenticacion import ErrorAutenticacion
from servicios.notificaciones import notificar as enviar_notificacion

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
    en_mapa = BooleanProperty(False)       # tarjeta del panel de Inicio: al tocarla se dibuja en el mapa
    seleccionada = BooleanProperty(False)  # es la ruta que está dibujada en el mapa


class AvisoCard(MDCard):
    icono = StringProperty("bell")
    titulo = StringProperty("")
    detalle = StringProperty("")
    color = ListProperty(GRIS)
    aviso_id = StringProperty("")
    votos_ok = NumericProperty(0)
    votos_mal = NumericProperty(0)
    mi_voto = NumericProperty(0)     # 1 (correcto), -1 (erróneo) o 0 (sin voto)


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


class DetalleScreen(Screen):
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


class CapaRuta(MapLayer):
    """Capa del mapa que dibuja el recorrido de una línea (de A a B).

    Es una capa "window": MapView llama a reposition() cada vez que el mapa
    se mueve o cambia el zoom, y aquí se recalcula la posición en pantalla
    de cada punto del trazado y se redibuja la línea. Lo que se dibuja queda
    recortado al área del mapa."""

    COLOR_LINEA = (0.16, 0.45, 0.87, 1)
    COLOR_INICIO = (0.05, 0.62, 0.43, 1)
    COLOR_FIN = (0.80, 0.18, 0.18, 1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.puntos = []   # [(lat, lon), ...] desde el origen hasta el destino

    def poner(self, puntos):
        self.puntos = list(puntos)
        self.reposition()

    def limpiar(self):
        self.puntos = []
        self.canvas.clear()

    def reposition(self):
        mapa = self.parent
        self.canvas.clear()
        if mapa is None or len(self.puntos) < 2:
            return
        xy = []
        for lat, lon in self.puntos:
            x, y = mapa.get_window_xy_from(lat, lon, mapa.zoom)
            xy.extend((x, y))
        r = dp(7)
        with self.canvas:
            Color(1, 1, 1, 0.95)                      # borde blanco (se ve sobre cualquier mapa)
            Line(points=xy, width=dp(5), cap="round", joint="round")
            Color(*self.COLOR_LINEA)
            Line(points=xy, width=dp(3), cap="round", joint="round")
            Color(1, 1, 1, 1)
            Ellipse(pos=(xy[0] - r - dp(1.5), xy[1] - r - dp(1.5)), size=(2 * r + dp(3),) * 2)
            Ellipse(pos=(xy[-2] - r - dp(1.5), xy[-1] - r - dp(1.5)), size=(2 * r + dp(3),) * 2)
            Color(*self.COLOR_INICIO)                 # A: origen
            Ellipse(pos=(xy[0] - r, xy[1] - r), size=(2 * r, 2 * r))
            Color(*self.COLOR_FIN)                    # B: destino
            Ellipse(pos=(xy[-2] - r, xy[-1] - r), size=(2 * r, 2 * r))


# ------------------------------------------------------------
# Aplicación
# ------------------------------------------------------------
class InterurbanoApp(MDApp):
    menu_origen = None
    menu_linea = None
    dialogo = None
    _marcadores = []
    marcador_yo = None
    gps_activo = False
    panel_expandido = False
    consentimiento = False   # ¿el usuario aceptó compartir ubicación?
    compartiendo = False
    linea_actual = ""
    favoritas = []
    viajes = 0
    avisos = []               # más nuevo primero: {ruta, tipo, minutos, ts, propio, autor}
    origen_actual = ""
    menu_atraso = None
    notificar_favoritas = True
    solo_favoritas = False
    _ultimo_aviso = {}
    capa_ruta = None          # CapaRuta: la línea A -> B dibujada sobre el mapa
    ruta_mapa = ""            # línea dibujada ahora en el mapa ("" = ninguna)
    _trazados = {}            # {ruta: [(lat, lon), ...]} trazados por carretera ya descargados
    ruta_detalle = ""         # línea que se está viendo en la pantalla de detalle
    pantalla_previa = "recorridos"   # a dónde vuelve la flecha "atrás" del detalle
    UMBRAL_DUDOSO = -3        # con este puntaje (o menos) un aviso se marca como dudoso

    usuario_actual = ""       # "" = nadie ha iniciado sesión
    nombre_visible = ""
    _cargando = False         # True mientras se aplica el perfil a la interfaz
    config = {}               # valores de la configuración remota
    fuente_config = ""        # "remota" | "caché" | "valor por defecto"

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.title = "EnRuta Ya!"
        self.favoritas = []
        self.avisos = []
        self._ultimo_aviso = {}
        # Configuración inmediata (caché o valores por defecto); la remota
        # llega después, en on_start, sin bloquear la interfaz.
        self.config, self.fuente_config = config_remota.cargar_local()
        return Builder.load_file(os.path.join(BASE_DIR, "root.kv"))

    def on_start(self):
        mapa = self.root.ids.sm.get_screen("home").ids.mapa
        mapa.bind(zoom=self._ajustar_marcadores)
        # La capa de la ruta se agrega primero para que los iconos de bus
        # (capa de marcadores, que se crea después) queden por encima.
        self.capa_ruta = CapaRuta()
        mapa.add_layer(self.capa_ruta)
        self._cargar_trazados()
        self.cargar_avisos()
        self._aplicar_config(self.config, self.fuente_config)
        self.actualizar_config_remota()
        # Cada minuto se actualizan los "hace X min" y se descartan avisos vencidos.
        Clock.schedule_interval(lambda dt: self.refrescar_avisos(), 60)

    def _ajustar_marcadores(self, *args):
        """Achica/agranda los iconos de bus según el zoom actual del mapa."""
        try:
            zoom = self.root.ids.sm.get_screen("home").ids.mapa.zoom
        except Exception:
            return
        buses = [m for m in self._marcadores if isinstance(m, MarcadorBus)]
        if self.marcador_yo:
            buses.append(self.marcador_yo)
        for m in buses:
            m.ajustar_zoom(zoom)

    def cambiar_pantalla(self, nombre):
        self.root.ids.sm.current = nombre

    def _pantalla(self, nombre):
        return self.root.ids.sm.get_screen(nombre)

    def _tarjeta(self, ruta, en_mapa=False):
        d = RUTAS[ruta]
        texto, color = self._texto_estado(ruta)
        return LineaCard(
            ruta=ruta,
            detalle=f'{d["parada"]} · {d["frecuencia"]}',
            minutos=d["minutos"],
            aviso=texto,
            aviso_color=list(color),
            en_mapa=en_mapa,
            seleccionada=en_mapa and ruta == self.ruta_mapa,
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
        self.refrescar_reputacion()
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
            self.avisos = guardados

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
        self.origen_actual = lugar
        self.quitar_ruta_mapa()   # limpia la ruta anterior y pone el título del panel
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
            caja.add_widget(self._tarjeta(d["ruta"], en_mapa=True))

    def alternar_panel_buses(self):
        """Expande o colapsa el panel de 'Buses desde...' para estorbar
        menos la vista del mapa."""
        home = self._pantalla("home")
        self.panel_expandido = not self.panel_expandido
        alto = dp(260) if self.panel_expandido else dp(48)
        Animation(height=alto, d=0.18, t="out_quad").start(home.ids.panel_buses)
        home.ids.panel_icono.icon = "chevron-down" if self.panel_expandido else "chevron-up"

    @staticmethod
    def _minutos(texto):
        """'1 h 20 min' -> 80, '15 min' -> 15 (para ubicar buses de demo)."""
        horas = re.search(r"(\d+)\s*h", texto)
        mins = re.search(r"(\d+)\s*min", texto)
        return (int(horas.group(1)) * 60 if horas else 0) + (int(mins.group(1)) if mins else 0)

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
            destino = d["ruta"].split("->")[-1].strip()
            if destino not in COORDENADAS:
                continue
            dlat, dlon = COORDENADAS[destino]
            dur = max(self._minutos(d["duracion"]), 1)
            frac = min(0.8, max(0.15, self._minutos(d["minutos"]) / dur))
            bus = MarcadorBus(
                lat=lat + (dlat - lat) * frac,
                lon=lon + (dlon - lon) * frac,
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
    # Ruta A -> B dibujada en el mapa de Inicio. Al tocar una línea del
    # panel "Buses desde..." se dibuja su recorrido (por carretera si hay
    # internet; si no, una línea recta). Tocarla otra vez la quita.
    # --------------------------------------------------------
    ARCHIVO_TRAZADOS = os.path.join(DATA_DIR, "trazados.json")

    def _cargar_trazados(self):
        """Recupera los trazados ya descargados para no pedirlos de nuevo."""
        guardados = almacenamiento.leer_json(self.ARCHIVO_TRAZADOS, {})
        self._trazados = {r: [tuple(p) for p in pts] for r, pts in guardados.items()
                          if isinstance(pts, list) and len(pts) >= 2}

    def _guardar_trazados(self):
        try:
            almacenamiento.guardar_json(
                self.ARCHIVO_TRAZADOS,
                {r: [list(p) for p in pts] for r, pts in self._trazados.items()})
        except OSError as e:
            registrar_error(e)

    def _titulo_panel(self):
        if self.ruta_mapa:
            return f'{self.ruta_mapa.replace("->", "→")} · toca para cambiar'
        if self.origen_actual:
            return f"Buses desde {self.origen_actual} (toca uno para verlo en el mapa)"
        return "Elige una localidad para ver los buses"

    def tocar_linea(self, tarjeta):
        """Tarjetas del panel de Inicio: dibujan la ruta. En el resto de las
        pantallas (Recorridos, Perfil) abren el detalle de la línea."""
        if tarjeta.en_mapa:
            self.seleccionar_ruta_mapa(tarjeta.ruta)
        else:
            self.mostrar_detalle(tarjeta.ruta)

    def seleccionar_ruta_mapa(self, ruta):
        if ruta == self.ruta_mapa:          # tocar la misma ruta = quitarla
            self.quitar_ruta_mapa()
            return
        d = RUTAS[ruta]
        destino = ruta.split("->")[-1].strip()
        if d["origen"] not in COORDENADAS or destino not in COORDENADAS:
            self._snack("Esta línea aún no tiene coordenadas para dibujarla.")
            return
        self.ruta_mapa = ruta
        trazado = self._trazados.get(ruta)
        puntos = trazado or [COORDENADAS[d["origen"]], COORDENADAS[destino]]
        self.capa_ruta.poner(puntos)
        self._encuadrar(puntos)
        self._llenar_lineas_home()
        self._pantalla("home").ids.lineas_titulo.text = self._titulo_panel()
        if self.panel_expandido:            # se pliega el panel para ver el mapa
            self.alternar_panel_buses()
        if trazado is None:
            threading.Thread(target=self._descargar_trazado,
                             args=(ruta, d["origen"], destino), daemon=True).start()

    def quitar_ruta_mapa(self):
        self.ruta_mapa = ""
        if self.capa_ruta is not None:
            self.capa_ruta.limpiar()
        self._llenar_lineas_home()
        self._pantalla("home").ids.lineas_titulo.text = self._titulo_panel()

    def _descargar_trazado(self, ruta, origen, destino):
        """Hilo aparte: pide a OSRM el recorrido por carretera entre las dos
        localidades. Si falla (sin internet), se queda la línea recta."""
        puntos = None
        try:
            import requests
            la1, lo1 = COORDENADAS[origen]
            la2, lo2 = COORDENADAS[destino]
            url = (f"https://router.project-osrm.org/route/v1/driving/"
                   f"{lo1},{la1};{lo2},{la2}?overview=full&geometries=geojson")
            r = requests.get(url, timeout=8, headers={"User-Agent": "EnRutaYa/1.0"})
            datos = r.json()
            if datos.get("code") == "Ok":
                coords = datos["routes"][0]["geometry"]["coordinates"]  # [lon, lat]
                paso = max(1, len(coords) // 400)    # se aligera para dibujar rápido
                puntos = [(c[1], c[0]) for c in coords[::paso]]
                ultimo = (coords[-1][1], coords[-1][0])
                if puntos[-1] != ultimo:
                    puntos.append(ultimo)
        except Exception as e:
            print("No se pudo descargar el trazado:", e)
        Clock.schedule_once(lambda dt: self._trazado_listo(ruta, puntos))

    def _trazado_listo(self, ruta, puntos):
        if puntos and len(puntos) >= 2:
            self._trazados[ruta] = puntos
            self._guardar_trazados()
            if ruta == self.ruta_mapa:
                self.capa_ruta.poner(puntos)
        elif ruta == self.ruta_mapa:
            self._snack("Sin conexión: se muestra una línea recta entre las localidades.")

    @staticmethod
    def _px_mercator(lat, lon, zoom):
        """Posición en píxeles de un punto en el mapa completo a ese zoom."""
        n = 256 * (2 ** zoom)
        s = math.sin(math.radians(lat))
        x = (lon + 180.0) / 360.0 * n
        y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
        return x, y

    def _encuadrar(self, puntos):
        """Centra el mapa y elige el mayor zoom en el que cabe toda la ruta."""
        mapa = self._pantalla("home").ids.mapa
        lats = [p[0] for p in puntos]
        lons = [p[1] for p in puntos]
        ancho = mapa.width * 0.80
        alto = max(mapa.height - dp(58) - dp(48), dp(100)) * 0.70   # sin barra ni panel
        zoom = 8
        for z in range(15, 7, -1):
            x1, y1 = self._px_mercator(max(lats), min(lons), z)
            x2, y2 = self._px_mercator(min(lats), max(lons), z)
            if abs(x2 - x1) <= ancho and abs(y2 - y1) <= alto:
                zoom = z
                break
        mapa.zoom = zoom
        mapa.center_on((max(lats) + min(lats)) / 2, (max(lons) + min(lons)) / 2)

    # --------------------------------------------------------
    # Botón "reubicarme" del mapa: centra en mi posición GPS real
    # y me dibuja como un bus en el mapa.
    # --------------------------------------------------------
    def localizarme(self):
        """Botón de reubicarme: usa el GPS del dispositivo si existe
        (celular/tablet); en un PC de escritorio, que normalmente no
        tiene GPS, calcula una posición aproximada por IP en segundo
        plano para no congelar la interfaz."""
        if self.gps_activo:
            return
        if gps is not None:
            try:
                gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
                gps.start(minTime=2000, minDistance=5)
                self.gps_activo = True
                return
            except NotImplementedError:
                pass  # sin proveedor de GPS en este dispositivo -> sigue abajo
        threading.Thread(target=self._localizar_por_ip, daemon=True).start()

    def _localizar_por_ip(self):
        """Se ejecuta en un hilo aparte para no bloquear la app."""
        lat, lon = COORDENADAS["Temuco"]  # último recurso si todo falla
        try:
            import requests
            r = requests.get("http://ip-api.com/json/", timeout=4)
            datos = r.json()
            if datos.get("status") == "success":
                lat, lon = datos["lat"], datos["lon"]
        except Exception as e:
            print("No se pudo obtener ubicación aproximada por IP:", e)
        Clock.schedule_once(lambda dt: self.actualizar_mi_ubicacion(lat, lon))

    def on_gps_location(self, **kwargs):
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is not None and lon is not None:
            self.actualizar_mi_ubicacion(lat, lon)

    def on_gps_status(self, stype, status):
        print(f"GPS [{stype}]: {status}")

    def actualizar_mi_ubicacion(self, lat, lon):
        home = self._pantalla("home")
        mapa = home.ids.mapa
        if self.marcador_yo:
            mapa.remove_marker(self.marcador_yo)
        self.marcador_yo = MarcadorBus(
            lat=lat, lon=lon,
            source=ICONO_BUS if os.path.exists(ICONO_BUS)
                   else "atlas://data/images/defaulttheme/checkbox_on",
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
        self.detener_gps()
        self._guardar_perfil()
        self._guardar_avisos()

    # --------------------------------------------------------
    # Detalle de una línea (al tocar cualquier tarjeta)
    # --------------------------------------------------------
    def mostrar_detalle(self, ruta):
        """Al tocar cualquier tarjeta de línea se abre la pantalla de detalle."""
        actual = self.root.ids.sm.current
        if actual != "detalle":
            self.pantalla_previa = actual
        self.ruta_detalle = ruta
        self.poblar_detalle()
        self.cambiar_pantalla("detalle")

    def cerrar_detalle(self):
        self.ruta_detalle = ""
        self.cambiar_pantalla(self.pantalla_previa)

    def poblar_detalle(self):
        """Dibuja la pantalla de detalle de la línea abierta: datos del
        recorrido, estado actual y avisos recientes (con botones de voto)."""
        ruta = self.ruta_detalle
        if not ruta or ruta not in RUTAS:
            return
        d = RUTAS[ruta]
        ids = self._pantalla("detalle").ids
        ids.det_titulo.text = ruta.replace("->", "→")
        ids.det_parada.text = f'Parada: {d["parada"]}'
        ids.det_minutos.text = d["minutos"]
        ids.det_frecuencia.valor = d["frecuencia"]
        ids.det_duracion.valor = d["duracion"]
        ids.det_tarifa.valor = d["tarifa"]

        texto, color = self._texto_estado(ruta)
        ids.det_estado.text = texto
        ids.det_estado.text_color = list(color)

        es_fav = ruta in self.favoritas
        ids.det_fav_icono.icon = "star" if es_fav else "star-outline"
        ids.det_fav_texto.text = "Quitar de favoritas" if es_fav else "Agregar a favoritas"

        caja = ids.det_avisos_box
        caja.clear_widgets()
        ahora = time.time()
        recientes = [a for a in self.avisos
                     if a["ruta"] == ruta and ahora - a["ts"] <= HISTORIAL_S]
        niveles = {}
        for a in recientes:
            caja.add_widget(self._tarjeta_aviso(a, niveles))
        ids.det_vacio.opacity = 0 if recientes else 1
        ids.det_vacio.height = 0 if recientes else dp(40)

    def alternar_favorita(self, ruta):
        if ruta in self.favoritas:
            self.favoritas.remove(ruta)
            self._snack("Quitada de tus favoritas.")
        else:
            self.favoritas.append(ruta)
            self._snack("Agregada a tus favoritas.")
        self._guardar_perfil()
        self.refrescar_favoritos()
        self.poblar_avisos()
        self.poblar_detalle()

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
                text="Mientras vayas en la micro, otros usuarios verán la posición "
                     "del bus en el mapa. Solo se comparte durante el viaje y "
                     "puedes detenerlo cuando quieras."
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
        p.ids.estado_label.text = f"Compartiendo tu ubicación en {self.linea_actual}"

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
        """Devuelve (ocupación, atraso, cambio_ruta): el aviso vigente más
        reciente de cada tipo para esa línea, o None si no hay."""
        ahora = time.time()
        vigentes = [a for a in self.avisos
                    if a["ruta"] == ruta and ahora - a["ts"] <= self.vigencia_s
                    and not self._dudoso(a)]
        ocupacion = next((a for a in vigentes if a["tipo"] in ("lleno", "asientos")), None)
        atraso = next((a for a in vigentes if a["tipo"] == "atrasado"), None)
        cambio = next((a for a in vigentes if a["tipo"] == "cambio_ruta"), None)
        return ocupacion, atraso, cambio

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

    def publicar_aviso(self, ruta, tipo, minutos=0, propio=True, autor=""):
        # TODO: enviar el aviso a un servidor y recibir los de otros usuarios
        # (hoy queda solo en este dispositivo, guardado en data/avisos.json).
        autor = autor or (self.usuario_actual if propio else "")
        aviso = {"id": uuid.uuid4().hex[:8], "ruta": ruta, "tipo": tipo,
                 "minutos": minutos, "ts": time.time(), "propio": propio,
                 "autor": autor, "votos": {}}
        self.avisos.insert(0, aviso)
        self._guardar_avisos()
        try:
            reputacion.sumar_aviso(autor)
        except OSError as e:
            registrar_error(e)
        self.refrescar_avisos()
        if not propio and self.notificar_favoritas and ruta in self.favoritas:
            self.notificar(ruta, self._titulo_aviso(aviso))

    def refrescar_avisos(self):
        """Redibuja todo lo que muestra el estado de las líneas. Cada paso
        va aparte: si uno falla, los demás igual se actualizan."""
        for paso in (self._llenar_lineas_home, self.poblar_recorridos,
                     self.refrescar_favoritos, self.poblar_avisos,
                     self.poblar_detalle):
            try:
                paso()
            except Exception as e:
                registrar_error(e)

    def poblar_avisos(self):
        pantalla = self._pantalla("avisos")
        caja = pantalla.ids.avisos_box
        caja.clear_widgets()
        ahora = time.time()
        antes = len(self.avisos)
        self.avisos = [a for a in self.avisos if ahora - a["ts"] <= HISTORIAL_S]
        if len(self.avisos) != antes:
            self._guardar_avisos()
        visibles = [a for a in self.avisos
                    if not self.solo_favoritas or a["ruta"] in self.favoritas]
        niveles = {}   # autor -> nombre de nivel (se calcula una vez por autor)
        for a in visibles:
            caja.add_widget(self._tarjeta_aviso(a, niveles))
        pantalla.ids.avisos_vacio.text = (
            "No hay avisos en tus rutas favoritas." if self.solo_favoritas
            else "Aún no hay avisos. Cuando alguien avise, aparecerá aquí."
        )
        pantalla.ids.avisos_vacio.opacity = 0 if visibles else 1
        pantalla.ids.avisos_vacio.height = 0 if visibles else dp(40)

    # --------------------------------------------------------
    # Valoración de avisos y reputación de los autores
    # (los puntos viven en servicios/reputacion.py -> data/reputacion.json)
    # --------------------------------------------------------
    def _puntaje_aviso(self, aviso):
        return sum(aviso.get("votos", {}).values())

    def _dudoso(self, aviso):
        """Un aviso con muchos votos 'erróneo' deja de contar en el estado
        de la línea y se muestra como dudoso."""
        return self._puntaje_aviso(aviso) <= self.UMBRAL_DUDOSO

    def votar_aviso(self, aviso_id, valor):
        """valor: 1 = correcto, -1 = erróneo. Un voto por usuario y aviso;
        tocar de nuevo el mismo botón quita el voto. No se puede votar el
        propio aviso."""
        if not self.usuario_actual:
            return
        aviso = next((a for a in self.avisos if a.get("id") == aviso_id), None)
        if aviso is None:
            return
        if aviso.get("autor") and aviso["autor"] == self.usuario_actual:
            self._snack("No puedes votar tu propio aviso.")
            return
        votos = aviso.setdefault("votos", {})
        previo = votos.get(self.usuario_actual, 0)
        nuevo = 0 if previo == valor else valor
        if nuevo:
            votos[self.usuario_actual] = nuevo
        else:
            votos.pop(self.usuario_actual, None)
        try:
            reputacion.actualizar_voto(aviso.get("autor", ""), previo, nuevo)
        except OSError as e:
            registrar_error(e)
        self._guardar_avisos()
        self.refrescar_avisos()
        self.refrescar_reputacion()
        if nuevo:
            self._snack("¡Gracias por tu voto!")

    def refrescar_reputacion(self):
        """Muestra en Perfil el nivel y los puntos del usuario actual."""
        if not self.usuario_actual:
            return
        pf = self._pantalla("perfil").ids
        if "nivel_label" not in pf:   # por si root.kv aún no tiene la tarjeta
            return
        pts = reputacion.puntos(self.usuario_actual)
        nombre, icono, faltan = reputacion.nivel(pts)
        pf.nivel_label.text = f"{nombre} · {pts} puntos"
        pf.nivel_icono.icon = icono
        pf.nivel_falta.text = (f"Te faltan {faltan} puntos para el siguiente nivel"
                               if faltan else "¡Nivel máximo!")

    def _tarjeta_aviso(self, a, niveles):
        """Crea la tarjeta de un aviso (con sus botones de voto). La usan la
        pantalla Avisos y el detalle de cada línea. `niveles` es un caché
        {autor: nombre de nivel} para no leer el archivo por cada tarjeta."""
        t = TIPOS_AVISO[a["tipo"]]
        votos = a.get("votos", {})
        autor = a.get("autor", "")
        if autor and autor not in niveles:
            niveles[autor] = reputacion.nivel(reputacion.puntos(autor))[0]
        quien = f' · @{autor} ({niveles[autor]})' if autor else ""
        dudoso = self._dudoso(a)
        return AvisoCard(
            icono="alert-circle-outline" if dudoso else t["icono"],
            titulo=("Dudoso: " if dudoso else "") + self._titulo_aviso(a),
            detalle=f'{a["ruta"]} · {self._hace(a["ts"])}{quien}',
            color=list(GRIS if dudoso else t["color"]),
            aviso_id=a.get("id", ""),
            votos_ok=sum(1 for v in votos.values() if v == 1),
            votos_mal=sum(1 for v in votos.values() if v == -1),
            mi_voto=votos.get(self.usuario_actual, 0),
        )

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
        autor = random.choice(["maria_t", "pedro_r", "luis_v"])
        self.publicar_aviso(ruta, tipo, minutos, propio=False, autor=autor)
        if ruta not in self.favoritas:
            if self.notificar_favoritas:
                self.notificar(f"{ruta} (demo)", self._titulo_aviso(self.avisos[0]))
            else:
                self._snack("Aviso simulado agregado en la pantalla Avisos.")


if __name__ == "__main__":
    InterurbanoApp().run()