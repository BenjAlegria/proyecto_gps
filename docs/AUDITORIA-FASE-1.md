# Auditoría técnica — Fase 1 de EnRuta Ya!
**Fecha:** 11 de noviembre de 2026  
**Base revisada:** `feature/ui-redesign` (posterior al rediseño integral de Codex).  
**Rama de auditoría:** `audit/fase-1`  
**Tipo de revisión:** lectura estática del repositorio + pruebas de regresión añadidas; **sin ejecución gráfica o GPS físico en el entorno de auditoría**.

## 1. Resumen ejecutivo

**Conclusión:** la aplicación es una base viable para una demostración local y para continuar el desarrollo, pero **todavía no es un servicio de seguimiento de buses en vivo**. La principal brecha es la ausencia de API/servidor, autenticación compartida y distribución de posiciones y avisos entre teléfonos. Se debe conservar el rediseño de interfaz mientras se desacoplan gradualmente los servicios.

Hay una buena separación inicial entre la UI (Kivy/KivyMD), los datos de ejemplo y los módulos de autenticación, persistencia, notificaciones y configuración remota. El rediseño reciente incorpora `componentes.kv` y `tema.py`, navegación común y pruebas gráficas automatizadas.

## 2. Archivos y subsistemas auditados

| Área | Archivos revisados | Diagnóstico |
|---|---|---|
| UI y navegación | `root.kv`, `componentes.kv`, `tema.py`, `main.py` | Las ocho pantallas están declaradas; barra inferior fuera del ScreenManager; estilo centralizado |
| Mapas y rutas | `main.py`, `datos_rutas.py`, `bus_marker.png` | Marcadores calculados como simulación; estimaciones y tarifas son ejemplos |
| Autenticación | `servicios/autenticacion.py` | Hash PBKDF2-SHA256 con sal, pero las cuentas existen solo en JSON local |
| Almacenamiento | `servicios/almacenamiento.py`, `config.py` | Reemplazo temporal de JSON; no hay control de acceso multiusuario del servidor |
| Configuración | `servicios/config_remota.py`, `remote_config.json` | Descarga con timeout/caché; validación de tipos mejorada en esta rama |
| Notificaciones | `servicios/notificaciones.py`, `main.py` | Notificaciones locales, no push remoto |
| Pruebas | `tests/test_inicio.py`, `tools/verificar_interfaz.py` | Cobertura de pantalla, navegación y flujo local; faltan pruebas de backend y Android |
| Configuración de Git | `.gitignore`, `requirements.txt` | Filtros de archivos sensibles ampliados; dependencias principales fijadas |

## 3. Hallazgos priorizados

### P0 — Requisitos imprescindibles para un producto multiusuario

**A-01. No existe distribución GPS entre dispositivos — pendiente.**  
Evidencia: `main.py`, `iniciar_compartir()` y `actualizar_mi_ubicacion()`. El primero inicia la visualización local; el segundo actualiza un marcador del mapa del mismo teléfono. No aparece ningún cliente que envíe coordenadas al servidor.  
**Acción:** contrato de API y ciclo completo de viaje: iniciar, posición con marca temporal/precisión, consultar por ruta, detener y expirar.

**A-02. Avisos limitados a datos del dispositivo — pendiente.**  
Evidencia: `main.py` → `publicar_aviso()`, `servicios/almacenamiento.py` → `guardar_avisos()`. Los JSON no se sincronizan entre instalaciones.  
**Acción:** crear API de avisos con caducidad, autenticación y antispam impuesto por el servidor, no solo por la aplicación cliente.

**A-03. Las cuentas no son identidades compartidas entre teléfonos — pendiente.**  
Evidencia: `servicios/autenticacion.py` guarda usuarios en `data/usuarios.json`. PBKDF2 protege las contraseñas frente al texto plano, pero ese almacenamiento **no autentica peticiones de otros dispositivos**.  
**Acción:** diseñar autenticación de servidor y migración explícita o recreación de cuentas de prueba, evitando publicar usuarios existentes.

