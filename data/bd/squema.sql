-- ============================================================
-- EnRuta Ya! - esquema de base de datos (MySQL 5.7+/8 o MariaDB 10.3+)
--
-- Cómo usarlo: crea una base vacía (por ejemplo `enrutaya`) y ejecuta
-- este archivo completo (phpMyAdmin > Importar, o `mysql enrutaya < schema.sql`).
--
-- Reglas de diseño:
--  * Las contraseñas se guardan con password_hash() de PHP (nunca en claro).
--  * Los tokens de sesión se guardan como hash SHA-256, no en claro.
--  * Los recorridos NO se borran: se marcan como 'eliminado' (borrado
--    suave) para poder recuperarlos y mantener el historial de votos.
--  * Un usuario puede dar un solo voto por recorrido y por aviso (UNIQUE).
--  * La reputación se calcula en una vista (v_reputacion), no se guarda,
--    así nunca se desincroniza de los votos.
-- ============================================================

SET NAMES utf8mb4;

-- ------------------------------------------------------------
-- Roles y permisos (los administras desde tu web)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
  id                      TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre                  VARCHAR(30)  NOT NULL,
  puede_votar             TINYINT(1)   NOT NULL DEFAULT 0,
  puede_crear_recorridos  TINYINT(1)   NOT NULL DEFAULT 0,
  puede_publicar_avisos   TINYINT(1)   NOT NULL DEFAULT 0,
  es_admin                TINYINT(1)   NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY uq_roles_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO roles (id, nombre, puede_votar, puede_crear_recorridos, puede_publicar_avisos, es_admin) VALUES
  (1, 'invitado',   0, 0, 0, 0),   -- solo mira recorridos y mapa
  (2, 'registrado', 1, 1, 1, 0),   -- vota, agrega recorridos y avisa
  (3, 'admin',      1, 1, 1, 1);   -- además entra a la web de administración

