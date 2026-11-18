# Fase 1.5 — Preparación de código para backend y mapa alternativo

## Estado
Cambios implementados en la rama `audit/fase-1`. La interfaz aprobada
(`root.kv` y `componentes.kv`) y el proveedor actual (`MapView`) **no se
modificaron en esta fase**.

**Validación:** la persona que usa la app había obtenido 20/20 pruebas antes
de esta fase. Las pruebas nuevas y las 20 anteriores deben volver a ejecutarse
en Windows con Kivy: los cambios posteriores no están validados por ese
resultado anterior.

## Cambios en el código

1. **`servicios/recorridos.py`:** extrae la conversión de duración a minutos
   y el cálculo de posiciones *simuladas*, independiente de MapView. Esto
   permite que el futuro mapa use los mismos cálculos sin copiar lógica.
2. **`servicios/avisos_service.py`:** saneamiento de avisos JSON, ordenación,
   vencimiento y selección del estado actual de cada ruta. Los registros
   incompletos, con tipos desconocidos, timestamps futuros o no finitos se
   excluyen en lugar de hacer fallar una pantalla.
3. **`servicios/ubicacion.py`:** valida latitudes y longitudes y encapsula
   la geolocalización aproximada de IP. La alternativa de escritorio usa
   `https://ipwho.is/` con timeout. El usuario debe aceptar una ventana
   de confirmación antes de esa consulta (su IP pública se comunica al
   proveedor externo; no se guardan los datos IP). No se usa para viajes.
4. **`main.py`:** delega cálculos a servicios, valida ubicaciones, descarta
   resultados GPS/IP tardíos mediante tokens de solicitud, detiene el GPS
   tras la primera posición si solo se solicitó «localizarme» y cancela
   búsquedas pendientes al cerrar sesión o revocar permiso. Si no hay GPS
   no simula que se haya iniciado un viaje compartido.
5. **`servicios/autenticacion.py` y `servicios/almacenamiento.py`:**
   protecciones frente a documentos JSON con tipos incorrectos o
   credenciales incompletas; los perfiles vuelven a valores seguros y
   los errores de autenticación siguen apareciendo como validaciones.
6. **`tests/test_logica.py`:** nuevas pruebas unitarias puras de recorridos,
   avisos y ubicación. Se ampliaron `tests/test_inicio.py` y
   `tests/test_servicios.py` para cubrir respuestas tardías y JSON inválido.

## Cómo probar

Desde la rama `audit/fase-1`:

```powershell
git pull origin audit/fase-1
python -m unittest discover -s tests -v
python main.py
```

Pruebas manuales recomendadas:

- Entrar y salir de sesión, crear cuenta, guardar favoritas y cambiar nombre.
- Cambiar tema, filtrar avisos y enviar reportes locales.
- Pulsar ubicación desde un PC sin GPS: debe pedir confirmación antes de
  consultar al proveedor externo. Cancelar no debe consultar Internet.
- Iniciar un viaje sin GPS: no debe mostrarse como viaje activo ni incrementar
  viajes. Con GPS disponible debe poder iniciarse y detenerse.
- Cerrar sesión o revocar consentimiento con una búsqueda de ubicación
  en curso: no deben reaparecer ubicaciones tardías.

## Límites que no cambia esta fase

- Sigue sin existir un backend, API, autenticación remota, sincronización ni
  rastreo real entre dos dispositivos.
- Los marcadores de buses, tiempos y tarifas siguen siendo de demostración.
- Falta implementar y verificar permisos GPS de ejecución, ciclo de vida
  y funcionamiento en segundo plano en Android; los tests de Windows
  no demuestran compatibilidad con una APK.
- Los JSON locales no equivalen a una base de datos ni a un sistema de cuentas
  seguro entre dispositivos.
- No se envía la ubicación GPS a ningún servidor.

## Próxima etapa: Google Maps experimental

Crear `experimento/google-maps` a partir del código de esta fase,
conservando `audit/fase-1` y el MapView actual como base de comparación.
No comprometer claves Google Maps en Git ni introducir costos de API sin
revisarlos. Probar primero integración, marcadores y rendimiento en Windows
y Android antes de decidir un reemplazo.
