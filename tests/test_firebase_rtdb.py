"""Pruebas Firebase con mocks; no requieren Internet ni cuenta real."""
import unittest
from unittest.mock import Mock
from servicios.firebase_rtdb import FirebaseReportes, FirebaseError, configuracion


class FirebaseTests(unittest.TestCase):
    def test_configuracion_opcional(self):
        self.assertIsNone(configuracion({}))
        self.assertEqual(
            configuracion({"ENRUTA_FIREBASE_API_KEY": "A"*30,
                           "ENRUTA_FIREBASE_DATABASE_URL": "https://demo-default-rtdb.firebaseio.com"}),
            ("A"*30, "https://demo-default-rtdb.firebaseio.com"),
        )
        with self.assertRaises(FirebaseError):
            configuracion({"ENRUTA_FIREBASE_API_KEY": "A"*30,
                           "ENRUTA_FIREBASE_DATABASE_URL": "http://example.com"})

    def test_publicacion_sin_usuario_o_gps(self):
        transporte = Mock()
        auth = Mock()
        auth.raise_for_status.return_value = None
        auth.json.return_value = {
            "idToken": "token-demo", "refreshToken": "refresh-demo",
            "localId": "uid123", "expiresIn": "3600"}
        pub = Mock()
        pub.raise_for_status.return_value = None
        pub.json.return_value = {"ok": True}
        transporte.post.return_value = auth
        transporte.put.return_value = pub
        cliente = FirebaseReportes("key", "https://demo.firebaseio.com",
                                   transporte=transporte, reloj=lambda: 1000)
        aviso = {"id": "a"*32, "ruta": "Temuco -> Lautaro",
                 "tipo": "lleno", "minutos": 0, "ts": 1000,
                 "autor": "nombre privado", "lat": -38.7}
        cliente.publicar(aviso)
        enviado = transporte.put.call_args.kwargs["json"]
        self.assertEqual(enviado["uid"], "uid123")
        self.assertNotIn("autor", enviado)
        self.assertNotIn("lat", enviado)
        self.assertEqual(len(enviado), 5)

    def test_recientes_descarta_reportes_viejos(self):
        t = Mock()
        auth = Mock()
        auth.raise_for_status.return_value = None
        auth.json.return_value = {
            "idToken":"token", "refreshToken":"refresh",
            "localId":"uid1", "expiresIn":"3600"}
        t.post.return_value = auth
        datos = Mock()
        datos.raise_for_status.return_value = None
        datos.json.return_value = {
            "a"*32: {"ruta":"Temuco -> Lautaro", "tipo":"lleno",
                     "minutos":0, "ts":900},
            "b"*32: {"ruta":"Temuco -> Lautaro", "tipo":"lleno",
                     "minutos":0, "ts":1}
        }
        t.get.return_value = datos
        cl = FirebaseReportes("key","https://demo.firebaseio.com",
                              transporte=t,reloj=lambda:1000)
        self.assertEqual(len(cl.recientes()),1)


if __name__ == "__main__":
    unittest.main()
