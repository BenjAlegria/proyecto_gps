# DOCUMENTATION — EnRuta Ya! · Proyecto Integrado Final E4

Asignatura Desarrollo Móvil (A+S), TINF1119 — Secciones 1 y 2.
Documento de arquitectura y evidencia del prototipo (16-11-2026).

## 1. Problema social y diagnóstico

Las personas que utilizan buses interurbanos en La Araucanía necesitan
consultar recorridos, paradas, horarios referenciales y novedades antes
de viajar. La investigación del equipo, documentada en
[FUNDAMENTACION-UX-UI.md](FUNDAMENTACION-UX-UI.md), recogió 17 respuestas
entre el 14 y el 28 de septiembre de 2026.

Hallazgos principales: 71% mencionó problemas por buses llenos, 59%
pidió notificaciones de retraso y 76% seleccionó ubicación en mapa
como información deseada. Esta muestra es pequeña y no representa
estadísticamente a todos los pasajeros de la región.

Las principales pantallas responden a esas necesidades: Inicio (mapa),
Recorridos (consulta), Compartir (GPS local consentido y avisos) y
Avisos (reportes de la comunidad). **No hay seguimiento colectivo GPS
entre celulares ni datos oficiales de operadores.** Los buses y ETA
que aparecen en el mapa son ejemplos demostrativos.

## 2. Instalación y ejecución (Windows)

Python 3.10.11, Kivy 2.3.1, KivyMD 2.0.0, Kivy Garden MapView.

~~~powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py
~~~

La aplicación funciona en modo local incluso sin configurar Firebase.
Para el modo remoto opcional, ver [firebase/README.md](firebase/README.md).

## 3. Arquitectura con MVC/POO reconocibles

