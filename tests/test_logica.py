"""Pruebas rápidas de lógica pura (sin abrir Kivy ni hacer solicitudes reales)."""
import math
import time
import unittest
from unittest.mock import Mock

from servicios import avisos_service, recorridos, ubicacion


class RecorridosTests(unittest.TestCase):
    def test_minutos_desde_texto(self):
        self.assertEqual(recorridos.minutos_desde_texto("1 h 20 min"), 80)
        self.assertEqual(recorridos.minutos_desde_texto("15 min"), 15)
        self.assertEqual(recorridos.minutos_desde_texto(None), 0)
        self.assertEqual(recorridos.minutos_desde_texto("Sin ETA"), 0)

    def test_posicion_bus_demo_usa_fraccion_limitada(self):
        origen, destino = (-38.0, -72.0), (-39.0, -73.0)
        self.assertEqual(
            recorridos.posicion_bus_demo(origen, destino, "1 h", "0 min"),
            (-38.15, -72.15),
        )
        self.assertEqual(
            recorridos.posicion_bus_demo(origen, destino, "1 h", "90 min"),
            (-38.8, -72.8),
        )


class AvisosTests(unittest.TestCase):
    def test_descarta_estructuras_ilegibles(self):
        registros = [
            None, 123, [], {"ruta": "X", "tipo": [], "ts": 15},
            {"ruta": "X", "tipo": "lleno", "ts": "ayer"},
            {"ruta": "X", "tipo": "lleno", "ts": float("nan")},
            {"ruta": "X", "tipo": "lleno", "ts": True},
            {"ruta": "X", "tipo": "lleno", "ts": 17, "minutos": -2},
            {"ruta": "Temuco -> Lautaro", "tipo": "lleno", "ts": 15},
        ]
        saneados = avisos_service.sanear_avisos(registros)
        self.assertEqual(len(saneados), 1)
        self.assertEqual(saneados[0]["ruta"], "Temuco -> Lautaro")
        self.assertEqual(avisos_service.sanear_avisos({"no": "lista"}), [])

    def test_estado_selecciona_ultimo_reporte_valido(self):
        ahora = 1_000
        registros = [
            {"ruta": "A", "tipo": "lleno", "ts": 950},
            {"ruta": "A", "tipo": "asientos", "ts": 990},
            {"ruta": "A", "tipo": "atrasado", "ts": 970, "minutos": 10},
            {"ruta": "B", "tipo": "cambio_ruta", "ts": 995},
            {"ruta": "A", "tipo": "cambio_ruta", "ts": 1001},
        ]
        ocupacion, atraso, cambio = avisos_service.estado_ruta(registros, "A", 100, ahora)
        self.assertEqual(ocupacion["tipo"], "asientos")
        self.assertEqual(atraso["minutos"], 10)
        self.assertIsNone(cambio)

    def test_historial_caduca_y_descarta_futuros(self):
        ahora = 500
        registros = [
            {"ruta": "A", "tipo": "lleno", "ts": 480},
            {"ruta": "A", "tipo": "lleno", "ts": 399},
            {"ruta": "A", "tipo": "asientos", "ts": 501},
        ]
        reciente = avisos_service.historial_reciente(registros, 100, ahora)
        self.assertEqual(len(reciente), 1)
        self.assertEqual(reciente[0]["ts"], 480)


class UbicacionTests(unittest.TestCase):
    def test_valida_coordenadas_con_limites_geograficos(self):
        self.assertTrue(ubicacion.coordenadas_validas(-38.7359, -72.5904))
        for lat, lon in [(91, 1), (1, -181), (True, 1), ("-38", -72),
                         (float("nan"), 0), (0, math.inf), (None, 0)]:
            with self.subTest(lat=lat, lon=lon):
                self.assertFalse(ubicacion.coordenadas_validas(lat, lon))

    def test_consulta_ip_usa_https_y_valida_la_respuesta(self):
        respuesta = Mock()
        respuesta.json.return_value = {
            "success": True,
            "latitude": -38.7359,
            "longitude": -72.5904,
        }
        consultar = Mock(return_value=respuesta)
        self.assertEqual(
            ubicacion.aproximacion_por_ip(consultar),
            (-38.7359, -72.5904),
        )
        consultar.assert_called_once_with("https://ipwho.is/", timeout=4)
        respuesta.raise_for_status.assert_called_once()

    def test_respuesta_ip_invalida_no_inventa_coordenadas(self):
        respuesta = Mock()
        respuesta.json.return_value = {
            "success": False, "latitude": -38.0, "longitude": -72.0,
        }
        self.assertIsNone(ubicacion.aproximacion_por_ip(Mock(return_value=respuesta)))
        respuesta.json.return_value = {
            "success": True, "latitude": 500, "longitude": 0,
        }
        self.assertIsNone(ubicacion.aproximacion_por_ip(Mock(return_value=respuesta)))


if __name__ == "__main__":
    unittest.main()
