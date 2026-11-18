# Informe final — Proyecto Integrado EnRuta Ya!

**Instituto Tecnológico UC Temuco · Desarrollo Móvil (A+S) · TINF1119 · E4 · 2026**  
**Versión del proyecto que presentamos:** interfaz de `feature/diseno-v3-sobre-backend-final` y funcionalidades integradas desde `feature/Ajuste3-PLSFINAL`.

> Redactamos este informe como equipo, usando lo que efectivamente aparece en el proyecto y en nuestra encuesta. **Aún debemos incorporar las pruebas con personas, el periodo de medición y los resultados MJV reales.** No presentamos esas evidencias como completadas.

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

En la versión final integramos **PHP y MySQL como backend**, no Firebase. Nuestro flujo de datos es **app → API PHP → MySQL**. El backend gestiona cuentas por correo, sesiones, rutas, avisos y votaciones; permite que dos instalaciones consulten información del mismo servidor.

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

### Estado de la medición

A fecha de esta revisión, la planilla `docs/REGISTRO-PRUEBAS-USUARIOS.csv` contiene **solo el encabezado**, y no tenemos documentación verificable sobre fecha de inicio/fin, cantidad de participantes del test MJV, tareas efectivamente realizadas ni resultados de campo.

Por eso **no declaramos todavía un porcentaje de éxito real, una mediana observada ni una mejora validada**. La encuesta diagnóstica de 17 respuestas es una evidencia de RA1 y **no reemplaza** las pruebas de RA3.

## 4. Resultados, análisis y propuestas de mejora

La evidencia cuantitativa disponible hoy corresponde al **diagnóstico inicial**; no debemos mezclarla con resultados de uso.

**Qué obtuvimos del diagnóstico:** la necesidad de consultar ubicación, estados de ocupación y retrasos está justificada por las respuestas de la encuesta. Con esa información priorizamos mapa, reportes y recorridos en la navegación.

**Qué falta medir para concluir sobre el prototipo:** porcentaje de participantes que abren correctamente el detalle, mediana de tiempo de consulta, persistencia de favoritas y obstáculos de navegación detectados durante las pruebas.

Tenemos dos **hipótesis de mejora**, que deberán validarse después de registrar tareas reales:

1. **Acceso más rápido a recorridos.** Si detectamos demoras o búsquedas fallidas, podemos mejorar el selector de destino, la visibilidad del listado y los filtros; luego repetimos la misma tarea y comparamos.
2. **Claridad de información comunitaria.** Si los participantes confunden los avisos o una duración referencial con una predicción oficial, podemos reforzar etiquetas de origen, vigencia y estado de verificación; luego evaluamos si la confusión disminuye.

Estas propuestas no son conclusiones medidas. Para completar esta sección antes de la defensa necesitamos: periodo, participantes, resultados del generador, gráfico, observaciones por tarea, al menos dos decisiones apoyadas en datos y sus limitaciones.

## 5. Ética, accesibilidad y uso responsable de herramientas (RA4)

Nos preocupamos de que el GPS requiera un permiso del usuario y de que nuestro módulo de medición no registre datos personales directos. Los datos de uso se recopilan solo con consentimiento, y debemos evitar publicar registros crudos sin autorización.

La autenticación remota usa contraseñas hasheadas en PHP y sesiones gestionadas por la API. Sin embargo, **la seguridad de una aplicación real requiere revisión continua**: reglas de acceso, administración de credenciales, protección contra reportes falsos, caducidad y moderación.

Diseñamos pantallas con texto, iconos y modos claro/oscuro para facilitar la navegación. Reconocemos que **no hemos documentado aún pruebas de lector de pantalla, accesibilidad con adultos mayores o barreras concretas observadas por participantes**. La muestra diagnóstica tiene un fuerte sesgo hacia jóvenes.

Durante el desarrollo utilizamos herramientas de apoyo como Claude, ChatGPT/Codex y Figma para obtener ideas, revisar problemas y agilizar tareas. Somos responsables de revisar el resultado, comprobarlo con el código y poder explicarlo en la defensa; dejamos una declaración transparente en `USO_IA.md`.

## 6. Evaluación de nuestro trabajo y límites

Consideramos que el avance principal fue pasar de una interfaz demostrativa y datos locales a una aplicación que separa la interfaz Kivy de una **API PHP conectada a MySQL**, con cuentas, avisos, votos y herramientas administrativas.

Aprendimos que tener una funcionalidad escrita no significa que esté validada. Una pantalla que abre correctamente no prueba que una persona pueda cumplir su tarea; contar reportes no demuestra que sean confiables; y usar GPS local no equivale a compartir un bus en vivo.

**Trabajo pendiente verificable:** completar y documentar las pruebas MJV; obtener gráficos basados en datos; ensayar la defensa individual; finalizar prueba Android por el integrante responsable; y comprobar casos de conectividad/seguridad antes de entregar.

## 7. Referencias y evidencias

- `FUNDAMENTACION-UX-UI.md`: instrumento y resultados exploratorios de 17 respuestas.
- `main.py`, `root.kv`, `componentes.kv`, `tema.py`: implementación principal.
- `servicios/api_cliente.py` y `backend/api/index.php`: conexión a backend.
- `backend/sql/enruta_schema.sql`: modelo MySQL de diez tablas.
- `servicios/analitica.py` y `tools/generar_resultados_mjv.py`: registro y KPIs.
- `docs/PROTOCOLO-MJV-APP.md` y `docs/REGISTRO-PRUEBAS-USUARIOS.csv`: protocolo y planilla de evaluación.
- `USO_IA.md`: declaración del uso de herramientas de apoyo.
- `docs/GUIA-DEFENSA-84-PREGUNTAS.md`: respuestas y explicaciones para preparar la defensa individual basada en el código.

**Nota de cierre:** el texto narrativo del informe está actualizado; **la sección de resultados experimentales requiere evidencia que solo podemos obtener realizando las pruebas**. No la reemplazamos por cifras ficticias.
