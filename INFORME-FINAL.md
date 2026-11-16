# Informe Final — Proyecto Integrado EnRuta Ya!

**Desarrollo Móvil (A+S), TINF1119 · Evaluación E4 · 2026**

> Documento de entrega preparado para completar con **datos reales**
> de medición. No confundir encuesta diagnóstica con resultados de uso.

## 1. Introducción y problema social (RA1 · 20%)

Los viajes interurbanos en La Araucanía presentan incertidumbre sobre
horarios, recorridos, ocupación y atrasos. El equipo aplicó una encuesta
en línea de 15 preguntas y 17 respuestas entre el 14 y 28 de
septiembre de 2026 (ver `FUNDAMENTACION-UX-UI.md`).

El 71% reportó problemas por buses llenos; el 59% solicitó alertas
por atrasos y el 76% señaló la ubicación en el mapa como información
deseada. La muestra es pequeña, mayoritariamente de estudiantes
jóvenes, por lo que los hallazgos son exploratorios, no representativos
de toda la región.

**Decisiones de solución:**
- Mapa de Inicio: consulta visual de localidades y recorridos.
- Recorridos: acceso centralizado a datos referenciales.
- Avisos: reportes de ocupación, atrasos y desvíos.
- Compartir: control explícito del GPS local y consentimiento.
- Favoritos y notificaciones: acceso rápido a rutas de interés.

## 2. Solución desarrollada (RA2 · 25%)

Se implementó un prototipo en Python, Kivy y KivyMD, con MapView y
OpenStreetMap. Incluye registro/login, perfiles, favoritos,
navegación, persistencia JSON, avisos, ajustes y medición MJV App\nexportada fuera de la interfaz del pasajero.

La estructura separa:
- Vistas: `root.kv`, `componentes.kv`, `tema.py`.
- Controladores: `main.py` y sus callbacks de pantalla.
- Modelo/servicios: rutas, autenticación, persistencia,
  avisos, GPS, analítica y Firebase opcional.

La sincronización de avisos de la comunidad se inicia\nautomáticamente después de acceder mediante correo y contraseña en\nFirebase Authentication. Requiere activar el proveedor y publicar las\nreglas en el proyecto real; está pendiente de validación entre dos\ninstancias. No existe GPS colectivo entre dispositivos ni servidor de
localización en vivo. Los marcadores de buses y ETA son demos.

**Evidencia de demo a adjuntar:** [CAPTURA 1: Login y Inicio],
[CAPTURA 2: detalle de ruta y favorita],
[CAPTURA 3: persistencia tras reiniciar],
[CAPTURA 4: resultados MJV App generados fuera de la interfaz].

## 3. Método MJV App, KPIs y periodo (RA3 · 20%)

Se instrumentaron eventos locales con identificadores de sesión
aleatorios, marca de tiempo UTC y referencias de intento de búsqueda.
No se recopilan coordenadas, contraseñas ni nombres de usuarios.\nLa medición está desactivada por defecto y se activa manualmente,\ncon consentimiento, en Ajustes → Privacidad → Ayudar a mejorar la app.

KPIs implementados:
1. Éxito de consulta de recorrido = consultas con detalle /
   búsquedas iniciadas × 100.
2. Mediana del tiempo de consulta, desde entrar a Recorridos
   hasta abrir un detalle.

También se cuentan avisos publicados y favoritas agregadas.
Ver metodología, escenarios y limitaciones en
`docs/PROTOCOLO-MJV-APP.md`.

**Periodo real de pruebas:** [PENDIENTE DE REGISTRAR].
**Participantes voluntarios:** [PENDIENTE DE REGISTRAR].
**Contexto y consentimiento:** [PENDIENTE].

## 4. Resultados, gráficos y mejoras (RA3 · 20%)

Los resultados deben salir de la ejecución real de los escenarios.
Generar con:

~~~powershell
python tools/generar_resultados_mjv.py
~~~

**Adjuntar aquí, tras las pruebas:**
- `docs/resultados_mjv/RESULTADOS.md`
- Gráfico `docs/resultados_mjv/grafico_eventos.svg`
- Resultados manuales (persistencia de favoritas, barreras observadas).

**Hallazgo medido 1:** [PENDIENTE]
**Mejora fundamentada 1:** [PENDIENTE]
**Hallazgo medido 2:** [PENDIENTE]
**Mejora fundamentada 2:** [PENDIENTE]
**Priorización por impacto/esfuerzo:** [PENDIENTE]

No inventar estadísticas ni afirmar que las hipótesis son resultados.

## 5. Ética, accesibilidad e IA (RA4 · 15%)

**Privacidad:** GPS solo tras acción/consentimiento; no se transmite
posición a Firebase. Los eventos de medición son anónimos por sesión
de aplicación. Se usan hashes para contraseñas locales. Se evita
mezclar credenciales de backend con el cliente móvil.

**Accesibilidad:** navegación clara con etiquetas, pantalla diseñada
para teléfonos, tema claro/oscuro. Pendiente prueba con lector de
pantalla, distintos tamaños y usuarios mayores; la encuesta original
tiene sesgo hacia personas jóvenes.

**Sesgos y confiabilidad:** los horarios y buses son de demostración,
no oficiales. Avisos comunitarios pueden ser erróneos o
malintencionados, por lo que para un despliegue real harían falta
moderación y controles de abuso.

**Uso de IA:** se utilizaron asistentes de programación y diseño;
declarar con precisión qué utilizó cada integrante, cómo se validó
el código y cuáles decisiones tomó el equipo. Actualizar `USO_IA.md`.

**Reflexión final:** EnRuta Ya! busca reducir la incertidumbre de los
pasajeros, pero para prestar información confiable a personas
reales necesita validación, accesibilidad y protección de datos
superiores a las exigidas a un prototipo de curso.

## 6. Conclusiones y trabajo futuro

El prototipo demuestra navegación y persistencia locales,
organización visual y medición de uso. Para producción se requiere
un backend de ubicación temporal con permisos y vencimiento,
confirmación de recorridos por operadores y pruebas de campo.

## 7. Referencias y evidencias
- `FUNDAMENTACION-UX-UI.md` — encuesta y hallazgos.
- `README.md` — instalación.
- `DOCUMENTATION.md` — arquitectura.
- `docs/PROTOCOLO-MJV-APP.md` — metodología y KPIs.
- `USO_IA.md` — declaración de asistentes.
- `firebase/README.md` — sincronización opcional.
- Código y commits del repositorio GitHub.
