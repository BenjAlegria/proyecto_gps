# Fundamentación UX/UI — EnRuta Ya!

## a) Metodología de investigación
- **Encuestas aplicadas:** 17 respuestas, recolectadas mediante un
  formulario online ("Encuesta sobre Uso de Transporte Público e
  Interurbano") entre el 14 y el 28 de septiembre de 2026.
- **Perfil de los participantes:** mayoritariamente jóvenes de 18 a 25
  años (88%), con un participante menor de 18 años y uno mayor de 50.
  71% estudiantes, 18% "otra ocupación" y 12% trabajadores
  independientes. Residentes de Nueva Imperial (29%), Temuco (24%),
  Lautaro (18%), Padre Las Casas (6%) y otras comunas (24%). El uso
  principal declarado es para estudios (71%) y trámites médicos o
  personales (18%).
- **Instrumento:** cuestionario de 15 preguntas de opción única,
  opción múltiple y respuesta abierta, cubriendo frecuencia de uso,
  forma actual de informarse, problemas experimentados, utilidad
  percibida de una app, funciones deseadas y modelo de precio
  preferido.

## b) Resultados principales

- **Hallazgo 1 — La visualización en vivo es la función más pedida.**
  71% de los encuestados eligió "Visualización de recorrido en vivo"
  como la función más importante, y "Ubicación del bus en el mapa"
  fue, empatada en primer lugar, la información que más quieren
  consultar (76%). Un encuestado lo explicó así: *"La visualización
  del recorrido en tiempo real serviría mucho a modo de organización,
  el ver dónde viene y aprox. cuánto le falta por llegar a mi
  paradero, me permitiría salir a una buena hora de mi casa y no
  perder el bus"* (Respuesta 9).

- **Hallazgo 2 — Los horarios actuales no son confiables.** 76% quiere
  "horarios de salida en tiempo real" y 59% pidió "notificaciones de
  retrasos". El problema más reportado es que el bus queda lleno y no
  se puede subir (71%), seguido de que el bus no pasa a la hora
  indicada (41%). Un encuestado de una localidad fuera de Temuco lo
  planteó como un vacío de información: *"personas que viven fuera de
  Temuco no pueden saber cuándo pasa la micro o bus porque no hay
  registro de ese lugar"* (Respuesta 8).

- **Hallazgo 3 — Se informan hoy por canales informales y poco
  confiables.** 59% se informa "por experiencia propia o memoria" y
  35% "preguntándole al conductor"; solo 29% usa el sitio web oficial
  de la empresa. Consistente con eso, la utilidad percibida de una
  app de este tipo fue muy alta: promedio 4.7/5, con 82% marcando el
  puntaje máximo.

- **Hallazgo 4 — La ocupación del bus también preocupa.** 65% quiere
  poder ver la "capacidad de asientos disponibles", y quedarse sin
  subir por bus lleno es, como se dijo, el problema más común (71%).
  Un encuestado lo resumió así: *"Ver si lleva asiento o no para no
  preguntar ya directo en el bus y tener que irme parado"* (Respuesta
  11).

- **Hallazgo 5 — El modelo de pago no debe ser una barrera.** 71%
  contestó que "solo utilizaría la versión gratuita" si la app tuviera
  planes pagos, y solo 6% pagaría por uso.

## c) Matriz hallazgo → decisión de diseño

