# DOCUMENTATION.md — EnRuta Ya!

Documento técnico y funcional del Proyecto Integrado Final (PIF),
Desarrollo Móvil (A+S), TINF1119.

**Estado (11-11-2026):** prototipo funcional de escritorio con datos
locales y recorridos demostrativos. No existe sincronización de GPS
entre dispositivos ni backend. Existe una rama de prueba Google Maps
para comparar proveedores sin sustituir MapView.

## 1. Problema y objetivo

En zonas de La Araucanía las personas usuarias de buses interurbanos
pueden tener incertidumbre sobre recorridos, demoras y capacidad de
vehículos. El diagnóstico aplicado por el equipo se encuentra en
FUNDAMENTACION-UX-UI.md, con encuesta de 17 respuestas.

EnRuta Ya! busca ofrecer consulta de recorridos y reportes ciudadanos.
La idea futura es compartir ubicaciones GPS temporalmente y con permiso
desde un pasajero que viaja en un bus; **aún no está implementado
entre teléfonos**.

## 2. Tecnología

- Python 3.10+ (usuario ha ejecutado Python 3.10.11).
- Kivy 2.3.1 y KivyMD 2.0.0.
- Kivy Garden MapView 1.0.6 como proveedor estable de mapas.
- Plyer para intentar acceder a GPS/notificaciones cuando estén disponibles.
- JSON locales para usuarios, perfiles, avisos y caché de configuración.
- Requests para configuración remota y geolocalización IP opcional.
- Prueba Google Maps JavaScript API (solo rama experimento/google-maps).

Instalación en Windows desde la raíz del repositorio:

~~~powershell
python -m pip install -r requirements.txt
python main.py
~~~

## 3. Arquitectura de capas (MVC/POO reconocibles)

**Vista:** root.kv + componentes.kv: pantallas, formularios, botones,
interruptores, mapa y tarjetas.

**Controladores/coordinación:** main.py: clase InterurbanoApp (subclase
de MDApp), eventos, navegación y coordinación del estado de la UI.

**Modelos/datos/reglas:** datos_rutas.py, config.py y servicios/*.
Servicios principales:
- autenticacion.py: validar usuario, registrar, iniciar sesión, PBKDF2.
- almacenamiento.py: perfiles y avisos locales JSON.
- recorridos.py: cálculos independientes del mapa y marcadores de demo.
- avisos_service.py: validación, estado e historial de reportes.
- ubicacion.py: coordenadas válidas, geolocalización IP aproximada HTTPS.
- config_remota.py: configuración desde GitHub con fallback a caché.
- notificaciones.py: mensajes de app y del dispositivo cuando se puede.

No es un proyecto MVC académico con clases Model/View/Controller puras,
pero estas responsabilidades están diferenciadas en archivos y se
pueden demostrar con llamadas específicas.

## 4. Pantallas y funciones

1. **Login**: verificación de credenciales locales.
2. **Registro**: creación de cuenta con validaciones.
3. **Inicio**: selector de localidad/destino, mapa, buses simulados.
4. **Recorridos**: catálogo de rutas y detalles referenciales.
5. **Compartir**: selección de línea, solicitud de consentimiento y
   activación de GPS local cuando existe proveedor real; registro de avisos.
6. **Avisos**: historial local de reportes y filtro de favoritas.
7. **Ajustes**: tema, notificaciones, configuración remota, demo, sesión.
8. **Perfil**: nombre, contadores, favoritas y preferencia de ubicación.

La rama de Google Maps agrega en Ajustes un botón experimental que
abre el mapa alternativo en el navegador del PC. No altera Inicio.

## 5. Modelo de datos local

**Usuarios** (data/usuarios.json): nombre normalizado, hash PBKDF2-SHA256
con sal por cuenta y fecha de creación. No guardar claves en texto plano.

**Perfiles** (data/perfiles.json): nombre visible, favoritas, cantidad
de viajes, tema, notificaciones y preferencia de consentimiento.

**Avisos** (data/avisos.json): ruta, tipo, minutos, timestamp, bandera
de origen y autor local. Se consideran vigentes según configuración
y se eliminan del historial según HISTORIAL_S.

**Configuración remota** (data/config_remota_cache.json): mensaje
de Inicio, antispam y vigencia de avisos.

Los archivos dentro de data/ están excluidos por .gitignore. El formato
JSON es adecuado para demo local; no sustituye una BD multiusuario.

## 6. Seguridad y privacidad

- Contraseñas hasheadas con sal y comparación en tiempo constante.
- Datos de usuarios guardados localmente, sin servicio de cuentas remoto.
- Solicitud explícita de consentimiento para compartir ubicación.
- No se publica GPS a otros teléfonos ni se guarda una traza de viaje.
- La alternativa de IP en PC solicita confirmación y consulta HTTPS a
  un proveedor externo. No representa la ubicación de un bus.
- Las solicitudes de ubicación anteriores se invalidan al detener GPS
  o cerrar sesión, para evitar que aparezcan posiciones tardías.
- Los buses y ETA de demo se identifican como simulados.
- Claves de Google Maps no deben subirse al repositorio; usar restricciones
  por aplicación/API, cuotas y presupuestos.

## 7. Pruebas

La batería actual del experimento incluye:
- test_inicio.py: navegación, pantallas, comportamiento de MapView,
  temas, persistencia en flujo local y regresiones GPS/UI.
- test_servicios.py: autenticación, almacenamiento, configuraciones.
- test_logica.py: cálculos, validación de coordenadas y avisos.
- test_google_maps.py: servidor y datos del mapa experimental sin
  contacto con Google Maps real.

Comando:
~~~powershell
python -m unittest discover -s tests -v
~~~

**No afirmar que las pruebas nuevas del experimento pasaron** sin
ejecutar este comando en la máquina del equipo. El estudiante confirmó
la operación de la fase anterior, no de Google Maps con clave real.

Prueba de demo en vivo: crear cuenta o hacer login, seleccionar ruta,
guardar favorita, cerrar sesión/reabrir y comprobar persistencia;
generar y filtrar un aviso. No depende de Google Maps experimental.

## 8. Método MJV App y medición

PENDIENTE para la evaluación E4. La rúbrica requiere:
- Instrumento y estructura de eventos.
- KPIs operacionalizados, fórmula e interpretación.
- Periodo real de recolección, participantes y condiciones.
- Gráficos con datos verdaderos, mejoras y justificación.

Las propuestas concretas están en docs/E4-RUBRICA-CUMPLIMIENTO.md.
No inventar fechas, métricas ni resultados.

## 9. Límites del sistema

- No existe servidor ni comunicación entre dos teléfonos.
- MapView muestra cartografía; posiciones de bus y horarios son demos.
- Sin prueba aún de APK Android de esta rama experimental.
- Google Maps requiere clave autorizada, conexión y facturación.
- El prototipo no está listo para desplegar un servicio público de
  transporte sin verificar datos y proteger la privacidad.

## 10. Referencias internas

- README.md — instrucciones de uso.
- FUNDAMENTACION-UX-UI.md — diagnóstico y fundamentación.
- USO_IA.md — declaración de uso de inteligencia artificial.
- docs/AUDITORIA-FASE-1.md — análisis de riesgos.
- docs/FASE-1-5-REFACTORIZACION.md — refactorización.
- docs/GOOGLE-MAPS-EXPERIMENTO.md — configuración y pruebas de Google.
- docs/E4-RUBRICA-CUMPLIMIENTO.md — matriz de cumplimiento de E4.
