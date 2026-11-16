"""Eventos y KPIs: pruebas sin Kivy ni datos personales."""
import json
import tempfile
import unittest
from pathlib import Path

from servicios.analitica import Registrador, leer_eventos, resumen


class AnaliticaTests(unittest.TestCase):
    def test_intento_y_consulta_generan_tiempo_y_kpis(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = [10.]
            r = Registrador(str(Path(tmp) / "eventos.jsonl"),
                            reloj=lambda: 1790000000,
                            cronometro=lambda: t[0])
            r.registrar("aplicacion_iniciada")
            intento = r.iniciar_busqueda()
            t[0] += 3.5
            self.assertTrue(r.completar_busqueda(intento))
            self.assertFalse(r.completar_busqueda(intento))
            datos = leer_eventos(r.archivo)
            k = resumen(datos)
            self.assertEqual(k["sesiones"], 1)
            self.assertEqual(k["busquedas"], 1)
            self.assertEqual(k["exito_busqueda_pct"], 100.)
            self.assertEqual(k["mediana_busqueda_s"], 3.5)
            self.assertNotIn("usuario", json.dumps(datos))
            self.assertNotIn("lat", json.dumps(datos))
            self.assertNotIn("lon", json.dumps(datos))

    def test_sin_consentimiento_no_escribe_archivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "eventos.jsonl"
            medidor = Registrador(str(ruta), activo=False)
            self.assertFalse(medidor.registrar("aplicacion_iniciada"))
            self.assertIsNone(medidor.iniciar_busqueda())
            self.assertFalse(ruta.exists())
            medidor.activo = True
            self.assertTrue(medidor.registrar("aplicacion_iniciada"))
            self.assertEqual(len(leer_eventos(str(ruta))), 1)

    def test_sin_datos_no_inventa_kpis(self):
        k = resumen([])
        self.assertIsNone(k["exito_busqueda_pct"])
        self.assertIsNone(k["mediana_busqueda_s"])
        self.assertIsNone(k["periodo_inicio_utc"])

    def test_no_se_registran_metadatos_arbitrarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Registrador(str(Path(tmp) / "eventos.jsonl"))
            with self.assertRaises(ValueError):
                r.registrar("gps_latitud")
            r.registrar("pantalla_abierta", pantalla="cualquier_otro")
            self.assertNotIn("pantalla", leer_eventos(r.archivo)[0])

    def test_archivo_corrupto_no_cierra_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "eventos.jsonl"
            p.write_text('no json\n{"evento": "login_exitoso", "sesion": "s", "ts": "fecha"}\n')
            self.assertEqual(len(leer_eventos(str(p))), 1)

    def test_exito_considera_intentos_sin_conversion(self):
        eventos = [
            {"evento":"busqueda_iniciada","intento":"a","sesion":"s","ts":"2026-11-16T10:00:00Z"},
            {"evento":"busqueda_iniciada","intento":"b","sesion":"s","ts":"2026-11-16T10:00:01Z"},
            {"evento":"recorrido_consultado","intento":"a","duracion_ms":2000,"sesion":"s","ts":"2026-11-16T10:00:02Z"},
        ]
        k = resumen(eventos)
        self.assertEqual(k["exito_busqueda_pct"], 50.)
        self.assertEqual(k["consultas_exitosas"], 1)


if __name__ == "__main__":
    unittest.main()
