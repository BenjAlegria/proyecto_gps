"""
EnRuta Ya! - App móvil para consultar horarios y llegada
de buses interurbanos mediante un mapa.

Evaluación: Kivy + KivyMD 2.0, ScreenManager, KV Language.
Separación estricta: la interfaz vive en root.kv, la lógica aquí.
"""

import os
import random
import threading
import time
import traceback

from kivy.animation import Animation
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapView, MapMarker, MapMarkerPopup  # noqa: F401
try:
    from plyer import gps
except Exception:
    # plyer.gps no está disponible en este sistema (falta un proveedor de
    # GPS para esta plataforma, ej. Windows/Linux de escritorio). La app
    # sigue funcionando: el botón de ubicación usará una posición de prueba.
    gps = None

try:
    from plyer import notification
except Exception:
    # Sin proveedor de notificaciones del sistema (ej. PC de escritorio):
    # los avisos igual se muestran dentro de la app (snackbar + pantalla Avisos).
    notification = None

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


# ------------------------------------------------------------
# Registro de errores: si algo falla dentro de la app, en vez de cerrarse
# se guarda el detalle completo en crash_log.txt (junto a main.py) y la
# app sigue funcionando.
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_ERRORES = os.path.join(BASE_DIR, "crash_log.txt")
ICONO_BUS = os.path.join(BASE_DIR, "bus_marker.png")


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
# Datos de ejemplo (frecuencias, tarifas y horarios son referenciales:
# reemplazar por los datos reales del socio comunitario)
# ------------------------------------------------------------
COORDENADAS = {
    "Nueva Imperial": (-38.7442, -72.9503),
    "Lautaro": (-38.5285, -72.4318),
    "Carahue": (-38.7103, -73.1561),
    "Padre Las Casas": (-38.7683, -72.5975),
    "Temuco": (-38.7359, -72.5904),
}

LOCALIDADES = {
    "Nueva Imperial": [
        {"ruta": "Nueva Imperial -> Temuco", "parada": "Terminal Nueva Imperial",
         "minutos": "15 min", "frecuencia": "Cada 20 min", "tarifa": "$1.500", "duracion": "50 min"},
        {"ruta": "Nueva Imperial -> Carahue", "parada": "Terminal Nueva Imperial",
         "minutos": "40 min", "frecuencia": "Cada 45 min", "tarifa": "$1.200", "duracion": "35 min"},
    ],
    "Lautaro": [
        {"ruta": "Lautaro -> Temuco", "parada": "Parada Balmaceda",
         "minutos": "50 min", "frecuencia": "Cada 30 min", "tarifa": "$1.800", "duracion": "1 h"},
        {"ruta": "Lautaro -> Victoria", "parada": "Terminal Lautaro",
         "minutos": "25 min", "frecuencia": "Cada 40 min", "tarifa": "$1.000", "duracion": "35 min"},
    ],
    "Carahue": [
        {"ruta": "Carahue -> Temuco", "parada": "Terminal Carahue",
         "minutos": "30 min", "frecuencia": "Cada 30 min", "tarifa": "$2.500", "duracion": "1 h 20 min"},
        {"ruta": "Carahue -> Nueva Imperial", "parada": "Terminal Carahue",
         "minutos": "10 min", "frecuencia": "Cada 45 min", "tarifa": "$1.200", "duracion": "35 min"},
    ],
    "Padre Las Casas": [
        {"ruta": "Padre Las Casas -> Temuco", "parada": "Parada Balmaceda",
         "minutos": "20 min", "frecuencia": "Cada 10 min", "tarifa": "$700", "duracion": "20 min"},
    ],
    "Temuco": [
        {"ruta": "Temuco -> Lautaro", "parada": "Terminal Rodoviario",
         "minutos": "5 min", "frecuencia": "Cada 30 min", "tarifa": "$1.800", "duracion": "1 h"},
        {"ruta": "Temuco -> Nueva Imperial", "parada": "Terminal Rodoviario",
         "minutos": "12 min", "frecuencia": "Cada 20 min", "tarifa": "$1.500", "duracion": "50 min"},
    ],
}

