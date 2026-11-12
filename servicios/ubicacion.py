"""Ubicación: validaciones y geolocalización IP aproximada.

La consulta IP solo debe ejecutarse por una acción explícita del usuario,
nunca al iniciar la aplicación ni mientras se comparte un viaje.
Una IP no identifica un autobús ni la posición exacta de un pasajero.
"""
import math

URL_GEO_IP = "https://ipwho.is/"


def coordenadas_validas(lat, lon):
    """Valida números finitos y límites geográficos; rechaza bool y cadenas."""
    return (
        type(lat) in (int, float)
        and type(lon) in (int, float)
        and math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    )


def aproximacion_por_ip(consultar=None):
    """Devuelve (lat, lon) o None desde un servicio HTTPS.

    Si se facilita `consultar`, debe tener la firma de `requests.get`.
    Se evita hacer solicitudes HTTP sin cifrar y no se guardan datos IP.
    """
    if consultar is None:
        import requests
        consultar = requests.get
    respuesta = consultar(URL_GEO_IP, timeout=4)
    respuesta.raise_for_status()
    datos = respuesta.json()
    if not isinstance(datos, dict) or datos.get("success") is not True:
        return None
    lat, lon = datos.get("latitude"), datos.get("longitude")
    if not coordenadas_validas(lat, lon):
        return None
    return lat, lon
