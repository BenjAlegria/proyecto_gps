# DOCUMENTATION — EnRuta Ya! · Evaluación E4

**Asignatura:** Desarrollo Móvil (A+S), TINF1119 · **Versión documentada:** `feature/diseno-v3-sobre-backend-final`.

## 1. Objetivo y alcance

Diseñamos EnRuta Ya! para disminuir la incertidumbre de quienes viajan en buses interurbanos de La Araucanía. Basamos las decisiones iniciales en una encuesta exploratoria de **17 personas** (14–28 de septiembre de 2026): 71 % señaló problemas con buses llenos y 76 % solicitó ubicación del bus en mapa. La encuesta diagnostica necesidades, **no demuestra que nuestra aplicación las haya resuelto**.

Nuestro prototipo permite consultar rutas, registrar y votar avisos comunitarios, iniciar una sesión local de GPS y administrar la cuenta. **No tenemos ubicación de buses compartida en vivo** ni horarios verificados oficialmente.

## 2. Arquitectura: vistas, control y servicios

Usamos **Python 3.10, Kivy 2.3.1, KivyMD 2.0.0, MapView y OpenStreetMap**. Organizamos responsabilidades de forma **similar a MVC**, sin afirmar un MVC estricto:

| Capa | Archivos | Lo que hacemos |
|---|---|---|
| Vista | `root.kv`, `componentes.kv`, `tema.py` | Definimos widgets, pantallas, tarjetas, colores, tamaños e identificadores `id:` |
| Controlador principal | `main.py` — `InterurbanoApp` | Respondemos a botones, validamos flujos, actualizamos pantalla y coordinamos servicios/hilos |
| Cliente de datos | `servicios/api_cliente.py` — `ClienteApi` | Realizamos solicitudes HTTP JSON, mantenemos caché y reenviamos acciones pendientes |
| Backend / lógica y seguridad | `backend/api/index.php` | Aplicamos reglas de acceso, validamos peticiones y consultamos MySQL con sentencias preparadas |
| Modelo de persistencia | `backend/sql/enruta_schema.sql` | Estructura de usuarios, recorridos, reportes, votos, viajes, reputación y eventos |
| Datos del dispositivo | `servicios/almacenamiento.py` y caché del cliente | Persistimos preferencias y la última información disponible |
| Analítica | `servicios/analitica.py` y `tools/generar_resultados_mjv.py` | Instrumentamos eventos consentidos y calculamos indicadores reproducibles |

**Flujo de ejemplo:**

1. Tocamos «Recorridos» en `root.kv`; el evento activa `app.cambiar_pantalla("recorridos")`.
2. `main.py` solicita al cliente las rutas; `ClienteApi` lee caché y consulta `?r=recorridos`.
3. La API PHP consulta MySQL y devuelve JSON; el controlador lo transforma y actualiza las tarjetas.
4. Al abrir Detalle, recuperamos información y avisos, y podemos votar con una cuenta registrada.

## 3. Qué queda en MySQL y qué queda local

**MySQL tiene diez tablas** en `backend/sql/enruta_schema.sql`: `usuarios`, `sesiones`, `recorridos`, `recorrido_puntos`, `votos_recorrido`, `avisos`, `votos_aviso`, `viajes`, `puntos_movimientos` y `eventos`.

- Gestionamos cuentas en `usuarios`; guardamos `clave_hash`, nunca contraseñas en claro.
- Conservamos hashes de tokens de sesión en `sesiones`; el cliente envía el token por el encabezado `X-Token`.
- Guardamos rutas y sus puntos geográficos en `recorridos` y `recorrido_puntos`.
- Los avisos y votos quedan asociados a usuarios/recorridos; usamos IDs de aviso para evitar duplicar publicaciones al reintentar.
- Registramos viajes y movimientos de puntos para el sistema de reputación.
- La tabla `eventos` recibe únicamente ciertos tipos de acciones anónimas permitidas por la API.

