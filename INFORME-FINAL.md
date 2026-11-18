# Informe final — Proyecto Integrado EnRuta Ya!

**Instituto Tecnológico UC Temuco · Desarrollo Móvil (A+S) · TINF1119 · E4 · 2026**  
**Versión del proyecto que presentamos:** interfaz de `feature/diseno-v3-sobre-backend-final`, funcionalidades integradas desde `feature/Ajuste3-PLSFINAL` y preparación Android en `feature/apk-android-buildozer`.

> Elaboramos este informe como equipo a partir del código, la encuesta de diagnóstico y los registros de pruebas disponibles. Distinguimos entre funcionalidades implementadas, verificaciones técnicas y evaluación con personas. No atribuimos resultados a pruebas que todavía no cuentan con evidencia documentada.

## 1. Problema y diagnóstico de la comunidad (RA1)

Como equipo nos propusimos abordar la falta de información clara y oportuna sobre los buses interurbanos de La Araucanía. Nos interesó especialmente la incertidumbre que enfrentan los pasajeros al consultar un recorrido, saber si la micro viene llena o enterarse de un atraso.

Para fundamentar la idea aplicamos una encuesta en línea de **15 preguntas** y obtuvimos **17 respuestas** entre el **14 y el 28 de septiembre de 2026**. Encontramos que:

- **71 %** había tenido problemas con buses llenos.
- **76 %** quería consultar la ubicación del bus en un mapa.
- **59 %** pidió notificaciones sobre retrasos.
- **59 %** se informaba por experiencia o memoria y **35 %** preguntaba al conductor.
- La utilidad esperada de una aplicación de este tipo obtuvo una media de **4,7/5**.

Estos datos explican por qué priorizamos el mapa, el catálogo de recorridos y los avisos sobre ocupación y atrasos. La encuesta fue exploratoria y mayoritariamente respondida por jóvenes; reconocemos que no podemos extrapolar sus porcentajes a toda la región ni utilizarlos como prueba de eficacia del producto.

**Evidencia:** `FUNDAMENTACION-UX-UI.md`.

## 2. Solución implementada (RA2)

Desarrollamos una aplicación en **Python, Kivy y KivyMD** con un mapa interactivo basado en **Kivy Garden MapView y OpenStreetMap**. Organizamos el trabajo en vistas KV, un controlador principal y servicios para las funciones de negocio y la persistencia.

En la versión final integramos **PHP y MySQL como backend**. Nuestro flujo de datos es **app → API PHP → MySQL**. El backend gestiona cuentas por correo, sesiones, rutas, avisos y votaciones; permite que dos instalaciones consulten información del mismo servidor.

Las funciones principales que construimos son:

1. **Registro, login e invitado.** Las cuentas pueden entrar con correo y contraseña; como invitado se pueden realizar consultas limitadas.
2. **Inicio y Recorridos.** Se elige una localidad, se consultan líneas, sus datos referenciales y el detalle sobre mapa.
3. **Avisos.** Podemos publicar «Bus lleno», «Hay asientos», «Atrasado» y «Cambio de ruta». Los avisos son de usuarios y se sincronizan mediante la API.
4. **Votaciones y reputación.** Los usuarios registrados pueden evaluar recorridos y avisos. El servidor administra los puntos y el nivel.
5. **Compartir viaje.** Podemos elegir línea, indicar patente o agendar el viaje; el GPS se solicita con permiso y se usa localmente.
6. **Favoritas y preferencias.** Podemos marcar recorridos y personalizar el tema. Esas preferencias se guardan actualmente **en el dispositivo**, no en la base compartida.
7. **Panel administrativo.** Contamos con herramientas web para revisar usuarios, rutas, avisos y contadores.
8. **Conexión con caché.** Si falla internet, se muestran los datos guardados y se intenta sincronizar posteriormente.

Nuestra interfaz fue rediseñada conservando la lógica final del equipo. Se comprobó por automatización que las **10 pantallas** abren y permiten navegar en Linux/Xvfb y en varios tamaños. No confundimos esta prueba técnica con usabilidad de personas ni con validación Android.

**Limitación central:** todavía no publicamos posiciones GPS de buses para que otros pasajeros las sigan en vivo. Por eso no afirmamos que el prototipo ofrezca seguimiento en tiempo real ni estimaciones basadas en buses reales.

## 3. Metodología MJV App (RA3)

