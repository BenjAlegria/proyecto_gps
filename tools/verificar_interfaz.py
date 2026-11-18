"""Capturas reales reproducibles de las ocho pantallas; sin red ni escrituras JSON.

Desde proyecto_gps: python tools/verificar_interfaz.py
En Windows puede usarse KIVY_GL_BACKEND=angle_sdl2 para capturar con ANGLE.
"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.environ.setdefault("KIVY_NO_FILELOG", "1")

from kivy.base import ExceptionManager
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import NoTransition
from kivy.uix.scrollview import ScrollView
from kivy_garden.mapview.downloader import Downloader
from main import InterurbanoApp
from config import CONFIG_REMOTA_DEFECTO


def main():
    salida = BASE / "docs" / "verificacion-ui"
    salida.mkdir(parents=True, exist_ok=True)
    app = InterurbanoApp()
    # Las excepciones deben abortar la validación, nunca quedar silenciadas.
    handlers = ExceptionManager.handlers[:]
    ExceptionManager.handlers.clear()
    pantallas = ("home", "recorridos", "compartir", "avisos", "perfil", "ajustes", "login", "registro")
    casos = [(tema, ancho, alto, nombre, "base") for tema in ("Light", "Dark")
             for ancho, alto in ((390, 844), (360, 800)) for nombre in pantallas]
    casos += [("Light", 360, 800, nombre, "final")
              for nombre in ("recorridos", "compartir", "avisos", "perfil", "ajustes")]
    casos += [("Light", 390, 844, "login", "error"),
              ("Light", 390, 844, "registro", "error"),
              ("Light", 390, 844, "compartir", "activo"),
              ("Light", 390, 844, "avisos", "vacio")]
    archivos = []

    def preparar(dt):
        app.root.ids.sm.transition = NoTransition()
        app.usuario_actual = "demo_visual"
        app.nombre_visible = "Pasajero de prueba"
        app.favoritas = ["Temuco -> Lautaro", "Temuco -> Nueva Imperial"]
        pf = app._pantalla("perfil").ids
        pf.nombre_label.text = app.nombre_visible
        pf.usuario_label.text = "@demo_visual"
        app.avisos = [dict(ruta=ruta, tipo=tipo, minutos=minutos,
                          ts=time.time() - edad * 60, propio=False, autor="")
                      for ruta, tipo, minutos, edad in (
                          ("Temuco -> Lautaro", "asientos", 0, 3),
                          ("Temuco -> Nueva Imperial", "lleno", 0, 8),
                          ("Carahue -> Temuco", "atrasado", 10, 15),
                          ("Lautaro -> Temuco", "cambio_ruta", 0, 40))]
        app.seleccionar_origen("Temuco")
        app.refrescar_avisos()
        app._aplicar_config(app.config, "valor por defecto")
        siguiente(0)

    def siguiente(dt):
        if not casos:
            (salida / "capturas.txt").write_text("\n".join(archivos) + "\n", encoding="utf8")
            print(f"VERIFICACION VISUAL: {len(archivos)} capturas en {salida}")
            app.stop()
            return
        tema, ancho, alto, nombre, estado = casos.pop(0)
        app.theme_cls.theme_style = tema
        # En Windows con escala 125%, size se convierte a píxeles de framebuffer.
        # Compensar la densidad permite exportar los tamaños exactos solicitados.
        densidad = getattr(Window, "_density", 1)
        Window.size = (round(ancho / densidad), round(alto / densidad))
        app.cambiar_pantalla(nombre)
        for widget in app._pantalla(nombre).walk(restrict=True):
            if isinstance(widget, ScrollView):
                widget.scroll_y = 0 if estado == "final" else 1
        if estado == "error":
            if nombre == "login":
                app.hacer_login()
            else:
                app.hacer_registro()
        elif estado == "activo":
            # Solo presentación: no se inicia GPS ni se transmite nada.
            app.compartiendo = True
            ids = app._pantalla("compartir").ids
            ids.linea_text.text = "Temuco -> Lautaro"
            ids.compartir_btn_text.text = "DETENER VIAJE"
            ids.estado_label.text = "Ubicación local activa en Temuco -> Lautaro"
        elif estado == "vacio":
            app.favoritas = []
            app._pantalla("avisos").ids.filtro_favoritas.active = True
        # El primer cambio de ventana necesita que SDL y los layouts terminen
        # de procesar el tamaño inicial antes de leer el framebuffer.
        espera = 2 if not archivos else .6
        Clock.schedule_once(lambda dt: capturar(tema, ancho, alto, nombre, estado), espera)

    def capturar(tema, ancho, alto, nombre, estado):
        sufijo = "" if estado == "base" else f"-{estado}"
        archivo = f"{tema.lower()}-{ancho}x{alto}-{nombre}{sufijo}.png"
        app.root.export_to_png(str(salida / archivo))
        archivos.append(archivo)
        Clock.schedule_once(siguiente, .05)

    try:
        with patch.object(Downloader, "download_tile"), \
                patch("main.config_remota.cargar_local", return_value=(dict(CONFIG_REMOTA_DEFECTO), "valor por defecto")), \
                patch("main.almacenamiento.cargar_avisos", return_value=[]), \
                patch("main.config_remota.descargar_en_hilo"), \
                patch.object(app, "_guardar_perfil"), patch.object(app, "_guardar_avisos"):
            Clock.schedule_once(preparar, .4)
            app.run()
        crear_resumenes(salida, pantallas)
    finally:
        ExceptionManager.handlers[:] = handlers


def crear_resumenes(salida, pantallas):
    from PIL import Image, ImageDraw
    for tema in ("light", "dark"):
        for ancho, alto in ((390, 844), (360, 800)):
            hoja = Image.new("RGB", (1000, 1120), "#C6CED9")
            texto = ImageDraw.Draw(hoja)
            for indice, nombre in enumerate(pantallas):
                with Image.open(salida / f"{tema}-{ancho}x{alto}-{nombre}.png") as imagen:
                    imagen = imagen.convert("RGB")
                    imagen.thumbnail((240, 520))
                    x, y = indice % 4 * 250, indice // 4 * 560
                    hoja.paste(imagen, (x, y + 24))
                    texto.text((x + 6, y + 4), nombre, fill="black")
            archivo = f"resumen-{tema}.png" if ancho == 390 else f"resumen-{tema}-{ancho}.png"
            hoja.save(salida / archivo)


if __name__ == "__main__":
    main()
