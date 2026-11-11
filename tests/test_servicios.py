"""Pruebas de servicios sin abrir la interfaz Kivy.

Ejecutar desde la raíz:
    python -m unittest discover -s tests -p "test_servicios.py" -v

Estas pruebas no validan UI ni ubicación real entre dispositivos.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from servicios import almacenamiento, autenticacion, config_remota
from servicios.autenticacion import ErrorAutenticacion


class AutenticacionLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        ruta = str(Path(self.temp.name) / "usuarios.json")
        p = patch.object(autenticacion, "ARCHIVO_USUARIOS", ruta)
        p.start()
        self.addCleanup(p.stop)
        self.ruta = Path(ruta)

    def test_registro_login_y_hash_sin_clave_en_texto_plano(self):
        usuario = autenticacion.registrar("  USUARIO_1  ", "abc12345", "abc12345")
        self.assertEqual(usuario, "usuario_1")
        self.assertEqual(autenticacion.iniciar_sesion("USUARIO_1", "abc12345"), usuario)
        contenido = self.ruta.read_text(encoding="utf-8")
        self.assertNotIn("abc12345", contenido)
        datos = json.loads(contenido)
        self.assertEqual(len(datos["usuario_1"]["sal"]), 32)
        self.assertEqual(len(datos["usuario_1"]["hash"]), 64)

    def test_rechaza_credenciales_incorrectas_y_duplicados(self):
        autenticacion.registrar("pasajero", "abc12345", "abc12345")
        with self.assertRaises(ErrorAutenticacion):
            autenticacion.iniciar_sesion("pasajero", "no_es_la_clave")
        with self.assertRaises(ErrorAutenticacion):
            autenticacion.registrar("PASAJERO", "abc12345", "abc12345")

    def test_validacion_de_campos(self):
        casos = [
            ("!", "abc12345", "abc12345"),
            ("ab", "abc12345", "abc12345"),
            ("valido", "123456", "123456"),
            ("valido", "abcdef", "abcdef"),
            ("valido", "abc12345", "distinta"),
        ]
        for nombre, clave, repetir in casos:
            with self.subTest(nombre=nombre, clave=clave):
                with self.assertRaises(ErrorAutenticacion):
                    autenticacion.registrar(nombre, clave, repetir)


class AlmacenamientoLocalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        carpeta = Path(self.temp.name)
        for atributo, archivo in (("ARCHIVO_PERFILES", "perfiles.json"),
                                  ("ARCHIVO_AVISOS", "avisos.json")):
            p = patch.object(almacenamiento, atributo, str(carpeta / archivo))
            p.start()
            self.addCleanup(p.stop)
        self.carpeta = carpeta

    def test_lectura_escritura_y_aislamiento_de_perfiles(self):
        self.assertEqual(almacenamiento.cargar_perfil("ana")["favoritas"], [])
        almacenamiento.guardar_perfil("ana", {"nombre": "Ana", "favoritas": ["Lautaro"]})
        almacenamiento.guardar_perfil("ben", {"nombre": "Ben", "favoritas": []})
        self.assertEqual(almacenamiento.cargar_perfil("ana")["favoritas"], ["Lautaro"])
        self.assertEqual(almacenamiento.cargar_perfil("ben")["nombre"], "Ben")
        self.assertFalse((self.carpeta / "perfiles.json.tmp").exists())

    def test_avisos_persisten_en_formato_json(self):
        avisos = [{"ruta": "Temuco -> Lautaro", "tipo": "lleno", "ts": 10}]
        almacenamiento.guardar_avisos(avisos)
        self.assertEqual(almacenamiento.cargar_avisos(), avisos)

    def test_json_corrupto_se_aparta_y_se_retorna_default(self):
        ruta = self.carpeta / "corrupto.json"
        ruta.write_text("{invalido", encoding="utf-8")
        self.assertEqual(almacenamiento.leer_json(str(ruta), {}), {})
        self.assertTrue((self.carpeta / "corrupto.json.corrupto").exists())


class ConfiguracionRemotaTests(unittest.TestCase):
    def test_sanear_descarta_claves_desconocidas_y_numeros_invalidos(self):
        datos = {
            "mensaje_inicio": "Hola",
            "antispam_segundos": -2,
            "vigencia_aviso_min": 15,
            "clave_no_permitida": "ignorar",
        }
        self.assertEqual(config_remota._sanear(datos),
                         {"mensaje_inicio": "Hola", "vigencia_aviso_min": 15})

    def test_sanear_no_acepta_booleanos_como_enteros(self):
        self.assertNotIn("antispam_segundos",
                         config_remota._sanear({"antispam_segundos": True}))

    def test_config_local_conserva_defaults_y_cache_valida(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = str(Path(carpeta) / "config_cache.json")
            with patch.object(config_remota, "ARCHIVO_CACHE_REMOTA", ruta):
                datos, fuente = config_remota.cargar_local()
                self.assertEqual(fuente, config_remota.FUENTE_DEFECTO)
                self.assertIn("mensaje_inicio", datos)
                almacenamiento.guardar_json(ruta, {"vigencia_aviso_min": 45,
                                                   "clave_no_permitida": 1})
                datos, fuente = config_remota.cargar_local()
                self.assertEqual(fuente, config_remota.FUENTE_CACHE)
                self.assertEqual(datos["vigencia_aviso_min"], 45)
                self.assertNotIn("clave_no_permitida", datos)


if __name__ == "__main__":
    unittest.main()
