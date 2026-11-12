"""Regresiones de Inicio. Ejecutar: python -m unittest discover -s tests -v."""
import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("KIVY_NO_FILELOG", "1")

from kivy.clock import Clock
from kivy.core.window import Window
from kivy_garden.mapview.downloader import Downloader

from main import InterurbanoApp


class InicioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.descarga = patch.object(Downloader, "download_tile")
        cls.descarga.start()
        cls.app = InterurbanoApp()
        cls.app.root = cls.app.build()
        Window.add_widget(cls.app.root)
        cls.app.cambiar_pantalla("home")
        cls.home = cls.app._pantalla("home")

    @classmethod
    def tearDownClass(cls):
        Window.remove_widget(cls.app.root)
        cls.descarga.stop()

    def setUp(self):
        self.app.avisos = []
        self.app.seleccionar_origen("Temuco")

    def test_filtro_y_cambio_localidad(self):
        self.assertEqual(len(self.home.ids.lineas_box.children), 2)
        self.app.seleccionar_recorrido_home("Temuco -> Lautaro")
        self.assertEqual(len(self.home.ids.lineas_box.children), 1)
        self.assertEqual(len(self.app._marcadores), 2)  # parada y bus
        self.app.seleccionar_origen("Carahue")
        self.assertEqual(self.app.recorrido_home, "")
        self.assertEqual(len(self.home.ids.lineas_box.children), 2)

    def test_estados_sin_reporte_y_desactualizado(self):
        self.assertTrue(all(c.aviso == "Sin reportes recientes"
                            for c in self.home.ids.lineas_box.children))
        self.app.avisos = [dict(ruta="Temuco -> Lautaro", tipo="lleno",
                               minutos=0, ts=time.time() - self.app.vigencia_s - 1)]
        self.app._llenar_lineas_home()
        self.assertTrue(any(c.aviso == "Reporte desactualizado"
                            for c in self.home.ids.lineas_box.children))
        self.app.avisos[0]["ts"] = time.time()
        self.app._llenar_lineas_home()
        self.assertTrue(any(c.aviso == "Bus lleno"
                            for c in self.home.ids.lineas_box.children))

    def test_fallo_ip_no_inventa_ubicacion(self):
        with patch("requests.get", side_effect=OSError("sin red")), \
                patch.object(self.app, "actualizar_mi_ubicacion") as actualizar:
            self.app._localizar_por_ip()
            Clock.tick()
            actualizar.assert_not_called()
        self.assertEqual(self.home.ids.ubicacion_estado.text, "Ubicación no disponible")

    def test_ip_tardia_no_actualiza_mapa_tras_detener_gps(self):
        # Simula que la consulta terminó después de cerrar una sesión.
        self.app.gps_activo = False
        solicitud = self.app._solicitud_ubicacion
        with patch("servicios.ubicacion.aproximacion_por_ip",
                   return_value=(-38.7359, -72.5904)), \
                patch.object(self.app, "actualizar_mi_ubicacion") as actualizar:
            self.app._localizar_por_ip(solicitud)
            self.app.detener_gps()
            Clock.tick()
            actualizar.assert_not_called()

    def test_gps_tardio_no_reubica_despues_de_revocar(self):
        self.app.gps_activo = False
        solicitud = self.app._solicitud_ubicacion
        with patch.object(self.app, "actualizar_mi_ubicacion") as actualizar:
            self.app.on_gps_location(
                _solicitud=solicitud, lat=-38.7359, lon=-72.5904
            )
            self.app.detener_gps()
            Clock.tick()
            actualizar.assert_not_called()

    def test_gps_invalido_no_actualiza_mapa(self):
        with patch.object(self.app, "actualizar_mi_ubicacion") as actualizar:
            self.app.on_gps_location(lat=float("nan"), lon=-72.5904)
            Clock.tick()
            actualizar.assert_not_called()

    def test_mapa_visible_y_panel_adaptable(self):
        for size in ((390, 844), (320, 568), (800, 600)):
            Window.size = size
            for _ in range(16):
                Clock.tick()
            self.assertGreater(self.home.ids.mapa.height, 100)
            self.assertLessEqual(self.home.ids.panel_buses.height,
                                 self.home.ids.mapa.height)
        self.app.panel_expandido = False
        self.app.ajustar_panel_home()
        from kivy.metrics import dp
        self.assertEqual(self.home.ids.panel_buses.height, dp(48))

    def test_navegacion_visible_y_funcional(self):
        from kivy.base import EventLoop
        from kivy.input.motionevent import MotionEvent
        from kivy.uix.label import Label

        class Toque(MotionEvent):
            def depack(self, args):
                self.sx, self.sy = args
                super().depack(args)

        nav = self.app.root.ids.nav_bar
        sm = self.app.root.ids.sm
        destinos = ("home", "recorridos", "compartir", "avisos", "ajustes")
        botones = list(reversed(nav.children))
        self.assertEqual([b.etiqueta for b in botones],
                         ["Inicio", "Recorridos", "Compartir", "Avisos", "Ajustes"])
        self.assertIs(nav.parent, sm.parent)
        for size in ((320, 480), (320, 568), (390, 844), (844, 390)):
            Window.size = size
            for tema in ("Light", "Dark"):
                self.app.theme_cls.theme_style = tema
                self.app.cambiar_pantalla("home")
                for _ in range(25):
                    Clock.tick()
                self.assertTrue(all(b.inicio for b in botones))
                self.assertEqual(nav.y, 0)
                self.assertAlmostEqual(sm.y, nav.top)
                self.assertEqual(nav.opacity, 1)
                for boton, destino in zip(botones, destinos):
                    self.assertGreater(boton.width, 0)
                    self.assertGreaterEqual(boton.x, nav.x)
                    self.assertLessEqual(boton.right, nav.right)
                    self.assertGreaterEqual(boton.y, nav.y)
                    self.assertLessEqual(boton.top, nav.top)
                    for label in boton.walk(restrict=True):
                        if isinstance(label, Label):
                            self.assertGreater(label.texture_size[0], 0)
                            self.assertNotEqual(list(label.color), list(nav.md_bg_color))
                            if hasattr(label, "icon_color"):
                                self.assertEqual(list(label.icon_color), list(boton.color_nav))
                    toque = Toque("test", destino,
                                  (boton.center_x / (Window.width - 1),
                                   boton.center_y / (Window.height - 1)),
                                  is_touch=True, type_id="touch")
                    toque.profile = ["pos"]
                    EventLoop.post_dispatch_input("begin", toque)
                    EventLoop.post_dispatch_input("end", toque)
                    self.assertEqual(sm.current, destino)
                    self.assertTrue(boton.activo)
                self.app.cambiar_pantalla("home")

    def test_mapa_alineado_sin_huecos_ni_solapamientos(self):
        from kivy.metrics import dp
        for size in ((320, 480), (390, 844), (844, 390)):
            Window.size = size
            for _ in range(20):
                Clock.tick()
            for expandido in (False, True):
                self.app.panel_expandido = expandido
                self.app.ajustar_panel_home()
                for _ in range(5):
                    Clock.tick()
                mapa = self.home.ids.mapa
                contenedor = self.home.ids.map_container
                panel = self.home.ids.panel_buses
                self.assertEqual(mapa.pos, [0, 0])  # coordenadas relativas
                self.assertEqual(mapa.size, contenedor.size)
                self.assertAlmostEqual(contenedor.y, panel.top)
                self.assertAlmostEqual(panel.y, 0)
                self.assertAlmostEqual(contenedor.top, self.home.ids.banner.y)
                self.assertGreater(mapa.height, dp(100))
                self.assertLessEqual(panel.height, mapa.height)
                nav = self.app.root.ids.nav_bar
                self.assertGreaterEqual(mapa.to_window(0, 0)[1], nav.top)

    def test_tarjetas_no_inventan_ocupacion_ni_actualizacion(self):
        tarjetas = self.home.ids.lineas_box.children
        self.assertTrue(all(c.ocupacion == "Sin dato" for c in tarjetas))
        self.assertTrue(all(c.actualizacion == "Sin actualización real" for c in tarjetas))
        self.app.avisos = [dict(ruta="Temuco -> Lautaro", tipo="asientos",
                               minutos=0, ts=time.time() - 180)]
        self.app._llenar_lineas_home()
        tarjeta = next(c for c in self.home.ids.lineas_box.children
                       if c.ruta == "Temuco -> Lautaro")
        self.assertEqual(tarjeta.ocupacion, "Hay asientos")
        self.assertIn("Reporte local", tarjeta.actualizacion)
        self.assertIn("3 min", tarjeta.actualizacion)

    def test_chips_y_controles_no_se_superponen(self):
        for size in ((320, 480), (390, 844), (844, 390)):
            Window.size = size
            for _ in range(20):
                Clock.tick()
            demo = self.home.ids.demo_chip
            ubicacion = self.home.ids.location_chip
            localizar = self.home.ids.localizar_btn
            self.assertLess(ubicacion.top, demo.y)
            self.assertLess(localizar.right, self.home.ids.map_container.width)
            self.assertGreaterEqual(localizar.y, 0)
            self.assertGreaterEqual(self.home.ids.origen_btn.height, 48)

    def test_ocho_pantallas_temas_y_zona_segura(self):
        from kivy.uix.screenmanager import NoTransition
        self.app.root.ids.sm.transition = NoTransition()
        for tema in ("Light", "Dark", "Light"):
            self.app.theme_cls.theme_style = tema
            for size in ((390, 844), (360, 800)):
                Window.size = size
                for nombre in ("home", "recorridos", "compartir", "avisos",
                               "perfil", "ajustes", "login", "registro"):
                    self.app.cambiar_pantalla(nombre)
                    for _ in range(4):
                        Clock.tick()
                    pantalla = self.app._pantalla(nombre)
                    self.assertEqual(len(pantalla.children), 1)
                    self.assertGreater(pantalla.width, 0)
                    nav = self.app.root.ids.nav_bar
                    self.assertEqual(nav.opacity, 0 if nombre in ("login", "registro") else 1)
                    self.assertEqual(list(nav.md_bg_color), list(self.app.ui.fondo))
                    for icono in (w for w in pantalla.walk(restrict=True)
                                  if hasattr(w, "icon_color") and hasattr(w, "texture")):
                        self.assertGreater(icono.color[3], 0)
            self.assertNotEqual(list(self.app.ui.texto), list(self.app.ui.fondo))
        self.assertEqual(list(self.app.ui.fondo), [1, 1, 1, 1])
        self.app.safe_bottom = 24
        self.app.cambiar_pantalla("home")
        for _ in range(5):
            Clock.tick()
        nav = self.app.root.ids.nav_bar
        self.assertTrue(all(b.y >= 24 for b in nav.children))
        self.app.safe_bottom = 0

    def test_flujo_local_completo_con_persistencia_aislada(self):
        import tempfile
        from pathlib import Path
        from contextlib import ExitStack
        from unittest.mock import Mock
        from servicios import almacenamiento
        with tempfile.TemporaryDirectory() as carpeta, ExitStack() as ctx:
            for modulo, atributo, archivo in (
                    ("servicios.autenticacion", "ARCHIVO_USUARIOS", "usuarios.json"),
                    ("servicios.almacenamiento", "ARCHIVO_PERFILES", "perfiles.json"),
                    ("servicios.almacenamiento", "ARCHIVO_AVISOS", "avisos.json")):
                ctx.enter_context(patch(f"{modulo}.{atributo}", str(Path(carpeta) / archivo)))
            ctx.enter_context(patch.object(self.app, "_snack"))
            ctx.enter_context(patch.object(self.app, "notificar"))
            ctx.enter_context(patch.object(self.app, "localizarme"))
            ctx.enter_context(patch.object(self.app, "detener_gps"))
            self.app.compartiendo = False
            registro = self.app._pantalla("registro").ids
            registro.usuario.text = "!"
            registro.clave.text = "abc123"
            registro.repetir.text = "abc123"
            self.app.hacer_registro()
            self.assertTrue(registro.err_usuario.text)
            registro.usuario.text = "pasajero_test"
            self.app.hacer_registro()
            self.assertEqual(self.app.usuario_actual, "pasajero_test")
            self.assertEqual(self.app.root.ids.sm.current, "home")
            self.app.dialogo = Mock()
            self.app.alternar_favorita("Temuco -> Lautaro")
            self.assertIn("Temuco -> Lautaro", self.app.favoritas)
            campo = self.app._pantalla("perfil").ids.nombre_field
            campo.text = "Nombre de prueba"
            self.app.guardar_nombre(campo)
            self.assertEqual(almacenamiento.cargar_perfil("pasajero_test")["nombre"], "Nombre de prueba")
            self.app.seleccionar_linea("Temuco -> Lautaro")
            self.app.consentimiento = False
            with patch.object(self.app, "mostrar_dialogo_consentimiento") as dialogo:
                self.app.alternar_compartir()
                dialogo.assert_called_once()
            self.app.consentimiento = True
            self.app.alternar_compartir()
            self.assertTrue(self.app.compartiendo)
            self.app.alternar_compartir()
            self.assertFalse(self.app.compartiendo)
            self.app._ultimo_aviso = {}
            self.app.enviar_aviso("asientos")
            self.assertTrue(almacenamiento.cargar_avisos())
            self.app.alternar_solo_favoritas(True)
            self.assertTrue(self.app._pantalla("avisos").ids.avisos_box.children)
            self.app.alternar_solo_favoritas(False)
            self.app.cerrar_sesion()
            login = self.app._pantalla("login").ids
            login.usuario.text = "pasajero_test"
            login.clave.text = "abc123"
            self.app.hacer_login()
            self.assertEqual(self.app.nombre_visible, "Nombre de prueba")
            self.app.cerrar_sesion()
            self.assertEqual(self.app.root.ids.sm.current, "login")
            self.app.cambiar_pantalla("home")

    def test_estado_conserva_contraste_al_cambiar_tema(self):
        self.app.avisos = [dict(ruta="Temuco -> Lautaro", tipo="asientos",
                               minutos=0, ts=time.time())]
        tarjeta = self.app._tarjeta("Temuco -> Lautaro")
        for tema in ("Light", "Dark", "Light"):
            self.app.theme_cls.theme_style = tema
            for _ in range(5):
                Clock.tick()
            etiqueta = next(w for w in tarjeta.walk(restrict=True)
                            if getattr(w, "text", None) == "Hay asientos")
            self.assertEqual(list(etiqueta.color), list(self.app.ui.exito))


if __name__ == "__main__":
    unittest.main()
