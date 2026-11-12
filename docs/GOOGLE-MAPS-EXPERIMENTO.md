# Experimento Google Maps — EnRuta Ya!

## ACTUALIZACIÓN: Google Map Tiles integrado en Inicio de Kivy (Windows)

Esta rama incluye ahora **dos modos de prueba independientes**:

- **Ajustes → Activar Google en Inicio**: usa los mosaicos oficiales
  de **Google Map Tiles API** directamente en el widget de mapa de
  Kivy. El mapa ocupa la misma área de Inicio, conserva los marcadores,
  la selección de recorridos, el panel inferior y el diseño aprobado.
- **Ajustes → Volver al mapa original**: restaura OpenStreetMap (MapView)
  sin borrar los favoritos ni cambiar los datos.
- **Ajustes → Abrir Google Maps en navegador**: conserva la primera
  prueba, que usa **Maps JavaScript API** en una pestaña externa.

**Aclaración:** en la primera opción usamos el widget MapView como
renderizador y la cartografía **Google Maps** como fuente de mosaicos
oficiales. Esto NO es el SDK nativo de Google Maps ni incorpora
automáticamente Places, Street View o rutas por carretera.

### Configuración de Google Map Tiles API

Se requiere activar en Google Cloud **Map Tiles API**, además de la
cuenta de facturación y una clave de API con restricciones.

**Crea una clave distinta de la Maps JavaScript API** (la clave web
está expuesta por diseño en el navegador). Para la prueba local en
Windows, limita la clave a la API **Map Tiles API** y aplica las
restricciones de aplicación pertinentes al origen de las solicitudes.
Google recomienda restringir por IP para clientes de servidor; una
clave embebida en una app de escritorio no puede mantenerse secreta.
**No distribuir esa clave con un APK.**

No se enviarán solicitudes de Map Tiles hasta que pulses el botón
de Activar Google dentro de Ajustes. Configura presupuesto, cuotas y
alertas antes de usar la clave. Las alertas no garantizan detener cargos.

En PowerShell, desde la rama experimental:

~~~powershell
git fetch origin
git switch experimento/google-maps
git pull origin experimento/google-maps

# Usa una clave NUEVA restringida a Map Tiles API
$env:ENRUTA_GOOGLE_TILES_API_KEY = "TU_NUEVA_CLAVE_MAP_TILES"
python -m unittest discover -s tests -v
python main.py
~~~

Dentro de Kivy: Ajustes → **Activar Google en Inicio**.
Si la API no está habilitada o rechaza facturación/restricciones,
se mantiene MapView y aparecerá un error legible.
Para regresar: Ajustes → **Volver al mapa original**.

### Derechos y atribuciones Google

La API requiere obtener atribuciones específicas desde el endpoint
`/tile/v1/viewport`. La app consulta esa información y permite abrir
**Google Maps · Fuentes de datos** en Inicio para mostrar los créditos
completos, además de identificar Google Maps como proveedor.

La implementación usa `GoogleTilesSource.fill_tile` propio, sin
guardar Google Maps Content en disco. Las imágenes solo se convierten
en texturas de Kivy para visualización. **No habilitar caché offline ni
prefetch masivo.** Las posiciones de los buses siguen siendo *demo* y
se diferencian del mapa base Google.

**No probado todavía con clave real ni con Android**. Debe verificarse
en tu Windows la aparición de las teselas, créditos, pan/zoom, cambios
de origen y restauración al mapa anterior. El modo de navegador ya fue
validado visualmente por el usuario; el modo dentro de Kivy no.

Fuentes oficiales:
- https://developers.google.com/maps/documentation/tile/overview
- https://developers.google.com/maps/documentation/tile/roadmap
- https://developers.google.com/maps/documentation/tile/session_tokens
- https://developers.google.com/maps/documentation/tile/policies

---

# Experimento Google Maps — EnRuta Ya!

## Estado real del experimento

Esta rama contiene una prueba de Google Maps JavaScript API en **el
navegador del PC**, accesible desde **Ajustes → Probar mapa de Google**
dentro de Kivy. **No reemplaza** MapView ni el mapa estable.

La vista de prueba ofrece filtros por localidades y recorridos, marca
orígenes, destinos y buses simulados. Los datos salen de datos_rutas.py
y del servicio de cálculo de recorridos existente. Las líneas punteadas
son rectas ilustrativas: NO corresponden al trazado real de las calles,
a un bus con GPS ni a tiempos reales.

Todavía no hay backend, sincronización entre celulares, ni Google Maps
embebido en Android. El navegador se abre fuera de Kivy.

## Requisitos en Google Cloud

1. Crear un proyecto en https://console.cloud.google.com/.
2. Habilitar **Maps JavaScript API**.
3. Activar **facturación** para el proyecto. Es un requisito de Google;
   los costos exactos dependen del uso y del plan vigente.
4. Crear una API key **exclusiva para la prueba**.
5. Restringir la clave a Maps JavaScript API.
6. Restringir los sitios web autorizados a:
   http://127.0.0.1:8765/*
   (comprobar el referrer real si el proveedor la rechaza).
7. Configurar límites de cuota y avisos de presupuesto.

La clave de Maps JavaScript es visible en las solicitudes del navegador:
guardar la clave en una variable de entorno evita subirla a GitHub,
pero NO la vuelve secreta. Debe restringirse por API y origen.

Fuentes oficiales:
- https://developers.google.com/maps/documentation/javascript/load-maps-js-api
- https://developers.google.com/maps/documentation/javascript/advanced-markers/add-marker
- https://developers.google.com/maps/api-security-best-practices

## Prueba desde PowerShell en Windows

~~~powershell
git fetch origin
git switch --track origin/experimento/google-maps

# Si ya tienes la rama:
# git switch experimento/google-maps
# git pull origin experimento/google-maps

# Sustituir por una clave real y restringida de Google Cloud:
$env:ENRUTA_GOOGLE_MAPS_API_KEY = "TU_CLAVE_REAL"
python main.py
~~~

Iniciar sesión en Kivy → Ajustes → Probar mapa de Google.
Se abrirá una pestaña en http://127.0.0.1:8765/ . No se activa
sin una API key configurada. Si Google rechaza la clave o la facturación,
revisar la consola del navegador y restricciones HTTP referrer.

Borrar la variable después:
~~~powershell
Remove-Item Env:ENRUTA_GOOGLE_MAPS_API_KEY
~~~

Pruebas locales:
~~~powershell
python -m unittest discover -s tests -v
~~~

Archivos: servicios/google_maps_preview.py, experimentos/google_maps.html,
tests/test_google_maps.py y botón experimental dentro de Ajustes.

## Decisiones y límites

- MapView, navegación y GPS original siguen en la aplicación.
- El servidor de prueba escucha solo en 127.0.0.1, con datos simulados.
- La interfaz no lee ni transmite la ubicación del usuario.
- Se detiene el servidor cuando se cierra la app.
- Esta etapa sirve para comparar visualmente, no para acreditar que
  Google Maps está integrado a la APK.
- Android requiere otra etapa: WebView/SDK móvil, claves restringidas,
  revisión de permisos, rendimiento y pruebas reales.
- Google advierte que páginas embebidas file:// pueden omitir el
  referrer de la clave web, por lo que podría requerirse hosting HTTPS.

Fuentes técnicas:
- https://developers.google.com/maps/api-security-best-practices
- https://kivy.org/doc/stable/guide/android.html
- https://developer.android.com/develop/ui/views/layout/webapps/webview
