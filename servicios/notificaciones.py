"""Notificaciones.

`notificar` hace dos cosas: muestra un aviso dentro de la app (el
snackbar lo dibuja main.py y llega como `mostrar_en_app`) y, si el
dispositivo lo permite, una notificación del sistema con plyer
(Android/iOS/Windows). En un equipo sin proveedor solo se ve la de la app.
"""

try:
    from plyer import notification as _plyer_notification
except Exception:  # sin proveedor de notificaciones (PC sin soporte)
    _plyer_notification = None

NOMBRE_APP = "EnRuta Ya!"


def notificar(titulo, mensaje, mostrar_en_app=None):
    """Dispara la notificación. Devuelve True si salió también la del sistema."""
    if mostrar_en_app is not None:
        mostrar_en_app(f"{titulo}: {mensaje}")
    if _plyer_notification is None:
        return False
    try:
        _plyer_notification.notify(
            title=titulo, message=mensaje, app_name=NOMBRE_APP, timeout=8)
        return True
    except Exception as e:
        print("No se pudo mostrar la notificación del sistema:", e)
        return False
