# Guía de defensa individual — EnRuta Ya! · 84 preguntas E4

**Desarrollo Móvil (A+S) · TINF1119 · Instituto Tecnológico UC Temuco · noviembre de 2026**

Preparé esta guía para que podamos defender el proyecto entendiendo sus decisiones y encontrando los archivos pertinentes, no para memorizar respuestas sin revisar el código. Las respuestas aplicadas están redactadas como explicaríamos nuestro propio trabajo, en primera persona del plural. Las explicaciones teóricas se acompañan de referencias al proyecto cuando corresponde.

**Versión de referencia:** `feature/diseno-v3-sobre-backend-final`, basada en `feature/Ajuste3-PLSFINAL`. **Arquitectura real final:** Python + Kivy/KivyMD + API PHP + MySQL; la analítica MJV es JSONL local y un subconjunto de eventos llega a MySQL. **No usamos Firebase en el backend final.** GPS remoto en vivo, medición con personas y validación Android: sin evidencia final confirmada al preparar esta guía.

**Convenciones:** «Ejemplo hipotético/didáctico» indica una cifra creada solo para practicar un cálculo. «Pendiente» indica algo no demostrado o todavía no implementado.

## Dónde mostrar el código al profesor

| Tema | Archivo o función que buscamos |
|---|---|
| Pantallas, IDs y botones | `root.kv`, `componentes.kv` |
| Flujo y consentimiento | `main.py → cambiar_pantalla()`, `cambiar_analitica()`, `_medir()` |
| Inicio y fin de búsqueda | `main.py → mostrar_detalle()`; `servicios/analitica.py → iniciar_busqueda(), completar_busqueda()` |
| Evento JSONL | `servicios/analitica.py → Registrador.registrar()` |
| Cálculo de indicadores | `servicios/analitica.py → resumen(eventos)` |
| Informe y gráfico | `tools/generar_resultados_mjv.py` |
| Pruebas del medidor | `tests/test_analitica.py` |
| Registro manual de usuarios | `docs/REGISTRO-PRUEBAS-USUARIOS.csv` |
| API, caché y sincronización | `servicios/api_cliente.py → ClienteApi`; `main.py → sincronizar()` |
| Datos servidor | `backend/api/index.php`, `backend/sql/enruta_schema.sql` |
| Protocolo RA3 | `docs/PROTOCOLO-MJV-APP.md` |

---


## 1. Anatomía del evento


### 01. ¿Qué es un evento en analítica de aplicaciones? Da un ejemplo de tu propio proyecto.

Un **evento** es una acción o situación significativa que transformamos en un registro para analizar cómo se usa la aplicación. En EnRuta Ya! registramos `busqueda_iniciada` cuando abrimos Recorridos y `recorrido_consultado` cuando accedemos a Detalle. No basta con que alguien toque un botón: el código debe llamar al registrador para crear el evento. **En el código:** `main.py → cambiar_pantalla()` y `mostrar_detalle()`.


### 02. ¿Cuáles son los tres componentes mínimos de un evento registrado y qué aporta cada uno?

Como mínimo necesitamos **nombre del evento**, **momento de ocurrencia** (`ts`) y **contexto o identificador de sesión** (`sesion`). El nombre responde qué pasó, la fecha indica cuándo y la sesión permite agrupar acciones de una ejecución. Nuestro código además crea un `id` único para cada registro. Los campos están en el diccionario de `Registrador.registrar()` de `servicios/analitica.py`.


### 03. ¿Por qué el timestamp es imprescindible? ¿Qué cálculos se vuelven imposibles si falta?

El *timestamp* permite ordenar acciones, delimitar un periodo y estudiar cambios por fecha u horario. Sin tiempo no podemos saber qué ocurrió primero ni comparar actividad en distintos días. Para medir cuánto tarda una tarea, además del `ts` usamos `time.monotonic()` y guardamos `duracion_ms`, porque es más adecuado para medir intervalos y evita alteraciones del reloj del sistema.


### 04. Además del nombre y la fecha, ¿qué otros campos conviene agregar a un evento? Justifica dos.

Agregaría **`sesion`**, para distinguir ejecuciones sin guardar nombre o correo, y **`intento`**, para relacionar `busqueda_iniciada` con `recorrido_consultado`. También es útil `pantalla` para identificar dónde ocurrió y `duracion_ms` para medir la rapidez. En nuestro proyecto solo aceptamos pantallas y tipos conocidos: evitamos datos arbitrarios que compliquen el análisis o expongan información personal.


### 05. ¿Cuál es la diferencia entre una acción del usuario y un evento registrado?

La acción es lo que una persona hace en la interfaz; el evento es el **dato estructurado que guardamos** cuando decidimos medir esa acción. Por ejemplo, entrar a Recorridos cambia de pantalla aunque la analítica esté desactivada. Solo al aceptar las métricas, `main.py → _medir()` y `Registrador` generan el registro. Así la aplicación funciona independientemente de la medición.


### 06. ¿Qué hace útil a un nombre de evento? Piensa en convenciones, consistencia y datos variables.

Un nombre útil es **claro, estable y consistente**, por ejemplo `favorito_agregado`, usando minúsculas y guiones bajos. No crearíamos nombres como `favorito_Temuco_17nov`: la localidad o fecha, si se justifica recopilarla, sería otro campo. En `servicios/analitica.py → EVENTOS` definimos una lista permitida para evitar variantes y errores de escritura.


### 07. ¿Registrarías cada toque en pantalla? Explica qué ganarías y qué perderías.

No registraríamos cada toque. Aumentaría el detalle para reconstruir un flujo, pero produciría ruido, archivos grandes, riesgo de privacidad y análisis difícil. Preferimos acciones relacionadas con objetivos: iniciar búsqueda, abrir detalle, guardar favorita, publicar aviso y errores de ubicación. Si necesitamos investigar un botón concreto, agregamos temporalmente un evento específico y consentido.


