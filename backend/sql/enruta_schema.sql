-- EnRuta Ya! · esquema MySQL / MariaDB (importar desde phpMyAdmin)
-- La app NUNCA se conecta a la base: solo habla con la API PHP.
-- Roles: "invitado" = sin cuenta (solo lectura); "registrado" = con cuenta;
-- "admin" = solo para el panel web.

SET NAMES utf8mb4;
SET time_zone = '+00:00';

CREATE TABLE usuarios (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  correo        VARCHAR(120) NOT NULL UNIQUE,
  nombre        VARCHAR(30)  NOT NULL,
  clave_hash    VARCHAR(255) NOT NULL,              -- password_hash() de PHP
  rol           ENUM('registrado','admin') NOT NULL DEFAULT 'registrado',
  puntos        INT NOT NULL DEFAULT 0,             -- caché; la verdad está en puntos_movimientos
  bloqueado     TINYINT(1) NOT NULL DEFAULT 0,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE sesiones (
  token_hash    CHAR(64) PRIMARY KEY,               -- sha256 del token; el token en claro solo lo tiene la app
  usuario_id    INT UNSIGNED NOT NULL,
  expira_en     DATETIME NOT NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  INDEX (expira_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE recorridos (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(80)  NOT NULL UNIQUE,       -- "Temuco -> Nueva Imperial"
  origen        VARCHAR(60)  NOT NULL,
  destino       VARCHAR(60)  NOT NULL,
  parada        VARCHAR(120) NOT NULL DEFAULT '',
  frecuencia    VARCHAR(40)  NOT NULL DEFAULT '',
  duracion_min  SMALLINT UNSIGNED NULL,
  tarifa        INT UNSIGNED NULL,
  creado_por    INT UNSIGNED NULL,
  estado        ENUM('pendiente','verificado','oculto') NOT NULL DEFAULT 'pendiente',
  votos_ok      INT UNSIGNED NOT NULL DEFAULT 0,    -- cachés recalculadas por la API
  votos_mal     INT UNSIGNED NOT NULL DEFAULT 0,
  actualizado_en DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (creado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
  INDEX (estado), INDEX (actualizado_en)            -- actualizado_en sirve para sincronizar solo lo nuevo
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Línea A -> B: con 2 puntos es una recta; con más, sigue las calles.
CREATE TABLE recorrido_puntos (
  recorrido_id  INT UNSIGNED NOT NULL,
  orden         SMALLINT UNSIGNED NOT NULL,         -- 0 = punto A, el último = punto B
  lat           DECIMAL(9,6) NOT NULL,
  lon           DECIMAL(9,6) NOT NULL,
  PRIMARY KEY (recorrido_id, orden),
  FOREIGN KEY (recorrido_id) REFERENCES recorridos(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Un voto por usuario y recorrido: 1 = "es real", -1 = "es falso".
CREATE TABLE votos_recorrido (
  usuario_id    INT UNSIGNED NOT NULL,
  recorrido_id  INT UNSIGNED NOT NULL,
  valor         TINYINT NOT NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (usuario_id, recorrido_id),
  FOREIGN KEY (usuario_id)   REFERENCES usuarios(id)   ON DELETE CASCADE,
  FOREIGN KEY (recorrido_id) REFERENCES recorridos(id) ON DELETE CASCADE,
  CHECK (valor IN (-1, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE avisos (
  id            CHAR(32) PRIMARY KEY,               -- uuid generado por la app (evita duplicados al reintentar)
  recorrido_id  INT UNSIGNED NOT NULL,
  usuario_id    INT UNSIGNED NOT NULL,
  tipo          ENUM('lleno','asientos','atrasado','cambio_ruta') NOT NULL,
  minutos       SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  votos_ok      INT UNSIGNED NOT NULL DEFAULT 0,
  votos_mal     INT UNSIGNED NOT NULL DEFAULT 0,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (recorrido_id) REFERENCES recorridos(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id)   REFERENCES usuarios(id)   ON DELETE CASCADE,
  INDEX (recorrido_id, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE votos_aviso (
  usuario_id    INT UNSIGNED NOT NULL,
  aviso_id      CHAR(32) NOT NULL,
  valor         TINYINT NOT NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (usuario_id, aviso_id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  FOREIGN KEY (aviso_id)   REFERENCES avisos(id)   ON DELETE CASCADE,
  CHECK (valor IN (-1, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Compartir ubicación: exige patente O un viaje agendado.
CREATE TABLE viajes (
  id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NOT NULL,
  recorrido_id  INT UNSIGNED NOT NULL,
  patente       VARCHAR(8) NULL,                    -- normalizada en mayúsculas, sin guion
  agendado_para DATETIME NULL,
  inicio        DATETIME NULL,
  fin           DATETIME NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id)   REFERENCES usuarios(id)   ON DELETE CASCADE,
  FOREIGN KEY (recorrido_id) REFERENCES recorridos(id) ON DELETE CASCADE,
  CHECK (patente IS NOT NULL OR agendado_para IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Registro auditable de cada punto ganado o perdido (para el panel y para revertir abusos).
CREATE TABLE puntos_movimientos (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT UNSIGNED NOT NULL,
  delta         SMALLINT NOT NULL,
  motivo        ENUM('voto_recorrido','voto_aviso','viaje_completado','ajuste_admin') NOT NULL,
  ref_id        VARCHAR(40) NULL,
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
  INDEX (usuario_id, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Métricas anónimas para el panel (solo si el usuario aceptó medir).
CREATE TABLE eventos (
  id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tipo          VARCHAR(40) NOT NULL,
  sesion        CHAR(16) NOT NULL,                  -- id aleatorio de sesión, sin usuario ni ubicación
  creado_en     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX (tipo, creado_en)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
