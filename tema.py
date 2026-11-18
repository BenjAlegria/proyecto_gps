"""Tokens visuales reactivos. No contiene estado de negocio ni persistencia."""
from kivy.event import EventDispatcher
from kivy.properties import ColorProperty, NumericProperty
from kivy.utils import get_color_from_hex


class PaletaVisual(EventDispatcher):
    fondo = ColorProperty("#FFFFFF")
    tarjeta = ColorProperty("#F6F8FC")
    texto = ColorProperty("#15263D")
    secundario = ColorProperty("#697A90")
    borde = ColorProperty("#E6ECF4")
    azul = ColorProperty("#2867E8")
    marino = ColorProperty("#122A48")
    suave = ColorProperty("#EDF3FF")
    verde = ColorProperty("#13996F")
    rojo = ColorProperty("#D94A4A")
    naranja = ColorProperty("#F3A23E")
    # Textos de estado más oscuros para que sean legibles sobre blanco.
    aviso = ColorProperty("#936016")
    exito = ColorProperty("#087B57")
    margen = NumericProperty(20)
    radio = NumericProperty(16)

    def aplicar(self, oscuro):
        colores = {
            "fondo": "#0F1928" if oscuro else "#FFFFFF",
            "tarjeta": "#18263A" if oscuro else "#F6F8FC",
            "texto": "#EDF3FC" if oscuro else "#15263D",
            "secundario": "#A9B8CC" if oscuro else "#697A90",
            "borde": "#2C3D54" if oscuro else "#E6ECF4",
            "azul": "#87AEFF" if oscuro else "#2867E8",
            "suave": "#213654" if oscuro else "#EDF3FF",
            "exito": "#69D6AC" if oscuro else "#087B57",
            "aviso": "#FFC77B" if oscuro else "#936016",
            "rojo": "#FF9292" if oscuro else "#D94A4A",
        }
        # Las expresiones KV que llaman estado() observan texto como señal.
        # Publicarla al final evita colores semánticos del tema anterior.
        texto = colores.pop("texto")
        for nombre, valor in colores.items():
            setattr(self, nombre, get_color_from_hex(valor))
        self.texto = get_color_from_hex(texto)

    def estado(self, color, _dependencia=None):
        """Traduce colores heredados de datos_rutas sin alterar esos datos."""
        r, g, b = color[:3]
        if r > .7 and g < .35:
            return self.rojo
        if r > .7 and .35 <= g < .7:
            return self.aviso
        if g > .5 and r < .3:
            return self.exito
        return self.secundario