### 08. En tu aplicación, ¿qué eventos registran y por qué esos y no otros?

Tenemos `aplicacion_iniciada`, `aplicacion_cerrada`, `login_exitoso`, `login_fallido`, `registro_exitoso`, `pantalla_abierta`, `busqueda_iniciada`, `recorrido_consultado`, `favorito_agregado`, `favorito_eliminado`, `aviso_publicado` y `error_ubicacion`. Elegimos los que permiten seguir navegación, consulta, participación y dificultades. **Importante:** no todos los eventos locales se envían al servidor; la API solo admite ciertos tipos de `EVENTOS_OK`.


### 09. ¿Cómo se relaciona un evento con el diagnóstico del socio comunitario (RA1)?

En nuestro diagnóstico RA1, un **71 % de 17 encuestados** indicó dificultades con buses llenos y muchas personas querían información de recorridos. Por eso el evento `recorrido_consultado` verifica si una persona consigue llegar al detalle, y `aviso_publicado` mide participación. El evento traduce una necesidad diagnosticada en una observación de uso, pero no demuestra por sí solo que solucionamos el problema comunitario.


### 10. ¿Qué evento registrarías para detectar que un usuario abandona el flujo principal?

Implementaría `busqueda_abandonada` o `tarea_cancelada` con el mismo `intento` y el motivo, por ejemplo volver atrás sin abrir Detalle. **Todavía no existe ese evento explícito**: hoy el informe deduce intentos no completados al comparar `busqueda_iniciada` con `recorrido_consultado`. Debemos distinguir abandono verdadero de cierre, error o interrupción.


## 2. Estructura y formato de los datos


### 11. ¿Qué estructura de datos de Python usarías para representar un evento en memoria y por qué?

Usaría un **diccionario (`dict`)** porque cada evento tiene campos con nombre y valores de distinto tipo: `{'evento':'busqueda_iniciada','sesion':'…','ts':'…'}`. Es fácil agregar campos opcionales como `intento` y convertir el diccionario a JSON. Nuestro `Registrador.registrar()` construye precisamente un diccionario y lo pasa a `json.dumps()`.


### 12. ¿Por qué JSON es adecuado para guardar eventos? ¿Qué tipos de datos admite y cuáles no?

JSON es legible e interoperable entre Python, JavaScript y PHP. Representa objetos, listas, cadenas, números, booleanos y `null`. No admite directamente objetos Kivy, `datetime`, conjuntos o instancias Python arbitrarias. En nuestra analítica convertimos el tiempo a una cadena ISO 8601 y solo guardamos tipos sencillos; `json.dumps()` serializa el diccionario.


### 13. ¿Qué diferencia hay entre guardar todos los eventos en una única lista JSON y usar JSON Lines (un objeto por línea)?

Una **lista JSON única** requiere abrir, leer, modificar y reescribir todo el archivo para agregar un evento; si se interrumpe, puede dañarse el conjunto. **JSON Lines (JSONL)** tiene un objeto por línea, así basta agregar una línea nueva. En `data/analitica_eventos.jsonl` usamos JSONL para escribir incrementalmente y leer línea a línea, descartando líneas corruptas.


### 14. ¿Cuándo conviene usar CSV? ¿Qué información se pierde al pasar de JSON a CSV?

CSV conviene para tablas planas, como la planilla `docs/REGISTRO-PRUEBAS-USUARIOS.csv`, donde cada fila es un participante y cada columna una medida. Pasar JSON a CSV puede perder jerarquías, listas, tipos complejos, distinción entre datos ausentes y estructuras anidadas. En nuestro caso el JSONL conserva campos variables de eventos y el CSV documenta observaciones manuales.


### 15. ¿Qué ventaja tiene un formato de registro por líneas al momento de agregar eventos nuevos?

La principal ventaja es escribir en **modo agregar** sin modificar los eventos anteriores. También permite procesar un registro con un iterador sin cargarlo completo y aislar una línea defectuosa. Nuestro código ejecuta `fh.write(json.dumps(evento, ensure_ascii=False) + '\n')` dentro de `Registrador.registrar()`: cada evento termina con salto de línea.


### 16. ¿En qué modo se abre el archivo para no perder los registros anteriores? ¿Qué ocurre si se abre en el modo equivocado?

Para conservar los anteriores se abre con **`'a'` (append)**, como hacemos en `servicios/analitica.py`: `open(self.archivo, 'a', encoding='utf-8')`. El modo `'w'` sobrescribe el contenido anterior al abrir; podríamos perder todas las pruebas anteriores por error. `'x'` solo crea si no existe y `'r'` es lectura.


### 17. ¿Qué formato de fecha y hora usarías para que los registros se puedan ordenar y comparar?

Elegimos **ISO 8601 con zona horaria explícita**, preferiblemente UTC: `2026-11-17T15:00:00+00:00`. Ese formato se ordena y compara más fácilmente que fechas ambiguas como `17/11/26 12:00`. Nuestra función `datetime.fromtimestamp(..., timezone.utc).isoformat()` guarda fecha UTC; para la defensa diferenciamos la hora de Chile de la almacenada.


### 18. ¿Dónde conviene guardar el archivo de eventos en un dispositivo Android y por qué no en la carpeta del código de la aplicación?

En Android conviene usar el almacenamiento privado de la aplicación, accesible desde **`App.user_data_dir`**, porque es escribible y no debe mezclarse con el paquete APK, que puede ser de solo lectura. **Brecha real:** nuestra caché API usa `App.user_data_dir`, pero `servicios/analitica.py` escribe en `config.DATA_DIR` dentro del proyecto. Debemos comprobar o corregir esa ruta antes de medir en Android.