| Responsabilidad | Componentes | Ejemplo |
|---|---|---|
| Vista | root.kv, componentes.kv, tema.py | Pantallas, formularios, tarjetas y colores |
| Control y coordinación | InterurbanoApp (main.py) | Navegación, validaciones, callbacks, actualización de pantallas |
| Modelos y datos | datos_rutas.py, config.py, servicios/* | Rutas, configuración y persistencia |
| Persistencia local | servicios/almacenamiento.py | JSON por usuario, avisos y preferencias |
| Seguridad | servicios/autenticacion.py | Sal aleatoria y hash PBKDF2-SHA256 |
| Reglas de negocio | servicios/recorridos.py y avisos_service.py | Cálculos simulados, estado y caducidad |
| Ubicación | servicios/ubicacion.py y MapView | Validación GPS, opción IP consentida |
| Analítica | servicios/analitica.py | Registro de eventos y KPIs |
| Identidad remota | servicios/firebase_auth.py | Correo y contraseña de Firebase Authentication, tokens solo en memoria |
| Avisos comunitarios | servicios/firebase_rtdb.py | REST Realtime Database tras iniciar sesión |

**Aclaración:** la app usa separación de responsabilidades y POO, no un
MVC estricto con clases denominadas Model/View/Controller. No prometer
una arquitectura que el código no demuestra.

## 4. Funcionalidades demostrables

1. **Registro/Login:** con Firebase configurado, correo y contraseña
   validados por Firebase Authentication. Sin Firebase se mantiene el
   modo local heredado para pruebas. Las contraseñas nunca se guardan
   en JSON cuando se utiliza Firebase.
2. **Inicio:** MapView OpenStreetMap, localidad de salida, destino,
   tarjetas de rutas, indicadores de demo y ubicación local.
3. **Recorridos:** catálogo y detalle con datos referenciales.
4. **Compartir:** permite seleccionar ruta, solicitar permiso de GPS
   local y crear avisos, sin transmitir coordenadas a un servidor.
5. **Avisos:** reportes locales, anti-spam por sesión, vigencia e
   indicador de favoritos. Los avisos se sincronizan automáticamente
   cuando hay una sesión de correo válida y conexión a Firebase.
6. **Perfil:** favoritas, estadísticas locales y nombre visible.
7. **Ajustes:** tema, notificaciones, configuración remota,
   consentimiento de métricas y estado informativo de conexión.
8. **Analítica MJV App:** sesiones y KPIs obtenidos de eventos locales.

Los eventos de analítica NO se suben a Firebase y no contienen usuario,
correo, ubicación ni IP. Los usuarios deben autorizar la recolección de
datos durante las pruebas y conocer su propósito.

## 5. Estructura de eventos para MJV App

Archivo privado local: `data/analitica_eventos.jsonl`, un JSON por línea:

~~~json
{"id":"uuid_aleatorio","sesion":"uuid_anonimo","evento":"busqueda_iniciada","ts":"ISO_8601_UTC","intento":"uuid_aleatorio","pantalla":"recorridos"}
~~~

La captura está desactivada por defecto y solo funciona tras activar **Ajustes → Participar en medición** con consentimiento. No se registra identidad real. La sesión identifica una ejecución de
la app, no a una persona; `intento` vincula la apertura de Recorridos
con el detalle consultado. Eventos: aplicación iniciada/cerrada,
login exitoso/fallido, registro, pantalla, inicio de búsqueda,
consulta exitosa, favorita agregada/eliminada, aviso publicado y error
de ubicación (si se instrumenta).

**KPI 1:** éxito de búsqueda = consultas exitosas con detalle /
entradas a Recorridos × 100.

**KPI 2:** mediana del tiempo de consulta = mediana del tiempo entre
abrir Recorridos y abrir el detalle, en segundos.

**Métricas auxiliares:** sesiones, número de avisos publicados y
favoritos agregados. No llamar KPI a cada contador sin objetivo.

Instrumento, protocolo y restricciones:
[docs/PROTOCOLO-MJV-APP.md](docs/PROTOCOLO-MJV-APP.md).

Resultados y SVG reproducibles:

~~~powershell
python tools/generar_resultados_mjv.py
~~~

El periodo de recolección lo establecen la primera y la última
marca de tiempo del archivo REAL. El reporte no inventa muestras ni
conclusiones antes de medir.

## 6. Firebase Authentication + Realtime Database

Cuando se configuran `ENRUTA_FIREBASE_API_KEY` y
`ENRUTA_FIREBASE_DATABASE_URL`, el usuario se registra o ingresa con
**correo y contraseña**. El servicio `servicios/firebase_auth.py`
obtiene un UID y tokens temporales desde Identity Toolkit REST, que
permanecen en memoria, sin persistir la contraseña ni el refresh token.

La app muestra un **splash al abrir** y una pantalla de carga durante
el registro o inicio de sesión. Cuando Firebase confirma la identidad,
se habilitan **automáticamente** las lecturas y publicaciones de
`/reportes` a través de `servicios/firebase_rtdb.py`, sin un switch
de sincronización en Ajustes. La consulta es por sondeo aproximadamente
cada 90 segundos, no por WebSocket.

Las reglas `firebase/database.rules.json` exigen
`auth.token.firebase.sign_in_provider == 'password'` y no permiten
datos de ubicación, correo o nombre en los avisos. Deben publicarse
manualmente en la consola de Firebase. La autenticación Email/Password
debe habilitarse en el proyecto.

**Limitaciones:** los perfiles/favoritos siguen guardándose en JSON
local por UID, no se sincronizan entre dispositivos. Las cuentas
anteriores de login local no migran automáticamente; conservan sus
archivos. Si Firebase falla tras autenticar, la app funciona
localmente con los datos ya disponibles. El inicio de sesión remoto
requiere internet y se solicita nuevamente al reiniciar la app,
porque no guardamos tokens persistentes.

Más detalles en [firebase/README.md](firebase/README.md). El servicio
de Firebase no es un criterio explícito de la rúbrica; no confundir
un backend de avisos con un rastreador GPS en vivo.

## 7. Seguridad y responsabilidad social

- Las contraseñas están hasheadas y los archivos JSON locales se
  ignoran en Git. No publicar datos de usuarios reales.
- GPS explícito: no se usa IP para fingir la ubicación de un bus.
- Se descartan callbacks de GPS que llegan tras detenerlo o cerrar sesión.
- En modo Firebase, no enviar ubicación, nombre ni analítica.
- Los horarios, tarifas y marcadores no están verificados por empresas
  de transporte; la UI indica su carácter demostrativo.
- Riesgos: conectividad, falsa información comunitaria, sesgos en la
  encuesta mayoritariamente joven y accesibilidad en pantallas pequeñas.
- Salvaguardas propuestas para producción: moderación, límites de
  frecuencia por cuenta, datos caducos, revisión de accesibilidad y
  pruebas en Android.

En `feature/ajusteV1` se detectó una contraseña MySQL real o
potencialmente real en `data/bd/config_DB.php`. Esa rama **no se
fusionó** con esta versión. Es necesario rotar esa contraseña y
retirar el secreto de Git, incluido el historial si el repositorio
es compartido.

## 8. Pruebas y limitaciones

Tests automatizados: `tests/test_inicio.py`, `test_servicios.py`,
`test_logica.py`, `test_analitica.py` y `test_firebase_rtdb.py`.
Las pruebas de Firebase Auth y Realtime Database usan mocks, sin tráfico real. Verificar en Windows
el resultado completo tras hacer pull, y conservar capturas para defensa.

La rúbrica permite demo en el equipo de desarrollo si no se logra APK,
sin descuento. No afirmar compatibilidad Android sin generar y probar
una APK real. La presentación oral debe cubrir login, navegación,
persistencia, analítica, gráficos y ética.

## 9. Declaración de IA y entregables

Uso de asistentes: ver `USO_IA.md`, actualizarlo conforme a lo que
usó cada integrante (incluye ChatGPT y Codex cuando corresponda).

Entregables: código, README, DOCUMENTATION.md, Informe Final, evidencia
de encuesta, protocolo de pruebas, resultados reales y presentación.
