# MJV App — Protocolo de medición E4

## Objetivo
Evaluar si un pasajero puede encontrar un recorrido de bus y
guardar información útil en EnRuta Ya!. **No evalúa precisión de GPS
ni calidad de rutas oficiales**, porque el mapa contiene demos.

## Instrumento
- Observación estructurada de tareas presenciales.
- Eventos automáticos anónimos en
  `data/analitica_eventos.jsonl`.
- Planilla de pruebas manuales:
  `docs/REGISTRO-PRUEBAS-USUARIOS.csv`.
- Generador de gráficos:
  `python tools/generar_resultados_mjv.py`.

## Consentimiento y participantes
Explicar a cada participante que los eventos de navegación se registran
localmente y no contienen su nombre, GPS, correo ni contraseña.
Solicitar autorización antes de probar. Si no desea participar, no
registrar sus resultados. Al comenzar la prueba, usar una cuenta
de demostración sin datos personales. Evitar subir archivos de eventos
crudos a repositorios públicos.

**Completar antes de presentar:**
- Fecha de inicio real: [POR COMPLETAR]
- Fecha de fin real: [POR COMPLETAR]
- Lugar y modalidad: [POR COMPLETAR]
- Participantes voluntarios (N): [POR COMPLETAR]
- Método de selección y sesgos: [POR COMPLETAR]
- Versión/commit de la app evaluada: [POR COMPLETAR]

## Escenarios (cada participante)

1. **Tarea A: consultar un recorrido.**
   Abrir Recorridos, encontrar una ruta y abrir el detalle.
   Anotar éxito/fracaso, tiempo y confusiones.
2. **Tarea B: guardar una favorita.**
   Guardar la ruta elegida, cerrar y volver a abrir la app,
   comprobar que siga en Perfil. Marcar persistencia.
3. **Tarea C: generar un reporte local.**
   Elegir línea y avisar «Bus lleno» o «Atrasado».
   Comprobar aparición en Avisos. Aclarar que es un reporte
   de prueba, no una alerta real para viajeros.

No activar GPS ni Firebase durante la prueba salvo que esa función
se esté evaluando específicamente con consentimiento adicional.

## Indicadores operacionalizados

| Indicador | Fórmula | Fuente | Interpretación |
|---|---|---|---|
| Éxito en consulta de recorrido | detalles abiertos / entradas a Recorridos × 100 | eventos `busqueda_iniciada`, `recorrido_consultado` | Mide si se llega a abrir un detalle después de entrar a Recorridos |
| Tiempo de consulta | mediana de segundos entre ambos eventos | `duracion_ms` | Menor tiempo suele indicar menor fricción |
| Persistencia de favoritos (prueba manual) | participantes con favorita retenida / participantes que completaron tarea B × 100 | registro manual CSV | Verifica almacenamiento tras reiniciar |
| Reportes registrados | conteo de avisos de usuarios, no los simulados | `aviso_publicado` | Actividad observada; no demuestra calidad del aviso |

Los contadores «sesiones» no representan número de personas.
No confundir eventos con impacto social. La encuesta inicial N=17
es diagnóstico previo, no sustituye la medición de uso.

## Gráficos y conclusiones
Tras ejecutar pruebas reales:

~~~powershell
python tools/generar_resultados_mjv.py
~~~

Consultar `docs/resultados_mjv/RESULTADOS.md` y
`grafico_eventos.svg`. Añadir análisis del CSV manual,
limitaciones y **dos mejoras concretas** justificadas con evidencia.
Comparar impacto y esfuerzo; distinguir hipótesis de hallazgos.

**Si los archivos están vacíos:** presentar la metodología y explicar
la ausencia de medición; no inventar datos.