### 19. ¿Qué problemas aparecen cuando el archivo de registro crece sin control?

Puede ocupar mucho espacio, ralentizar lectura, exportación y gráficos, gastar batería e incluir datos que ya no necesitamos. Nuestra función `leer_eventos()` limita la carga a **100.000 líneas**, pero el escritor **no rota ni limita el tamaño del archivo**. Para uso prolongado agregaríamos rotación por tamaño/fecha, retención y borrado seguro tras exportar.


### 20. ¿Cómo asegurarías que el archivo siga siendo legible si la aplicación se cierra a mitad de una escritura?

Escribimos un JSON completo más un salto de línea y cerramos el archivo mediante `with`; si se corta la energía durante la escritura, una línea final puede quedar incompleta. `leer_eventos()` ignora esa línea inválida para seguir leyendo el resto. Para mayor robustez usaríamos escritura en cola con bloqueo, `flush`/`fsync` si se requiere, y rotación o archivos temporales al exportar. No afirmamos que `with` garantice escritura atómica.


## 3. Implementación del registro en Python


### 21. ¿Qué módulos de la biblioteca estándar necesitas para registrar eventos con fecha en un archivo?

Bastan módulos estándar: **`json`** para serializar, **`datetime`/`timezone`** para fecha UTC, **`os`** para carpetas y **`threading`** si hay concurrencia. Nosotros también usamos `uuid` para IDs, `time.monotonic` para duraciones y `statistics` para medianas. No necesitamos instalar una librería externa para escribir el JSONL.


### 22. ¿Qué hace json.dumps() y en qué se diferencia de json.dump()?

`json.dumps(objeto)` **devuelve una cadena JSON** que podemos concatenar con `'\n'` y pasar a `write()`. En cambio `json.dump(objeto, archivo)` escribe directamente sobre un archivo abierto. Nuestro registro usa `json.dumps(evento, ensure_ascii=False)` porque cada evento es una línea separada dentro de un archivo JSONL.


### 23. ¿Por qué no basta con guardar datetime.now() tal cual? ¿Qué cuidado hay que tener con el formato y la zona horaria?

`datetime.now()` devuelve un objeto Python que JSON no serializa automáticamente y, sin zona horaria, puede resultar ambiguo entre computadores. Conviene usar `datetime.now(timezone.utc).isoformat()` o nuestro equivalente `datetime.fromtimestamp(self.reloj(), timezone.utc).isoformat()`. Para medir tiempos de respuesta preferimos `time.monotonic()` en lugar de restar horas de reloj.


### 24. ¿Para qué sirve el módulo logging y en qué se diferencia de escribir con open()?

`logging` es el módulo estándar para **mensajes de diagnóstico** con niveles como DEBUG, INFO, WARNING y ERROR, filtros y manejadores. `open()` permite diseñar nuestro propio registro estructurado de eventos. `logging` sirve para fallos técnicos; nuestro JSONL se diseñó para medir acciones y calcular KPIs. No conviene confundir un log de errores con analítica de uso.


### 25. ¿Cómo configurarías logging para que escriba en un archivo con fecha, hora y nivel?

Podría configurar `logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')` y luego `logging.info('Inicio')` o `logging.error('Error de red')`. Ese sería un **ejemplo de alternativa**, no nuestra instrumentación principal. Para eventos seguimos usando `Registrador` con JSONL porque necesitamos campos como `intento` y `duracion_ms`.


### 26. ¿Cuál es la diferencia entre abrir un archivo en modo "w" y en modo "a"?

`'w'` **vacía o crea** un archivo; `'a'` **añade al final o crea** sin borrar lo anterior. Si registráramos una sesión de prueba con `'w'` en cada evento, solo quedaría el último. Por eso `Registrador.registrar()` abre en `'a'`; el lector abre en modo lectura mediante `open(self.archivo, encoding='utf-8')`.


### 27. ¿Por qué conviene declarar encoding="utf-8" al escribir el archivo?

UTF-8 permite registrar correctamente acentos, ñ y textos de nuestra interfaz sin depender de la codificación predeterminada del sistema. Así funciona igual en Windows, Linux y Android. Usamos `ensure_ascii=False` para mantener caracteres legibles y `encoding='utf-8'` tanto al escribir como al leer JSONL.


### 28. ¿Qué ocurre si el evento incluye un dato que no se puede serializar, como un objeto de Kivy? ¿Cómo lo resolverías?

`json.dumps()` normalmente lanzaría **`TypeError: Object of type ... is not JSON serializable`**. La solución es guardar solo datos primitivos relevantes, por ejemplo una cadena `pantalla='recorridos'`, no el objeto `Screen`. Si necesitamos una propiedad, extraemos explícitamente su valor y validamos el tipo. Nuestro registrador limita los campos que acepta, justamente para evitar objetos o datos arbitrarios.


### 29. ¿Cómo probarías el módulo de registro sin pasar por la interfaz gráfica?

Probamos el módulo **sin abrir Kivy** con `unittest` y `tempfile.TemporaryDirectory()`. Creamos un `Registrador` apuntando a una ruta temporal, inyectamos relojes controlados, registramos una búsqueda de 3,5 segundos y comprobamos que el resumen entrega una sesión, 100 % de éxito y mediana 3,5. También probamos consentimiento desactivado, archivo corrupto y eventos inválidos. **Archivo:** `tests/test_analitica.py`.


## 4. Analítica en Kivy


### 30. ¿Kivy incorpora un sistema de analítica? ¿Qué ofrece en su lugar?

Kivy no incluye un sistema integral de analítica de producto con cohortes y KPIs. Aporta **eventos de interfaz**, *bindings*, `Clock`, `Logger`, almacenamiento y acceso al ciclo de vida de la app. Nosotros conectamos callbacks como `app.cambiar_pantalla(...)` a nuestro `Registrador`, que convierte acciones seleccionadas en eventos JSONL. Kivy facilita instrumentar, pero no decide qué medir.


