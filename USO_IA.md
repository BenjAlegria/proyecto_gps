# Declaración de uso de inteligencia artificial

Proyecto: **EnRuta Ya!** · Evaluación N°3, Desarrollo Móvil.

## 1. IA usada
- **Claude** (Anthropic), usado en el chat web/app como asistente de programación.
- No se usó ninguna otra herramienta de IA. 

## 2. Modelo
- Familia Claude (Anthropic). Versión exacta: 

## 3. Prompts realizados
Resumidos con fidelidad (los que explican decisiones del proyecto):

1. **Primeras versiones:** pedí la app de buses interurbanos en Kivy y luego su migración a KivyMD 2.0,
   con `ScreenManager`, interfaz en `root.kv`, mapa con `kivy_garden.mapview`, panel de buses por
   localidad y diálogo de consentimiento para compartir ubicación.
2. **Avisos de pasajeros:** pedí avisos de "bus lleno / hay asientos / atrasado / cambio de ruta" con
   anti-spam y notificación en rutas favoritas, a partir de los resultados de la encuesta.
3. **Corrección de errores:** consulté por el error `FBO Initialization failed` del snackbar y por los
   íconos de bus demasiado grandes al alejar el mapa.
4. **Cierre de la Evaluación N°3:** pegué las instrucciones de la evaluación y pedí "añade, corrige,
   termina el proyecto" para cumplir los requisitos (registro y login, JSON, notificaciones,
   configuración remota, README y USO_IA).
5. **Cómo integrarlo:** pedí que los cambios se pudieran aplicar por partes (config y datos, JSON, login,
   notificaciones, configuración remota) y que me explicara cómo separar el código de `main.py`.
6. **Entender el código:** pedí una explicación completa de cómo funciona la app, qué hace cada archivo,
   cómo se conectan y qué pasa si se modifica algo, para poder defenderlo.
7. **Preguntas de diseño:** qué pasa si dos pasajeros comparten ubicación en el mismo bus, y cómo
   evitar que alguien envíe una posición falsa.
8. **Pedí la app lo más completa posible:** de ahí salió el servidor para compartir ubicación y avisos.
9. **Conceptos:** qué son los tests y qué pasa si se quitan.
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

