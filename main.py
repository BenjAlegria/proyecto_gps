"""
Interurbano Sur - App móvil para consultar horarios y llegada
de buses interurbanos mediante un mapa.

Evaluación: Kivy + KivyMD 2.0, ScreenManager, KV Language.
Separación estricta: la interfaz vive en root.kv, la lógica aquí.
"""

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import Screen

from kivymd.app import MDApp


# ------------------------------------------------------------
# Widget propio: espacio reservado para el mapa
# (se reemplazará por un mapa real, ej. plyer/mapview o una API de mapas)
# ------------------------------------------------------------
class MapPlaceholder(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(0.08, 0.12, 0.18, 1)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size


# ------------------------------------------------------------
# Pantallas (la interfaz de cada una vive en root.kv)
# ------------------------------------------------------------
class HomeScreen(Screen):
    pass


class RecorridosScreen(Screen):
    pass


class PerfilScreen(Screen):
    pass


# ------------------------------------------------------------
# Aplicación
# ------------------------------------------------------------
class InterurbanoApp(MDApp):

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        self.title = "Interurbano Sur"
        return Builder.load_file("root.kv")

    def cambiar_pantalla(self, nombre):
        """Navega entre pantallas usando el ScreenManager (id: sm en root.kv)."""
        self.root.ids.sm.current = nombre

    def buscar_destino(self, campo_texto):
        """Validación básica de entrada del buscador de la Home."""
        texto = campo_texto.text.strip()
        if texto == "":
            campo_texto.error = True
            return
        campo_texto.error = False
        # TODO: conectar con la búsqueda real de recorridos/paradas
        print(f"Buscando destino/línea: {texto}")


if __name__ == "__main__":
    InterurbanoApp().run()