### 31. ¿Para qué sirve kivy.storage.jsonstore.JsonStore y en qué se diferencia de un registro de eventos?

`JsonStore` guarda pares clave–valor persistentes, como preferencias o estado actual, en JSON. Un **registro de eventos** es una secuencia histórica: no queremos sobrescribir lo sucedido ayer al actualizar el estado de hoy. EnRuta Ya! usa persistencia JSON de preferencias y una caché en `ClienteApi`, pero para analítica utiliza **JSONL por línea**, no `JsonStore`.


### 32. ¿Qué es App.user_data_dir y por qué conviene usarlo para guardar datos de la aplicación?

`App.user_data_dir` devuelve una ruta privada y escribible para datos de esa instalación, especialmente útil en Android. En nuestro proyecto `ClienteApi` recibe `self.user_data_dir` y guarda allí `cache_api.json`. En cambio el módulo MJV usa `config.DATA_DIR` y debemos comprobar su comportamiento dentro del APK. La carpeta del código no es un lugar fiable para escribir en aplicaciones empaquetadas.


### 33. ¿Para qué sirve kivy.logger y qué límites tiene si se lo usa como sistema de analítica?

`kivy.logger.Logger` informa errores y estados técnicos del framework, como advertencias de renderizado o fallos. No proporciona automáticamente datos de producto como intentos iniciados, tasas de éxito, consentimiento ni cohortes. Nuestro `Registrador` escribe eventos explícitos con campos estables. Podemos usar ambos: `Logger` para depuración y el registro MJV para decisiones de diseño.


### 34. ¿Analizarías el registro dentro de la aplicación o fuera de ella? Justifica.

**Fuera de la app** para no consumir memoria/batería del pasajero ni mostrarle un tablero académico. Guardamos eventos y luego ejecutamos `python tools/generar_resultados_mjv.py` en el computador. Solo dejaríamos en la app información operativa que ayude al usuario, como estado de conexión. Una analítica ligera interna podría ser útil, pero para el proyecto la separación es más sencilla y prudente.


### 35. ¿Qué librerías usarías para analizar el registro en el computador y por qué no dentro del APK?

Para analizar en el computador usaría **`json`, `statistics`** y, si necesitamos gráficos más elaborados, `pandas` y `matplotlib`. Nuestro código actual calcula con la biblioteca estándar y produce un **SVG** manualmente en `tools/generar_resultados_mjv.py`; no utiliza pandas ni matplotlib. Evitamos meter esas librerías pesadas al APK porque no hacen falta para que un pasajero consulte recorridos.


### 36. ¿Cómo exportarías el archivo de eventos desde el teléfono al computador para analizarlo?

Primero debemos guardar el JSONL en la ruta privada correcta del teléfono. Después podemos **exportar con consentimiento** mediante un botón de compartir archivo, conexión USB/ADB en un teléfono de pruebas o una exportación controlada. **Actualmente no hay botón de exportación implementado**, así que no debemos demostrarlo como función terminada. La alternativa temporal para la evaluación es medir en PC y usar el mismo generador de resultados.


### 37. Si necesitaras analítica en tiempo real dentro de la aplicación, ¿qué alternativa existiría y qué costo tendría?

Una alternativa es enviar eventos anónimos a una API/servicio de analítica y mostrar un tablero actualizado, o almacenar/consultar agregados en el servidor. El costo es más red, almacenamiento, privacidad, seguridad, mantenimiento y posible dependencia de terceros. Nuestra API PHP ya tiene una tabla `eventos`, pero recibe datos simplificados; no entrega un sistema completo de analítica en tiempo real.


## 5. Métricas y KPIs


### 38. ¿Qué es una métrica? Defínela con un ejemplo de tu aplicación.

Una **métrica** es un valor cuantitativo que describe un aspecto de uso. Por ejemplo, `resumen(eventos)['avisos_publicados']` cuenta cuántos eventos `aviso_publicado` registramos. También medimos intentos de búsqueda y sesiones. Una métrica informa «cuánto ocurrió», pero no demuestra por sí sola que logramos nuestro objetivo.


### 39. ¿Qué es un KPI? ¿Qué lo distingue de una métrica cualquiera?

Un **KPI** (indicador clave de desempeño) es una métrica seleccionada porque se relaciona con un objetivo y permite tomar decisiones. Nuestro KPI principal es el **porcentaje de búsquedas que llegan al detalle**. Es clave porque queremos que las personas encuentren información de rutas. Para interpretarlo necesitamos periodo, muestra y una meta definida antes de las pruebas.


### 40. Explica la diferencia entre métrica y KPI usando dos ejemplos de tu propio proyecto.

Métrica: **cantidad de veces que entramos a Recorridos** (`busqueda_iniciada`). KPI: **tasa de consulta exitosa** = intentos que abren Detalle / intentos iniciados × 100. Otra métrica es el conteo de avisos; solo sería KPI si definiéramos qué objetivo de participación evaluamos y con qué criterio. Una actividad numerosa no equivale automáticamente a utilidad.


### 41. ¿Toda métrica puede ser un KPI? Justifica con un caso concreto.

No. Una métrica se convierte en KPI **solo si es relevante para una meta y se usa para decidir**. Contar pantallas abiertas es descriptivo; no nos dice si la navegación fue fácil. En cambio, el porcentaje de búsquedas con detalle abierto puede revelar fricción en el flujo principal y motivar rediseñar el selector o las tarjetas.


### 42. ¿Cuántos KPIs conviene elegir en un proyecto y por qué esa cantidad?

