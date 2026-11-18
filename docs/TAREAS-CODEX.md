# Tareas preparadas para Codex — EnRuta Ya!
Este archivo contiene instrucciones por etapas. Ejecutar UNA tarea por vez en VS Code y trabajar siempre sobre una rama propia. **No implementar todas a la vez.**

## Tarea 1 — Analizar y proponer contrato de sincronización
```text
Actúa como ingeniero Python para el proyecto EnRuta Ya!, desarrollado con Kivy 2.3.1, KivyMD 2.0.0 y kivy-garden.mapview. Lee README.md, main.py, root.kv, config.py, datos_rutas.py, servicios/ y docs/PLAN-REDISENO-Y-MVP.md antes de modificar nada.

Objetivo de esta tarea: elaborar docs/CONTRATO-API-GPS.md con arquitectura mínima de cliente-servidor que sincronice la posición voluntaria de un pasajero con otro teléfono.

Incluye endpoints HTTPS propuestos: crear viaje, publicar posición, consultar viajes activos de una ruta, publicar/consultar avisos, detener viaje. Define JSON request/response, identificadores de viaje efímeros, timestamp UTC, precisión del GPS, TTL, autenticación, validación, errores, permisos y límites de frecuencia. Distingue datos reales, simulados, vencidos y desconocidos. No codifiques el backend ni cambies la UI todavía. No guardes tokens o credenciales reales. Propón pruebas con dos dispositivos.
```

## Tarea 2 — Cliente HTTP desacoplado (después de aprobar el contrato)
```text
Usa docs/CONTRATO-API-GPS.md como contrato aprobado. Implementa servicios/api_cliente.py y pruebas con un servidor simulado (mocks). Nunca hagas requests bloqueantes en el hilo principal de Kivy: usa Thread o Clock de forma segura. Configura URL base por entorno sin secretos, timeouts, reintentos limitados y errores claros. Aún no reemplaces la simulación existente. Demuestra tests que pasan.
```

## Tarea 3 — Backend mínimo (solo tras decisión tecnológica)
```text
Implementa una API Python para el contrato aprobado en una carpeta separada backend/. No cambies root.kv ni main.py. Añade validación, almacenamiento, caducidad, autenticación de emisor y una forma de ejecutar pruebas locales. No expongas credenciales ni datos personales. Implementa protección contra spam y actualizaciones excesivas. Documenta la puesta en marcha.
```

## Tarea 4 — UI Kivy (paralela en otra rama, sin modificar comunicación)
```text
Usa el Figma https://www.figma.com/design/CSDvMcoNqK51KMT8dPbXEi y docs/PLAN-REDISENO-Y-MVP.md como referencia. Mantén el MAPA como pantalla de Inicio, según FUNDAMENTACION-UX-UI.md. Rediseña un componente por vez y conserva IDs KV, rutas de navegación y lógica actual. Separa componentes visuales y datos, mantiene accesibilidad/contraste y muestra etiquetas “Simulación” en contenido que no proviene del servidor. No declares tiempo real antes de implementar el backend. Proporciona screenshots y pasos de prueba.
```

## Tarea 5 — Integración y prueba de campo
```text
Después de integrar backend, cliente HTTP y nueva UI, reemplaza gradualmente los puntos TODO de publicar_aviso e iniciar_compartir. Prueba: teléfono A inicia viaje, teléfono B ve posición con antigüedad, B recibe aviso, A detiene el viaje y B ve cierre/expiración. Valida sin GPS, conexión cortada, viaje detenido, actualización vencida, permisos denegados y ausencia de colaboradores. No inventes ETA o disponibilidad de asientos.
```

## Revisión antes de fusionar
- [ ] `python -m unittest discover tests -v` sin regresiones.
- [ ] Sin credenciales, tokens o JSON locales de usuarios en Git.
- [ ] El mapa diferencia simulación, datos compartidos y ausencia de datos.
- [ ] La ubicación se transmite solo con consentimiento explícito y puede detenerse.
- [ ] Funciona con dos dispositivos, no solo dos ventanas del mismo proceso.
- [ ] PR revisado por otro integrante.
