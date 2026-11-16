"""Genera informe MJV y gráfico SVG solo con eventos realmente capturados.

Uso: python tools/generar_resultados_mjv.py
Salida: docs/resultados_mjv/RESULTADOS.md + grafico_eventos.svg
No publica usuarios ni ubicaciones; no inventa datos si no hay eventos.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from servicios.analitica import leer_eventos, resumen  # noqa: E402


def grafico_conteos(datos):
    items = [
        ("Sesiones", datos["sesiones"]),
        ("Búsquedas iniciadas", datos["busquedas"]),
        ("Consultas exitosas", datos["consultas_exitosas"]),
        ("Avisos publicados", datos["avisos_publicados"]),
        ("Favoritos agregados", datos["favoritos_agregados"]),
    ]
    maximo = max([n for _, n in items] + [1])
    rects = []
    for i, (titulo, valor) in enumerate(items):
        y = 65 + 65 * i
        w = round(470 * valor / maximo)
        rects.extend([
            f'<text x="22" y="{y}" font-size="15" fill="#13233e">{escape(titulo)}</text>',
            f'<rect x="22" y="{y+12}" width="470" height="22" rx="6" fill="#e3eafa"/>',
            f'<rect x="22" y="{y+12}" width="{w}" height="22" rx="6" fill="#2867e8"/>',
            f'<text x="505" y="{y+29}" font-size="15" font-weight="bold" fill="#13233e">{valor}</text>',
        ])
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 570 430" '
        'role="img" aria-label="Conteo real de eventos EnRuta Ya!">'
        '<rect width="570" height="430" fill="#ffffff"/>'
        '<text x="22" y="32" font-size="20" font-weight="bold" '
        'fill="#102a54">Eventos registrados · MJV App</text>'
        + "".join(rects)
        + '<text x="22" y="410" font-size="12" fill="#617086">'
        'Fuente: eventos locales anónimos, no posiciones GPS</text></svg>'
    )


def redactar(datos):
    n = datos["busquedas"]
    aciertos = datos["consultas_exitosas"]
    exito = (f'{datos["exito_busqueda_pct"]}%' if n else
             "Sin datos (denominador = 0)")
    mediana = (f'{datos["mediana_busqueda_s"]} segundos'
               if datos["mediana_busqueda_s"] is not None else "Sin datos")
    inicio = datos["periodo_inicio_utc"] or "Sin mediciones"
    fin = datos["periodo_fin_utc"] or "Sin mediciones"
    advertencia = (
        "**NO HAY DATOS SUFICIENTES PARA CONCLUIR:** antes de presentar "
        "resultados hay que realizar pruebas reales y ejecutar este comando."
        if n == 0 else
        "**INTERPRETACIÓN:** este indicador mide solo la ruta de prueba "
        "Recorridos → detalle; no demuestra la precisión del GPS ni "
        "el impacto social por sí solo."
    )
    return f"""# Resultados MJV App — EnRuta Ya!

> Generado únicamente desde eventos observados. Sin datos de GPS, cuentas
> ni porcentajes inventados. Registrar participantes y condiciones de
> pruebas en el protocolo aparte.

## Periodo observado

- **Inicio UTC:** {inicio}
- **Fin UTC:** {fin}
- **Sesiones anónimas registradas:** {datos["sesiones"]}
- **Eventos registrados:** {datos["eventos"]}

## KPIs operacionalizados

| KPI | Definición | Resultado |
|---|---|---|
| Éxito al buscar recorrido | Consultas que abren detalle / entradas a Recorridos × 100 | {aciertos}/{n} = {exito} |
| Tiempo para encontrar recorrido | Mediana de segundos entre entrar a Recorridos y abrir detalle | {mediana} |
| Avisos registrados | Número de avisos locales publicados por usuarios, excluye simulados | {datos["avisos_publicados"]} |
| Favoritos agregados | Veces que se guardó una ruta en favoritas | {datos["favoritos_agregados"]} |

![Gráfico de eventos](grafico_eventos.svg)

## Lectura y limitaciones

{advertencia}

Estos datos proceden del dispositivo donde se ejecutó la app. Una
sesión es una ejecución, **no una persona**. La consulta de recorrido
se registra al abrir un detalle desde la pantalla Recorridos. No hay
seguimiento GPS remoto ni verificación de horarios. No usar los datos
como evidencia de impacto social sin un protocolo de usuarios.

## Mejoras candidatas a contrastar con participantes

1. **Buscar recorridos más rápido:** si la mediana observada resulta alta,
   facilitar acceso directo a destino y filtros; evaluar antes/después.
2. **Explicar mejor qué datos son simulados:** observar si los
   participantes confunden ETA de ejemplo con telemetría real;
   aumentar visibilidad de avisos de demostración.

Estas son **hipótesis**, no conclusiones medidas. Documentar
participantes, tarea, observaciones y justificación antes de
presentarlas como hallazgos.

## Evidencia reproducible

Ejecutar en la raíz del proyecto:

```powershell
python tools/generar_resultados_mjv.py
```

Archivo original: `data/analitica_eventos.jsonl` (local, excluido de Git).
No subir el archivo bruto sin autorización y revisión de privacidad.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eventos", default=None, help="Ruta a JSONL de medición")
    ap.add_argument("--salida", default=str(ROOT / "docs" / "resultados_mjv"))
    args = ap.parse_args()
    eventos = leer_eventos(args.eventos) if args.eventos else leer_eventos()
    datos = resumen(eventos)
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "grafico_eventos.svg").write_text(
        grafico_conteos(datos), encoding="utf-8")
    (salida / "RESULTADOS.md").write_text(redactar(datos), encoding="utf-8")
    print("Informe generado:", salida / "RESULTADOS.md")
    print("Búsquedas registradas:", datos["busquedas"])
    if datos["busquedas"] == 0:
        print("Faltan sesiones reales de evaluación; NO hay KPI de éxito todavía.")


if __name__ == "__main__":
    main()