Elegiríamos **dos o tres KPIs principales**, suficientes para evaluar el flujo sin dispersarnos. En EnRuta Ya! priorizamos tasa de éxito de consulta y mediana del tiempo para llegar al detalle; además podemos observar persistencia de favoritas de forma manual. Muchos indicadores vuelven difícil distinguir qué problema estamos intentando resolver. La cantidad no es una regla universal.


### 43. ¿Cómo se calcula un KPI a partir de los eventos registrados? Muestra la fórmula de uno tuyo.

En `servicios/analitica.py → resumen()` formamos conjuntos de `intento`: iniciados con `busqueda_iniciada` y completados con `recorrido_consultado`. **Fórmula:** `100 × |iniciados ∩ completados| / |iniciados|`. **Ejemplo didáctico, NO resultado real:** 8 detalles abiertos de 10 intentos = 80 %. Si no hay búsquedas, devolvemos `None`, no 0 %.


### 44. ¿Qué diferencia hay entre una métrica descriptiva y un indicador de éxito? Ejemplifica.

Una **métrica descriptiva** dice que se registraron, por ejemplo, 12 aperturas de una pantalla; es actividad sin juicio de éxito. Un **indicador de éxito** compara una conducta con el objetivo, como 8 de 10 búsquedas que llegan al detalle. En nuestro proyecto un aviso publicado también es una métrica, pero sin validar su veracidad no demuestra transporte mejor informado.


### 45. ¿Qué es una métrica vanidosa? Da un ejemplo y explica por qué no sirve para decidir.

Una métrica vanidosa luce bien pero no ayuda a tomar decisiones. Por ejemplo, presumir de 1.000 pantallas abiertas sin saber si alguien encontró su bus. Incluso muchas cuentas creadas pueden no significar uso sostenido. Preferimos medir finalización de tareas y tiempos, porque se relacionan con la incertidumbre de los pasajeros detectada en el diagnóstico.


### 46. ¿Cómo calcularías la retención de usuarios con los eventos que registras hoy?

**Con los eventos de hoy no podemos calcular retención de personas de forma fiable.** Nuestro campo `sesion` cambia entre ejecuciones y no incluye un identificador longitudinal de usuario por privacidad. Para retención D1/D7 necesitaríamos un identificador pseudónimo estable, consentimiento, política de retención y verificar regreso al día 1/7. Solo podríamos describir actividad por sesiones, no personas que volvieron.


### 47. Para la tasa de tareas completadas, ¿qué eventos necesitas y qué fórmula usarías?

Se necesitan **inicio de tarea con ID** y **finalización con el mismo ID**. Para nuestra consulta usamos `busqueda_iniciada(intento)` y `recorrido_consultado(intento)`. Fórmula: `100 × tareas completadas / tareas iniciadas`. Abrir Detalle significa completar esta tarea operacionalizada; **no prueba que la persona entendió los horarios**, por eso agregamos observación manual.


### 48. ¿Cómo definirías la frecuencia de errores y qué decisión habilita ese dato?

Definiría frecuencia como `100 × tareas con error / tareas iniciadas` o errores por cada 100 sesiones, según la pregunta. Registraríamos `error_ubicacion` para GPS y, si hace falta, eventos de error por login o consulta. **Hoy nuestro módulo no ofrece un KPI completo de errores por tarea**. Si detectamos errores frecuentes de GPS, revisaríamos permisos y mensajes antes de añadir nuevas funciones.


### 49. ¿Cuál es tu KPI principal y por qué responde al problema diagnosticado en el RA1?

El **porcentaje de consultas que abren un detalle** es nuestro KPI principal: `100 × consultas_exitosas / busquedas_iniciadas`. Se relaciona con RA1 porque muchas personas se informan por memoria o preguntando a un conductor, y queremos facilitar acceso a información centralizada. **Límite:** abrir una ficha no demuestra que el dato sea preciso ni que el viaje mejoró.


## 6. Herramientas de análisis: industria y solución propia


### 50. Nombra dos herramientas de analítica móvil de la industria y describe qué capturan.

Dos ejemplos son **Google Analytics for Firebase** (eventos, sesiones, usuarios, conversiones/engagement) y **Amplitude** (eventos de producto, embudos, cohortes y retención). Son alternativas de industria, **no servicios integrados en nuestro APK final**. Nuestra versión final usa una API PHP/MySQL para la app y un registrador propio JSONL para KPIs académicos.


### 51. ¿Qué entrega Firebase Analytics que un registro local no entrega?

Firebase Analytics puede recopilar eventos de varias instalaciones, agregarlos automáticamente, ofrecer paneles, audiencias y análisis de uso sin tener que reunir manualmente todos los archivos. Un JSONL local conserva solo lo ocurrido en ese dispositivo, hasta exportarlo. **No debemos confundir Firebase Analytics con Firebase Authentication o Realtime Database**; son servicios distintos y nuestro backend final es PHP/MySQL.


### 52. ¿Qué entrega un registro local que una herramienta de la industria no entrega?

Un registro local nos da **control directo sobre campos, archivos y conservación**, funciona sin internet y puede minimizar envío de información a terceros. También podemos auditar el código exacto y reproducir cada fórmula. A cambio requiere más trabajo para agregar registros entre teléfonos y construir informes. Para nuestro prototipo elegimos eventos pequeños y consentidos.


### 53. ¿Qué implicancias tiene en privacidad enviar datos de uso a un servicio externo?

Enviar datos a un tercero implica revisar consentimiento, finalidad, información compartida, ubicación/identificadores, transferencias, conservación y acceso. Incluso sin nombres, una combinación de timestamps e identificadores podría permitir inferencias. Por eso nuestro JSONL evita correo, coordenadas y contraseñas, y el registro se activa solo mediante consentimiento; cualquier servicio externo requeriría una evaluación adicional.


### 54. Las condiciones de tu proyecto —sin internet y sin servicios externos— ¿cómo limitan la elección de herramientas?