Para evaluar el uso de la aplicación adoptamos el ciclo **Medir → Jugar → Validar**. Primero definimos qué queremos descubrir, luego damos a una persona una tarea concreta y observamos su ejecución, y finalmente analizamos la evidencia para tomar una decisión de mejora.

**Hipótesis de trabajo:** un pasajero puede encontrar un recorrido y abrir su detalle sin demasiada dificultad utilizando nuestra pantalla Recorridos.

**Qué preparamos para medir:** instrumentamos el módulo `servicios/analitica.py`, que registra eventos de uso **solo si activamos previamente el consentimiento en Ajustes**. Los eventos locales se guardan en `data/analitica_eventos.jsonl`, uno por línea, con nombre del evento, identificador aleatorio de sesión y fecha/hora UTC. El intento de búsqueda tiene un ID propio para relacionar el inicio con el detalle abierto. No añadimos nombres, correos, contraseñas ni coordenadas.

**Prueba de tarea propuesta:** pedir a cada participante que abra Recorridos, identifique una línea y acceda a Detalle. Complementamos con guardar una favorita y publicar un aviso en un entorno controlado, sin confundirlo con información real para otros pasajeros.

**KPIs que programamos:**

- **Éxito de consulta:** `100 × consultas con detalle abierto / búsquedas iniciadas`.
- **Mediana de tiempo de consulta:** mediana de los segundos transcurridos entre `busqueda_iniciada` y `recorrido_consultado` para un mismo intento.

También contamos avisos publicados, favoritas agregadas y sesiones. Estas últimas son ejecuciones de la app, **no personas únicas**.

Con `python tools/generar_resultados_mjv.py` podemos producir el informe `docs/resultados_mjv/RESULTADOS.md` y un gráfico SVG basado únicamente en eventos registrados.

### Estado documentado de la medición (18-11-2026)

La instrumentación MJV está implementada y cuenta con pruebas automatizadas sobre el cálculo de indicadores, el consentimiento y el tratamiento de archivos de eventos. En `tests/test_analitica.py` incluimos casos con datos artificiales controlados para comprobar, por ejemplo, el cálculo de porcentajes, medianas y el comportamiento sin registros. **Estos casos son pruebas del software, no resultados obtenidos de pasajeros.**

El archivo `docs/REGISTRO-PRUEBAS-USUARIOS.csv` conserva únicamente los encabezados. En el repositorio revisado no hay una medición de campo documentada con participantes, fechas y ejecución del protocolo. Por lo tanto, los indicadores siguientes se presentan con su estado real:

| Indicador MJV | Forma de cálculo | Resultado documentado |
|---|---|---|
| Participantes de prueba con consentimiento | Total de códigos anónimos del registro | **Sin datos de campo** |
| Éxito de consulta | Consultas con detalle abierto / búsquedas iniciadas × 100 | **Sin datos de campo** |
| Tiempo para consultar un recorrido | Mediana de duración de intentos completados | **Sin datos de campo** |
| Persistencia de favoritas | Tareas que conservaron la favorita / tareas evaluadas × 100 | **Sin datos de campo** |
| Avisos enviados durante la prueba | Conteo de acciones verificadas en entorno de prueba | **Sin datos de campo** |

La encuesta diagnóstica con 17 respuestas sustenta la necesidad (RA1), pero no mide la facilidad de uso del prototipo (RA3). Conservar esta separación permite interpretar correctamente nuestras evidencias y evita presentar resultados simulados como observaciones reales.

### Procedimiento de validación preparado

Definimos el mismo recorrido de tareas para cada participante: abrir Recorridos y consultar un detalle; guardar una favorita, reiniciar y comprobar su persistencia en el mismo equipo; y publicar un aviso únicamente en un entorno controlado. Registraríamos el consentimiento antes de activar la analítica, el tiempo y cumplimiento de cada tarea, y observaciones anónimas en el CSV. Al concluir, desactivaríamos la medición y ejecutaríamos `python tools/generar_resultados_mjv.py` para calcular indicadores exclusivamente con eventos observados. El protocolo completo se encuentra en `docs/PROTOCOLO-MJV-APP.md`.

La realización de este procedimiento con personas sigue siendo una **limitación de la evaluación**, y no se presenta como una actividad ejecutada.

## 4. Resultados, análisis y propuestas de mejora

### 4.1 Resultados del diagnóstico inicial

