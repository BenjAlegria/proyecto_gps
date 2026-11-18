# EnRuta Ya! — Documento de producto y plan de evolución
**Estado:** propuesta de rediseño y planificación, 11-11-2026.  
**Equipo:** 3 estudiantes.  
**Repositorio:** https://github.com/BenjAlegria/proyecto_gps  
**Figma editable:** https://www.figma.com/design/CSDvMcoNqK51KMT8dPbXEi

## 1. ¿Qué es y para qué sirve?
EnRuta Ya! es una aplicación móvil de transporte interurbano enfocada inicialmente en recorridos de la Región de La Araucanía, como Lautaro, Nueva Imperial, Carahue y Padre Las Casas hacia Temuco. Busca reducir la incertidumbre de quienes esperan un bus: dónde viene, cuánto podría tardar y si existe un aviso reciente de ocupación, atraso o desvío.

**Modelo colaborativo:** un pasajero que efectivamente viaja en el bus acepta compartir temporalmente la ubicación de su teléfono. Otros usuarios ven la posición asociada al viaje. **No equivale a un GPS instalado en el vehículo**: es una posición aportada por una persona, puede contener errores y debe identificarse como información colaborativa.

## 2. Fundamento UX/UI
La investigación del equipo (17 respuestas, véase `FUNDAMENTACION-UX-UI.md`) muestra alta preferencia por la ubicación del bus y la visualización en vivo; por ello **Inicio debe priorizar el mapa**, con selección de localidad y un panel inferior plegable de líneas. Las tarjetas de rutas son una vista secundaria, no un reemplazo del mapa principal.

Principios: claridad al distinguir datos reales de simulados, botones legibles, navegación simple, privacidad explícita, mensajes útiles sin internet y tolerancia a ubicación imprecisa.

## 3. Funciones actuales verificadas en el repositorio
- Kivy + KivyMD, MapView; interfaz declarada en `root.kv`.
- Login y registro locales con validaciones y contraseña derivada mediante hash.
- Inicio con mapa, localidades y marcadores.
- Recorridos, compartir, avisos, perfil, ajustes, favoritos.
- Almacenamiento local en JSON para perfiles y avisos.
- Configuración remota con caché y notificaciones locales.
- Simulación de posiciones y avisos para la demostración.

**Límite decisivo:** no hay sincronización de posiciones/avisos entre dispositivos; la vista compartida entre usuarios todavía **no es una funcionalidad operativa**. Los horarios y tarifas actuales son ejemplos, no datos oficiales verificados.

## 4. Rediseño visual en Figma
- **Mapa / Inicio:** mapa visible inmediatamente, indicador «datos colaborativos», filtros por comuna/ruta, marcadores distinguibles y ficha inferior del viaje.
- **Recorridos:** tarjetas resumidas por origen/destino y estado de reportes, búsqueda y favoritos.
- **Detalle de viaje:** tiempo estimado identificado como aproximado, última actualización, calidad/frescura de la señal, ocupación reportada y avisos.
- **Compartir:** elegir línea, permiso expreso, iniciar/detener transmisión, estado persistente «compartiendo», selección de ocupación.
- **Avisos:** lleno, hay asientos, atrasado, cambio de ruta; fecha del reporte y vigencia.
- **Cuenta:** login, registro, perfil, favoritos y ajustes.
- **Estados críticos:** sin internet, GPS desactivado, sin colaboradores activos, viaje vencido, permiso denegado.

**Importante:** Figma es una maqueta editable; no demuestra integración backend ni datos en directo.

## 5. MVP real entre dispositivos: criterios de aceptación
1. Dos teléfonos A y B pueden iniciar sesión y elegir la misma ruta.
2. A inicia compartir tras consentimiento; el servidor recibe posiciones vinculadas a un identificador efímero del viaje, con marca temporal.
3. B consulta una ruta y ve una posición real publicada recientemente; el UI muestra «actualizado hace X segundos».
4. Si A detiene el viaje, el servidor marca el viaje inactivo; B deja de mostrarlo como activo.
5. Si no hay reportes recientes, B ve «Sin ubicación reciente», nunca una posición demo haciéndose pasar por actual.
6. Los avisos publicados desde A pueden leerse desde B y expiran al vencer su vigencia.
7. Se aplica limitación de frecuencia, validación y control básico de abuso; no se envían credenciales en el repositorio.
8. Se prueban dos teléfonos físicos, conexiones intermitentes y denegación de permisos.