**A-04. Privacidad y expiración de ubicación — pendiente.**  
La futura API debe evitar mostrar identidad del pasajero o conservar trazas indefinidamente. Requerir consentimiento explícito por sesión de viaje, desactivación efectiva y vencimiento automático cuando deja de recibirse GPS. Un GPS compartido representa la posición del teléfono de un pasajero, no telemetría certificada del bus.

### P1 — Robustez y protección de datos antes de incorporar backend

**A-05. Consulta de ubicación aproximada mediante HTTP — pendiente.**  
Evidencia: `main.py` → `_localizar_por_ip()` consulta `http://ip-api.com/json/`. No está cifrada y depende de un tercero para estimar la ubicación.  
**Acción:** evitar un endpoint HTTP en producción; preferir permiso GPS del sistema o un proveedor HTTPS verificado. Si no hay ubicación confiable, mostrar «No disponible». No reemplazar a ciegas por otra API sin validar condiciones de uso.

**A-06. Consentimiento almacenado en perfil — pendiente de definición.**  
Evidencia: `servicios/almacenamiento.py` persiste `consentimiento` y `main.py` lo restaura al iniciar sesión. Actualmente sirve como preferencia de la demo, pero no debe interpretarse automáticamente como autorización para emitir GPS a un servidor en un nuevo viaje.  
**Acción:** solicitar consentimiento contextual antes de cada viaje remoto y permitir revocarlo.

**A-07. Excepciones de interfaz registradas y suprimidas globalmente — pendiente.**  
Evidencia: `main.py` → `ManejadorErrores.handle_exception()` registra errores y devuelve `ExceptionManager.PASS`. Eso evita cierres, pero puede ocultar fallos críticos o dejar estados incoherentes.  
**Acción:** conservar registro, clasificar fallos recuperables/no recuperables y asegurar que las pruebas los detecten.

**A-08. Persistencia JSON local no equivale a base de datos transaccional — pendiente.**  
Evidencia: `servicios/almacenamiento.py` escribe un temporal fijo `<ruta>.tmp` y usa `os.replace`. Resiste cierres a mitad de escritura para un único escritor, pero no incluye bloqueo/concurrencia ni versionado de esquema.  
**Acción:** mantenerlo para preferencias locales; mover viajes y avisos compartidos a almacenamiento del servidor, con validación estructural.

**A-09. Registros locales de credenciales malformedos podrían generar excepciones — pendiente.**  
Evidencia: `servicios/autenticacion.py` supone que `registro["hash"]` y `registro["sal"]` existen y son válidos. Si el JSON contiene un registro con esquema incorrecto, puede producir `KeyError` o `ValueError`, en lugar de un error controlado.  
**Acción:** validar la forma del registro antes de derivar/verificar el hash. No introducir cambios de autenticación más amplios sin pruebas de regresión.

### P2 — Calidad de la información, UX y despliegue

**A-10. Horarios, tarifas, ETAs y posiciones son demostrativos — pendiente.**  
Evidencia: `datos_rutas.py` y `main.py` → `actualizar_mapa()`. La posición se interpola entre origen y destino y no corresponde al trazado real de la ruta.  
**Acción:** etiquetar claramente las simulaciones; no afirmar que una hora estimada sea oficial o precisa. Reemplazarla luego por un ETA basado en trayectoria/velocidad observada y calidad del dato.

**A-11. El antispam de la demo es local — pendiente.**  
Evidencia: `main.py` → `enviar_aviso()` usa `_ultimo_aviso` en memoria. No sirve como control confiable para emisores de distintas cuentas/dispositivos ni reinicios.  
**Acción:** imponer límites de frecuencia y validación en el servidor.

**A-12. Preparación Android incompleta — pendiente.**  
No se observó archivo de configuración de empaquetado Android (p. ej. `buildozer.spec`) en el árbol revisado. El GPS con `plyer`, la autorización de ubicación, el comportamiento en segundo plano, las notificaciones y las zonas seguras deben validarse físicamente.  
**Acción:** plan de empaquetado Android, permisos por versión, pruebas con dos teléfonos y compilación reproducible.

