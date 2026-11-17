# Lista de verificación E4 — EnRuta Ya! (17-11-2026)

Esta es nuestra lista de evidencias, separando lo que realmente tenemos de lo que debemos producir antes de la presentación. Marcamos como logrado solo aquello que pudimos confirmar revisando el repositorio o las pruebas.

## Código y documentación

- [x] Conservamos la arquitectura final con **Kivy/KivyMD + API PHP + MySQL**.
- [x] Elaboramos la interfaz visual de 10 pantallas en `feature/diseno-v3-sobre-backend-final`.
- [x] Verificamos apertura/navegación de diez pantallas con Kivy en Linux/Xvfb y en tres tamaños, en tema claro y oscuro.
- [x] Actualizamos `README.md` con la tecnología y las limitaciones actuales.
- [x] Actualizamos `DOCUMENTATION.md`, `INFORME-FINAL.md`, este checklist y protocolo MJV.
- [x] Conservamos investigación diagnóstica de 17 respuestas en `FUNDAMENTACION-UX-UI.md`.
- [x] Tenemos código del medidor de eventos y del generador de indicadores.
- [x] Declaramos el uso de herramientas en `USO_IA.md`; cada integrante debe comprobar su parte.
- [x] Respondimos las 84 preguntas oficiales en `docs/GUIA-DEFENSA-84-PREGUNTAS.md`, con respuestas, explicación y archivos que podemos mostrar.

## Evidencia pendiente (no señalar como realizada)

- [ ] Probar **APK Android real** y verificar instalación, permisos y conexión (a cargo del compañero).
- [ ] Probar con dos dispositivos reales creación/acceso a cuenta, reportes, votos y recuperación de red.
- [ ] Revisar y actualizar los tests antiguos que siguen refiriéndose a Firebase y pantallas anteriores.
- [ ] Ejecutar pruebas MJV con consentimiento de personas voluntarias; completar `docs/REGISTRO-PRUEBAS-USUARIOS.csv`.
- [ ] Registrar periodo, lugar/modalidad, N de participantes y commit exacto evaluado.
- [ ] Generar `docs/resultados_mjv/RESULTADOS.md` y `grafico_eventos.svg` **a partir de datos reales**.
- [ ] Interpretar KPIs y observaciones; justificar al menos dos propuestas de mejora.
- [ ] Comprobar accesibilidad con usuarios/tamaños reales y documentar limitaciones.
- [ ] Confirmar credenciales/secretos del servidor y corregir cualquier exposición en ramas antiguas.
- [ ] Ensayar exposición y **defensa individual** del banco de 84 preguntas, mostrando código y cálculos. La guía escrita existe, pero debemos practicar cada uno por separado.

## Secuencia que ensayaremos

1. Explicamos el problema y la encuesta diagnóstica (**RA1**).
2. Mostramos login, invitado, Inicio, Recorridos y Detalle (**RA2**).
3. Publicamos un aviso de prueba; explicamos API PHP/MySQL, votación y caché.
4. Mostramos `main.py → _medir()`, `servicios/analitica.py → Registrador` y el JSONL.
5. Explicamos el consentimiento y el ciclo **Medir → Jugar → Validar**.
6. Mostramos con resultados **reales** éxito y tiempo de consulta; si no los tenemos, explicamos que la medición no ha concluido.
7. Conectamos observaciones con dos decisiones y sus limitaciones (**RA3 / ética**).

## Para exportar los KPIs

```powershell
python tools/generar_resultados_mjv.py
```

Este comando **no fabrica mediciones**. Si falta el archivo de eventos o no hay búsquedas, muestra «Sin datos». El CSV de pruebas manuales está vacío y debe llenarse solo con participantes que hayan aceptado.

## Información que debemos saber defender

- `main.py`: pantalla → callback, hilos, sincronización, consentimiento, GPS y búsqueda.
- `servicios/api_cliente.py`: solicitudes HTTP, caché y cola offline.
- `backend/api/index.php`: autenticación, autorización, consultas y eventos recibidos.
- `backend/sql/enruta_schema.sql`: diez tablas MySQL.
- `servicios/analitica.py`: evento local, `json.dumps`, UTC, `a`, `resumen()`.
- `tools/generar_resultados_mjv.py`: generación del reporte y gráfico SVG.

**Nota:** no afirmamos que el GPS de buses en vivo esté terminado. Solo compartimos reportes comunitarios entre usuarios; el GPS de un viaje sigue siendo local.
