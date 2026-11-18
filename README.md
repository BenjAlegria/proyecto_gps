# EnRuta Ya! — Proyecto Integrado Final (E4)

**Asignatura:** Desarrollo Móvil (A+S), TINF1119 · Instituto Tecnológico UC Temuco.  
**Versión de referencia:** `feature/diseno-v3-sobre-backend-final` (interfaz rediseñada sobre `feature/Ajuste3-PLSFINAL`).

## ¿Qué problema abordamos?

En nuestra investigación diagnóstica recibimos **17 respuestas**, recolectadas entre el 14 y el 28 de septiembre de 2026. Entre los problemas señalados estuvieron los buses llenos (71 %), la incertidumbre de horarios y la falta de información de localidades interurbanas. El 76 % eligió la ubicación del bus en el mapa entre los datos que desea consultar. La muestra es exploratoria; no podemos generalizarla a todos los habitantes de La Araucanía. Los porcentajes y el instrumento están en [FUNDAMENTACION-UX-UI.md](FUNDAMENTACION-UX-UI.md).

Construimos **EnRuta Ya!** para facilitar la consulta de recorridos y el intercambio de reportes comunitarios sobre ocupación, retrasos y cambios de ruta.

## ¿Qué implementamos?

- **Autenticación:** registro e inicio de sesión por correo y contraseña a través de nuestra **API PHP y MySQL**. También permitimos consultar como invitado.
- **Inicio y Recorridos:** mapa interactivo Kivy Garden MapView / OpenStreetMap, selección de localidades, catálogo, detalle, duración y tarifa cuando están disponibles.
- **Avisos comunitarios:** publicar bus lleno, asientos disponibles, atraso o cambio de ruta; consultar novedades, votar avisos y recorridos y acumular puntos de reputación.
- **Compartir viaje:** identificar una línea y una patente o agendar el viaje; iniciar/detener una sesión y mostrar nuestro **GPS local**, previo consentimiento.
- **Perfil:** nombre asociado a la cuenta y puntos provenientes del servidor; favoritas y ajustes guardados localmente por dispositivo.
- **Sincronización:** consultas automáticas al abrir la app y periódicas, caché local para lecturas, cola de algunas acciones pendientes cuando falla internet y reenvío al recuperarlo.
- **Panel de administración web:** administración de recorridos, usuarios, reportes y métricas en `backend/admin/index.php`.
- **Medición MJV App:** registro de eventos de uso con consentimiento, cálculo local de KPIs y generador de gráfico SVG para la defensa.

**Límites reales:** no tenemos posición GPS de buses **en vivo entre teléfonos**, ni llegada estimada (ETA) calculada desde buses reales, ni datos oficiales de las empresas. La ubicación del usuario solo se usa localmente; el código todavía no la publica en el servidor. No debemos presentar recorridos referenciales como seguimiento oficial en tiempo real.

## Tecnologías y arquitectura

```text
Kivy / KivyMD (main.py, root.kv, componentes.kv, tema.py)
           │ HTTP / JSON, X-Token
           ▼
API PHP (backend/api/index.php)
           │ consultas SQL parametrizadas
           ▼
MySQL / MariaDB (backend/sql/enruta_schema.sql)
```

La app móvil **no se conecta directamente a MySQL** ni necesita introducir API keys de Firebase. El servicio remoto está configurado en `config.py` mediante `API_URL`. Conservamos Firebase en archivos históricos de otras ramas, pero **no es el backend de esta versión**.

### Qué datos se guardan

| Lugar | Datos |
|---|---|
| MySQL | cuentas, sesiones, recorridos, geometría, reportes, votos, viajes, puntos y métricas seleccionadas |
| Caché local del cliente | últimas lecturas de recorridos/reportes, sesión y cola de acciones, mediante `servicios/api_cliente.py` |
| JSON local por dispositivo | favoritas, tema, consentimiento y preferencias, mediante `servicios/almacenamiento.py` |
| JSONL local de analítica | eventos de navegación consentidos, mediante `servicios/analitica.py` |

Las contraseñas se procesan con `password_hash()` y `password_verify()` en PHP; **no guardamos contraseñas en el JSON del cliente**. La cuenta sí se comparte entre equipos mediante el servidor; favoritas y tema **todavía no** se sincronizan entre dispositivos.

## Ejecución en Windows

Usamos Python 3.10.11. Recomendamos abrir la terminal en la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Dependencias principales: `kivy==2.3.1`, `kivymd==2.0.0`, `kivy-garden.mapview==1.0.6`, `plyer`, `requests` y `pillow`.

Para probar con el diseño nuevo sin alterar la rama final del equipo:

```powershell
git fetch origin
git switch --track origin/feature/diseno-v3-sobre-backend-final
python main.py
```

Si ya tenemos esa rama local, usamos `git switch feature/diseno-v3-sobre-backend-final` y `git pull --ff-only`. La API requiere un servidor PHP/MySQL operativo y conexión para las funciones remotas; con fallas de red podemos seguir viendo la información que hubiera quedado en caché.

## Pruebas

- Comprobamos mediante un **smoke test Kivy en Linux/Xvfb** que las **10 pantallas** se crean y pueden recorrerse, y repetimos la apertura en resoluciones 320×568, 390×844 y 844×390, en temas claro y oscuro. Esto valida construcción y navegación; no sustituye pruebas manuales de usabilidad.
- El repositorio incluye pruebas de analítica y servicios. **La batería anterior también contiene tests de Firebase y pantallas antiguas**, así que no afirmamos que el conjunto completo sea válido para la arquitectura final hasta revisarlo.
- El equipo debe confirmar con dos dispositivos reales registro/login, avisos, votos y cola offline, además de la instalación Android. El APK queda a cargo del integrante que realizará esa prueba.

## Medición y resultados E4

Con consentimiento activamos **Ajustes → Ayudar a mejorar la app**. La captura local de eventos usa `data/analitica_eventos.jsonl`. Para generar el resumen y gráfico a partir de eventos existentes:

```powershell
python tools/generar_resultados_mjv.py
```

Obtendremos `docs/resultados_mjv/RESULTADOS.md` y `docs/resultados_mjv/grafico_eventos.svg`. **Sin eventos reales de prueba no hay un KPI observado que podamos presentar.** Las instrucciones para las pruebas están en [docs/PROTOCOLO-MJV-APP.md](docs/PROTOCOLO-MJV-APP.md) y el estado de evidencias en [docs/CHECKLIST-E4.md](docs/CHECKLIST-E4.md).

## Documentación para la entrega y la defensa

- [DOCUMENTATION.md](DOCUMENTATION.md): arquitectura, módulos, seguridad y eventos.
- [INFORME-FINAL.md](INFORME-FINAL.md): relato del equipo sobre RA1–RA4 y limitaciones.
- [docs/PROTOCOLO-MJV-APP.md](docs/PROTOCOLO-MJV-APP.md): aplicación del ciclo Medir–Jugar–Validar.
- [docs/REGISTRO-PRUEBAS-USUARIOS.csv](docs/REGISTRO-PRUEBAS-USUARIOS.csv): registro **todavía vacío** de pruebas con participantes.
- [USO_IA.md](USO_IA.md): declaración del uso real de herramientas de apoyo.
- [backend/sql/enruta_schema.sql](backend/sql/enruta_schema.sql): estructura de las diez tablas MySQL.

**Antes de presentar:** completar el periodo, los participantes y las observaciones de MJV; ejecutar el generador con las mediciones obtenidas; fundamentar al menos dos mejoras; ensayar las preguntas de defensa. No atribuimos a la app una medición ni un impacto que no hayamos comprobado.
