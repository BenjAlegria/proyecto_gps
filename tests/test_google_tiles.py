"""Pruebas sin red ni clave real para el proveedor Map Tiles de Google.

El mapa Kivy completo debe validarse además desde Windows.
"""
import os
import unittest
from unittest.mock import Mock, patch

from servicios import google_tiles_api as tiles


class GoogleTilesClientTests(unittest.TestCase):
    def setUp(self):
        self.transport = Mock()
        self.respuesta = Mock()
        self.respuesta.status_code = 200
        self.respuesta.json.return_value = {
            "session": "sesion-de-prueba",
            "expiry": "9999999999",
            "imageFormat": "png",
        }
        self.transport.post.return_value = self.respuesta
        self.cliente = tiles.ClienteMapTiles(
            "clave-de-prueba", transporte=self.transport
        )

    def test_falta_clave_no_intenta_api(self):
        with patch.dict(os.environ, {tiles.VARIABLE_CLAVE: ""}):
            with self.assertRaises(tiles.ErrorMapTiles):
                tiles.clave_configurada()

    def test_sesion_realiza_post_y_no_imprime_clave(self):
        self.cliente.iniciar()
        self.assertEqual(self.cliente.session, "sesion-de-prueba")
        self.transport.post.assert_called_once()
        args, kwargs = self.transport.post.call_args
        self.assertTrue(args[0].startswith("https://tile.googleapis.com"))
        self.assertEqual(kwargs["params"]["key"], "clave-de-prueba")
        self.assertEqual(kwargs["json"]["mapType"], "roadmap")

    def test_mosaico_usa_coordenadas_google_y_no_guarda_archivos(self):
        self.cliente.iniciar()
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.content = b"\x89PNG\r\n\x1a\n" + b"contenido"
        self.transport.get.return_value = respuesta
        self.assertEqual(self.cliente.mosaico(10, 120, 350), respuesta.content)
        url = self.transport.get.call_args.args[0]
        self.assertIn("/v1/2dtiles/10/120/350", url)
        self.assertEqual(
            self.transport.get.call_args.kwargs["params"]["session"],
            "sesion-de-prueba",
        )

    def test_limite_por_activacion_reduce_riesgo_de_consumo(self):
        self.cliente.iniciar()
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.content = b"png"
        self.transport.get.return_value = respuesta
        with patch.object(tiles, "MAX_MOSAICOS_POR_ACTIVACION", 1):
            self.assertEqual(self.cliente.mosaico(10, 120, 350), b"png")
            with self.assertRaises(tiles.ErrorMapTiles):
                self.cliente.mosaico(10, 120, 351)
        self.assertEqual(self.transport.get.call_count, 1)

    def test_creditos_consulta_viewport_y_retorna_copyright(self):
        self.cliente.iniciar()
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.json.return_value = {"copyright": "Mapa © Google y proveedores"}
        self.transport.get.return_value = respuesta
        self.assertEqual(
            self.cliente.atribucion(10, -38.0, -39.0, -72.0, -73.0),
            "Mapa © Google y proveedores",
        )
        self.assertIn("/tile/v1/viewport", self.transport.get.call_args.args[0])

    def test_respuesta_sin_creditos_es_error(self):
        self.cliente.iniciar()
        respuesta = Mock()
        respuesta.status_code = 200
        respuesta.json.return_value = {}
        self.transport.get.return_value = respuesta
        with self.assertRaises(tiles.ErrorMapTiles):
            self.cliente.atribucion(10, -38.0, -39.0, -72.0, -73.0)

    def test_error_http_no_filtra_clave(self):
        self.respuesta.status_code = 403
        with self.assertRaises(tiles.ErrorMapTiles) as error:
            self.cliente.iniciar()
        self.assertNotIn("clave-de-prueba", str(error.exception))

    def test_sin_sesion_no_permite_pedir_tiles(self):
        with self.assertRaises(tiles.ErrorMapTiles):
            self.cliente.mosaico(10, 120, 350)

    def test_tipo_no_admitido(self):
        with self.assertRaises(ValueError):
            tiles.ClienteMapTiles("clave", tipo="streetview", transporte=self.transport)


if __name__ == "__main__":
    unittest.main()