# Índice por nombre de ruta: {ruta: {..., "origen": localidad}}
RUTAS = {
    d["ruta"]: {**d, "origen": lugar}
    for lugar, lista in LOCALIDADES.items()
    for d in lista
}


# ------------------------------------------------------------
# Avisos de pasajeros (pedidos en la encuesta: 71% quedó sin poder subir
# por bus lleno, 41% sufrió buses que no pasaron a la hora, 59% quiere
# notificaciones de retrasos y 65% ver la capacidad de asientos).
# ------------------------------------------------------------
ROJO = (0.80, 0.18, 0.18, 1)
NARANJA = (0.90, 0.50, 0.05, 1)
VERDE = (0.05, 0.62, 0.43, 1)
GRIS = (0.50, 0.52, 0.58, 1)

TIPOS_AVISO = {
    "lleno": {"texto": "Bus lleno", "icono": "account-group", "color": ROJO},
    "asientos": {"texto": "Hay asientos", "icono": "seat-passenger", "color": VERDE},
    "atrasado": {"texto": "Bus atrasado", "icono": "clock-alert", "color": NARANJA},
    "cambio_ruta": {"texto": "Cambio de ruta", "icono": "map-marker-alert", "color": NARANJA},
}

VIGENCIA_S = 30 * 60        # un aviso cuenta como "estado actual" por 30 min
HISTORIAL_S = 2 * 60 * 60   # la pantalla Avisos muestra hasta las últimas 2 h
ANTISPAM_S = 2 * 60         # mismo aviso, misma línea: máximo 1 cada 2 min
OPCIONES_ATRASO = (5, 10, 15, 20)


# ------------------------------------------------------------
# Widgets propios (su diseño está en root.kv)
# ------------------------------------------------------------
class LineaCard(MDCard):
    ruta = StringProperty("")
    detalle = StringProperty("")
    minutos = StringProperty("")
    aviso = StringProperty("")
    aviso_color = ListProperty(GRIS)


class AvisoCard(MDCard):
    icono = StringProperty("bell")
    titulo = StringProperty("")
    detalle = StringProperty("")
    color = ListProperty(GRIS)


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


