# Interurbano Sur

App móvil para consultar la hora de llegada de los buses interurbanos
y ver su ubicación en un mapa (Lautaro, Nueva Imperial, Carahue, Padre
Las Casas → Temuco, entre otros recorridos). Como la empresa de buses
no cuenta con GPS en sus vehículos, la posición del bus en el mapa la
aporta un usuario que va viajando en él y acepta compartir su
ubicación mientras dura el viaje.

## Problema que resuelve
Según la encuesta aplicada (17 respuestas, ver
`FUNDAMENTACION-UX-UI.md`), el 76% de los usuarios de buses
interurbanos en la Araucanía se informa hoy por memoria o
preguntándole al conductor, no por un canal oficial confiable, y el
71% ha quedado con el bus lleno sin poder subir. La utilidad percibida
de una app que muestre horarios y ubicación en vivo fue de 4.7/5.
Interurbano Sur resuelve esa falta de información centralizando
horarios y mostrando la ubicación real del bus en un mapa, aportada
por los propios pasajeros ante la ausencia de GPS en los buses.

## Usuario objetivo
Personas que viajan en bus interurbano entre comunas de la Araucanía
(Nueva Imperial, Lautaro, Carahue, Padre Las Casas, Temuco). Según la
encuesta, el perfil predominante son estudiantes de 18 a 25 años que
usan el bus a diario o varias veces por semana para ir a estudiar,
aunque también incluye trabajadores y personas que lo usan
ocasionalmente para trámites médicos.

## Pantallas
1. **Inicio** — mapa a pantalla completa con barra superior (perfil,
   selector de localidad, acceso directo a Compartir), botón flotante
   para centrarse en la ubicación real del usuario, y un panel
   inferior plegable con los buses de la localidad elegida (toca uno
   para ver el detalle).
2. **Recorridos** — listado de todos los recorridos con su próximo
   bus; cada tarjeta abre el mismo detalle.
3. **Compartir** — el usuario elige su línea y, tras aceptar un
   diálogo de consentimiento, comparte su ubicación durante el viaje
   (por ahora simulada localmente, ver limitaciones). Además puede
   **avisar a otros pasajeros** el estado de su línea con cuatro
   botones: *Bus lleno*, *Hay asientos*, *Atrasado* (pregunta cuántos
   minutos) y *Cambio de ruta*.
4. **Avisos** — lista de los avisos de las últimas 2 horas, con
   interruptor para ver solo los de las rutas favoritas.
5. **Ajustes** — interruptor de tema oscuro/claro, interruptor para
   recibir notificaciones de atrasos y buses llenos en las rutas
   favoritas, y un botón de demo que simula el aviso de otro pasajero.
6. **Perfil** — accesible desde el ícono de la barra superior; nombre
   editable con validación, contador de viajes y favoritas,
   interruptor de permiso de ubicación y lista de rutas favoritas.

La barra inferior navega entre Inicio, Recorridos, Compartir, Avisos
y Ajustes; el Perfil se abre desde el ícono de la barra superior.

### Avisos de buses llenos y atrasados
Las tarjetas de cada línea (Inicio, Recorridos y Perfil) muestran una
tercera línea con el estado actual — *Bus lleno* (rojo), *Atraso ~10
min* o *Cambio de ruta* (naranjo), *Hay asientos* (verde) o *Sin avisos
recientes* — y el detalle de la línea suma ocupación y atraso. Un aviso
cuenta como estado actual por 30 minutos (el más reciente de cada tipo
manda) y se conserva 2 horas en la pantalla Avisos. Para evitar spam,
la misma persona no puede repetir el mismo aviso en la misma línea
antes de 2 minutos, y debe elegir su línea antes de avisar. Cuando
llega un aviso de una ruta favorita se muestra una notificación dentro
de la app y, si el dispositivo lo permite (plyer), del sistema.

## Requisitos
- Python 3.10+
- Kivy 2.3+
- KivyMD 2.0+
- kivy-garden.mapview (mapa; necesita internet para cargar los tiles)
- plyer (GPS del dispositivo)
- requests (ubicación aproximada por IP cuando no hay GPS de hardware)

Instalación:
```bash
pip install -r requirements.txt
```

## Ejecución
```bash
python main.py
```

## Estructura del proyecto
```
interurbano_app/
├── main.py                    # Lógica: App, pantallas, validaciones, navegación
├── root.kv                    # Interfaz declarativa (KV Language)
├── assets/bus_marker.png      # Ícono del bus/usuario en el mapa
├── requirements.txt
├── README.md
├── FUNDAMENTACION-UX-UI.md
└── investigacion/
    └── Encuesta sobre Uso de Transporte Público e Interurbano.csv
```