-- ------------------------------------------------------------
-- Usuarios (incluye lo que hoy guarda perfiles.json)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
  id                   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  usuario              VARCHAR(30)  NOT NULL,            -- nombre de acceso (login)
  nombre               VARCHAR(30)  NOT NULL,            -- nombre visible
  clave_hash           VARCHAR(255) NOT NULL,            -- password_hash()
  rol_id               TINYINT UNSIGNED NOT NULL DEFAULT 2,
  bloqueado            TINYINT(1)   NOT NULL DEFAULT 0,
  motivo_bloqueo       VARCHAR(255) NULL,
  bloqueado_en         DATETIME     NULL,
  -- ajustes del perfil
  viajes               INT UNSIGNED NOT NULL DEFAULT 0,
  tema_oscuro          TINYINT(1)   NOT NULL DEFAULT 0,
  notificar_favoritas  TINYINT(1)   NOT NULL DEFAULT 1,
  consentimiento_ubic  TINYINT(1)   NOT NULL DEFAULT 0,
  creado_en            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_acceso        DATETIME     NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_usuarios_usuario (usuario),
  KEY ix_usuarios_rol (rol_id),
  CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Sesiones de la app (token que la app manda en cada petición)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sesiones (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  usuario_id  INT UNSIGNED NOT NULL,
  token_hash  CHAR(64)     NOT NULL,                      -- hash('sha256', token)
  creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_en   DATETIME     NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_sesiones_token (token_hash),
  KEY ix_sesiones_usuario (usuario_id),
  CONSTRAINT fk_sesiones_usuario FOREIGN KEY (usuario_id)
    REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Localidades (reemplaza COORDENADAS de datos_rutas.py)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS localidades (
  id      SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  nombre  VARCHAR(60)    NOT NULL,
  lat     DECIMAL(9,6)   NOT NULL,
  lon     DECIMAL(9,6)   NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_localidades_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO localidades (nombre, lat, lon) VALUES
  ('Nueva Imperial',  -38.744200, -72.950300),
  ('Lautaro',         -38.528500, -72.431800),
  ('Carahue',         -38.710300, -73.156100),
  ('Padre Las Casas', -38.768300, -72.597500),
  ('Temuco',          -38.735900, -72.590400),
  ('Victoria',        -38.233300, -72.333300);

-- ------------------------------------------------------------
-- Recorridos (reemplaza LOCALIDADES/RUTAS de datos_rutas.py)
--   estado:
--     en_revision -> recién creado por un usuario, aún sin verificar
--     activo      -> confirmado (por votos o por ti)
--     cuestionado -> muchos votos de "falso": aparece en tu cola de revisión
--     eliminado   -> borrado suave: la app no lo muestra
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recorridos (
  id                INT UNSIGNED NOT NULL AUTO_INCREMENT,
  origen_id         SMALLINT UNSIGNED NOT NULL,
  destino_id        SMALLINT UNSIGNED NOT NULL,
  parada            VARCHAR(80)  NOT NULL,
  frecuencia_min    SMALLINT UNSIGNED NULL,               -- "cada N min"
  tarifa            INT UNSIGNED NULL,                    -- pesos CLP
  duracion_min      SMALLINT UNSIGNED NULL,
  trazado           JSON         NULL,                    -- [[lat, lon], ...] por carretera
  estado            ENUM('en_revision','activo','cuestionado','eliminado')
                    NOT NULL DEFAULT 'en_revision',
  creado_por        INT UNSIGNED NULL,                    -- NULL = cargado por el sistema
  creado_en         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  eliminado_en      DATETIME     NULL,
  eliminado_por     INT UNSIGNED NULL,
  motivo_eliminado  VARCHAR(255) NULL,
  PRIMARY KEY (id),
  KEY ix_recorridos_estado (estado),
  KEY ix_recorridos_origen (origen_id),
  KEY ix_recorridos_destino (destino_id),
  CONSTRAINT fk_rec_origen   FOREIGN KEY (origen_id)  REFERENCES localidades (id),
  CONSTRAINT fk_rec_destino  FOREIGN KEY (destino_id) REFERENCES localidades (id),
  CONSTRAINT fk_rec_creador  FOREIGN KEY (creado_por) REFERENCES usuarios (id) ON DELETE SET NULL,
  CONSTRAINT fk_rec_elimina  FOREIGN KEY (eliminado_por) REFERENCES usuarios (id) ON DELETE SET NULL,
  CONSTRAINT chk_rec_distintos CHECK (origen_id <> destino_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Los 9 recorridos de ejemplo de datos_rutas.py (valores referenciales)
INSERT INTO recorridos (origen_id, destino_id, parada, frecuencia_min, tarifa, duracion_min, estado)
SELECT o.id, d.id, x.parada, x.frecuencia_min, x.tarifa, x.duracion_min, 'activo'
FROM (
  SELECT 'Nueva Imperial' AS origen, 'Temuco'         AS destino, 'Terminal Nueva Imperial' AS parada, 20 AS frecuencia_min, 1500 AS tarifa, 50 AS duracion_min UNION ALL
  SELECT 'Nueva Imperial',           'Carahue',                   'Terminal Nueva Imperial',            45,                   1200,             35 UNION ALL
  SELECT 'Lautaro',                  'Temuco',                    'Parada Balmaceda',                   30,                   1800,             60 UNION ALL
  SELECT 'Lautaro',                  'Victoria',                  'Terminal Lautaro',                   40,                   1000,             35 UNION ALL
  SELECT 'Carahue',                  'Temuco',                    'Terminal Carahue',                   30,                   2500,             80 UNION ALL
  SELECT 'Carahue',                  'Nueva Imperial',            'Terminal Carahue',                   45,                   1200,             35 UNION ALL
  SELECT 'Padre Las Casas',          'Temuco',                    'Parada Balmaceda',                   10,                    700,             20 UNION ALL
  SELECT 'Temuco',                   'Lautaro',                   'Terminal Rodoviario',                30,                   1800,             60 UNION ALL
  SELECT 'Temuco',                   'Nueva Imperial',            'Terminal Rodoviario',                20,                   1500,             50
) AS x
JOIN localidades o ON o.nombre = x.origen
JOIN localidades d ON d.nombre = x.destino
WHERE NOT EXISTS (SELECT 1 FROM recorridos);   -- solo si la tabla está vacía

-- ------------------------------------------------------------
-- Votos de recorrido: "es real" (1) o "es falso" (-1)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS votos_recorrido (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  recorrido_id  INT UNSIGNED NOT NULL,
  usuario_id    INT UNSIGNED NOT NULL,
  valor         TINYINT      NOT NULL,                    -- 1 = real, -1 = falso
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_voto_recorrido (recorrido_id, usuario_id),   -- un voto por usuario
  KEY ix_voto_rec_usuario (usuario_id),
  CONSTRAINT fk_vr_recorrido FOREIGN KEY (recorrido_id) REFERENCES recorridos (id) ON DELETE CASCADE,
  CONSTRAINT fk_vr_usuario   FOREIGN KEY (usuario_id)   REFERENCES usuarios (id)   ON DELETE CASCADE,
  CONSTRAINT chk_vr_valor CHECK (valor IN (-1, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Avisos de pasajeros (lo que hoy guarda avisos.json)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS avisos (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  recorrido_id  INT UNSIGNED NOT NULL,
  autor_id      INT UNSIGNED NULL,
  tipo          ENUM('lleno','asientos','atrasado','cambio_ruta') NOT NULL,
  minutos       SMALLINT UNSIGNED NOT NULL DEFAULT 0,     -- solo para 'atrasado'
  creado_en     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_avisos_recorrido (recorrido_id, creado_en),
  KEY ix_avisos_autor (autor_id),
  CONSTRAINT fk_av_recorrido FOREIGN KEY (recorrido_id) REFERENCES recorridos (id) ON DELETE CASCADE,
  CONSTRAINT fk_av_autor     FOREIGN KEY (autor_id)     REFERENCES usuarios (id)   ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS votos_aviso (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  aviso_id    BIGINT UNSIGNED NOT NULL,
  usuario_id  INT UNSIGNED NOT NULL,
  valor       TINYINT      NOT NULL,                      -- 1 = correcto, -1 = erróneo
  creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_voto_aviso (aviso_id, usuario_id),
  KEY ix_voto_av_usuario (usuario_id),
  CONSTRAINT fk_va_aviso   FOREIGN KEY (aviso_id)   REFERENCES avisos (id)   ON DELETE CASCADE,
  CONSTRAINT fk_va_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE,
  CONSTRAINT chk_va_valor CHECK (valor IN (-1, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Favoritas de cada usuario
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS favoritas (
  usuario_id    INT UNSIGNED NOT NULL,
  recorrido_id  INT UNSIGNED NOT NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (usuario_id, recorrido_id),
  CONSTRAINT fk_fav_usuario   FOREIGN KEY (usuario_id)   REFERENCES usuarios (id)   ON DELETE CASCADE,
  CONSTRAINT fk_fav_recorrido FOREIGN KEY (recorrido_id) REFERENCES recorridos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------
-- Configuración remota (reemplaza la config_remota actual)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS configuracion (
  clave  VARCHAR(50)  NOT NULL,
  valor  VARCHAR(255) NOT NULL,
  PRIMARY KEY (clave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO configuracion (clave, valor) VALUES
  ('antispam_segundos',   '60'),   -- ajusta a los valores que usas hoy
  ('vigencia_aviso_min',  '30'),
  ('mensaje_inicio',      ''),
  ('umbral_cuestionado',  '5'),    -- votos "falso" para pasar a 'cuestionado'
  ('umbral_aviso_dudoso', '-3');

-- ------------------------------------------------------------
-- Bitácora de acciones de administración (quién eliminó/bloqueó qué)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bitacora_admin (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  admin_id    INT UNSIGNED NULL,
  accion      VARCHAR(40)  NOT NULL,       -- 'eliminar_recorrido', 'bloquear_usuario', 'cambiar_rol'...
  entidad     VARCHAR(30)  NOT NULL,       -- 'recorrido', 'usuario'...
  entidad_id  BIGINT UNSIGNED NOT NULL,
  detalle     VARCHAR(255) NULL,
  creado_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_bitacora_entidad (entidad, entidad_id),
  CONSTRAINT fk_bit_admin FOREIGN KEY (admin_id) REFERENCES usuarios (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- VISTAS (para la API y para tu web de administración)
-- ============================================================

-- Recorridos con su conteo de votos. Ordena por (votos_falso - votos_real)
-- DESC para ver arriba los más cuestionados.
CREATE OR REPLACE VIEW v_recorridos AS
SELECT r.id,
       r.estado,
       o.nombre AS origen,
       d.nombre AS destino,
       CONCAT(o.nombre, ' -> ', d.nombre) AS nombre,
       r.parada, r.frecuencia_min, r.tarifa, r.duracion_min,
       r.creado_por, r.creado_en,
       COALESCE(v.votos_real, 0)  AS votos_real,
       COALESCE(v.votos_falso, 0) AS votos_falso
FROM recorridos r
JOIN localidades o ON o.id = r.origen_id
JOIN localidades d ON d.id = r.destino_id
LEFT JOIN (
  SELECT recorrido_id,
         SUM(valor = 1)  AS votos_real,
         SUM(valor = -1) AS votos_falso
  FROM votos_recorrido
  GROUP BY recorrido_id
) v ON v.recorrido_id = r.id;

-- Reputación: 1 punto por aviso publicado, +3 por cada voto "correcto"
-- recibido y -2 por cada "erróneo" (nunca baja de 0).
CREATE OR REPLACE VIEW v_reputacion AS
SELECT u.id AS usuario_id,
       u.usuario,
       COALESCE(a.publicados, 0)  AS avisos,
       COALESCE(b.confirmados, 0) AS confirmados,
       COALESCE(b.erroneos, 0)    AS erroneos,
       GREATEST(0, COALESCE(a.publicados, 0) * 1
                 + COALESCE(b.confirmados, 0) * 3
                 - COALESCE(b.erroneos, 0) * 2) AS puntos
FROM usuarios u
LEFT JOIN (
  SELECT autor_id, COUNT(*) AS publicados
  FROM avisos
  WHERE autor_id IS NOT NULL
  GROUP BY autor_id
) a ON a.autor_id = u.id
LEFT JOIN (
  SELECT av.autor_id,
         SUM(va.valor = 1)  AS confirmados,
         SUM(va.valor = -1) AS erroneos
  FROM avisos av
  JOIN votos_aviso va ON va.aviso_id = av.id
  WHERE av.autor_id IS NOT NULL
  GROUP BY av.autor_id
) b ON b.autor_id = u.id;

-- ============================================================
-- Primer administrador: NO se crea aquí porque necesita un hash real.
-- Desde PHP genera el hash:  echo password_hash('TuClaveSegura', PASSWORD_DEFAULT);
-- y luego ejecuta:
--   INSERT INTO usuarios (usuario, nombre, clave_hash, rol_id)
--   VALUES ('admin', 'Administrador', '<hash generado>', 3);
-- ============================================================