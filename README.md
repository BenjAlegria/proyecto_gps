# EnRuta Ya!

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
EnRuta Ya! resuelve esa falta de información centralizando
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
0. **Login / Registro** — pantallas de entrada: crear cuenta o iniciar sesión (ver *Servicios*).
1. **Inicio** — mapa a pantalla completa con barra superior (perfil,
   selector de localidad, acceso directo a Compartir), botón flotante
   para centrarse en la ubicación real del usuario, un banner con el mensaje de la
   configuración remota y un panel
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
5. **Ajustes** — tema oscuro/claro, interruptor de notificaciones, resumen de la
   **configuración remota** con botón *Actualizar*, botón de demo que simula el
   aviso de otro pasajero y *Cerrar sesión*.
6. **Perfil** — accesible desde el ícono de la barra superior; usuario, nombre
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
- Python 3.10 o superior (probado con 3.12)
- Git
- Conexión a internet (tiles del mapa y configuración remota; sin internet la app
  igual abre y usa los valores guardados)

## Instalación paso a paso
```bash
git clone https://github.com/BenjAlegria/proyecto_gps.git
cd proyecto_gps

# (recomendado) entorno virtual
python -m venv myenv
myenv\Scripts\activate          # Windows
# source myenv/bin/activate      # Linux / macOS

pip install -r requirements.txt
```
Dependencias (`requirements.txt`): `kivy==2.3.1`, `kivymd==2.0.0`,
`kivy-garden.mapview==1.0.6`, `plyer`, `requests`, `pillow`.

## Cómo ejecutarla
```bash
python main.py
```
1. Toca **¿No tienes cuenta? Regístrate** y crea un usuario (3-20 caracteres) con
   contraseña de al menos 6 caracteres, con letra y número.
2. Entras a Inicio. Elige una localidad, toca un bus y agrégalo a favoritas.
3. En *Compartir* elige una línea y avisa "Bus lleno" (queda guardado).
4. En *Ajustes* toca **Simular aviso** para ver la notificación.
5. Cierra la app, ábrela de nuevo e inicia sesión: tus favoritas, nombre, tema,
   viajes y los avisos siguen ahí.

Pruebas automáticas de los servicios (sin interfaz):
```bash
python -m unittest discover tests -v
```

## Estructura del proyecto
```
proyecto_gps/
├── main.py                     # App (InterurbanoApp): pantallas, navegación y eventos.
│                               #   Es quien llama a los servicios.
├── root.kv                     # Interfaz declarativa (KV Language), incluye login y registro
├── config.py                   # Rutas de archivos, URL remota y valores por defecto
├── datos_rutas.py              # Localidades, recorridos y tipos de aviso (datos de ejemplo)
├── servicios/
│   ├── autenticacion.py        # Registro, login, validación y hash de contraseñas
│   ├── almacenamiento.py       # Leer/guardar JSON: perfiles y avisos
│   ├── config_remota.py        # Descarga, validación y caché de la configuración remota
│   └── notificaciones.py       # Notificación en la app + del sistema (plyer)
├── remote_config.json          # Fuente de la configuración remota (se sirve desde GitHub)
├── tests/test_servicios.py     # Pruebas automáticas de los servicios
├── bus_marker.png              # Ícono del bus en el mapa
├── data/                       # Se crea sola al usar la app (no se sube al repo)
│   ├── usuarios.json           #   credenciales (sal + hash)
│   ├── perfiles.json           #   favoritas, nombre, viajes y ajustes por usuario
│   ├── avisos.json             #   avisos de pasajeros
│   └── config_remota_cache.json#   última configuración remota descargada
├── requirements.txt
├── README.md
├── USO_IA.md
└── FUNDAMENTACION-UX-UI.md
```
**Quién llama a quién:** `main.py` → `servicios/*` → `config.py`. Los servicios
no conocen la interfaz; `main.py` no sabe cómo se guarda un hash ni cómo se
descarga un JSON.

## Servicios implementados y dónde está cada uno

