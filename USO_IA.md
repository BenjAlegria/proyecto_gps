# Declaración de uso de inteligencia artificial

Proyecto: **EnRuta Ya!** · Evaluación N°3, Desarrollo Móvil.

## 1. IA usada
- **Claude** (Anthropic), usado en el chat web/app como asistente de programación.
- No se usó ninguna otra herramienta de IA. 

## 2. Modelo
- Familia Claude (Anthropic). Versión exacta: 

## 3. Prompts realizados
Resumidos con fidelidad (los que explican decisiones del proyecto):

1. *Primeras versiones:* pedir la app de buses en Kivy plano y luego migrarla a **KivyMD 2.0**
   con `ScreenManager`, interfaz en `root.kv`, mapa con `kivy_garden.mapview`, panel de buses
   por localidad y diálogo de consentimiento para compartir ubicación.
2. *Avisos de pasajeros:* "bus lleno / hay asientos / atrasado / cambio de ruta", con
   antispam y notificación para rutas favoritas, a partir de los resultados de la encuesta.
3. *Corrección de errores:* el error `FBO Initialization failed` del snackbar y los íconos de
   bus demasiado grandes al alejar el mapa.
4. *Cierre del proyecto (Evaluación N°3):* se pegaron las instrucciones de la evaluación y se
   pidió "añade, corrige, termina el proyecto" para cumplir: registro y login, persistencia en
   JSON, notificaciones desde un evento, configuración remota, `README.md` y `USO_IA.md`.

## 4. Outputs
Lo que entregó la herramienta:

- Estructura modular: `servicios/autenticacion.py`, `almacenamiento.py`, `config_remota.py`,
  `notificaciones.py`, más `config.py` y `datos_rutas.py` (antes todo estaba en `main.py`).
- Pantallas de **login y registro** en `root.kv` y su lógica en `main.py`
  (`hacer_login`, `hacer_registro`, `_entrar`, `cerrar_sesion`).
- Hash de contraseñas con PBKDF2-SHA256 y sal, validaciones y mensajes de error.
- Guardado/lectura de JSON (`perfiles.json`, `avisos.json`, `usuarios.json`) con escritura segura.
- Descarga de configuración remota en un hilo, con caché y valores por defecto, y el banner de
  Inicio + resumen en Ajustes que la reflejan.
- Pruebas automáticas (`tests/test_servicios.py`), el `README.md` y el borrador de este archivo.

