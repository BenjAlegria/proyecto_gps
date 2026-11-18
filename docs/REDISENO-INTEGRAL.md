# Rediseño integral — EnRuta Ya!

## Alcance

Las ocho pantallas comparten fondo blanco en tema claro y una paleta oscura
completa al activar esa preferencia. Se conserva MapView interactivo, autenticación
local, perfiles, favoritos, configuración remota, notificaciones y almacenamiento
JSON. No se agregaron dependencias ni sincronización entre teléfonos.

Se consultaron los frames de Inicio, Recorridos, Compartir, Avisos, Perfil y
Acceso del archivo Figma `CSDvMcoNqK51KMT8dPbXEi`. Se adaptaron a la paleta blanca
solicitada; Ajustes usa el mismo sistema, sin atribuirle un frame inexistente.

## Causas corregidas

- En KivyMD 2.0 `MDIcon` representa su color con `icon_color`, no con el mismo
  contrato que `MDLabel.text_color`. Tamaños personalizados requieren desactivar
  el tamaño de fuente del tema.
- Los controles MD con propiedades `theme_* = "Primary"` recuperaban colores
  calculados al cambiar de tema. Los campos conservados usan las propiedades
  `Custom`; menús y diálogos reciben los colores globales equivalentes.
- Reglas KV heredadas conservaban bindings de color y tamaño incluso cuando una
  regla posterior escribía otro valor. El prefijo KV `-propiedad` elimina esos
  bindings antes de aplicar el estilo. Esto también evita alturas circulares
  al combinar textos adaptables y `text_size` heredado.
- La navegación ahora usa una sola apariencia en todas las secciones y sigue
  fuera del ScreenManager. Login y Registro la ocultan y deshabilitan.
- Los estados vacíos ocultos tienen altura controlada por Python, sin un binding
  de altura automática que vuelva a reservar espacio al actualizar su texto.

## Sistema compartido

`tema.py` define paletas reactivas, colores semánticos y tokens de margen/radio.
`componentes.kv` contiene UiHeader, UiAvatar, UiSurface, UiAction, UiButton,
UiText, UiParagraph, UiSection, UiError, UiIcon, UiField, UiSwitch, UiNotice,
UiBrand, UiBody y UiScroll. Los iconos usan la fuente Icons ya incluida en KivyMD.
Las flechas se dibujan con iconos, sin depender de glifos ausentes en Roboto.

Inicio conserva chips y panel plegable. Recorridos y favoritos comparten tarjetas
con ETA demostrativa y acceso al detalle. Compartir indica explícitamente el modo
local, consentimiento y estado de inicio/detención. Avisos distingue reportes
vigentes de vencidos, con hora y antigüedad. Ajustes y Perfil son desplazables
para que sus últimas acciones no queden debajo de la navegación.

## Verificación reproducible

Desde `proyecto_gps`:

```powershell
$env:KIVY_NO_FILELOG='1'
$env:KIVY_GL_BACKEND='angle_sdl2'  # Windows, si se necesita ANGLE para capturas
python -m unittest discover -v
python tools/verificar_interfaz.py
```

El verificador ejecuta la aplicación y `on_start`, captura las ocho pantallas en
390 × 844 y 360 × 800 píxeles, tanto claras como oscuras, y genera vistas adicionales
de finales de listas, errores, compartir activo y avisos vacíos. Usa datos de
prueba en memoria y deshabilita descargas de teselas, consultas remotas y
escrituras de perfiles/avisos durante esa ejecución. No activa GPS para simular
el estado visual de compartir. Las teselas ausentes no son una imagen sustitutiva:
el widget sigue siendo MapView con sus marcadores.

- [Ocho pantallas claras](verificacion-ui/resumen-light.png)
- [Ocho pantallas oscuras](verificacion-ui/resumen-dark.png)
- [Claras a 360 × 800](verificacion-ui/resumen-light-360.png)
- [Oscuras a 360 × 800](verificacion-ui/resumen-dark-360.png)
- [Listado de capturas individuales](verificacion-ui/capturas.txt)

Se conservan las ocho pruebas previas. Las tres nuevas verifican las ocho
pantallas y los temas, margen inferior, regresión de colores semánticos al
alternar tema y el flujo local completo con archivos JSON temporales. Las pruebas
de navegación envían toques mediante el sistema de entrada de Kivy.

Resultado registrado: **11 pruebas aprobadas**, compilación Python y
`git diff --check` correctos. Se generaron y revisaron las 32 vistas principales
y nueve vistas de estados/finales de listas, 41 capturas en total. Se comprobó
que los archivos individuales tienen exactamente los tamaños solicitados.

## Límites pendientes

- Capturas revisadas en escritorio con Kivy 2.3.1, KivyMD 2.0.0 y ANGLE. No equivalen
  a una prueba física Android: teclado, gestos, permiso GPS, notificaciones del
  sistema y zona segura del fabricante requieren validación en teléfono.
- La barra acepta un inset inferior; en Android se consulta WindowInsets y se
  reserva espacio solo cuando SDL invade el área de las barras. Ese cálculo
  específico de Android aún necesita comprobación física.
- La red del entorno impide verificar la descarga real de teselas. No se cambia
  el proveedor ni la lógica de GPS.
- El mapa conserva su cartografía del proveedor al activar modo oscuro; se
  oscurecen los controles de la app, no se finge una capa cartográfica nocturna.
- En ventanas estrechas los textos largos se ajustan o abrevian y los controles
  de reporte pasan a una columna. Listas y paneles permiten desplazamiento.
- Permanecen los avisos de obsolescencia de `allow_stretch` y `keep_ratio` del
  marcador de MapView; no impiden el inicio.
