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