| Hallazgo | Decisión de diseño | Por qué |
|---|---|---|
| 1. Visualización en vivo es la función más pedida (71%) y la ubicación en mapa la información más deseada (76%) | La pantalla de Inicio es el mapa a pantalla completa (no un buscador de texto ni una lista como pantalla principal) | Es literalmente lo que la mayoría dijo que quiere ver primero |
| 2. Falta de registro de horarios para localidades fuera de Temuco; problema frecuente de retrasos/bus lleno | Modelo de "Compartir ubicación": cualquier usuario que va en la micro puede aportar la posición, sin depender de que la empresa instale GPS | Cubre justo el vacío de información que reportaron los encuestados de localidades más chicas |
| 3. Se informan hoy por memoria o preguntando al conductor (informal, poco confiable) | Pantalla "Recorridos" centraliza todos los horarios y paradas en un solo lugar dentro de la app | Reemplaza el canal informal por uno consultable en cualquier momento |
| 4. 65% quiere ver capacidad de asientos disponibles; 71% ha quedado sin poder subir por bus lleno | Botones "Bus lleno" y "Hay asientos" en Compartir; el estado de ocupación se ve en cada tarjeta de línea y en su detalle | Sin GPS ni sensores en los buses, los propios pasajeros son la fuente del dato, igual que con la ubicación |
| 2 y 4. 59% pidió notificaciones de retrasos; 41% sufrió buses que no pasaron a la hora; 24% cambios de ruta no informados (y 4 de 17 lo eligieron como la función más importante: "Notificaciones de cambios de horario") | Botones "Atrasado" (con minutos) y "Cambio de ruta", pantalla Avisos y notificación cuando el aviso es de una ruta favorita | Convierte el problema más reclamado en una acción de un toque para quien viaja y en una alerta para quien espera |
| 5. 71% solo usaría la versión gratuita | La app no tiene ningún esquema de pago ni función bloqueada | Alineado con lo que la mayoría de los encuestados prefiere |

## d) Justificación de la estructura de la app
La app tiene 6 pantallas: Inicio, Recorridos, Compartir, Avisos,
Ajustes y Perfil. El orden y el peso visual de cada una responden directamente
a la encuesta: como "visualización en vivo" y "ubicación en el mapa"
fueron lo más pedido (hallazgo 1), el mapa ocupa toda la pantalla de
Inicio en vez de compartir espacio con un buscador o una lista larga.
"Recorridos" existe como pantalla aparte porque buena parte de los
encuestados hoy se informa por memoria o preguntando al conductor
(hallazgo 3): centralizar los horarios ahí les da un lugar fijo donde
consultarlos. "Compartir" es su propia pantalla y no una función
escondida, porque sin usuarios dispuestos a compartir su ubicación el
mapa de Inicio no tiene datos que mostrar (hallazgo 2) — se le da la
misma jerarquía de navegación que a Inicio y Recorridos para
incentivar que la gente la use. "Avisos" entra a la barra principal porque notificaciones de
retrasos (59%) y capacidad de asientos (65%) fueron de lo más pedido
después del mapa, y porque quedarse sin subir por bus lleno es el
problema más común (71%); el aviso se envía desde "Compartir" para
que quien va en la micro lo haga en un solo lugar. "Perfil" y "Ajustes" quedaron con menor
jerarquía (Perfil se abre desde un ícono, no desde la barra principal)
porque ninguna pregunta de la encuesta señaló la personalización o la
cuenta de usuario como una prioridad.

## e) Diversidad y accesibilidad
La mayoría de los encuestados son jóvenes de 18 a 25 años, pero la
muestra incluye un menor de 18 y un mayor de 50, y un 18-12% no son
estudiantes (trabajador independiente, otra ocupación). El caso más
revelador es el de la persona mayor de 50 años (Respuesta 3): calificó
con nota máxima (5/5) la utilidad de una app así, pero le puso solo
2/5 a la probabilidad de que realmente la usara — una posible brecha
entre "esto me serviría" y "esto lo voy a usar", típica de usuarios
con menor familiaridad tecnológica. Esto respalda mantener la interfaz
simple: pocos pasos para ver el mapa (no hay que buscar ni loguearse
para ver los buses de una localidad), texto en botones e iconos
grandes, y un lenguaje directo ("Elegir localidad", "Iniciar viaje")
en vez de términos técnicos. [COMPLETAR si hicieron alguna prueba de
uso con esta persona u otro adulto mayor: qué tan fácil le resultó
navegar la app en la práctica].

---
**Nota sobre las citas:** las citas textuales de este documento
provienen directamente de las respuestas abiertas de la encuesta
(archivo `Encuesta sobre Uso de Transporte Público e Interurbano.csv`,
17 respuestas). Los porcentajes se calcularon sobre ese mismo total
(N=17).