## 6. Arquitectura propuesta (por implementar)
Kivy UI → capa `servicios/api_cliente.py` → API HTTPS → almacenamiento servidor. Un emisor publica latitud, longitud, precisión, hora y ruta; un receptor lee posiciones recientes por ruta. Se recomienda empezar con consultas periódicas (polling) para el MVP, antes de optimizar con WebSockets.

**Seguridad y privacidad:** credenciales por entorno, HTTPS, autenticación del emisor, UUID efímero del viaje, no exponer identidad del pasajero en el mapa, caducidad de coordenadas, cierre automático por inactividad, consentimiento revocable y política de retención corta. Una cuenta local en JSON no sirve para validar sesiones en un backend multiusuario sin un sistema de autenticación compatible.

**ETA:** no anunciar una hora como certera. Primero «aproximación» basada en distancia sobre el recorrido y velocidad observada, con control de errores y estado «ETA no disponible» si faltan datos. Un solo GPS de pasajero no permite conocer la ocupación automáticamente; debe ser un reporte voluntario.

## 7. Priorización
| Prioridad | Entregable | Estado |
|---|---|---|
| P0 | Mantener funcionando la demo y pruebas existentes | Ya existe; preservar |
| P0 | Diseñar contrato API, modelo de viaje, expiración, privacidad | Pendiente |
| P0 | Sincronizar posiciones entre dos teléfonos | Pendiente |
| P0 | Mostrar fuente y antigüedad del dato | Pendiente |
| P1 | Compartir avisos entre teléfonos | Pendiente |
| P1 | Rediseño Kivy alineado a Figma | Diseño iniciado, implementación pendiente |
| P1 | Manejar conectividad intermitente y permisos | Pendiente |
| P2 | ETA mejorada, confianza del reporte y detección de trayecto | Pendiente |
| P2 | Historial agregado y métricas anónimas | Por evaluar |

## 8. Propuesta de trabajo para 3 integrantes
**Integrante A — interfaz:** pantallas `root.kv`, componentes reutilizables, estados vacíos, accesibilidad, coherencia Figma/Kivy.  
**Integrante B — GPS / backend:** contrato API, servidor y almacenamiento, ciclo iniciar/actualizar/detener viaje, expiración, credenciales.  
**Integrante C — integración/calidad:** cliente HTTP, avisos multiusuario, pruebas automatizadas, pruebas físicas y documentación de resultados.

Todos deben revisar pull requests y evitar editar simultáneamente los mismos bloques de `main.py`/`root.kv`.

## 9. Flujo Git y Codex
- Branches sugeridas: `feature/ui-redesign`, `feature/gps-backend`, `feature/sync-client`, `test/multi-device`.
- Antes de programar: `git pull origin main`, luego `git switch -c <rama>`.
- Commits pequeños con pruebas; PR hacia `main` con captura, descripción, limitaciones y responsable.
- Pedir a Codex modificaciones de un subsistema por vez, preservando servicios existentes y pruebas.
- Nunca confirmar archivos `data/`, claves, tokens, credenciales, `.env` ni logs personales.

## 10. Registro de cambios — propuesta 11-11-2026
- Creado Figma «EnRuta Ya! — Rediseño UI/UX móvil» y primeras pantallas editables.
- Analizado el README, base Kivy, KV y fundamentación UX/UI existente.
- Identificada la brecha principal para convertir la demo en producto: backend y sincronización multiusuario.
- Definido alcance, criterios de aceptación, medidas de privacidad y división del trabajo.
- **No se modificó el código de producción ni se habilitó GPS en vivo con esta documentación.**
