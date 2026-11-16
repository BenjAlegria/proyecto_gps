# Declaración de uso de inteligencia artificial — EnRuta Ya!

**Asignatura:** Desarrollo Móvil (A+S), TINF1119. **Etapa:** PIF E4.

Este archivo sustituye la declaración anterior centrada en E3: en las
fases posteriores del proyecto también se utilizó ChatGPT/Codex.

## Herramientas que deben declarar los integrantes
- **Claude (Anthropic):** se utilizó en etapas anteriores para apoyar
  prototipos, migración a KivyMD, formularios, validaciones,
  documentación y correcciones de errores.
- **ChatGPT (OpenAI):** apoyo a revisión de la rúbrica, rediseño,
  refactorización, documentación de privacidad, generación de pruebas
  y preparación del cliente Firebase y la instrumentación MJV App.
- **Codex (OpenAI):** apoyo a generación y revisión de código Kivy,
  cambios de interfaz y pruebas del repositorio.
- **Figma:** herramienta de diseño empleada para los mockups; confirmar
  si se usaron funcionalidades generativas de IA dentro de Figma.

**Verificación del equipo pendiente:** cada integrante debe
comprobar si usó otras herramientas (y versiones concretas) para
incluirlas. No atribuir a una sola persona decisiones del grupo.

## Ejemplos de solicitudes y contribuciones
- Diseñar una app KivyMD con registro, login, mapa, favoritos,
  reportes de viajeros y configuración remota.
- Mejorar UX/UI para pantallas móviles manteniendo navegación.
- Identificar errores de permisos GPS, callbacks tardíos y formatos JSON.
- Probar Google Maps en rama aislada; abandonar el experimento por
  dificultades de facturación y conservar MapView.
- Incorporar pruebas, registrar eventos anónimos y generar KPIs
  trazables para la rúbrica.
- Preparar una integración opcional de Firebase con seguridad de reglas
  y modo local de respaldo.

## Validación y responsabilidad humana
El equipo conserva la responsabilidad por el diseño, la lógica, la
seguridad, la exactitud de la información y la defensa oral. El código
generado por IA no se asume correcto sin pruebas; debe revisarse
con `python -m unittest discover -s tests -v` y demo real.
La primera prueba de Google Maps presentó errores de sintaxis y API;
se decidió no incluirla en la versión de evaluación.

No se usó IA para inventar encuestas ni resultados MJV App.
Los indicadores deben derivarse exclusivamente de eventos registrados
y observaciones con participantes voluntarios.

## Limitaciones a explicar al docente
- Los datos de buses y ETA son simulados, no telemetría oficial.
- Firebase es opcional y no reemplaza el login local.
- Los resultados de medición solo serán válidos al registrar un
  periodo y contexto de prueba reales.
- Los riesgos de privacidad, accesibilidad y abuso de reportes
  requieren revisión adicional antes de publicar la app.