## Capturas de pantalla
[COMPLETAR: agregar una captura por pantalla — Inicio, Recorridos,
Compartir, Ajustes y Perfil]

## Limitaciones conocidas (fuera del alcance de esta evaluación)
- La ubicación que ve cada usuario es local a su propia app: aún no
  hay un servidor que reciba la posición de quien comparte y se la
  envíe a los demás usuarios en tiempo real.
- Los horarios y frecuencias mostrados son datos de ejemplo, no
  información en vivo.
- Igual que la ubicación, los avisos quedan solo en el dispositivo:
  falta el servidor que los reciba y los reparta a los demás usuarios
  (`publicar_aviso` en `main.py` tiene el TODO). Los 3 avisos que
  aparecen al abrir la app y el botón "Simular aviso" de Ajustes son
  de ejemplo, para la demo.
- No hay persistencia (los favoritos, el nombre y los avisos se
  pierden al cerrar la app), autenticación ni notificaciones push
  remotas (las notificaciones actuales son locales) — esto está
  explícitamente fuera del alcance técnico exigido hasta la semana 8.

## Declaración de uso de IA
Este proyecto se desarrolló con apoyo de Claude (Anthropic) como
asistente de programación. Lo que se generó o apoyó con IA:
- La migración de la interfaz de Kivy plano a KivyMD 2.0 y su
  estructura declarativa en `root.kv`.
- La implementación técnica de: `ScreenManager` y navegación,
  `MDDropdownMenu` para elegir localidad/línea, integración de
  `kivy_garden.mapview` con marcadores, el flujo de
  consentimiento/compartir ubicación con `MDDialog`, la
  geolocalización aproximada por IP como respaldo cuando no hay GPS,
  y ajustes de diseño (colores, tema oscuro, panel plegable).
- Corrección de errores durante el desarrollo (ej. compatibilidad de
  componentes con KivyMD 2.0, imports opcionales de `plyer`).

Lo que es trabajo propio del equipo:
[COMPLETAR: ej. la definición del problema y del usuario objetivo, el
diagnóstico con el socio comunitario, el diseño de la investigación
UX/UI (entrevistas/encuestas), las decisiones de qué localidades y
recorridos incluir, la revisión y prueba de la app en dispositivo
real, y cualquier dato (horarios, tarifas, paradas) reemplazado por
información real].

## Checklist de cumplimiento de la pauta (autoevaluación)
- [x] App ejecutable con `python main.py`, con recorrido entre
      pantallas (B1).
- [x] 6 pantallas con `ScreenManager` (mínimo exigido: 3) (C2).
- [x] Interfaz en `.kv` separada de la lógica en `.py`, con `ids` y
      vinculación correcta (C1).
- [x] Componentes KivyMD con principios Material (color, jerarquía,
      espaciado): `MDButton`, `MDTextField`, `MDCard`, `MDDialog`,
      `MDLabel`, `MDSwitch`, `MDIcon` (B2, B3). *Nota:* la barra
      superior es un contenedor propio (no `MDTopAppBar`) para poder
      controlar sus colores; si la pauta exige literalmente ese
      componente, se puede volver a usar `MDTopAppBar` — avisar si se
      necesita ese cambio.
- [x] Interacción y validación básica de entrada: campo de nombre en
      Perfil (vacío o > 30 caracteres), selección obligatoria de
      línea antes de compartir ubicación o enviar un aviso, y límite
      de 1 aviso repetido cada 2 minutos (C4).
- [x] Estructura de archivos ordenada y reproducible (`main.py`,
      `root.kv`, `assets/`, `requirements.txt`, `README.md`) (C3).
- [x] **A — Fundamentación UX/UI:** completada con datos reales de
      la encuesta (17 respuestas): metodología, 5 hallazgos con
      evidencia (porcentajes y citas textuales), matriz hallazgo →
      decisión, justificación de estructura y accesibilidad. Falta
      solo: indicar si además hicieron entrevistas (o aclarar que no)
      y, si quieren reforzar A5, una prueba de uso real con un adulto
      mayor u otro perfil no-estudiante.
- [ ] **README:** completar problema, usuario objetivo, capturas y la
      parte de "trabajo propio del equipo" en la declaración de IA.
- [ ] **Datos reales:** horarios, frecuencias, tarifas y paradas en
      `main.py` (diccionario `LOCALIDADES`) siguen siendo de ejemplo;
      reemplazar por los datos del socio comunitario antes de la
      demo.
- [ ] **Presentación oral (D):** preparar demo en vivo y respuestas
      sobre las decisiones de diseño — no depende del código.