Las **17 respuestas** a la encuesta, recogidas entre el 14 y el 28 de septiembre de 2026, muestran las necesidades que guiaron el proyecto: 71 % reportó dificultades con buses llenos; 76 % señaló interés por conocer la ubicación del bus en un mapa; y 59 % solicitó notificaciones sobre retrasos. La utilidad esperada fue de 4,7 sobre 5. La muestra es exploratoria y predominantemente joven, por lo que **estos resultados justifican decisiones de diseño, pero no representan a toda la comunidad**.

| Hallazgo respaldado por la encuesta | Decisión incorporada al prototipo | Alcance actual |
|---|---|---|
| Interés por la ubicación en el mapa | Mapa como elemento destacado y acceso a detalles de recorridos | Mapa de consulta; sin posiciones colectivas de buses en vivo |
| Problemas con buses llenos y atrasos | Avisos de ocupación, atraso y cambio de ruta | Reportes de usuarios, sujetos a disponibilidad y confiabilidad de la información |
| Uso de memoria y preguntas al conductor para informarse | Pantalla Recorridos con consulta centralizada | Información referencial, no garantía de horarios reales |

### 4.2 Validaciones técnicas y resultado Android

Revisamos la interfaz mediante automatización y capturas con `tools/verificar_interfaz.py`, que contempla ocho vistas de uso habitual, diferentes tamaños de ventana, tema claro y oscuro, y estados como formularios con errores. Las vistas `carga` y `detalle` también están declaradas en `root.kv`. **Este ejercicio técnico no sustituye una prueba de usabilidad ni certifica el funcionamiento de una APK instalada.**

Asimismo, preparamos pruebas de lógica y servicios en `tests/`, incluidas las pruebas del registrador MJV. El conjunto contiene casos con información artificial para verificar el código; no debe leerse como resultado de una evaluación con pasajeros.

En las pruebas Android observamos un problema de arranque: las APK compiladas por GitHub Actions y una prueba mediante Google Colab se instalaron, pero se cerraban al iniciarse. Con ADB Logcat identificamos, en una de las compilaciones, el error `ModuleNotFoundError: No module named 'materialyoucolor.dynamiccolor.color_spec'`. A partir del diagnóstico fijamos `materialyoucolor==3.0.3` en la configuración de compilación y los requisitos. **Al momento de redactar esta versión del informe no disponemos de una verificación en dispositivo que confirme que la corrección ya permite abrir y usar toda la aplicación.** No confundimos compilación exitosa con funcionamiento validado.

### 4.3 Interpretación y decisiones de mejora

A partir de las evidencias disponibles, priorizamos las siguientes líneas de trabajo, separando su justificación de su validación posterior:

1. **Estabilizar el arranque de Android (prioridad alta).** La aplicación debe abrir en un teléfono real antes de evaluar sus funciones. La evidencia es el cierre reproducido y el registro de ADB. El criterio de verificación será abrir la APK, llegar al login, navegar por las pantallas y comprobar funciones esenciales sin cierre.
2. **Facilitar la consulta de recorridos (prioridad alta).** La encuesta muestra interés en acceder rápidamente a información de buses. Mantendremos visible la opción Recorridos y revisaremos el selector de localidad, los filtros y el paso a Detalle. Su eficacia deberá medirse con tareas de usuarios, tasa de éxito y mediana de tiempo; todavía no contamos con esa comparación.
3. **Diferenciar datos referenciales de avisos comunitarios (prioridad media).** Dado que la aplicación no sigue buses reales en vivo, es importante no presentar tiempos o posiciones estimadas como confirmadas. Revisaremos textos de orientación, origen del aviso y vigencia de la información, y comprobaremos su comprensión con participantes.
4. **Revisar accesibilidad y legibilidad (prioridad media).** La encuesta no constituye una validación con adultos mayores ni con lectores de pantalla. Una prueba posterior deberá observar legibilidad, tamaño de controles y facilidad de navegación con perfiles diversos.

### 4.4 Límites de los resultados

No podemos afirmar porcentajes de éxito MJV, mejoras de tiempo, satisfacción de usuarios reales, confiabilidad estadística de avisos ni impacto regional porque **no se registró evidencia de campo suficiente**. Tampoco afirmamos haber validado seguimiento GPS colectivo en tiempo real. Presentamos como resultado confirmado el diagnóstico exploratorio, el trabajo de implementación y las verificaciones técnicas descritas; el resto permanece como hipótesis o criterio de prueba.