Si la evaluación debe funcionar **sin internet y sin servicios externos**, no podemos depender de una plataforma remota para registrar y analizar eventos. Elegimos JSONL local con módulos estándar. EnRuta Ya! **sí usa internet y una API PHP/MySQL para funciones de pasajeros**, pero el módulo de medición puede funcionar localmente. Es importante distinguir condiciones de la práctica de una aplicación real.


### 55. ¿Qué significa una solución in-house? Señala dos ventajas y dos costos.

Una solución **in-house** es diseñada y mantenida por nuestro equipo, en lugar de contratar una plataforma analítica. Ventajas: control de datos y personalización exacta de eventos/KPIs. Costos: mantenimiento, pruebas, seguridad y desarrollo de tableros/exportación. `servicios/analitica.py` + `tools/generar_resultados_mjv.py` es nuestra solución propia; no tiene todas las funciones de una plataforma comercial.


### 56. ¿En qué momento recomendarías migrar del registro local a una herramienta profesional?

La recomendaríamos si EnRuta Ya! se usara de verdad por muchas personas y necesitáramos comparar versiones, detectar retención por cohortes, analizar embudos y recibir resultados de varios teléfonos. Antes definiríamos métricas, base legal/consentimiento, presupuesto y política de datos. Para el prototipo universitario un registro propio basta para evaluar el flujo principal si hacemos pruebas reales.


### 57. ¿Qué se pierde cuando se mide sin herramienta: agregación, segmentación, cohortes, retención?

Sin plataforma automática perdemos **comodidad**, no necesariamente la posibilidad matemática: debemos programar agregación, segmentación, cohortes y retención manualmente. Nuestro resumen actual calcula sesiones, éxitos, tiempos, avisos y favoritas, pero **no segmenta cohortes ni identifica usuarios recurrentes**. Evitamos inventar retención con IDs de sesión que cambian en cada ejecución.


### 58. ¿Cómo compararías los resultados del registro propio con los de una herramienta externa?

Instrumentaríamos el mismo evento y periodo en ambos sistemas, compararíamos definición, filtros, consentimientos, zona horaria y pérdida de eventos, y analizaríamos diferencias. Por ejemplo, la cantidad de `recorrido_consultado` debería concordar si ambos registros reciben todas las acciones. **No hemos hecho esa comparación**; es un plan de verificación, no un resultado existente.


### 59. Si el socio comunitario no puede pagar un servicio de analítica, ¿qué alternativa propones?

Propondríamos continuar con **JSONL local más un generador gratuito de resúmenes y gráficos**, por ejemplo nuestro `Registrador` y `tools/generar_resultados_mjv.py`. La organización tendría un protocolo de consentimiento, exportación controlada y conservación limitada. Otra alternativa sería analítica agregada en su propio servidor, pero solo si puede mantenerlo con seguridad.


## 7. Método MJV App


### 60. ¿Qué significa MJV App y cuál es su propósito?

**MJV App significa Medir → Jugar → Validar**, un ciclo para evaluar una aplicación mediante tareas, observaciones y decisiones. No es un juego de entretenimiento: «Jugar» es poner a prueba el prototipo con un escenario y personas. El propósito es que nuestras mejoras se basen en evidencia y no solo en que el diseño nos parezca cómodo.


### 61. Describe los tres pasos del método y qué se hace en cada uno.

**Medir:** elegimos problema, hipótesis, tarea, eventos, fórmula y criterio de éxito. **Jugar:** una persona intenta la tarea con la app, mientras registramos resultados y observamos dificultades sin guiarla. **Validar:** analizamos indicadores y notas, contrastamos con la hipótesis y decidimos mantener, cambiar o probar otra alternativa. El resultado vuelve a alimentar una nueva medición.


### 62. ¿Por qué se plantea como un ciclo y no como una secuencia que termina?

Porque una mejora puede ayudar en un flujo y perjudicar otro; necesitamos **iterar**. Medimos un estado inicial, jugamos un escenario, validamos, modificamos lo necesario y repetimos con una tarea comparable. Terminar la primera evaluación no significa que la aplicación ya sea buena para todos los usuarios o dispositivos.


### 63. ¿Qué se define en el paso Medir y de dónde sale esa definición?

Definimos **qué pregunta queremos responder, qué tarea observar, cómo sabremos que se completó, qué eventos y fórmula usaremos** y bajo qué condiciones. Esto sale del diagnóstico RA1 y los objetivos del prototipo RA2. Para EnRuta Ya!: «¿Una persona puede abrir el detalle de una ruta desde Recorridos?»; usaremos éxito y tiempo de búsqueda.


### 64. ¿Qué significa Jugar dentro de este método? ¿Se trata de una prueba informal?

«Jugar» es una **prueba de uso planificada**, no navegar al azar. Damos la misma instrucción a cada participante, pedimos consentimiento, observamos qué hace, evitamos enseñarle la respuesta y anotamos dificultad/tiempo. Nuestro protocolo en `docs/PROTOCOLO-MJV-APP.md` define consulta, favorita y aviso como escenarios, aunque las pruebas con personas todavía están pendientes.


### 65. ¿Qué se hace en el paso Validar y qué tipo de decisión se toma al final?

En **Validar** calculamos los KPIs, revisamos observaciones, comparamos con una hipótesis o meta y justificamos una decisión: mantener la interfaz, corregir un control, cambiar el flujo o repetir la prueba. Una tasa alta con varias quejas también exige revisar la experiencia. Nuestro generador produce indicadores, pero la decisión necesita participantes y contexto.


### 66. ¿Qué evidencia necesitas para pasar de Medir a Validar sin saltarte etapas?

