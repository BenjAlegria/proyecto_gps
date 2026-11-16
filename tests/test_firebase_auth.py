"""Pruebas Firebase Authentication por correo sin red y sin secretos."""
import unittest
from unittest.mock import Mock
from servicios.firebase_auth import (SesionFirebase, ErrorFirebaseAuth,
                                     validar_correo, validar_clave)
from servicios.firebase_rtdb import FirebaseReportes


def respuesta(data, codigo=200):
    r = Mock()
    r.status_code = codigo
    r.json.return_value = data
    return r


class FirebaseCorreoTests(unittest.TestCase):
    def test_validaciones_de_correo_y_clave(self):
        self.assertEqual(validar_correo("  DEMO@MAIL.CL  "), "demo@mail.cl")
        with self.assertRaises(ErrorFirebaseAuth):
            validar_correo("sin-arroba")
        with self.assertRaises(ErrorFirebaseAuth):
            validar_clave("abc123")
        with self.assertRaises(ErrorFirebaseAuth):
            validar_clave("abcdefghi", "otra")

    def test_registro_login_y_refresh(self):
        http = Mock()
        http.post.side_effect = [
            respuesta({"idToken":"TOKEN1", "refreshToken":"REFRESH1",
                       "localId":"uid-demo", "expiresIn":"3600"}),
            respuesta({"id_token":"TOKEN2", "refresh_token":"REFRESH2",
                       "user_id":"uid-demo", "expires_in":"3600"}),
        ]
        reloj = [100.]
        s = SesionFirebase("web-key", transporte=http, reloj=lambda:reloj[0])
        self.assertEqual(s.registrar("Demo@Mail.cl", "password123", "password123"), "uid-demo")
        self.assertEqual(s.email, "demo@mail.cl")
        self.assertEqual(s.token(), "TOKEN1")
        reloj[0] += 3600
        self.assertEqual(s.token(), "TOKEN2")
        self.assertEqual(http.post.call_count, 2)
        s.cerrar()
        with self.assertRaises(ErrorFirebaseAuth):
            s.token()

    def test_error_login_no_filtra_password(self):
        http = Mock()
        http.post.return_value = respuesta(
            {"error":{"message":"INVALID_LOGIN_CREDENTIALS"}}, 400)
        s = SesionFirebase("web-key", transporte=http)
        with self.assertRaises(ErrorFirebaseAuth) as error:
            s.login("demo@mail.cl", "SecretoSuper123")
        self.assertIn("incorrectos", str(error.exception))
        self.assertNotIn("SecretoSuper123", str(error.exception))

    def test_rtdb_usa_mismo_uid_y_token_cuenta(self):
        sesion = Mock()
        sesion.uid = "uid-demo"
        sesion.token.return_value = "ID_TOKEN"
        http = Mock()
        http.get.return_value = respuesta({})
        reportes = FirebaseReportes("web-key", "https://x.firebaseio.com",
                                    transporte=http, sesion=sesion)
        self.assertEqual(reportes.recientes(), [])
        sesion.token.assert_called_once()
        self.assertEqual(http.get.call_args.kwargs["params"]["auth"], "ID_TOKEN")
        http.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