En el dispositivo dejamos `cache_api.json` dentro de `App.user_data_dir` a través de `ClienteApi`: últimas rutas, avisos, token y cola. Guardamos otras preferencias y favoritas mediante `servicios/almacenamiento.py` en JSON local por usuario; **esas preferencias no se comparten automáticamente entre celulares**. No llamamos Firebase a esta implementación final.

## 4. Autenticación, concurrencia y sincronización

El registro y login se hacen mediante `auth_registro` y `auth_login` en PHP. Validamos correo y contraseña; PHP utiliza `password_hash()` y `password_verify()`. Las sesiones tienen token generado por el servidor y este guarda un hash SHA-256 del token.

Cuando abrimos la app, mostramos los datos de la caché, intentamos conectarnos al servidor y programamos sincronización. `main.py → sincronizar()` coordina `ClienteApi.vaciar_cola()`, `recorridos()`, `avisos()` y, si corresponde, `perfil()`; utiliza `_en_hilo()` y `Clock.schedule_once()` para actualizar los widgets sin bloquear la interfaz. La sincronización periódica está programada aproximadamente **cada 45 segundos**. La caché offline no significa que todos los datos estén en tiempo real.

Si una acción se inicia sin conexión, las operaciones compatibles pueden quedar en una **cola local** y reenviarse después. Algunas peticiones pueden fallar por permisos o reglas y no deben presentarse como publicadas hasta que el servidor las acepte.

## 5. GPS y límites de información

Integramos `plyer.gps`, MapView y mecanismos de permiso/consentimiento. En Compartir elegimos línea e identificamos un bus con patente o viaje agendado; el GPS obtenido se utiliza para mostrar nuestra posición y el tramo restante. En `main.py → iniciar_compartir()` todavía existe una tarea pendiente para enviar posiciones GPS al servidor. **No almacenamos ni compartimos ubicación en vivo con otros pasajeros**.

Los estados de bus lleno, asientos, atraso y desvío sí pueden reportarse por la API y ser consultados desde otras instalaciones. Son aportes comunitarios sujetos a errores o abuso; no los presentamos como información oficial.

## 6. Medición MJV: anatomía del evento

Implementamos un módulo propio en `servicios/analitica.py`, clase `Registrador`. Con consentimiento activado en **Ajustes → Ayudar a mejorar la app**, los eventos locales se registran como JSON Lines en `data/analitica_eventos.jsonl`. Cada evento tiene:

| Campo | Para qué lo usamos |
|---|---|
| `id` | Identificador único del evento, generado con `uuid.uuid4().hex` |
| `sesion` | Identificador aleatorio de una ejecución; **no identifica a una persona** |
| `evento` | Nombre estable, p. ej. `busqueda_iniciada` |
| `ts` | Fecha y hora UTC ISO 8601 |
| `pantalla` | Contexto opcional, limitado a pantallas conocidas |
| `intento` | Relaciona el inicio de una consulta con su finalización |
| `duracion_ms` | Tiempo de la consulta en milisegundos, cuando corresponde |

Ejemplo **ilustrativo**, no obtenido de una sesión real:

```json
{"id":"8c1e2d...","sesion":"4b5a6d...","evento":"busqueda_iniciada","ts":"2026-11-17T15:00:00+00:00","pantalla":"recorridos","intento":"abc123..."}
```

No registramos coordenadas, correos ni contraseñas. Controlamos tipos de eventos permitidos y usamos `threading.Lock` para evitar escrituras simultáneas. Abrimos el archivo con `open(..., "a", encoding="utf-8")`, escribiendo **un JSON por línea**.

Para medir la consulta, `InterurbanoApp.cambiar_pantalla("recorridos")` llama a `Registrador.iniciar_busqueda()`, que guarda el evento y el instante `time.monotonic()`. Cuando el usuario abre un detalle, `mostrar_detalle()` llama a `completar_busqueda()`, calcula la duración y registra `recorrido_consultado` usando el mismo `intento`.