Necesitamos **registros de tarea reales** (`busqueda_iniciada`, `recorrido_consultado`, IDs y duraciones), una planilla anónima de participantes, fechas, versión del proyecto, consentimiento y observaciones. Sin pasar por Jugar estaríamos interpretando números sin saber qué hicieron realmente las personas. Hoy tenemos el instrumento, pero el CSV de pruebas no tiene participantes registrados.


### 67. Aplica MJV App a tu proyecto: describe una iteración completa con tus propios datos.

**Iteración preparada, no realizada:** (1) Medir: proponemos que el usuario llegue a Detalle desde Recorridos; definimos éxito y mediana. (2) Jugar: pedimos abrir una ruta y registramos eventos/observaciones, con consentimiento. (3) Validar: calculamos `resumen()` y, si hay demoras, revisamos selector o tarjetas. **Dato real disponible:** el diagnóstico RA1 tuvo 17 encuestados; **no tenemos resultados reales del ciclo RA3**. No llamaría a esto «iteración completada» hasta ejecutar la prueba.


### 68. ¿Qué ocurre si la validación resulta negativa? Da un ejemplo aplicado a tu aplicación.

Si obtenemos, por ejemplo, una tasa baja o tiempos altos, revisamos dónde se pierde la persona, cambiamos la interfaz y repetimos la misma tarea para comparar. No asumimos que el usuario «se equivocó». **Ejemplo hipotético:** varios participantes no ubican el botón de Recorridos; haríamos más evidente el acceso y validaríamos otra vez. El resultado negativo es información útil para iterar, no un fracaso que deba ocultarse.


## 8. Capacidad crítica: para qué sirve medir


### 69. ¿Para qué sirve todo esto? Responde en una frase y defiéndela.

**Medimos para saber si la aplicación resuelve una tarea real y para decidir qué mejorar.** La defiendo así: una interfaz puede abrir sin errores, pero eso no demuestra que una persona encuentre la ruta. La tasa de consulta y el tiempo, acompañados por observaciones, permiten detectar esa diferencia entre código funcional y experiencia útil.


### 70. ¿Qué decisión de tu proyecto cambió, o cambiaría, a partir de un dato concreto?

La encuesta RA1 mostró que **71 % había enfrentado buses llenos** y **59 % se informaba por experiencia o memoria**; por eso priorizamos rutas y avisos en el diseño. Para una decisión futura: si la mediana de consulta fuera alta, simplificaríamos selector y listado. Esa mejora sería **condicionada a datos reales de RA3**, que aún no tenemos.


### 71. ¿Qué riesgo existe al medir sin una hipótesis previa?

Podríamos medir muchas cosas y seleccionar después solo las cifras favorables, confundiendo coincidencia con aprendizaje. Definir primero hipótesis, métricas y periodo reduce esa selección interesada. Nuestra hipótesis de consulta está escrita en `INFORME-FINAL.md` y el protocolo. Si la tarea falla, debemos informarlo en vez de cambiar la definición de éxito a mitad de prueba.


### 72. ¿Cómo evitas que los datos terminen confirmando lo que ya creías?

Comparamos **casos exitosos y fallidos**, observamos sin guiar, registramos límites y discutimos explicaciones alternativas. No debemos convertir un evento `recorrido_consultado` en prueba de que se entendió el contenido. También separamos la encuesta diagnóstica de las pruebas de la app: respuestas de intención no equivalen a comportamiento real.


### 73. ¿Qué responsabilidad ética implica recolectar datos de uso de personas reales?

Debemos informar qué medimos, pedir consentimiento, evitar información innecesaria, proteger archivos y permitir retirarse. Nuestra analítica no registra correo, contraseña ni GPS, y solo escribe si `medidor.activo=True`. Si exportamos archivos, los revisamos antes para no exponer datos. El historial de eventos tampoco debe publicarse sin revisión de privacidad.


### 74. ¿Qué harías si, después de una mejora, tu KPI principal empeora?

Verificaríamos primero que ambas muestras usaron las mismas tareas, versiones y condiciones; luego buscaríamos dónde aumentaron errores o tiempos. Si empeoró, revertiríamos o modificaríamos el cambio y probaríamos otra opción. **No esconderíamos el KPI negativo.** Un cambio estético no garantiza una mejora de usabilidad: para afirmarlo necesitamos comparar datos observados.


### 75. ¿Cómo se conectan la medición (RA3) con el diagnóstico (RA1) y el desarrollo (RA2) en tu proyecto?

**RA1** detectó incertidumbre de información en buses (17 encuestas); **RA2** produjo una app con mapa, rutas, avisos y un backend; **RA3** define si las personas pueden usar ese flujo mediante eventos y pruebas. La conexión es «necesidad → solución → evidencia de uso». Actualmente tenemos diagnóstico y desarrollo, pero nos falta completar el ciclo con participantes reales para validar resultados.


### 76. ¿Qué límites tiene tu medición actual? Sé honesto: qué no puedes afirmar con tus datos.

No podemos afirmar todavía un porcentaje real de éxito o mediana del test MJV, ni impacto social, retención de personas, eficacia para adultos mayores o precisión del GPS de buses. Tenemos encuesta **exploratoria de N=17**, pruebas técnicas de apertura de pantallas y un medidor preparado. El archivo de pruebas de usuarios está vacío. Tampoco existe seguimiento GPS compartido entre teléfonos.


## 9. Preguntas integradoras de defensa


### 77. Muéstrame un evento de tu aplicación y explica por qué está registrado ahí.

Mostraría `servicios/analitica.py → Registrador.registrar()`. Al entrar a Recorridos con consentimiento se registra `busqueda_iniciada`, con campos `id`, `sesion`, `evento`, `ts`, `pantalla='recorridos'` e `intento`. Es importante porque después `recorrido_consultado` trae ese mismo intento y `duracion_ms`. Para la defensa puedo **mostrar un ejemplo ilustrativo de estructura**, no atribuirlo a usuarios reales si no hay archivo de campo.


