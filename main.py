"""
Interurbano Sur - App móvil para consultar horarios y llegada
de buses interurbanos mediante un mapa.

Evaluación: Kivy + KivyMD 2.0, ScreenManager, KV Language.
Separación estricta: la interfaz vive en root.kv, la lógica aquí.
"""

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapView, MapMarker, MapMarkerPopup  # noqa: F401

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
# Widgets propios (su diseño está en root.kv)
# ------------------------------------------------------------
class LineaCard(MDCard):
    ruta = StringProperty("")
    detalle = StringProperty("")
    minutos = StringProperty("")


class HomeScreen(Screen):
    pass


class RecorridosScreen(Screen):
    pass


class CompartirScreen(Screen):
    pass


class PerfilScreen(Screen):
    pass


# ------------------------------------------------------------
# Aplicación
# ------------------------------------------------------------
class InterurbanoApp(MDApp):
    menu_origen = None
    menu_linea = None
    dialogo = None
    _marcadores = []
    consentimiento = False   # ¿el usuario aceptó compartir ubicación?
    compartiendo = False
    linea_actual = ""
    favoritas = []
    viajes = 0

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.title = "Interurbano Sur"
        self.favoritas = []
        return Builder.load_file("root.kv")

    def on_start(self):
        self.poblar_recorridos()
        self.refrescar_favoritos()

    def cambiar_pantalla(self, nombre):
        self.root.ids.sm.current = nombre

    def _tarjeta(self, ruta):
        d = RUTAS[ruta]
        return LineaCard(
            ruta=ruta,
            detalle=f'{d["parada"]} · {d["frecuencia"]}',
            minutos=d["minutos"],
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
        caja = home.ids.lineas_box
        caja.clear_widgets()
        for d in LOCALIDADES[lugar]:
            caja.add_widget(self._tarjeta(d["ruta"]))
        self.actualizar_mapa(home.ids.mapa, lugar)

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
            bus = MapMarker(lat=(lat + tlat) / 2, lon=(lon + tlon) / 2,
                            source="atlas://data/images/defaulttheme/checkbox_on")
            mapa.add_marker(bus)
            self._marcadores.append(bus)

        mapa.zoom = 11
        mapa.center_on(lat, lon)

    # --------------------------------------------------------
    # Detalle de una línea (al tocar cualquier tarjeta)
    # --------------------------------------------------------
    def mostrar_detalle(self, ruta):
        d = RUTAS[ruta]
        es_fav = ruta in self.favoritas
        self.dialogo = MDDialog(
            MDDialogHeadlineText(text=ruta),
            MDDialogSupportingText(
                text=(
                    f'Parada: {d["parada"]}\n'
                    f'Próximo bus: {d["minutos"]}\n'
                    f'Frecuencia: {d["frecuencia"]}\n'
                    f'Duración del viaje: {d["duracion"]}\n'
                    f'Tarifa: {d["tarifa"]}'
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
        # TODO: en Android, obtener GPS con plyer y enviarlo a un servidor
        self.compartiendo = True
        p = self.root.ids.sm.get_screen("compartir")
        p.ids.compartir_btn_text.text = "DETENER VIAJE"
        p.ids.estado_label.text = f"Compartiendo tu ubicación en {self.linea_actual}"

    def detener_compartir(self):
        self.compartiendo = False
        self.viajes += 1
        self.root.ids.sm.get_screen("perfil").ids.viajes_num.text = str(self.viajes)
        p = self.root.ids.sm.get_screen("compartir")
        p.ids.compartir_btn_text.text = "INICIAR VIAJE"
        p.ids.estado_label.text = "Tu ubicación no se está compartiendo."


if __name__ == "__main__":
    InterurbanoApp().run()