-- Datos de ejemplo para probar (ajusta nombres, paradas y coordenadas a tus recorridos reales).
-- Las coordenadas son aproximadas (centro de cada ciudad); con 2 puntos la línea A->B es una recta.
INSERT INTO recorridos (nombre, origen, destino, parada, frecuencia, duracion_min, tarifa, estado) VALUES
 ('Temuco -> Nueva Imperial', 'Temuco', 'Nueva Imperial', 'Terminal de buses rurales', 'Cada 30 min', 50, 1500, 'pendiente'),
 ('Nueva Imperial -> Temuco', 'Nueva Imperial', 'Temuco', 'Plaza de Armas', 'Cada 30 min', 50, 1500, 'pendiente'),
 ('Lautaro -> Temuco',        'Lautaro',        'Temuco', 'Terminal de buses', 'Cada 20 min', 45, 1800, 'pendiente');

INSERT INTO recorrido_puntos (recorrido_id, orden, lat, lon)
SELECT id, 0, -38.7359, -72.5904 FROM recorridos WHERE nombre = 'Temuco -> Nueva Imperial'
UNION ALL SELECT id, 1, -38.7447, -72.9500 FROM recorridos WHERE nombre = 'Temuco -> Nueva Imperial'
UNION ALL SELECT id, 0, -38.7447, -72.9500 FROM recorridos WHERE nombre = 'Nueva Imperial -> Temuco'
UNION ALL SELECT id, 1, -38.7359, -72.5904 FROM recorridos WHERE nombre = 'Nueva Imperial -> Temuco'
UNION ALL SELECT id, 0, -38.5306, -72.4336 FROM recorridos WHERE nombre = 'Lautaro -> Temuco'
UNION ALL SELECT id, 1, -38.7359, -72.5904 FROM recorridos WHERE nombre = 'Lautaro -> Temuco';
