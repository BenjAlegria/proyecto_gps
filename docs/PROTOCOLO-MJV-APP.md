# Protocolo MJV App — EnRuta Ya! (E4)

## Nuestro propósito

Queremos comprobar si una persona puede encontrar un recorrido, abrir su detalle y guardar información útil en EnRuta Ya! sin que tengamos que explicarle cada botón. Nos interesa la **usabilidad** de ese flujo, no demostrar aún seguimiento GPS en vivo.

## Método Medir → Jugar → Validar

1. **Medir:** definimos una pregunta, la tarea y el indicador antes de invitar a participantes. Por ejemplo: «¿Con qué frecuencia se llega al detalle del recorrido después de abrir Recorridos?».
2. **Jugar:** solicitamos que la persona complete el recorrido de prueba en condiciones conocidas. Registramos eventos y anotamos obstáculos; no guiamos de forma que alteremos el resultado.
3. **Validar:** calculamos el indicador, revisamos observaciones, contrastamos con la hipótesis y decidimos conservar, modificar o volver a probar. Después repetimos el ciclo.

## Requisitos éticos y preparación

**Antes de cada participante** explicamos qué vamos a medir, para qué se utilizará, que su colaboración es voluntaria y que puede detenerse. Pedimos consentimiento explícito. En Ajustes activamos **«Ayudar a mejorar la app»**, que habilita el registro local; al terminar lo desactivamos. Sin consentimiento no registramos resultados de esa persona.

- No solicitamos ni guardamos nombre, correo, contraseña ni coordenadas GPS en la planilla de estudio.
- Usamos códigos anónimos (`P01`, `P02`…), no identificadores personales.
- Si publicamos un aviso como prueba, usamos un entorno controlado y no hacemos creer a otros pasajeros que es un reporte real de transporte.
- Evitamos mezclar datos de distintas pruebas: respaldamos el JSONL previo, identificamos versión/commit y comenzamos cada sesión de forma documentada.
- Por seguridad no subimos `data/analitica_eventos.jsonl` crudo a un repositorio público.
- La tabla MySQL `eventos` recibe solo ciertos eventos simplificados; **el cálculo local de búsqueda necesita el archivo JSONL**, porque allí están `intento` y `duracion_ms`.

## Instrumentos ya preparados

- **Automático:** `servicios/analitica.py` escribe `data/analitica_eventos.jsonl` (JSON Lines).
- **Manual:** `docs/REGISTRO-PRUEBAS-USUARIOS.csv` permite registrar código, fecha, consentimiento, éxito/tiempo de tarea, persistencia de favorita, reporte y observaciones.
- **Análisis:** `servicios/analitica.py → resumen()` calcula las métricas.
- **Exportación:** `python tools/generar_resultados_mjv.py` genera `docs/resultados_mjv/RESULTADOS.md` y `grafico_eventos.svg`.

**Advertencia Android:** el JSONL se crea usando `config.DATA_DIR`, que apunta al directorio del proyecto. Esa ruta debe verificarse en APK; el uso de `App.user_data_dir` para ese archivo es una mejora técnica pendiente.

## Escenarios para las pruebas

**A. Consulta del recorrido (KPI principal).** Pedimos: «Abre Recorridos, elige una ruta de la lista y revisa su detalle». Anotamos si lo logra, cuánto tarda y qué dificultades presenta. La entrada a Recorridos genera `busqueda_iniciada`; al abrir Detalle se genera `recorrido_consultado` con el mismo ID `intento` y una duración.

**B. Persistencia de favorita.** Pedimos guardar la ruta, cerrar y volver a abrir la aplicación en el **mismo dispositivo**, y comprobar si aparece en Perfil. No debemos inferir que la favorita se sincroniza entre teléfonos.

**C. Reporte comunitario.** En una instalación de pruebas pedimos elegir una línea y enviar «Bus lleno» o «Atrasado», y observamos su aparición en Avisos. Confirmamos si el servidor lo aceptó, sin producir alertas reales engañosas.

**D. Observación transversal.** Anotamos dudas de navegación, confusión entre datos referenciales y avisos, tamaño de controles y dificultad para entender los mensajes. No necesitamos recolectar datos identificatorios para hacerlo.

## Indicadores y fórmulas

| Indicador | Fórmula | Qué podemos interpretar |
|---|---|---|
| **Éxito de consulta (%)** | `100 × intentos con recorrido_consultado / intentos con busqueda_iniciada` | Frecuencia de apertura exitosa del detalle |
| **Tiempo de consulta (s)** | `mediana(duracion_ms / 1000)` para intentos completados | Rapidez del flujo entre Recorridos y Detalle |
| **Persistencia de favorita (%)** | `100 × tareas B con favorita conservada / tareas B completadas` | Funcionamiento de guardado local en la prueba |
| **Reportes creados** | Conteo de `aviso_publicado` | Actividad; no demuestra veracidad ni utilidad del reporte |

La «consulta exitosa» significa **abrir Detalle**, no demostrar que se comprendió la información. No llamamos personas únicas a las sesiones de ejecución. El cálculo de tiempo excluye intentos sin duración válida.

## Cómo realizaremos y documentaremos la medición

1. Registraremos fecha de inicio/fin, lugar, modalidad, versión exacta y número de participantes.
2. Obtendremos consentimiento previo, activaremos el registro y seguiremos el mismo guion de tareas.
3. Completaremos una fila del CSV por participante, sin datos personales, y revisaremos el archivo JSONL.
4. Ejecutaremos el generador de resultados. No editaremos el SVG manualmente para fabricar cifras.
5. Compararemos indicadores y observaciones con la hipótesis, y documentaremos **al menos dos mejoras**, su prioridad y cómo volveríamos a comprobarlas.
6. Reconoceremos tamaño de muestra, selección no aleatoria, uso de datos de prueba y diferencias respecto del servicio real.

## Estado de la evidencia

Este documento describe nuestro **protocolo preparado**, no una prueba finalizada. En la revisión del **17-11-2026** el CSV tiene solo encabezados; **no consta aún** fecha de campo, N de participantes, resultados reales de estas tareas ni dos mejoras validadas. La encuesta diagnóstica N=17 corresponde a RA1 y no la usaremos como si fuera RA3.

Cuando obtengamos evidencia real, actualizaremos `INFORME-FINAL.md` y el resultado exportado. Si el KPI no tiene denominador, consignaremos **«Sin datos»** en lugar de inventar un porcentaje.