| Servicio | Dónde está en el código | Cómo funciona |
|---|---|---|
| **Registro** | `servicios/autenticacion.py` → `registrar()`; pantalla `RegistroScreen` en `root.kv`; `hacer_registro()` en `main.py` | Valida usuario y contraseña, crea la cuenta en `data/usuarios.json` |
| **Login** | `autenticacion.iniciar_sesion()`; `LoginScreen`; `hacer_login()` / `_entrar()` en `main.py` | Compara el hash de la contraseña; si es válido carga el perfil y abre Inicio |
| **Validación de contraseña** | `autenticacion.validar_contrasena()` | Mínimo 6 caracteres, una letra y un número, y que coincida con la repetición |
| **Persistencia en JSON** | `servicios/almacenamiento.py` (`leer_json`, `guardar_json`, `cargar_perfil`, `guardar_perfil`, `cargar_avisos`, `guardar_avisos`); `_guardar_perfil()` y `_guardar_avisos()` en `main.py` | Se guarda al cambiar favoritas, nombre, tema, ajustes, viajes y al publicar un aviso; se recupera al iniciar sesión / abrir la app |
| **Notificaciones** | `servicios/notificaciones.py` → `notificar()`; `InterurbanoApp.notificar()` en `main.py` | Se disparan por eventos: aviso en una ruta favorita (`publicar_aviso`), fin de viaje (`detener_compartir`) y el botón de demo (`simular_aviso`) |
| **Configuración remota** | `servicios/config_remota.py`; `URL_CONFIG_REMOTA` y `CONFIG_REMOTA_DEFECTO` en `config.py`; `_aplicar_config()` en `main.py` | Lee `remote_config.json` desde GitHub en un hilo y lo refleja en la app |

### Detalle de la configuración remota
- **Fuente remota:** `remote_config.json` de este repositorio, servido por
  `raw.githubusercontent.com` (URL en `config.py`).
- **Valores:** `mensaje_inicio` (banner de Inicio), `antispam_segundos` (tiempo mínimo
  para repetir un aviso) y `vigencia_aviso_min` (cuánto dura un aviso como estado actual).
- **Orden de prioridad:** valor remoto → última copia guardada (caché) → valor por
  defecto de `config.py`. La pantalla Ajustes muestra cuál fuente se está usando.
- **Probarlo:** editar `mensaje_inicio` en `remote_config.json`, hacer `git push`, y en
  Ajustes tocar *Actualizar* (o reabrir la app): el banner de Inicio cambia.
- Un JSON remoto con claves desconocidas o tipos incorrectos se ignora (`_sanear`).

### Seguridad de las contraseñas
No se guardan en texto plano: se usa PBKDF2-SHA256 (120.000 iteraciones) con sal
aleatoria por usuario, y la comparación usa `hmac.compare_digest`. El mensaje de
error del login es el mismo si falla el usuario o la clave.

## Dificultades encontradas y cómo las resolvimos
- **Error `FBO Initialization failed` al mostrar un snackbar** (KivyMD 2.0.0 lo crea con
  alto 0): se creó `AvisoSnackbar`, que fuerza un tamaño mínimo antes de crear el FBO.
- **Íconos de bus gigantes al alejar el mapa:** los marcadores de MapView no escalan;
  `MarcadorBus.ajustar_zoom` cambia su tamaño según el zoom.
- **PC sin GPS ni notificaciones del sistema:** `plyer` se importa dentro de `try`; sin
  GPS se calcula una ubicación aproximada por IP en un hilo, y sin proveedor de
  notificaciones igual se muestra el aviso dentro de la app.
- **Interfaz congelada al consultar internet:** la configuración remota y la ubicación
  por IP corren en hilos y vuelven a la interfaz con `Clock.schedule_once`.
- **Archivos JSON corruptos o a medias:** `guardar_json` escribe a un temporal y lo
  reemplaza; `leer_json` aparta el archivo dañado (`.corrupto`) en vez de cerrar la app.
- **Guardados por error al cargar el perfil:** al aplicar el perfil se activan los
  interruptores y disparaban guardados; la bandera `_cargando` lo evita.
- **Sin internet en la demo:** la app no depende de la red para abrir; cae a la caché
  o a los valores por defecto.

## Limitaciones conocidas
- La ubicación y los avisos son locales al dispositivo: aún no hay un servidor que los
  reparta a otros usuarios (`publicar_aviso` e `iniciar_compartir` tienen el TODO).
- Los horarios, frecuencias y tarifas de `datos_rutas.py` son datos de ejemplo.
- Los 3 avisos iniciales y el botón *Simular aviso* son de demostración.
- La autenticación es local (no hay servidor ni recuperación de contraseña).

## Declaración de uso de IA
Ver [`USO_IA.md`](USO_IA.md).

## Documentación de diseño
La fundamentación UX/UI (encuesta, hallazgos y decisiones) está en
[`FUNDAMENTACION-UX-UI.md`](FUNDAMENTACION-UX-UI.md).