## 5. Ética, accesibilidad y uso responsable de herramientas (RA4)

Nos preocupamos de que el GPS requiera un permiso del usuario y de que nuestro módulo de medición no registre datos personales directos. Los datos de uso se recopilan solo con consentimiento, y debemos evitar publicar registros crudos sin autorización.

La autenticación remota usa contraseñas hasheadas en PHP y sesiones gestionadas por la API. Sin embargo, **la seguridad de una aplicación real requiere revisión continua**: reglas de acceso, administración de credenciales, protección contra reportes falsos, caducidad y moderación.

Diseñamos pantallas con texto, iconos y modos claro/oscuro para facilitar la navegación. Reconocemos que **no hemos documentado aún pruebas de lector de pantalla, accesibilidad con adultos mayores o barreras concretas observadas por participantes**. La muestra diagnóstica tiene un fuerte sesgo hacia jóvenes.

Durante el desarrollo utilizamos herramientas de apoyo como Claude, ChatGPT/Codex y Figma para obtener ideas, revisar problemas y agilizar tareas. Somos responsables de revisar el resultado, comprobarlo con el código y poder explicarlo en la defensa; dejamos una declaración transparente en `USO_IA.md`.

## 6. Evaluación de nuestro trabajo y límites

Consideramos que el avance principal fue pasar de una interfaz demostrativa y datos locales a una aplicación que separa la interfaz Kivy de una **API PHP conectada a MySQL**, con cuentas, avisos, votos y herramientas administrativas.

Aprendimos que tener una funcionalidad escrita no significa que esté validada. Una pantalla que abre correctamente no prueba que una persona pueda cumplir su tarea; contar reportes no demuestra que sean confiables; y usar GPS local no equivale a compartir un bus en vivo.

### Síntesis de cumplimiento y límites

| Ámbito | Resultado que podemos respaldar | Límite reconocido |
|---|---|---|
| RA1 — Diagnóstico | Encuesta exploratoria de 17 respuestas y fundamentación UX/UI | Muestra pequeña, no representativa de la región |
| RA2 — Solución | Interfaz Kivy/KivyMD, recorridos, mapas, avisos, autenticación y API PHP/MySQL implementados en el repositorio | Sin seguimiento remoto de buses en vivo; APK aún sin apertura confirmada tras la última corrección |
| RA3 — MJV App | Protocolo, instrumentación, fórmulas y pruebas automatizadas de analítica | Sin participantes ni indicadores de campo documentados |
| RA4 — Ética y accesibilidad | Consentimiento de analítica, permisos de ubicación, separación de credenciales y declaración de uso de IA | Sin auditoría integral de seguridad ni pruebas formales de accesibilidad con usuarios |

Nuestros siguientes criterios para considerar la entrega validada son: registrar tareas MJV con participantes y consentimiento, generar un informe basado en eventos reales, documentar dos mejoras contrastables, confirmar el funcionamiento Android mediante instalación y registros de prueba, y revisar casos de conectividad y seguridad. Hasta disponer de estas evidencias no marcaremos dichos criterios como cumplidos.

## 7. Referencias y evidencias

- `FUNDAMENTACION-UX-UI.md`: instrumento y resultados exploratorios de 17 respuestas.
- `main.py`, `root.kv`, `componentes.kv`, `tema.py`: implementación principal.
- `servicios/api_cliente.py` y `backend/api/index.php`: conexión a backend.
- `backend/sql/enruta_schema.sql`: modelo MySQL de diez tablas.
- `servicios/analitica.py` y `tools/generar_resultados_mjv.py`: registro y KPIs.
- `docs/PROTOCOLO-MJV-APP.md` y `docs/REGISTRO-PRUEBAS-USUARIOS.csv`: protocolo y planilla de evaluación.
- `USO_IA.md`: declaración del uso de herramientas de apoyo.
- `docs/GUIA-DEFENSA-84-PREGUNTAS.md`: respuestas y explicaciones para preparar la defensa individual basada en el código.

**Declaración final de evidencia:** dejamos documentados los hallazgos de la encuesta, la implementación, las verificaciones técnicas, el diagnóstico de Android y el protocolo MJV. Las mediciones con participantes y la validación final de APK quedan expresamente identificadas como no verificadas. Este informe no atribuye resultados inexistentes a nuestro equipo.