**A-13. Cobertura de pruebas y entorno — parcialmente atendido.**  
El repositorio incluye `tests/test_inicio.py` (11 casos declarados) y capturas de verificación UI reportadas por Codex. En esta rama se incorporó `tests/test_servicios.py` para cubrir autenticación, almacenamiento y configuración sin abrir Kivy. **Las nuevas pruebas aún deben ejecutarse localmente o por CI**; esta auditoría no puede certificar su resultado.

## 4. Correcciones implementadas en esta fase

- **C-01:** `servicios/config_remota.py` ahora exige coincidencia exacta de tipos; evita que `True` se acepte como número entero positivo de antispam/vigencia (en Python, `bool` deriva de `int`).
- **C-02:** `.gitignore` añade exclusiones preventivas de `.env`, archivos de clave, entornos virtuales, logs y artefactos de compilación. **No revoca credenciales ya publicadas ni elimina archivos ya rastreados**.
- **C-03:** `tests/test_servicios.py` agrega pruebas aisladas de registro/login/hash, duplicados, validaciones, perfiles, avisos, JSON corrupto y sanidad/caché de configuración. No modifica `main.py`, `root.kv` ni `componentes.kv`.

## 5. Pruebas de aceptación de la Fase 1

Desde la raíz del repositorio y el entorno virtual:

```powershell
python -m unittest discover -s tests -p "test_servicios.py" -v
python -m unittest discover -s tests -v
python main.py
```

Prueba manual rápida:
1. Registrar un usuario de prueba y hacer login; cerrar e iniciar sesión.
2. Elegir localidad y recorrido; confirmar que el mapa sigue mostrando **Demo**.
3. Agregar/quitar una ruta favorita, cerrar la app y comprobar que persiste.
4. Cambiar tema claro/oscuro y navegar entre las ocho pantallas.
5. En Compartir, iniciar/detener viaje local con consentimiento; revisar mensajes.
6. Generar aviso y confirmar que aparece en la sección Avisos (solo dispositivo).
7. Desactivar red: la app debe abrir con valores guardados o por defecto y no atribuir GPS ficticio.
8. Comprobar que las opciones de Inicio, Recorridos, Compartir, Avisos y Ajustes siguen visibles.

**Evidencia de ejecución:** este documento se fundamenta en lectura estática del código remoto y los reportes ya existentes del repositorio. No se ejecutaron pruebas de Kivy, Android, red o GPS en esta sesión. Los pasos anteriores requieren verificación en tu máquina.

## 6. Orden recomendado después de aprobar esta auditoría

1. Proteger la rama de rediseño y validar las pruebas de la fase 1.
2. Definir la API y modelo de viajes GPS temporales (sin alterar el frontend).
3. Elegir backend tras comparar costos, despliegue y autenticación (por ejemplo FastAPI/PostgreSQL o alternativa gestionada).
4. Implementar API con pruebas de expiración, autenticación y límites.
5. Agregar cliente de red a `servicios/` y conectarlo a iniciar/actualizar/detener viaje.
6. Probar teléfono A ↔ teléfono B; recién entonces sincronizar avisos y calcular ETA.
7. Validar Android y preparar una APK de prueba.

## 7. Separación de trabajo para el equipo

- **Integrante UI:** preserva el rediseño, estados «Demo», «Sin señal» y «Último reporte».
- **Integrante backend:** contrato API, base de datos, privacidad, expiración y autenticación.
- **Integrante integración/pruebas:** cliente HTTP, pruebas de flujos, Android y evidencia.

Trabajar en ramas y aprobar pull requests. Evitar cambios simultáneos extensos en `main.py`/`root.kv`.

## 8. Evidencia y estado final

- Base revisada: `feature/ui-redesign`.
- Rama resultante: `audit/fase-1`.
- La fase 1 **documenta riesgos y añade medidas pequeñas y comprobables**; no implementa GPS remoto ni arregla todos los hallazgos.
- Antes de fusionar, ejecutar pruebas y revisar el PR. No cambiar `main` directamente.
