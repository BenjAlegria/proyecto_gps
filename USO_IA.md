# Declaración de uso de inteligencia artificial

Proyecto: **EnRuta Ya!** · Evaluación N°3, Desarrollo Móvil.

> Las partes marcadas con **[COMPLETAR]** solo las puede escribir el equipo/estudiante:
> son lo que hizo, decidió o entendió por su cuenta. Se evalúa que sean honestas y propias.

## 1. IA usada
- **Claude** (Anthropic), usado en el chat web/app como asistente de programación.
- No se usó ninguna otra herramienta de IA. **[COMPLETAR: confirmar o agregar otras, ej. Copilot]**

## 2. Modelo
- Familia Claude (Anthropic). Versión exacta: **[COMPLETAR: ej. Claude Sonnet 5.5, según lo que indique la app]**.

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
5. **[COMPLETAR: otros prompts que hayan hecho, con sus propias palabras]**

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

**Qué se tomó y qué se descartó:** **[COMPLETAR: ej. "se tomó la estructura de servicios y el hash;
se descartó X porque Y"]**

## 5. Ajustes
*(El punto más importante: qué modificó el equipo respecto de lo que entregó la IA y por qué.)*

**[COMPLETAR con cambios reales hechos por ustedes. Ejemplos del tipo de cosa que va aquí, solo si
es verdad: cambié el largo mínimo de contraseña de 6 a N; cambié el mensaje y valores de
`remote_config.json`; reemplacé los horarios de ejemplo por datos reales de las empresas; cambié
el texto o el tiempo de una notificación; probé la app en un celular y corregí X.]**

Para poder defender el código, el equipo debe poder explicar estas partes sin leer:
- Dónde se valida la contraseña: `servicios/autenticacion.py` → `validar_contrasena()`.
- Dónde se guarda el JSON: `servicios/almacenamiento.py` → `guardar_json()` / `guardar_perfil()`.
- Qué dispara la notificación: `main.py` → `notificar()`, llamado desde `publicar_aviso()`,
  `detener_compartir()` y `simular_aviso()`.
- De dónde sale el valor remoto: `servicios/config_remota.py` → `descargar()`, con la URL y los
  valores por defecto en `config.py`.
- Qué módulo llama a cuál: `main.py` → `servicios/*` → `config.py`.

## 6. Reflexión en el uso de IA
**[COMPLETAR con palabras propias, breve y honesta: qué les sirvió, qué les costó y qué
aprendieron. No se evalúa la postura, se evalúa que sea suya.]**
