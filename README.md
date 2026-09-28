# Interurbano Sur

App móvil para consultar en tiempo real la ubicación en el mapa y el
tiempo de llegada de los buses interurbanos (Lautaro, Padre Las Casas,
Nueva Imperial → Temuco, entre otros recorridos).

## Problema que resuelve
[COMPLETAR: 2-3 líneas describiendo el problema real detectado en el
diagnóstico con el socio comunitario — ej. falta de información
confiable de horarios de buses interurbanos en localidades rurales].

## Usuario objetivo
[COMPLETAR: quién usa la app — ej. habitantes de comunas rurales de la
Araucanía que se desplazan a Temuco en bus interurbano].

## Pantallas
1. **Inicio** — buscador de destino/línea, mapa (placeholder) y líneas
   cercanas con tiempo estimado de llegada.
2. **Recorridos** — listado completo de recorridos y sus próximos
   horarios.
3. **Perfil** — datos del usuario y espacio para rutas favoritas.

## Requisitos
- Python 3.10+
- Kivy 2.3+
- KivyMD 2.0+

Instalación:
```bash
pip install kivy kivymd
```

## Ejecución
```bash
python main.py
```

## Estructura del proyecto
```
interurbano_app/
├── main.py     # Lógica: App, pantallas, validaciones, navegación
├── root.kv     # Interfaz declarativa (KV Language)
├── README.md
└── FUNDAMENTACION-UX-UI.md
```

## Capturas de pantalla
[COMPLETAR: agregar 3 capturas, una por pantalla]

## Declaración de uso de IA
[COMPLETAR: indicar qué partes se generaron o apoyaron con IA (ej.
estructura base del código Kivy/KivyMD) y qué partes son trabajo
propio del equipo, según lo exigido por la pauta].
