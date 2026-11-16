# Lista de verificación final — E4 PIF EnRuta Ya! (16-11-2026)

## Entregables exigidos por la rúbrica
- [x] Código fuente GitHub en rama de trabajo `feature/ajustesV2`.
- [x] README con instrucciones de uso, arquitectura y limitaciones.
- [x] DOCUMENTATION.md (vistas/modelos/controladores, seguridad y KPI).
- [x] INFORME-FINAL.md (borrador estructurado, por completar con medición real).
- [x] Encuesta diagnóstica N=17 en `FUNDAMENTACION-UX-UI.md`.
- [x] Declaración actualizada de IA en `USO_IA.md`.
- [x] Analítica local por eventos y generador de gráfico SVG.
- [x] Firebase RTDB opcional con reglas y tests simulados.
- [ ] **Ejecutar pruebas visuales de Kivy en Windows** con esta rama.
- [ ] **Crear proyecto Firebase y validar 2 instancias** si el tiempo lo permite.
- [ ] **Realizar pruebas con personas voluntarias**, registrar periodo, N y escenario.
- [ ] **Generar resultados y gráficos** con eventos reales, analizar y proponer 2 mejoras.
- [ ] **Revisar y completar Informe Final** sin placeholders.
- [ ] **Ensayar la demo de 8–10 minutos y roles del equipo**.
- [ ] **APK Android real** si resulta viable; opcional respecto a demo de PC.
- [ ] **Rotar contraseña MySQL expuesta en feature/ajusteV1** y revisar historial.

## Demostración recomendada (sección 1/2, 8–10 min)

1. Presentar problema con la encuesta y conectar 4 funcionalidades (1–1.5 min).
2. Mostrar Registro/Login, Inicio con MapView, búsqueda y detalle (1.5 min).
3. Agregar favorita, cerrar/reabrir y comprobar persistencia JSON (1 min).
4. Publicar aviso local; explicar por qué es reporte ciudadano y no dato oficial (1 min).
5. En Ajustes habilitar Participar en medición con consentimiento, entrar a
   Recorridos, abrir detalle y volver a Analítica para mostrar KPI (1.5 min).
6. Mostrar resultados MJV del periodo real, gráficos e interpretación (1.5–2 min).
7. Describir arquitectura, Firebase opcional, ética, limitaciones, IA y mejoras (1.5 min).

**Ojo:** para el KPI de búsqueda, activar la medición **antes** de entrar
a Recorridos y abrir un detalle. Nunca inventar los números.

## Puesta en marcha

~~~powershell
git fetch origin
git switch --track origin/feature/ajustesV2
# O si ya existe:
# git switch feature/ajustesV2
# git pull --ff-only origin feature/ajustesV2

python -m unittest discover -s tests -v
python main.py
~~~

Si hay cambios locales, respaldarlos antes de cambiar rama.
Firebase es opcional: si no existe configuración, mantenerlo apagado.

Para generar resultados después de las pruebas:

~~~powershell
python tools/generar_resultados_mjv.py
~~~

Incluir el gráfico de `docs/resultados_mjv/grafico_eventos.svg` en la
presentación y discutir el resultado junto con los registros manuales.
