"""Google Maps experimental: pruebas de rutas y servidor local sin API real.

Este módulo no necesita Kivy, navegador ni facturación en Google Cloud.
"""
import json
import os
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch

from datos_rutas import RUTAS
from servicios import google_maps_preview as gmaps


CLAVE_FICTICIA = "AIza" + "A" * 35


class GoogleMapsPreviewTests(unittest.TestCase):
    def test_catalogo_tiene_rutas_y_no_publica_gps_usuario(self):
        datos = gmaps.construir_datos_demo()
        self.assertTrue(datos["demo"])
        self.assertEqual(len(datos["rutas"]), len(RUTAS))
        self.assertTrue(all("bus_demo" in r and "inicio" in r and "fin" in r
                            for r in datos["rutas"]))
        self.assertNotIn("usuario_actual", json.dumps(datos))
        self.assertNotIn("gps_usuario", json.dumps(datos))

    def test_validacion_de_clave(self):
        for clave in ("", "abc", "123<script>", "abc def", None):
            with self.subTest(clave=clave), self.assertRaises(gmaps.ErrorGoogleMaps):
                gmaps.validar_clave(clave)
        self.assertEqual(gmaps.validar_clave(CLAVE_FICTICIA), CLAVE_FICTICIA)

    def test_no_inicia_sin_clave_configurada(self):
        with patch.dict(os.environ, {gmaps.CLAVE_ENV: ""}):
            with self.assertRaises(gmaps.ErrorGoogleMaps):
                gmaps.abrir_en_navegador(abrir=lambda url: True)

    def test_servidor_solo_entrega_html_y_rutas_demo(self):
        servidor = gmaps.crear_servidor(CLAVE_FICTICIA, puerto=0)
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        base = "http://127.0.0.1:" + str(servidor.server_address[1])
        try:
            with urlopen(base + "/", timeout=3) as respuesta:
                pagina = respuesta.read().decode("utf-8")
                self.assertEqual(respuesta.status, 200)
                self.assertIn(CLAVE_FICTICIA, pagina)
                self.assertIn("Google Maps", pagina)
                self.assertIn("no-store", respuesta.headers["Cache-Control"])
            with urlopen(base + "/api/rutas", timeout=3) as respuesta:
                datos = json.load(respuesta)
                self.assertEqual(respuesta.status, 200)
                self.assertTrue(datos["demo"])
                self.assertEqual(len(datos["rutas"]), len(RUTAS))
            with self.assertRaises(HTTPError) as error:
                urlopen(base + "/no-existe", timeout=3)
            self.assertEqual(error.exception.code, 404)
        finally:
            servidor.shutdown()
            servidor.server_close()
            hilo.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
