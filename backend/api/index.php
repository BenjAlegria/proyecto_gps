<?php
declare(strict_types=1);
/*
 * EnRuta Ya! · API (puente entre la app y MySQL)
 * Uso: https://tu-dominio/api/index.php?r=<ruta>   (JSON de entrada y salida)
 * Sesión: la app envía el header  X-Token: <token>  (sin token = invitado).
 *
 *  GET  ping                 salud del servidor (la app lo usa para saber si hay conexión)
 *  POST auth_registro        {correo, clave, nombre?}
 *  POST auth_login           {correo, clave}
 *  POST auth_logout
 *  GET  perfil
 *  POST perfil_nombre        {nombre}
 *  GET  recorridos           ?desde=<servidor_ts>  (sincronización incremental)
 *  GET  recorrido            ?id=   detalle + línea A->B + avisos con votos
 *  POST recorrido_crear      {nombre, origen, destino, parada?, frecuencia?, duracion_min?, tarifa?, puntos:[{lat,lon},...]}
 *  POST voto_recorrido       {id, valor: 1|-1}
 *  GET  avisos               ?recorrido_id=
 *  POST aviso_crear          {id(32 hex), recorrido_id, tipo, minutos?}
 *  POST voto_aviso           {id, valor: 1|-1}
 *  POST viaje_iniciar        {recorrido_id, patente? , agendado_para?}  (al menos uno)
 *  POST viaje_fin            {id}
 *  POST evento               {tipo, sesion}   métricas anónimas
 */
require __DIR__ . '/config.php';

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

const NIVELES = [[0, 'Novato'], [20, 'Colaborador'], [60, 'Confiable'], [150, 'Verificador']];
const TIPOS_AVISO = ['lleno', 'asientos', 'atrasado', 'cambio_ruta'];
const EVENTOS_OK = ['aplicacion_iniciada', 'pantalla_abierta', 'login_exitoso', 'login_fallido',
    'registro_exitoso', 'favorito_agregado', 'favorito_eliminado', 'aviso_publicado', 'busqueda_completada'];