# ------------------------------------------------------------
# Aplicación
# ------------------------------------------------------------
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
    a dp(40) (mapa cerca)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.fit_mode = "contain"

    def ajustar_zoom(self, zoom):
        lado = dp(min(40, max(16, 16 + (zoom - 10) * 4)))
        self.size = (lado, lado)
        capa = self._layer
        if capa is not None and capa.parent is not None:
            capa.set_marker_position(capa.parent, self)


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
    avisos = []               # más nuevo primero: {ruta, tipo, minutos, ts, propio}
    origen_actual = ""
    menu_atraso = None
    notificar_favoritas = True
    solo_favoritas = False
    _ultimo_aviso = {}

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.title = "EnRuta Ya!"
        self.favoritas = []
        self.avisos = []
        self._ultimo_aviso = {}
        return Builder.load_file(os.path.join(BASE_DIR, "root.kv"))

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

    def on_start(self):
        self.root.ids.sm.get_screen("home").ids.mapa.bind(zoom=self._ajustar_marcadores)
        self.cargar_avisos_ejemplo()
        self.refrescar_avisos()
        # Cada minuto se actualizan los "hace X min" y se descartan avisos vencidos.
        Clock.schedule_interval(lambda dt: self.refrescar_avisos(), 60)

    def cambiar_pantalla(self, nombre):
        self.root.ids.sm.current = nombre

    def cambiar_tema(self, oscuro):
        self.theme_cls.theme_style = "Dark" if oscuro else "Light"

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
        home = self.root.ids.sm.get_screen("home")
        home.ids.origen_text.text = lugar
        home.ids.lineas_titulo.text = f"Buses desde {lugar} (toca uno para ver más)"
        self.origen_actual = lugar
        self._llenar_lineas_home()
        self.actualizar_mapa(home.ids.mapa, lugar)
        self.panel_expandido = False
        self.alternar_panel_buses()  # se abre mostrando los buses recién cargados

    def _llenar_lineas_home(self):
        """Redibuja las tarjetas del panel 'Buses desde...' de Inicio."""
        if not self.origen_actual:
            return
        home = self.root.ids.sm.get_screen("home")
        caja = home.ids.lineas_box
        caja.clear_widgets()
        for d in LOCALIDADES[self.origen_actual]:
            caja.add_widget(self._tarjeta(d["ruta"]))

    def alternar_panel_buses(self):
        """Expande o colapsa el panel de 'Buses desde...' para estorbar
        menos la vista del mapa."""
        home = self.root.ids.sm.get_screen("home")
        self.panel_expandido = not self.panel_expandido
        alto = dp(260) if self.panel_expandido else dp(48)
        Animation(height=alto, d=0.18, t="out_quad").start(home.ids.panel_buses)
        home.ids.panel_icono.icon = "chevron-down" if self.panel_expandido else "chevron-up"

    def actualizar_mapa(self, mapa, lugar):
        """Centra el mapa en la localidad y dibuja parada + bus (simulado)."""
        lat, lon = COORDENADAS[lugar]
        for m in self._marcadores:
            mapa.remove_marker(m)
        self._marcadores = []

        parada = MapMarkerPopup(lat=lat, lon=lon)
        mapa.add_marker(parada)
        self._marcadores.append(parada)

        if lugar != "Temuco":
            tlat, tlon = COORDENADAS["Temuco"]
            bus = MarcadorBus(lat=(lat + tlat) / 2, lon=(lon + tlon) / 2,
                            source="atlas://data/images/defaulttheme/checkbox_on")
            mapa.add_marker(bus)
            self._marcadores.append(bus)

        mapa.zoom = 11
        mapa.center_on(lat, lon)
        self._ajustar_marcadores()

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
        home = self.root.ids.sm.get_screen("home")
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
        self.refrescar_favoritos()
        self.poblar_avisos()

    # --------------------------------------------------------
    # Recorridos y Perfil
    # --------------------------------------------------------
    def poblar_recorridos(self):
        pantalla = self.root.ids.sm.get_screen("recorridos")
        caja = pantalla.ids.recorridos_box
        caja.clear_widgets()
        for ruta in RUTAS:
            caja.add_widget(self._tarjeta(ruta))
        pantalla.ids.recorridos_resumen.text = (
            f"{len(RUTAS)} recorridos en {len(LOCALIDADES)} localidades"
        )

    def refrescar_favoritos(self):
        p = self.root.ids.sm.get_screen("perfil")
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
        p = self.root.ids.sm.get_screen("perfil")
        p.ids.nombre_label.text = texto
        campo.text = ""

    def cambiar_consentimiento(self, activo):
        self.consentimiento = activo
        if not activo and self.compartiendo:
            self.detener_compartir()

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
        pantalla = self.root.ids.sm.get_screen("compartir")
        self.linea_actual = ruta
        pantalla.ids.linea_text.text = ruta
        pantalla.ids.linea_error.text = ""

    def alternar_compartir(self):
        pantalla = self.root.ids.sm.get_screen("compartir")
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
        self.root.ids.sm.get_screen("perfil").ids.switch_consent.active = True
        self.dialogo.dismiss()
        self.iniciar_compartir()

    def iniciar_compartir(self):
        # TODO: además de mostrar mi posición local, enviarla a un servidor
        # para que otros usuarios la vean en su propio mapa.
        self.compartiendo = True
        self.localizarme()
        p = self.root.ids.sm.get_screen("compartir")
        p.ids.compartir_btn_text.text = "DETENER VIAJE"
        p.ids.estado_label.text = f"Compartiendo tu ubicación en {self.linea_actual}"

    def detener_compartir(self):
        self.compartiendo = False
        self.detener_gps()
        home = self.root.ids.sm.get_screen("home")
        if self.marcador_yo:
            home.ids.mapa.remove_marker(self.marcador_yo)
            self.marcador_yo = None
        self.viajes += 1
        self.root.ids.sm.get_screen("perfil").ids.viajes_num.text = str(self.viajes)
        p = self.root.ids.sm.get_screen("compartir")
        p.ids.compartir_btn_text.text = "INICIAR VIAJE"
        p.ids.estado_label.text = "Tu ubicación no se está compartiendo."


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
                    if a["ruta"] == ruta and ahora - a["ts"] <= VIGENCIA_S]
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
        """Notificación dentro de la app y, si el dispositivo lo permite,
        también del sistema (Android/iOS vía plyer)."""
        self._snack(f"{titulo}: {mensaje}")
        if notification is not None:
            try:
                notification.notify(title=titulo, message=mensaje,
                                    app_name="EnRuta Ya!", timeout=8)
            except Exception as e:
                print("No se pudo mostrar la notificación del sistema:", e)

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
        elegida y no repetir el mismo aviso en menos de 2 minutos)."""
        pantalla = self.root.ids.sm.get_screen("compartir")
        if not self.linea_actual:
            pantalla.ids.linea_error.text = "Primero elige la línea en la que vas"
            return
        ahora = time.time()
        clave = (self.linea_actual, tipo)
        if ahora - self._ultimo_aviso.get(clave, 0) < ANTISPAM_S:
            self._snack("Ya enviaste este aviso hace un momento. ¡Gracias!")
            return
        self._ultimo_aviso[clave] = ahora
        self.publicar_aviso(self.linea_actual, tipo, minutos, propio=True)
        self._snack("¡Aviso enviado! Gracias por ayudar a otros pasajeros.")

    def publicar_aviso(self, ruta, tipo, minutos=0, propio=True):
        # TODO: enviar el aviso a un servidor y recibir los de otros usuarios
        # (hoy queda solo en este dispositivo, igual que la ubicación).
        aviso = {"ruta": ruta, "tipo": tipo, "minutos": minutos,
                 "ts": time.time(), "propio": propio}
        self.avisos.insert(0, aviso)
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
        pantalla = self.root.ids.sm.get_screen("avisos")
        caja = pantalla.ids.avisos_box
        caja.clear_widgets()
        ahora = time.time()
        self.avisos = [a for a in self.avisos if ahora - a["ts"] <= HISTORIAL_S]
        visibles = [a for a in self.avisos
                    if not self.solo_favoritas or a["ruta"] in self.favoritas]
        for a in visibles:
            t = TIPOS_AVISO[a["tipo"]]
            caja.add_widget(AvisoCard(
                icono=t["icono"],
                titulo=self._titulo_aviso(a),
                detalle=f'{a["ruta"]} · {self._hace(a["ts"])}',
                color=list(t["color"]),
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

    def cambiar_notificaciones(self, activo):
        self.notificar_favoritas = activo

    def cargar_avisos_ejemplo(self):
        """Avisos de ejemplo para la demo (como los horarios, son
        referenciales hasta que exista el servidor)."""
        ahora = time.time()
        ejemplo = [
            ("Temuco -> Nueva Imperial", "asientos", 0, 3),
            ("Nueva Imperial -> Temuco", "lleno", 0, 6),
            ("Lautaro -> Temuco", "atrasado", 10, 12),
        ]
        self.avisos = [
            {"ruta": r, "tipo": t, "minutos": m, "ts": ahora - hace * 60, "propio": False}
            for r, t, m, hace in ejemplo
        ]

    def simular_aviso(self):
        """Solo para la demo: simula que otro pasajero envió un aviso
        (prefiere una ruta favorita para mostrar la notificación)."""
        ruta = random.choice(self.favoritas or list(RUTAS))
        tipo = random.choice(list(TIPOS_AVISO))
        minutos = random.choice(OPCIONES_ATRASO) if tipo == "atrasado" else 0
        self.publicar_aviso(ruta, tipo, minutos, propio=False)
        if not (self.notificar_favoritas and ruta in self.favoritas):
            self._snack("Aviso simulado agregado en la pantalla Avisos.")


if __name__ == "__main__":
    InterurbanoApp().run()