### 78. Si tuvieras que eliminar la mitad de tus eventos, ¿cuáles conservarías y por qué?

Conservaría prioritariamente `busqueda_iniciada` y `recorrido_consultado` (para tasa de éxito y tiempo), `error_ubicacion` (para problemas técnicos) y `aviso_publicado` (participación comunitaria); evaluaría conservar también `favorito_agregado`. Reduciría `pantalla_abierta` genérico u otros conteos menos vinculados al diagnóstico. La selección depende de la hipótesis y no del deseo de mostrar muchas estadísticas.


### 79. Calcula en vivo, con tus datos, uno de los KPIs que declaraste.

En la defensa abriría `docs/resultados_mjv/RESULTADOS.md` generado desde nuestro JSONL y explicaría `100 × consultas_exitosas / busquedas_iniciadas`. **No tenemos aún un valor empírico para calcular aquí.** Ejemplo de práctica: 7 consultas exitosas de 10 intentos = **70 %**, pero lo identificaría como simulación. Si hay 0 intentos, `resumen()` devuelve «Sin datos»; no inventaría éxito ni división por cero.


### 80. ¿Qué cambiarías de tu sistema de medición si el proyecto se usara durante un año?

Movería el archivo JSONL a `App.user_data_dir` en Android, aplicaría rotación y conservación, exportación controlada, separación por versión y cohortes con consentimiento si fuera necesaria. También agregaría monitoreo de pérdida de eventos, documentación de cambios en la definición de KPIs y revisión de acceso a datos. Nuestra solución actual sirve para pruebas breves, no para un año de uso a escala.


### 81. ¿Qué afirmaciones de tu informe se sostienen en datos y cuáles en opinión?

**Respaldado por evidencia:** 17 respuestas diagnósticas, porcentajes de necesidades declaradas, existencia de rutas/avisos/cuentas en código, diez pantallas abiertas en una prueba automatizada. **No medido todavía:** que nuestra interfaz sea fácil para todas las personas, que reduzca esperas, que los reportes sean correctos o que mejore la movilidad regional. Eso último son objetivos e hipótesis, no resultados demostrados.


### 82. ¿Cómo le explicarías a una persona no técnica qué mides y para qué sirve?

«Anotamos, sin tu nombre ni ubicación, si pudiste encontrar una ruta en la aplicación y cuánto te demoraste. Eso nos ayuda a hacerla más clara para las personas que viajan. Solo lo medimos si aceptas participar». Esta explicación evita términos como JSONL o KPI y deja claro el propósito y la voluntariedad.


### 83. ¿Qué preguntas sobre el uso de tu aplicación no puedes responder con los datos que registras?

No sabemos cuántas **personas únicas** vuelven tras varios días, en qué paso exacto abandonan una consulta, si comprendieron la ficha, si los datos de buses son correctos, ni cuánto retraso real evitaron. Tampoco podemos medir uso entre dispositivos solo con el JSONL. Necesitaríamos eventos adicionales, pruebas de comprensión y fuentes externas fiables, sin recolectar datos personales innecesarios.


### 84. Si empezaras la medición hoy otra vez, ¿qué harías distinto?

Definiría desde el inicio hipótesis y meta de consulta, una muestra variada, tareas idénticas con consentimiento y registro completo de fecha/versión. Prepararía la ruta segura de datos en Android, un evento de abandono y una exportación fácil. Realizaría una medición base **antes** de rediseñar y otra después para comparar. Así separaríamos percepciones del equipo de cambios respaldados por evidencia.


---

## Práctica rápida antes de la defensa

**Demostración A — Un evento real (si registramos uno con consentimiento).** Abrimos `servicios/analitica.py`, buscamos `Registrador.registrar()` y explicamos `id`, `sesion`, `evento`, `ts`, `intento` y `duracion_ms`. Luego vemos el JSONL del equipo **sin exhibir información innecesaria**.

**Demostración B — KPI.** Abrimos `resumen()` y explicamos la intersección entre intentos iniciados y exitosos. Si hay datos reales, ejecutamos `python tools/generar_resultados_mjv.py`, mostramos el numerador, denominador y resultado. Si no hay datos, explicamos el cálculo sin hacer pasar un ejemplo por evidencia.

**Demostración C — Arquitectura.** Señalamos un botón de `root.kv`, su callback en `main.py`, la solicitud en `ClienteApi`, el endpoint PHP y su tabla MySQL. Recordamos: **el mapa y los avisos funcionan con la API; el GPS del viaje todavía no se transmite como telemetría en vivo**.

**Demostración D — Qué no debemos exagerar.** La encuesta RA1 tuvo 17 personas, pero no es la prueba MJV de RA3. Abrir las diez pantallas en una prueba automatizada tampoco es una evaluación de usabilidad. No afirmamos que Android, el seguimiento colectivo o la retención estén validados sin pruebas correspondientes.

## Fórmulas que conviene recordar

- **Éxito de consulta:** `100 × intentos que llegan a Detalle / intentos iniciados`.
- **Tiempo de consulta:** mediana de `duracion_ms / 1000` para intentos completados.
- **Finalización de tareas:** `100 × tareas completadas / tareas iniciadas`, definiendo de antemano qué significa «completar».
- **Frecuencia de errores propuesta:** `100 × tareas con error / tareas iniciadas` (todavía no está automatizada así).
- **Retención D1 propuesta:** `100 × usuarios del día inicial que regresan al día siguiente / usuarios del día inicial` (no calculable con sesiones anónimas efímeras actuales).

## Fuente

Banco de preguntas E4 — TINF1119, 84 preguntas, profesor Cristian Iglesias Vera (documento facilitado al equipo). Respuestas fundamentadas en la implementación de nuestra rama final y su documentación disponible a fecha de revisión.