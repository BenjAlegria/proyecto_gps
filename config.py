"""Configuración central del proyecto: rutas de archivos y valores por defecto.
"""

import os

API_URL = "https://teclab.uct.cl/~fcaullan2022/enruta/api/index.php"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# En Android los archivos de la app empaquetada no son un lugar fiable
# para escribir datos. Usamos la carpeta privada persistente de la aplicación.
# En Windows/Linux mantenemos la ruta habitual de desarrollo.
def _directorio_datos():
    try:
        from kivy.utils import platform
        if platform == "android":
            from android.storage import app_storage_path
            return os.path.join(app_storage_path(), "enrutaya")
    except (ImportError, OSError):
        pass
    return os.path.join(BASE_DIR, "data")


DATA_DIR = _directorio_datos()
ARCHIVO_USUARIOS = os.path.join(DATA_DIR, "usuarios.json")
ARCHIVO_PERFILES = os.path.join(DATA_DIR, "perfiles.json")
ARCHIVO_AVISOS = os.path.join(DATA_DIR, "avisos.json")
ARCHIVO_CACHE_REMOTA = os.path.join(DATA_DIR, "config_remota_cache.json")

LOG_ERRORES = os.path.join(DATA_DIR, "crash_log.txt")
ICONO_BUS = os.path.join(BASE_DIR, "bus_marker.png")

# ------------------------------------------------------------
# Configuración remota (remote config)
# ------------------------------------------------------------
# Fuente remota: el archivo remote_config.json de este mismo repositorio,
# servido por GitHub. Si se edita y se hace push, la app muestra el nuevo
# valor la próxima vez que se abre (o al tocar "Actualizar" en Ajustes).
URL_CONFIG_REMOTA = (
    ""
)
TIMEOUT_CONFIG_REMOTA_S = 5

# Valores que se usan cuando no hay internet ni caché.
CONFIG_REMOTA_DEFECTO = {
    "mensaje_inicio": "Bienvenido a EnRuta Ya!",   # banner de la pantalla Inicio
    "antispam_segundos": 120,                       # mismo aviso, misma línea
    "vigencia_aviso_min": 30,                       # cuánto dura un aviso como "estado actual"
}

# ------------------------------------------------------------
# Reglas de la app (no remotas)
# ------------------------------------------------------------
HISTORIAL_S = 2 * 60 * 60   # la pantalla Avisos muestra hasta las últimas 2 h
OPCIONES_ATRASO = (5, 10, 15, 20)

