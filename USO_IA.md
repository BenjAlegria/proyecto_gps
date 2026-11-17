# Declaración de uso de herramientas de IA — EnRuta Ya!

**Asignatura:** Desarrollo Móvil (A+S), TINF1119 · Proyecto Integrado Final E4.

## Cómo trabajamos

Durante el desarrollo utilizamos herramientas de apoyo para revisar ideas, proponer código, corregir errores, comparar opciones tecnológicas y preparar documentación. **La decisión de qué incorporar, ejecutar, revisar y presentar corresponde a nuestro equipo.** No consideramos válido un fragmento generado solo porque compila; debemos entenderlo y explicarlo en la defensa.

### Herramientas utilizadas

- **Claude (Anthropic):** lo utilizamos durante etapas anteriores para apoyar prototipos, formularios, validaciones y correcciones.
- **ChatGPT (OpenAI):** lo utilizamos para analizar requisitos, revisar la rúbrica, estudiar el código, proponer pruebas, apoyar documentación y el rediseño de interfaz.
- **Codex (OpenAI):** lo utilizamos como asistencia de programación en VS Code para revisar e implementar partes del proyecto y pruebas.
- **Figma:** lo utilizamos para mockups y decisiones visuales. **Debemos confirmar entre integrantes** si se usó alguna función generativa de la herramienta.
- **Otros apoyos:** cada integrante debe verificar si utilizó herramientas adicionales antes de cerrar la declaración.

No atribuimos el trabajo del servidor y MySQL a una herramienta particular si no tenemos registro verificable de qué utilizó el integrante que lo implementó.

## Decisiones y validación

Probamos Google Maps en una rama separada, pero no lo incluimos por dificultades de configuración y facturación; conservamos Kivy Garden MapView y OpenStreetMap. En la versión final **integramos PHP/MySQL para autenticación y datos compartidos**, y conservamos el rediseño de las diez pantallas sobre esa lógica.

Comprobamos mediante una prueba de Kivy en Linux/Xvfb que las diez pantallas abren en distintos tamaños y temas. **Eso no certifica aún el APK, la seguridad del servidor ni la facilidad de uso de personas reales.** Nuestro compañero está encargado de la validación Android y debemos agregar la evidencia cuando exista.

## Qué no hacemos con IA

- No inventamos respuestas de encuestas ni participantes.
- No atribuimos al sistema KPIs o efectos sociales que no hayamos medido.
- No presentamos el GPS local como seguimiento colectivo en tiempo real.
- No usamos el apoyo de IA para sustituir la comprensión individual del código.

Los documentos de entrega se redactan **en primera persona del plural** porque presentan el trabajo del grupo; la redacción no sustituye la revisión y aprobación de los integrantes.

## Responsabilidad antes de entregar

Revisaremos estas declaraciones entre todos, verificaremos las herramientas de cada compañero y citaremos sus usos en la versión de entrega. Podemos mostrar archivos y funciones concretas para explicar qué hace cada parte y por qué la elegimos.
