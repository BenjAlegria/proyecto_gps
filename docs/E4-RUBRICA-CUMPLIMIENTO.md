# E4 — Revisión de cumplimiento de rúbrica (11-11-2026)

**Asignatura:** Desarrollo Móvil (A+S) TINF1119.
**Evaluación:** PIF Proyecto Integrado Final, presentación grupal y demo en vivo.
**Instrumento:** E4-rubrica.docx entregado por el estudiante.
**Ponderación de la evaluación:** 40% de la nota final de la asignatura.
**Duración:** 8 a 10 minutos por equipo, cada integrante responde preguntas.
**Fechas:** sección 1: 18-19 noviembre; sección 2: 16 y 18 noviembre de 2026.

Los estados son una auditoría preliminar del repositorio; **no representan
la nota del docente** y no sustituyen lo demostrado durante la defensa.

| Criterio | Peso | Estado verificable | Brecha principal |
|---|---:|---|---|
| 1. Problema social y diagnóstico (RA1) | 20% | AVANCE: encuesta de 17 respuestas en FUNDAMENTACION-UX-UI.md, problema definido en README | Vincular cada funcionalidad con resultados verificables de la encuesta; mostrar citas o método de recolección |
| 2. Solución Kivy, MVC/POO, persistencia (RA2) | 25% | AVANCE ALTO: 8 pantallas, servicios separados, registro/login local, JSON, favoritos, reportes, pruebas del usuario aprobadas | Demo de funcionamiento y persistencia, explicación explícita de capas/controlador/servicio/modelo y manejo de errores en vivo |
| 3. Método MJV App, KPIs y periodo (RA3) | 20% | NO DEMOSTRADO: no hay un registro de eventos/KPIs con periodo medido en repositorio | Crear un plan de medición, instrumento, eventos, recolectar datos verdaderos por fechas y operacionalizar KPIs |
| 4. Resultados de medición y propuestas (RA3) | 20% | NO DEMOSTRADO: no se encontraron resultados MJV con gráficos y conclusiones en los entregables revisados | Registrar observaciones de pruebas de usuarios, hacer gráficos legibles, proponer al menos dos mejoras basadas en resultados |
| 5. Conclusión social/ética e IA | 15% | PARCIAL: existe USO_IA.md y consentimiento GPS local; se aclara que las posiciones son demo | Explicar accesibilidad, sesgos, privacidad y decisiones concretas visibles en el código; análisis de consecuencias del uso real |

## Entrega documental obligatoria

- [x] Código fuente GitHub.
- [x] README.md (revisar consistencia final con demo y comandos).
- [ ] DOCUMENTATION.md en la raíz: **no se encontró** (11-11-2026).
- [ ] Informe Final: **no se encontró** en la raíz ni la carpeta docs revisada.
- [x] Declaración de IA (USO_IA.md), comprobar que refleje todo uso real.
- [x] Fundamentación UX/UI (FUNDAMENTACION-UX-UI.md).

## Recomendación urgente: medición antes de la exposición

La suma de los criterios 3 y 4 equivale al **40% de esta evaluación**.
El mapa Google es un extra visual, **no un requisito** del instrumento.

Propuesta de instrumento MJV App (por implementar y ejecutar):

**Eventos mínimos** (no guardar lat/lon ni credenciales):
- app_abierta: fecha/hora UTC, identificador anónimo de sesión.
- inicio_sesion_ok: fecha/hora, resultado, sin nombre de usuario.
- pantalla_abierta: pantalla visitada y hora.
- recorrido_seleccionado: ruta consultada, sin posición del usuario.
- favorito_agregado: ruta guardada y hora.
- aviso_registrado: tipo de aviso y hora, sin identidad ni ubicación exacta.
- error_controlado: categoría técnica del error, nunca claves o datos privados.

**KPI 1. Éxito de búsqueda de recorrido** =
(sesiones de prueba que llegan a seleccionar una ruta / sesiones que
intentan buscar una ruta) × 100.

**KPI 2. Tiempo para encontrar un recorrido** =
mediana de segundos desde pantalla Recorridos hasta ruta seleccionada,
medido con timestamps del instrumento.

**KPI 3. Persistencia de favoritas** =
(participantes cuya ruta favorita sigue guardada tras cerrar y reabrir
la app / participantes que intentan el escenario) × 100.

El protocolo debe declarar **fechas reales**, tamaño y criterios de
muestra, contexto, instrucciones de prueba, consentimiento, forma de
registro, fórmula, objetivos y limitaciones. No inventar una muestra
ni presentar valores de ejemplo como resultados.

## Guion recomendado para 8-10 minutos

1. Problema y resultados de la encuesta: 1-1.5 min.
2. Demo en vivo (login, navegación, elegir ruta, guardar favorita,
   cerrar/reabrir y verificar persistencia, avisos): 3-3.5 min.
3. Arquitectura MVC/POO y servicios: 1 min.
4. Método MJV App, KPIs, periodo y gráficos: 2-2.5 min.
5. Mejoras basadas en datos, privacidad, sesgos, IA, cierre: 1.5 min.

Cada integrante debe poder explicar su tarea y al menos una pregunta
sobre eventos, métrica vs. KPI, MJV App o periodo de recolección.

## Riesgos para la defensa

- La demo no debe prometer GPS en vivo entre móviles: eso no existe.
- No presentar ETA, tarifas, buses o rutas ilustrativas como telemetría
  verificada del operador.
- No depender exclusivamente de una API de mapas que requiera clave,
  facturación o Internet para demostrar las funciones solicitadas.
- La rúbrica permite demostrar desde el equipo de desarrollo si no hay
  APK funcional, sin bonificación ni descuento.
- La valoración final depende de lo que se muestre y explique
  oralmente, no solo del código guardado.

## Próxima acción sugerida

Terminar la prueba visual de Google Maps; **inmediatamente después**
implementar la medición de eventos y el protocolo MJV App, recolectar
una muestra acotada y producir gráficos, DOCUMENTATION.md e Informe Final.