**No confundimos los dos registros de analítica:**
- **Local (`analitica_eventos.jsonl`)**: datos suficientes para relacionar intentos y medir duración. Aquí calculamos nuestros KPIs de búsqueda.
- **Servidor (`backend/api/index.php?r=evento`)**: `main.py → _medir()` también intenta enviar `tipo` y un ID aleatorio de sesión de 16 caracteres a la tabla `eventos`, si hay consentimiento. La API solo acepta tipos listados en `EVENTOS_OK` y almacena `tipo, sesion, creado_en`. **No envía `intento` ni `duracion_ms`; por tanto no permite reconstruir por sí sola el KPI de tiempo de búsqueda.** Si el servidor no acepta un tipo o falla la red, ese envío se descarta.

## 7. KPIs que podemos defender

El cálculo está en `servicios/analitica.py → resumen(eventos)`, y su exportación en `tools/generar_resultados_mjv.py`.

**KPI principal: éxito en consulta de recorrido**

```text
100 × (intentos de búsqueda con detalle abierto / intentos iniciados)
```

Solo contamos el mismo `intento` en ambos conjuntos. Si no hubo intentos, devolvemos `None` («Sin datos») en lugar de presentar 0 % como resultado.

**KPI complementario: mediana del tiempo de consulta**

Tomamos `duracion_ms / 1000` de los intentos completados y calculamos `statistics.median()`. Usamos la mediana para reducir el efecto de tiempos atípicos.

Contamos además sesiones de ejecución, reportes publicados y favoritas agregadas; **son métricas descriptivas**, no necesariamente KPIs de impacto. No hemos definido todavía una meta observada ni una cohorte de personas que permita afirmar retención.

## 8. Validación, privacidad y reproducibilidad

El procedimiento propuesto para pruebas con voluntarios se encuentra en `docs/PROTOCOLO-MJV-APP.md`. Nuestra planilla `docs/REGISTRO-PRUEBAS-USUARIOS.csv` **solo contiene encabezados** a la fecha de esta actualización. No incluimos números ficticios en el informe.

Para obtener resultados reproducibles desde el JSONL real ejecutamos:

```powershell
python tools/generar_resultados_mjv.py
```

El programa genera `RESULTADOS.md` y `grafico_eventos.svg` dentro de `docs/resultados_mjv/`. Si no se registran búsquedas, el informe lo señala explícitamente.

**Pruebas comprobadas:** el rediseño de las diez pantallas se construyó y navegó en Linux con pantalla virtual (Xvfb), probado en tamaños 320×568, 390×844 y 844×390, tanto claro como oscuro. No equivale a validación humana ni a funcionamiento Android certificado. La suite automatizada anterior incluye tests de Firebase y de versiones previas; requiere actualización antes de considerar validada toda la rama final.

**Limitación en Android:** la caché de `ClienteApi` usa `user_data_dir`, pero el JSONL de analítica todavía se define desde `config.DATA_DIR` dentro del proyecto; debemos revisar esa ruta y su escritura en APK antes de confiar en mediciones móviles.

## 9. Seguridad, ética y uso de IA

Protegemos contraseñas en PHP mediante hash, exigimos token para acciones de cuentas y utilizamos consultas parametrizadas para los accesos a MySQL. El panel web comprueba sesiones de administrador y formularios con protección CSRF. No almacenamos claves de MySQL dentro de la app.

Pedimos consentimiento antes de medir o utilizar GPS. El hecho de que un evento no tenga nombre o correo **no garantiza anonimato absoluto**: las sesiones y el transporte de datos también requieren una revisión de privacidad. No debemos subir a Git registros crudos de personas voluntarias.

En `USO_IA.md` declaramos el apoyo de herramientas de IA durante desarrollo y documentación. Los cambios de código y la interpretación académica deben revisarse por nosotros y ser defendibles sin depender de esas herramientas.

## 10. Pendientes técnicos conocidos

1. Seguimiento GPS de buses en vivo entre dispositivos.
2. Sincronización de favoritas/preferencias entre equipos.
3. Prueba Android/APK a cargo de un integrante; comprobar permisos de ubicación y ruta de analítica.
4. Actualizar o aislar pruebas de la arquitectura antigua Firebase.
5. Validar accesibilidad/usabilidad con participantes y obtener resultados MJV reales.
6. Verificar configuración del servidor y evitar credenciales expuestas en ramas/historial antiguos.