// ---------- utilidades ----------
function salir(int $codigo, array $datos = []): void {
    http_response_code($codigo);
    if ($codigo !== 204) {
        echo json_encode($datos, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
    exit;
}

function q(mysqli $db, string $sql, string $tipos = '', array $p = []): array {
    $st = $db->prepare($sql);
    if ($tipos !== '') $st->bind_param($tipos, ...$p);
    $st->execute();
    $r = $st->get_result();
    $out = $r ? $r->fetch_all(MYSQLI_ASSOC) : [];
    $st->close();
    return $out;
}

function ejecutar(mysqli $db, string $sql, string $tipos = '', array $p = []): int {
    $st = $db->prepare($sql);
    if ($tipos !== '') $st->bind_param($tipos, ...$p);
    $st->execute();
    $n = $st->affected_rows;
    $st->close();
    return $n;
}

function nivel(int $puntos): array {
    $actual = NIVELES[0];
    $siguiente = null;
    foreach (NIVELES as $n) {
        if ($puntos >= $n[0]) $actual = $n;
        elseif ($siguiente === null) $siguiente = $n;
    }
    return ['nombre' => $actual[1], 'faltan' => $siguiente ? $siguiente[0] - $puntos : 0];
}

function perfil_de(mysqli $db, int $uid): array {
    $f = q($db, "SELECT id, correo, nombre, rol, puntos FROM usuarios WHERE id=?", 'i', [$uid])[0];
    $f['nivel'] = nivel((int)$f['puntos']);
    return $f;
}

function usuario(mysqli $db): ?array {
    $t = $_SERVER['HTTP_X_TOKEN'] ?? '';
    if ($t === '') return null;
    $f = q($db, "SELECT u.id, u.bloqueado FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id
                 WHERE s.token_hash = ? AND s.expira_en > UTC_TIMESTAMP()", 's', [hash('sha256', $t)]);
    return ($f && !$f[0]['bloqueado']) ? perfil_de($db, (int)$f[0]['id']) : null;
}

function exigir(mysqli $db): array {
    $u = usuario($db);
    if (!$u) salir(401, ['error' => 'Inicia sesión para hacer esto.', 'codigo' => 'auth']);
    return $u;
}

function nuevo_token(mysqli $db, int $uid): string {
    $t = bin2hex(random_bytes(32));
    ejecutar($db, "INSERT INTO sesiones (token_hash, usuario_id, expira_en)
                   VALUES (?, ?, DATE_ADD(UTC_TIMESTAMP(), INTERVAL ? DAY))", 'sii', [hash('sha256', $t), $uid, TOKEN_DIAS]);
    return $t;
}

function dar_puntos(mysqli $db, int $uid, int $delta, string $motivo, string $ref): void {
    ejecutar($db, "INSERT INTO puntos_movimientos (usuario_id, delta, motivo, ref_id) VALUES (?, ?, ?, ?)",
        'iiss', [$uid, $delta, $motivo, $ref]);
    ejecutar($db, "UPDATE usuarios SET puntos = GREATEST(0, puntos + ?) WHERE id = ?", 'ii', [$delta, $uid]);
}

// ---------- votos y puntos (mismo mecanismo para recorridos y avisos) ----------
// Un voto por usuario; repetir el mismo voto no cambia nada (seguro para reintentos).
// Puntos al AUTOR: recorrido real +2 / falso -3; aviso correcto +1 / erróneo -1.
function votar(mysqli $db, array $u, string $tipo, string $id, int $valor): array {
    if (!in_array($valor, [1, -1], true)) salir(422, ['error' => 'Voto inválido.']);
    if ($tipo === 'recorrido') {
        [$tv, $tabla, $col, $tp, $autorCol, $ok, $mal, $motivo] = ['votos_recorrido', 'recorridos', 'recorrido_id', 'i', 'creado_por', 2, -3, 'voto_recorrido'];
        $idv = (int)$id;
    } else {
        if (!preg_match('/^[a-f0-9]{32}$/', $id)) salir(422, ['error' => 'Aviso inválido.']);
        [$tv, $tabla, $col, $tp, $autorCol, $ok, $mal, $motivo] = ['votos_aviso', 'avisos', 'aviso_id', 's', 'usuario_id', 1, -1, 'voto_aviso'];
        $idv = $id;
    }
    $efecto = fn(int $v): int => $v === 1 ? $ok : ($v === -1 ? $mal : 0);

    $db->begin_transaction();
    $f = q($db, "SELECT $autorCol AS autor FROM $tabla WHERE id = ? FOR UPDATE", $tp, [$idv]);
    if (!$f) { $db->rollback(); salir(404, ['error' => 'No existe.']); }
    $autor = $f[0]['autor'] !== null ? (int)$f[0]['autor'] : null;
    if ($autor === (int)$u['id']) { $db->rollback(); salir(403, ['error' => 'No puedes votar tu propio aporte.']); }

    $prev = q($db, "SELECT valor FROM $tv WHERE usuario_id = ? AND $col = ?", 'i' . $tp, [$u['id'], $idv]);
    $antes = $prev ? (int)$prev[0]['valor'] : 0;
    if ($antes !== $valor) {
        ejecutar($db, "INSERT INTO $tv (usuario_id, $col, valor) VALUES (?, ?, ?)
                       ON DUPLICATE KEY UPDATE valor = VALUES(valor)", 'i' . $tp . 'i', [$u['id'], $idv, $valor]);
        $delta = $efecto($valor) - $efecto($antes);
        if ($autor !== null && $delta !== 0) dar_puntos($db, $autor, $delta, $motivo, (string)$idv);
        ejecutar($db, "UPDATE $tabla t SET
              t.votos_ok  = (SELECT COUNT(*) FROM $tv v WHERE v.$col = t.id AND v.valor = 1),
              t.votos_mal = (SELECT COUNT(*) FROM $tv v WHERE v.$col = t.id AND v.valor = -1)
              WHERE t.id = ?", $tp, [$idv]);
    }
    $c = q($db, "SELECT votos_ok, votos_mal" . ($tipo === 'recorrido' ? ", estado" : "") . " FROM $tabla WHERE id = ?", $tp, [$idv])[0];
    if ($tipo === 'recorrido' && in_array($c['estado'], ['pendiente', 'verificado'], true)) {
        // Verificado: >=5 votos "real" y >=70% a favor. Oculto: >=5 "falso" y >=60% en contra.
        $total = (int)$c['votos_ok'] + (int)$c['votos_mal'];
        $nuevo = 'pendiente';
        if ($c['votos_ok'] >= 5 && $c['votos_ok'] >= 0.7 * $total) $nuevo = 'verificado';
        elseif ($c['votos_mal'] >= 5 && $c['votos_mal'] >= 0.6 * $total) $nuevo = 'oculto';
        if ($nuevo !== $c['estado']) {
            ejecutar($db, "UPDATE recorridos SET estado = ? WHERE id = ?", 'si', [$nuevo, $idv]);
            $c['estado'] = $nuevo;
        }
    }
    $db->commit();
    $c['mi_voto'] = $valor;
    return $c;
}

// ---------- avisos ----------
function avisos_de(mysqli $db, ?array $u, ?int $rid): array {
    $sql = "SELECT a.id, a.recorrido_id, r.nombre AS ruta, a.tipo, a.minutos, a.votos_ok, a.votos_mal,
                   UNIX_TIMESTAMP(a.creado_en) AS ts, us.nombre AS autor, us.puntos AS autor_puntos,
                   COALESCE(v.valor, 0) AS mi_voto, (a.usuario_id = ?) AS es_mio
            FROM avisos a
            JOIN recorridos r ON r.id = a.recorrido_id
            JOIN usuarios us ON us.id = a.usuario_id
            LEFT JOIN votos_aviso v ON v.aviso_id = a.id AND v.usuario_id = ?
            WHERE a.creado_en > DATE_SUB(UTC_TIMESTAMP(), INTERVAL ? HOUR) AND r.estado <> 'oculto'";
    $t = 'iii';
    $p = [$u['id'] ?? 0, $u['id'] ?? 0, AVISO_HORAS];
    if ($rid) { $sql .= " AND a.recorrido_id = ?"; $t .= 'i'; $p[] = $rid; }
    $filas = q($db, $sql . " ORDER BY a.creado_en DESC LIMIT 100", $t, $p);
    foreach ($filas as &$x) {
        $x['autor_nivel'] = nivel((int)$x['autor_puntos'])['nombre'];
        $x['es_mio'] = (bool)$x['es_mio'];
        unset($x['autor_puntos']);
    }
    return $filas;
}

// ---------- handlers ----------
function h_ping(mysqli $db, array $in): void { salir(200, ['ok' => true, 'servidor_ts' => time()]); }

function h_registro(mysqli $db, array $in): void {
    $correo = strtolower(trim((string)($in['correo'] ?? '')));
    $clave = (string)($in['clave'] ?? '');
    if (!filter_var($correo, FILTER_VALIDATE_EMAIL) || strlen($correo) > 120)
        salir(422, ['error' => 'Escribe un correo válido.', 'campo' => 'usuario']);
    if (strlen($clave) < 6 || !preg_match('/[A-Za-z]/', $clave) || !preg_match('/\d/', $clave))
        salir(422, ['error' => 'Mínimo 6 caracteres, con letra y número.', 'campo' => 'clave']);
    if (q($db, "SELECT id FROM usuarios WHERE correo = ?", 's', [$correo]))
        salir(409, ['error' => 'Ese correo ya está registrado.', 'campo' => 'usuario']);
    $nombre = trim((string)($in['nombre'] ?? '')) ?: explode('@', $correo)[0];
    ejecutar($db, "INSERT INTO usuarios (correo, nombre, clave_hash) VALUES (?, ?, ?)", 'sss',
        [$correo, mb_substr($nombre, 0, 30), password_hash($clave, PASSWORD_DEFAULT)]);
    $uid = (int)$db->insert_id;
    salir(201, ['token' => nuevo_token($db, $uid), 'usuario' => perfil_de($db, $uid)]);
}

function h_login(mysqli $db, array $in): void {
    $correo = strtolower(trim((string)($in['correo'] ?? '')));
    $f = q($db, "SELECT id, clave_hash, bloqueado FROM usuarios WHERE correo = ?", 's', [$correo]);
    if (!$f || !password_verify((string)($in['clave'] ?? ''), $f[0]['clave_hash']))
        salir(401, ['error' => 'Correo o contraseña incorrectos.', 'campo' => 'general']);
    if ($f[0]['bloqueado']) salir(403, ['error' => 'Tu cuenta está bloqueada.', 'campo' => 'general']);
    $uid = (int)$f[0]['id'];
    salir(200, ['token' => nuevo_token($db, $uid), 'usuario' => perfil_de($db, $uid)]);
}

function h_logout(mysqli $db, array $in): void {
    $t = $_SERVER['HTTP_X_TOKEN'] ?? '';
    if ($t !== '') ejecutar($db, "DELETE FROM sesiones WHERE token_hash = ?", 's', [hash('sha256', $t)]);
    salir(204);
}

function h_perfil(mysqli $db, array $in): void { salir(200, ['usuario' => exigir($db)]); }

function h_perfil_nombre(mysqli $db, array $in): void {
    $u = exigir($db);
    $n = mb_substr(trim((string)($in['nombre'] ?? '')), 0, 30);
    if ($n === '') salir(422, ['error' => 'Escribe un nombre.']);
    ejecutar($db, "UPDATE usuarios SET nombre = ? WHERE id = ?", 'si', [$n, $u['id']]);
    salir(200, ['usuario' => perfil_de($db, (int)$u['id'])]);
}

function h_recorridos(mysqli $db, array $in): void {
    $u = usuario($db);
    $desde = max(0, (int)($_GET['desde'] ?? 0));
    $base = "SELECT id, nombre, origen, destino, parada, frecuencia, duracion_min, tarifa, estado, votos_ok, votos_mal,
                    UNIX_TIMESTAMP(actualizado_en) AS ts FROM recorridos WHERE ";
    // Con "desde" también llegan los ocultos, para que la app los quite de su copia.
    $filas = $desde ? q($db, $base . "actualizado_en > FROM_UNIXTIME(?)", 'i', [$desde])
                    : q($db, $base . "estado <> 'oculto'");
    if ($filas) {
        $ids = array_map(fn($r) => (int)$r['id'], $filas);
        $ph = implode(',', array_fill(0, count($ids), '?'));
        $tipos = str_repeat('i', count($ids));
        $pts = [];
        foreach (q($db, "SELECT recorrido_id, lat, lon FROM recorrido_puntos WHERE recorrido_id IN ($ph) ORDER BY recorrido_id, orden", $tipos, $ids) as $p)
            $pts[$p['recorrido_id']][] = [(float)$p['lat'], (float)$p['lon']];
        $mis = [];
        if ($u) foreach (q($db, "SELECT recorrido_id, valor FROM votos_recorrido WHERE usuario_id = ? AND recorrido_id IN ($ph)", 'i' . $tipos, array_merge([$u['id']], $ids)) as $v)
            $mis[$v['recorrido_id']] = (int)$v['valor'];
        foreach ($filas as &$r) {
            $r['linea'] = $pts[$r['id']] ?? [];
            $r['mi_voto'] = $mis[$r['id']] ?? 0;
        }
    }
    salir(200, ['servidor_ts' => time(), 'recorridos' => $filas]);
}

function h_recorrido(mysqli $db, array $in): void {
    $u = usuario($db);
    $id = (int)($_GET['id'] ?? 0);
    $f = q($db, "SELECT r.id, r.nombre, r.origen, r.destino, r.parada, r.frecuencia, r.duracion_min, r.tarifa, r.estado,
                        r.votos_ok, r.votos_mal, COALESCE(v.valor, 0) AS mi_voto
                 FROM recorridos r LEFT JOIN votos_recorrido v ON v.recorrido_id = r.id AND v.usuario_id = ?
                 WHERE r.id = ? AND r.estado <> 'oculto'", 'ii', [$u['id'] ?? 0, $id]);
    if (!$f) salir(404, ['error' => 'Recorrido no encontrado.']);
    $r = $f[0];
    $r['linea'] = array_map(fn($p) => [(float)$p['lat'], (float)$p['lon']],
        q($db, "SELECT lat, lon FROM recorrido_puntos WHERE recorrido_id = ? ORDER BY orden", 'i', [$id]));
    $r['avisos'] = avisos_de($db, $u, $id);
    salir(200, ['recorrido' => $r]);
}

function h_recorrido_crear(mysqli $db, array $in): void {
    $u = exigir($db);
    $campos = [];
    foreach (['nombre' => 80, 'origen' => 60, 'destino' => 60] as $c => $max) {
        $campos[$c] = trim((string)($in[$c] ?? ''));
        if ($campos[$c] === '' || mb_strlen($campos[$c]) > $max) salir(422, ['error' => "Revisa el campo $c."]);
    }
    if (q($db, "SELECT id FROM recorridos WHERE nombre = ?", 's', [$campos['nombre']]))
        salir(409, ['error' => 'Ya existe un recorrido con ese nombre.']);
    $pts = $in['puntos'] ?? [];
    if (!is_array($pts) || count($pts) < 2 || count($pts) > 200) salir(422, ['error' => 'Marca al menos el punto A y el punto B.']);
    foreach ($pts as $p) {
        $lat = $p['lat'] ?? null; $lon = $p['lon'] ?? null;
        if (!is_numeric($lat) || !is_numeric($lon) || abs((float)$lat) > 90 || abs((float)$lon) > 180)
            salir(422, ['error' => 'Coordenadas inválidas.']);
    }
    $hoy = q($db, "SELECT COUNT(*) c FROM recorridos WHERE creado_por = ? AND creado_en > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 DAY)", 'i', [$u['id']])[0]['c'];
    if ($hoy >= 5) salir(429, ['error' => 'Llegaste al límite de recorridos nuevos por hoy.']);

    $db->begin_transaction();
    ejecutar($db, "INSERT INTO recorridos (nombre, origen, destino, parada, frecuencia, duracion_min, tarifa, creado_por)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 'sssssiii',
        [$campos['nombre'], $campos['origen'], $campos['destino'],
         mb_substr(trim((string)($in['parada'] ?? '')), 0, 120), mb_substr(trim((string)($in['frecuencia'] ?? '')), 0, 40),
         isset($in['duracion_min']) ? (int)$in['duracion_min'] : null, isset($in['tarifa']) ? (int)$in['tarifa'] : null, $u['id']]);
    $rid = (int)$db->insert_id;
    foreach (array_values($pts) as $i => $p)
        ejecutar($db, "INSERT INTO recorrido_puntos (recorrido_id, orden, lat, lon) VALUES (?, ?, ?, ?)", 'iidd',
            [$rid, $i, (float)$p['lat'], (float)$p['lon']]);
    $db->commit();
    salir(201, ['id' => $rid, 'estado' => 'pendiente']);
}

function h_voto_recorrido(mysqli $db, array $in): void {
    salir(200, votar($db, exigir($db), 'recorrido', (string)(int)($in['id'] ?? 0), (int)($in['valor'] ?? 0)));
}

function h_avisos(mysqli $db, array $in): void {
    $rid = isset($_GET['recorrido_id']) ? (int)$_GET['recorrido_id'] : null;
    salir(200, ['servidor_ts' => time(), 'avisos' => avisos_de($db, usuario($db), $rid)]);
}

function h_aviso_crear(mysqli $db, array $in): void {
    $u = exigir($db);
    $id = (string)($in['id'] ?? '');
    $rid = (int)($in['recorrido_id'] ?? 0);
    $tipo = (string)($in['tipo'] ?? '');
    $min = max(0, min(240, (int)($in['minutos'] ?? 0)));
    if (!preg_match('/^[a-f0-9]{32}$/', $id) || !in_array($tipo, TIPOS_AVISO, true)) salir(422, ['error' => 'Aviso inválido.']);
    if (q($db, "SELECT id FROM avisos WHERE id = ?", 's', [$id])) salir(200, ['id' => $id, 'repetido' => true]); // reintento seguro
    if (!q($db, "SELECT id FROM recorridos WHERE id = ? AND estado <> 'oculto'", 'i', [$rid])) salir(404, ['error' => 'Recorrido no encontrado.']);
    $rep = q($db, "SELECT id FROM avisos WHERE usuario_id = ? AND recorrido_id = ? AND tipo = ?
                   AND creado_en > DATE_SUB(UTC_TIMESTAMP(), INTERVAL ? SECOND)", 'iisi', [$u['id'], $rid, $tipo, ANTISPAM_S]);
    if ($rep) salir(429, ['error' => 'Ya enviaste este aviso hace un momento.']);
    ejecutar($db, "INSERT INTO avisos (id, recorrido_id, usuario_id, tipo, minutos) VALUES (?, ?, ?, ?, ?)", 'siisi', [$id, $rid, $u['id'], $tipo, $min]);
    salir(201, ['id' => $id]);
}

function h_voto_aviso(mysqli $db, array $in): void {
    salir(200, votar($db, exigir($db), 'aviso', (string)($in['id'] ?? ''), (int)($in['valor'] ?? 0)));
}

// Patentes chilenas: formato antiguo AB1234 y nuevo BCDF12 (sin vocales).
function normalizar_patente(string $p): string { return strtoupper(preg_replace('/[\s\-\.]/', '', $p)); }
function patente_valida(string $p): bool {
    return (bool)preg_match('/^([A-Z]{2}\d{4}|[BCDFGHJKLPRSTVWXYZ]{4}\d{2})$/', $p);
}

function h_viaje_iniciar(mysqli $db, array $in): void {
    $u = exigir($db);
    $rid = (int)($in['recorrido_id'] ?? 0);
    $patente = normalizar_patente((string)($in['patente'] ?? ''));
    $agenda = null;
    if (!empty($in['agendado_para'])) {
        $t = strtotime((string)$in['agendado_para']);
        if ($t === false || $t < time() - 600 || $t > time() + 7 * 86400)
            salir(422, ['error' => 'El horario agendado debe ser dentro de los próximos 7 días.', 'campo' => 'agenda']);
        $agenda = gmdate('Y-m-d H:i:s', $t);
    }
    if ($patente === '' && $agenda === null)
        salir(422, ['error' => 'Escribe la patente del bus o agenda el viaje para poder compartir.', 'campo' => 'patente']);
    if ($patente !== '' && !patente_valida($patente))
        salir(422, ['error' => 'Patente inválida (ej.: AB1234 o BCDF12).', 'campo' => 'patente']);
    if (!q($db, "SELECT id FROM recorridos WHERE id = ? AND estado <> 'oculto'", 'i', [$rid])) salir(404, ['error' => 'Recorrido no encontrado.']);
    $abierto = q($db, "SELECT id FROM viajes WHERE usuario_id = ? AND fin IS NULL AND inicio > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 12 HOUR)", 'i', [$u['id']]);
    if ($abierto) salir(200, ['id' => (int)$abierto[0]['id'], 'repetido' => true]);
    ejecutar($db, "INSERT INTO viajes (usuario_id, recorrido_id, patente, agendado_para, inicio) VALUES (?, ?, ?, ?, UTC_TIMESTAMP())",
        'iiss', [$u['id'], $rid, $patente !== '' ? $patente : null, $agenda]);
    salir(201, ['id' => (int)$db->insert_id]);
}

function h_viaje_fin(mysqli $db, array $in): void {
    $u = exigir($db);
    $id = (int)($in['id'] ?? 0);
    $v = q($db, "SELECT TIMESTAMPDIFF(MINUTE, inicio, UTC_TIMESTAMP()) AS min FROM viajes
                 WHERE id = ? AND usuario_id = ? AND fin IS NULL", 'ii', [$id, $u['id']]);
    if (!$v) salir(404, ['error' => 'No hay un viaje abierto con ese id.']);
    ejecutar($db, "UPDATE viajes SET fin = UTC_TIMESTAMP() WHERE id = ?", 'i', [$id]);
    $premio = 0;
    if ((int)$v[0]['min'] >= 5) { // viajes muy cortos no suman; máximo 3 viajes premiados por día
        $hoy = q($db, "SELECT COUNT(*) c FROM puntos_movimientos WHERE usuario_id = ? AND motivo = 'viaje_completado'
                       AND creado_en > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 1 DAY)", 'i', [$u['id']])[0]['c'];
        if ($hoy < 3) { dar_puntos($db, (int)$u['id'], 5, 'viaje_completado', (string)$id); $premio = 5; }
    }
    salir(200, ['puntos_ganados' => $premio, 'usuario' => perfil_de($db, (int)$u['id'])]);
}

function h_evento(mysqli $db, array $in): void {
    $tipo = (string)($in['tipo'] ?? '');
    $sesion = (string)($in['sesion'] ?? '');
    if (!in_array($tipo, EVENTOS_OK, true) || !preg_match('/^[a-f0-9]{16}$/', $sesion)) salir(422, ['error' => 'Evento inválido.']);
    ejecutar($db, "INSERT INTO eventos (tipo, sesion) VALUES (?, ?)", 'ss', [$tipo, $sesion]);
    salir(204);
}

// ---------- enrutador ----------
$rutas = [
    'ping' => ['GET', 'h_ping'], 'auth_registro' => ['POST', 'h_registro'], 'auth_login' => ['POST', 'h_login'],
    'auth_logout' => ['POST', 'h_logout'], 'perfil' => ['GET', 'h_perfil'], 'perfil_nombre' => ['POST', 'h_perfil_nombre'],
    'recorridos' => ['GET', 'h_recorridos'], 'recorrido' => ['GET', 'h_recorrido'],
    'recorrido_crear' => ['POST', 'h_recorrido_crear'], 'voto_recorrido' => ['POST', 'h_voto_recorrido'],
    'avisos' => ['GET', 'h_avisos'], 'aviso_crear' => ['POST', 'h_aviso_crear'], 'voto_aviso' => ['POST', 'h_voto_aviso'],
    'viaje_iniciar' => ['POST', 'h_viaje_iniciar'], 'viaje_fin' => ['POST', 'h_viaje_fin'], 'evento' => ['POST', 'h_evento'],
];
$r = (string)($_GET['r'] ?? '');
if (!isset($rutas[$r])) salir(404, ['error' => 'Ruta no encontrada.']);
if ($_SERVER['REQUEST_METHOD'] !== $rutas[$r][0]) salir(405, ['error' => 'Método no permitido.']);

try {
    $db = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    $db->set_charset('utf8mb4');
    $db->query("SET time_zone = '+00:00'");
    $entrada = json_decode((string)file_get_contents('php://input'), true);
    $rutas[$r][1]($db, is_array($entrada) ? $entrada : []);
} catch (Throwable $e) {
    error_log('EnRuta API: ' . $e->getMessage());
    salir(503, ['error' => 'Servidor no disponible. Reintenta en un momento.']);
}
