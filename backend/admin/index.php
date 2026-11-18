<?php
declare(strict_types=1);
/*
 * EnRuta Ya! · Panel de administración
 * Entra con una cuenta de rol "admin" (ver README). Usa la misma base y config que la API.
 * Secciones: Métricas · Recorridos (crear, editar, verificar, ocultar) · Usuarios y puntos · Avisos.
 */
require __DIR__ . '/../api/config.php';

mysqli_report(MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT);
session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax', 'secure' => !empty($_SERVER['HTTPS'])]);
session_start();
header('X-Frame-Options: DENY');
header('Content-Security-Policy: default-src \'self\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'');

const NIVELES = [[0, 'Novato'], [20, 'Colaborador'], [60, 'Confiable'], [150, 'Verificador']];

try {
    $db = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    $db->set_charset('utf8mb4');
    $db->query("SET time_zone = '+00:00'");
} catch (Throwable $e) {
    error_log('EnRuta admin: ' . $e->getMessage());
    http_response_code(503);
    exit('Base de datos no disponible.');
}

// ---------- utilidades ----------
function e($s): string { return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

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

function nivel(int $puntos): string {
    $actual = NIVELES[0][1];
    foreach (NIVELES as $n) if ($puntos >= $n[0]) $actual = $n[1];
    return $actual;
}

function flash(string $msg): void { $_SESSION['flash'] = $msg; }

function volver(string $p): void { header('Location: ?p=' . urlencode($p)); exit; }

function csrf(): string {
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(16));
    return $_SESSION['csrf'];
}

function serie7(mysqli $db, string $sql): array {
    $m = array_column(q($db, $sql), 'n', 'd');
    $out = [];
    for ($i = 6; $i >= 0; $i--) {
        $d = gmdate('Y-m-d', time() - $i * 86400);
        $out[] = [substr($d, 5), (int)($m[$d] ?? 0)];
    }
    return $out;
}

function barras(array $filas): string {   // filas: [[etiqueta, número], ...]
    $max = max(1, ...array_map(fn($f) => (int)$f[1], $filas ?: [[0, 0]]));
    $h = '<table class="barras">';
    foreach ($filas as [$et, $n])
        $h .= '<tr><td>' . e($et) . '</td><td><div style="width:' . round(100 * $n / $max) . '%"></div></td><td>' . (int)$n . '</td></tr>';
    return $h . '</table>';
}

// ---------- ajuste a las calles con OSRM ----------
// Se hace UNA vez, aquí en el servidor; la app solo dibuja los puntos guardados.
// El servidor público de OSRM es de demostración (uso liviano). Para mucho uso, instala uno propio.
const OSRM_URL = 'https://router.project-osrm.org';

function adelgazar(array $l, int $max): array {   // deja a lo más $max puntos, siempre con A y B
    $d = 20.0;                                     // distancia mínima entre puntos (m); crece hasta caber
    while (true) {
        $out = [$l[0]]; $u = $l[0];
        for ($i = 1; $i < count($l) - 1; $i++) {
            $dx = ($l[$i][1] - $u[1]) * 111320 * cos(deg2rad($u[0]));
            $dy = ($l[$i][0] - $u[0]) * 110540;
            if (hypot($dx, $dy) >= $d) { $out[] = $l[$i]; $u = $l[$i]; }
        }
        $out[] = end($l);
        if (count($out) <= $max) return $out;
        $d *= 1.5;
    }
}

/** [[lat,lon],...] -> línea que sigue las calles. Los puntos intermedios (hasta 25) obligan a pasar por ahí. */
function osrm_ajustar(array $pts): array {
    if (!function_exists('curl_init')) throw new RuntimeException('el hosting no tiene cURL');
    $w = count($pts) <= 25 ? $pts : [$pts[0], end($pts)];
    $coords = implode(';', array_map(fn($p) => $p[1] . ',' . $p[0], $w));   // OSRM usa lon,lat
    $ch = curl_init(OSRM_URL . "/route/v1/driving/$coords?overview=full&geometries=geojson");
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20,
        CURLOPT_USERAGENT => 'EnRutaYa-Admin/1.0 (proyecto academico)']);
    $resp = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($resp === false || $code !== 200) throw new RuntimeException("OSRM respondió $code");
    $j = json_decode($resp, true);
    if (($j['code'] ?? '') !== 'Ok' || empty($j['routes'][0]['geometry']['coordinates']))
        throw new RuntimeException('OSRM no encontró una ruta entre esos puntos');
    $linea = array_map(fn($c) => [round((float)$c[1], 6), round((float)$c[0], 6)], $j['routes'][0]['geometry']['coordinates']);
    return count($linea) >= 2 ? adelgazar($linea, 200) : $pts;
}

// ---------- sesión y acciones ----------
$admin = $_SESSION['admin'] ?? null;
$p = (string)($_GET['p'] ?? 'panel');

if (isset($_GET['salir'])) { session_destroy(); header('Location: ?'); exit; }

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $accion = (string)($_POST['accion'] ?? '');
    if ($accion === 'login') {
        if (($_SESSION['fallos'] ?? 0) >= 5 && time() < ($_SESSION['bloqueo'] ?? 0)) {
            flash('Demasiados intentos. Espera unos minutos.');
        } else {
            $f = q($db, "SELECT id, clave_hash FROM usuarios WHERE correo = ? AND rol = 'admin' AND bloqueado = 0",
                's', [strtolower(trim((string)($_POST['correo'] ?? '')))]);
            if ($f && password_verify((string)($_POST['clave'] ?? ''), $f[0]['clave_hash'])) {
                session_regenerate_id(true);
                $_SESSION['admin'] = (int)$f[0]['id'];
                $_SESSION['fallos'] = 0;
                header('Location: ?'); exit;
            }
            $_SESSION['fallos'] = ($_SESSION['fallos'] ?? 0) + 1;
            $_SESSION['bloqueo'] = time() + 300;
            usleep(500000);
            flash('Correo o contraseña incorrectos, o la cuenta no es de administrador.');
        }
        header('Location: ?'); exit;
    }
    if (!$admin || !hash_equals(csrf(), (string)($_POST['csrf'] ?? ''))) { http_response_code(403); exit('Solicitud no válida.'); }
    try {
        switch ($accion) {
            case 'recorrido_estado':
                $est = (string)($_POST['estado'] ?? '');
                if (in_array($est, ['pendiente', 'verificado', 'oculto'], true))
                    ejecutar($db, "UPDATE recorridos SET estado = ?, actualizado_en = UTC_TIMESTAMP() WHERE id = ?", 'si', [$est, (int)$_POST['id']]);
                flash('Estado actualizado.'); volver('recorridos');
            case 'recorrido_borrar':
                ejecutar($db, "DELETE FROM recorridos WHERE id = ?", 'i', [(int)$_POST['id']]);
                flash('Recorrido eliminado (los teléfonos lo quitan en su próxima sincronización completa).'); volver('recorridos');
            case 'recorrido_guardar':
                $id = (int)($_POST['id'] ?? 0);
                $nombre = trim((string)$_POST['nombre']); $origen = trim((string)$_POST['origen']); $destino = trim((string)$_POST['destino']);
                $pts = [];
                foreach (preg_split('/\R/', trim((string)$_POST['puntos'])) as $l) {
                    if (trim($l) === '') continue;
                    $c = array_map('trim', explode(',', $l));
                    if (count($c) !== 2 || !is_numeric($c[0]) || !is_numeric($c[1]) || abs((float)$c[0]) > 90 || abs((float)$c[1]) > 180)
                        { flash("Punto inválido: «$l». Usa «lat,lon» por línea."); volver($id ? "recorrido&id=$id" : 'recorrido'); }
                    $pts[] = [(float)$c[0], (float)$c[1]];
                }
                if ($nombre === '' || $origen === '' || $destino === '' || count($pts) < 2)
                    { flash('Nombre, origen, destino y al menos 2 puntos (A y B) son obligatorios.'); volver($id ? "recorrido&id=$id" : 'recorrido'); }
                $extra = '';
                if (!empty($_POST['ajustar'])) {
                    try { $pts = osrm_ajustar($pts); $extra = ' Línea ajustada a las calles (' . count($pts) . ' puntos).'; }
                    catch (Throwable $ex) {
                        error_log('EnRuta OSRM: ' . $ex->getMessage());
                        $extra = ' No se pudo ajustar con OSRM (' . $ex->getMessage() . '): se guardaron los puntos tal como los escribiste.';
                    }
                }
                $dur = $_POST['duracion_min'] !== '' ? (int)$_POST['duracion_min'] : null;
                $tar = $_POST['tarifa'] !== '' ? (int)$_POST['tarifa'] : null;
                $est = in_array($_POST['estado'] ?? '', ['pendiente', 'verificado', 'oculto'], true) ? $_POST['estado'] : 'pendiente';
                $db->begin_transaction();
                if ($id) {
                    ejecutar($db, "UPDATE recorridos SET nombre=?, origen=?, destino=?, parada=?, frecuencia=?, duracion_min=?, tarifa=?, estado=?, actualizado_en=UTC_TIMESTAMP() WHERE id=?",
                        'sssssiisi', [$nombre, $origen, $destino, trim((string)$_POST['parada']), trim((string)$_POST['frecuencia']), $dur, $tar, $est, $id]);
                    ejecutar($db, "DELETE FROM recorrido_puntos WHERE recorrido_id = ?", 'i', [$id]);
                } else {
                    ejecutar($db, "INSERT INTO recorridos (nombre, origen, destino, parada, frecuencia, duracion_min, tarifa, estado, creado_por) VALUES (?,?,?,?,?,?,?,?,?)",
                        'sssssiisi', [$nombre, $origen, $destino, trim((string)$_POST['parada']), trim((string)$_POST['frecuencia']), $dur, $tar, $est, $admin]);
                    $id = (int)$db->insert_id;
                }
                foreach ($pts as $i => [$la, $lo])
                    ejecutar($db, "INSERT INTO recorrido_puntos (recorrido_id, orden, lat, lon) VALUES (?,?,?,?)", 'iidd', [$id, $i, $la, $lo]);
                $db->commit();
                flash('Recorrido guardado.' . $extra); volver('recorridos');
            case 'recorrido_ajustar':
                $id = (int)$_POST['id'];
                $pts = array_map(fn($x) => [(float)$x['lat'], (float)$x['lon']],
                    q($db, "SELECT lat, lon FROM recorrido_puntos WHERE recorrido_id = ? ORDER BY orden", 'i', [$id]));
                if (count($pts) < 2) { flash('El recorrido necesita al menos 2 puntos.'); volver('recorridos'); }
                try { $nuevos = osrm_ajustar($pts); }
                catch (Throwable $ex) {
                    error_log('EnRuta OSRM: ' . $ex->getMessage());
                    flash('No se pudo ajustar con OSRM: ' . $ex->getMessage()); volver('recorridos');
                }
                $db->begin_transaction();
                ejecutar($db, "DELETE FROM recorrido_puntos WHERE recorrido_id = ?", 'i', [$id]);
                foreach ($nuevos as $i => [$la, $lo])
                    ejecutar($db, "INSERT INTO recorrido_puntos (recorrido_id, orden, lat, lon) VALUES (?,?,?,?)", 'iidd', [$id, $i, $la, $lo]);
                ejecutar($db, "UPDATE recorridos SET actualizado_en = UTC_TIMESTAMP() WHERE id = ?", 'i', [$id]);
                $db->commit();
                flash('Línea ajustada a las calles (' . count($nuevos) . ' puntos).'); volver('recorridos');
            case 'usuario_bloquear':
                if ((int)$_POST['id'] !== $admin)
                    ejecutar($db, "UPDATE usuarios SET bloqueado = ? WHERE id = ?", 'ii', [(int)$_POST['valor'], (int)$_POST['id']]);
                if ((int)$_POST['valor']) ejecutar($db, "DELETE FROM sesiones WHERE usuario_id = ?", 'i', [(int)$_POST['id']]);
                flash('Usuario actualizado.'); volver('usuarios');
            case 'usuario_rol':
                if ((int)$_POST['id'] !== $admin && in_array($_POST['rol'], ['registrado', 'admin'], true))
                    ejecutar($db, "UPDATE usuarios SET rol = ? WHERE id = ?", 'si', [$_POST['rol'], (int)$_POST['id']]);
                flash('Rol actualizado.'); volver('usuarios');
            case 'usuario_puntos':
                $delta = max(-100, min(100, (int)$_POST['delta']));
                if ($delta !== 0) {
                    ejecutar($db, "INSERT INTO puntos_movimientos (usuario_id, delta, motivo, ref_id) VALUES (?,?, 'ajuste_admin', ?)", 'iis', [(int)$_POST['id'], $delta, 'admin' . $admin]);
                    ejecutar($db, "UPDATE usuarios SET puntos = GREATEST(0, puntos + ?) WHERE id = ?", 'ii', [$delta, (int)$_POST['id']]);
                }
                flash('Puntos ajustados.'); volver('usuarios');
            case 'aviso_borrar':
                ejecutar($db, "DELETE FROM avisos WHERE id = ?", 's', [(string)$_POST['id']]);
                flash('Aviso eliminado.'); volver('avisos');
        }
    } catch (mysqli_sql_exception $ex) {
        error_log('EnRuta admin: ' . $ex->getMessage());
        flash($ex->getCode() === 1062 ? 'Ya existe un recorrido con ese nombre.' : 'No se pudo completar la acción.');
        volver($p);
    }
}

// ---------- vistas ----------
function cabecera(string $p, bool $logueado): void { ?>
<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EnRuta Ya! · Admin</title><style>
body{font:15px system-ui,sans-serif;margin:0;background:#f4f6fa;color:#1b2333}
header{background:#1f4fb8;color:#fff;padding:10px 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header a{color:#fff;text-decoration:none;padding:6px 10px;border-radius:8px}header a.on{background:rgba(255,255,255,.22)}
main{max-width:1100px;margin:20px auto;padding:0 16px}
.tarjetas{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:20px}
.t{background:#fff;border-radius:12px;padding:14px;box-shadow:0 1px 3px #0001}.t b{display:block;font-size:26px}
.caja{background:#fff;border-radius:12px;padding:16px;margin-bottom:20px;box-shadow:0 1px 3px #0001;overflow-x:auto}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid #e6e9f0;vertical-align:middle}
.barras td:nth-child(2){width:60%}.barras div{background:#2a73de;height:14px;border-radius:4px}
.msg{background:#e7f1ff;border-left:4px solid #1f4fb8;padding:10px 14px;margin-bottom:16px;border-radius:6px}
.ok{color:#0b8f5a}.mal{color:#c0392b}.tag{padding:2px 8px;border-radius:10px;font-size:12px;background:#e6e9f0}
.tag.verificado{background:#d7f5e6;color:#0b6b43}.tag.oculto{background:#fde0dc;color:#a52a1d}
input,select,textarea,button{font:inherit;padding:6px 8px;border:1px solid #c5ccd8;border-radius:8px}
button{background:#1f4fb8;color:#fff;border:0;cursor:pointer}button.rojo{background:#c0392b}button.gris{background:#6b7588}
form.fila{display:inline-flex;gap:4px;align-items:center;margin:2px}
label{display:block;margin:10px 0 3px;font-weight:600}.g2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
</style></head><body>
<header><strong>EnRuta Ya! · Admin</strong>
<?php if ($logueado): foreach (['panel' => 'Métricas', 'recorridos' => 'Recorridos', 'usuarios' => 'Usuarios', 'avisos' => 'Avisos'] as $k => $t): ?>
<a href="?p=<?= $k ?>" class="<?= ($p === $k || ($k === 'recorridos' && $p === 'recorrido')) ? 'on' : '' ?>"><?= $t ?></a>
<?php endforeach; ?><a href="?salir=1" style="margin-left:auto">Salir</a><?php endif; ?></header><main>
<?php if (!empty($_SESSION['flash'])): ?><div class="msg"><?= e($_SESSION['flash']) ?></div><?php unset($_SESSION['flash']); endif;
}

function pie(): void { echo '</main></body></html>'; }

function form_mini(string $accion, array $campos, string $boton, string $clase = ''): void {
    echo '<form method="post" class="fila"><input type="hidden" name="csrf" value="' . e(csrf()) . '"><input type="hidden" name="accion" value="' . e($accion) . '">';
    foreach ($campos as $k => $v) echo '<input type="hidden" name="' . e($k) . '" value="' . e($v) . '">';
    echo '<button class="' . $clase . '">' . e($boton) . '</button></form>';
}

if (!$admin) {
    cabecera($p, false); ?>
<div class="caja" style="max-width:360px;margin:60px auto"><h2>Iniciar sesión</h2>
<form method="post"><input type="hidden" name="accion" value="login">
<label>Correo</label><input name="correo" type="email" required style="width:100%">
<label>Contraseña</label><input name="clave" type="password" required style="width:100%"><br><br>
<button>Entrar</button></form></div>
<?php pie(); exit;
}

cabecera($p, true);

if ($p === 'panel') {
    $n = fn(string $sql) => (int)(q($db, $sql)[0]['n'] ?? 0);
    $rec = array_column(q($db, "SELECT estado, COUNT(*) n FROM recorridos GROUP BY estado"), 'n', 'estado'); ?>
<div class="tarjetas">
 <div class="t"><b><?= $n("SELECT COUNT(*) n FROM usuarios") ?></b>Usuarios registrados</div>
 <div class="t"><b><?= $n("SELECT COUNT(*) n FROM usuarios WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 7 DAY") ?></b>Nuevos (7 días)</div>
 <div class="t"><b><?= (int)($rec['verificado'] ?? 0) ?> / <?= (int)($rec['pendiente'] ?? 0) ?> / <?= (int)($rec['oculto'] ?? 0) ?></b>Recorridos verif. / pend. / ocultos</div>
 <div class="t"><b><?= $n("SELECT COUNT(*) n FROM avisos WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 24 HOUR") ?></b>Avisos (24 h)</div>
 <div class="t"><b><?= $n("SELECT COUNT(*) n FROM (SELECT creado_en FROM votos_recorrido UNION ALL SELECT creado_en FROM votos_aviso) v WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 7 DAY") ?></b>Votos (7 días)</div>
 <div class="t"><b><?= $n("SELECT COUNT(*) n FROM viajes WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 7 DAY") ?></b>Viajes (7 días)</div>
 <div class="t"><b><?= $n("SELECT COUNT(DISTINCT sesion) n FROM eventos WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 7 DAY") ?></b>Sesiones medidas (7 días)</div>
</div>
<div class="g2">
<div class="caja"><h3>Votos por día</h3><?= barras(serie7($db, "SELECT DATE(creado_en) d, COUNT(*) n FROM (SELECT creado_en FROM votos_recorrido UNION ALL SELECT creado_en FROM votos_aviso) v WHERE creado_en >= UTC_DATE() - INTERVAL 6 DAY GROUP BY d")) ?></div>
<div class="caja"><h3>Avisos por día</h3><?= barras(serie7($db, "SELECT DATE(creado_en) d, COUNT(*) n FROM avisos WHERE creado_en >= UTC_DATE() - INTERVAL 6 DAY GROUP BY d")) ?></div>
<div class="caja"><h3>Uso de la app (7 días)</h3><?= barras(array_map(fn($f) => [$f['tipo'], $f['n']], q($db, "SELECT tipo, COUNT(*) n FROM eventos WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 7 DAY GROUP BY tipo ORDER BY n DESC LIMIT 10"))) ?>
 <small>Solo de quienes aceptaron las métricas anónimas.</small></div>
<div class="caja"><h3>Avisos por tipo (7 días)</h3><?= barras(array_map(fn($f) => [$f['tipo'], $f['n']], q($db, "SELECT tipo, COUNT(*) n FROM avisos WHERE creado_en > UTC_TIMESTAMP() - INTERVAL 7 DAY GROUP BY tipo ORDER BY n DESC"))) ?></div>
</div>
<div class="caja"><h3>Recorridos con dudas (más votos «falso» que «real»)</h3><table><tr><th>Recorrido</th><th>Real</th><th>Falso</th><th>Estado</th></tr>
<?php foreach (q($db, "SELECT id, nombre, votos_ok, votos_mal, estado FROM recorridos WHERE votos_mal >= 2 AND votos_mal > votos_ok ORDER BY votos_mal DESC LIMIT 10") as $r): ?>
<tr><td><a href="?p=recorrido&id=<?= $r['id'] ?>"><?= e($r['nombre']) ?></a></td><td class="ok"><?= $r['votos_ok'] ?></td><td class="mal"><?= $r['votos_mal'] ?></td><td><span class="tag <?= e($r['estado']) ?>"><?= e($r['estado']) ?></span></td></tr>
<?php endforeach; ?></table></div>
<div class="caja"><h3>Ranking de usuarios</h3><table><tr><th>#</th><th>Nombre</th><th>Nivel</th><th>Puntos</th></tr>
<?php foreach (q($db, "SELECT nombre, puntos FROM usuarios WHERE bloqueado = 0 ORDER BY puntos DESC LIMIT 10") as $i => $u): ?>
<tr><td><?= $i + 1 ?></td><td><?= e($u['nombre']) ?></td><td><?= nivel((int)$u['puntos']) ?></td><td><?= (int)$u['puntos'] ?></td></tr>
<?php endforeach; ?></table></div>
<?php
} elseif ($p === 'recorridos') { ?>
<div class="caja"><p><a href="?p=recorrido"><button>+ Nuevo recorrido</button></a></p>
<table><tr><th>Recorrido</th><th>Estado</th><th>Real / Falso</th><th>Acciones</th></tr>
<?php foreach (q($db, "SELECT r.id, r.nombre, r.estado, r.votos_ok, r.votos_mal, (SELECT COUNT(*) FROM recorrido_puntos WHERE recorrido_id = r.id) AS np FROM recorridos r ORDER BY r.nombre") as $r): ?>
<tr><td><a href="?p=recorrido&id=<?= $r['id'] ?>"><?= e($r['nombre']) ?></a> <small>(<?= $r['np'] ?> puntos)</small></td>
<td><span class="tag <?= e($r['estado']) ?>"><?= e($r['estado']) ?></span></td>
<td><span class="ok"><?= $r['votos_ok'] ?></span> / <span class="mal"><?= $r['votos_mal'] ?></span></td>
<td><form method="post" class="fila"><input type="hidden" name="csrf" value="<?= e(csrf()) ?>"><input type="hidden" name="accion" value="recorrido_estado"><input type="hidden" name="id" value="<?= $r['id'] ?>">
<select name="estado"><?php foreach (['pendiente', 'verificado', 'oculto'] as $s): ?><option <?= $s === $r['estado'] ? 'selected' : '' ?>><?= $s ?></option><?php endforeach; ?></select><button>Cambiar</button></form>
<?php form_mini('recorrido_ajustar', ['id' => $r['id']], 'Ajustar a calles', 'gris'); ?>
<form method="post" class="fila" onsubmit="return confirm('¿Eliminar este recorrido y todo lo asociado?')"><input type="hidden" name="csrf" value="<?= e(csrf()) ?>"><input type="hidden" name="accion" value="recorrido_borrar"><input type="hidden" name="id" value="<?= $r['id'] ?>"><button class="rojo">Eliminar</button></form></td></tr>
<?php endforeach; ?></table></div>
<?php
} elseif ($p === 'recorrido') {
    $id = (int)($_GET['id'] ?? 0);
    $r = $id ? (q($db, "SELECT * FROM recorridos WHERE id = ?", 'i', [$id])[0] ?? null) : null;
    $pts = $id ? implode("\n", array_map(fn($x) => $x['lat'] . ',' . $x['lon'], q($db, "SELECT lat, lon FROM recorrido_puntos WHERE recorrido_id = ? ORDER BY orden", 'i', [$id]))) : '';
    $v = fn(string $k) => e($r[$k] ?? ''); ?>
<div class="caja"><h2><?= $r ? 'Editar recorrido' : 'Nuevo recorrido' ?></h2>
<form method="post"><input type="hidden" name="csrf" value="<?= e(csrf()) ?>"><input type="hidden" name="accion" value="recorrido_guardar"><input type="hidden" name="id" value="<?= $id ?>">
<label>Nombre (único, ej.: Temuco -> Nueva Imperial)</label><input name="nombre" value="<?= $v('nombre') ?>" required style="width:100%">
<div class="g2"><div><label>Origen (punto A)</label><input name="origen" value="<?= $v('origen') ?>" required style="width:100%"></div>
<div><label>Destino (punto B)</label><input name="destino" value="<?= $v('destino') ?>" required style="width:100%"></div>
<div><label>Parada</label><input name="parada" value="<?= $v('parada') ?>" style="width:100%"></div>
<div><label>Frecuencia</label><input name="frecuencia" value="<?= $v('frecuencia') ?>" style="width:100%"></div>
<div><label>Duración (min)</label><input name="duracion_min" type="number" min="0" value="<?= $v('duracion_min') ?>" style="width:100%"></div>
<div><label>Tarifa ($)</label><input name="tarifa" type="number" min="0" value="<?= $v('tarifa') ?>" style="width:100%"></div></div>
<label>Estado</label><select name="estado"><?php foreach (['pendiente', 'verificado', 'oculto'] as $s): ?><option <?= $s === ($r['estado'] ?? 'pendiente') ? 'selected' : '' ?>><?= $s ?></option><?php endforeach; ?></select>
<label>Línea del recorrido: un punto «lat,lon» por línea (el primero es A y el último es B; con 2 puntos es una recta)</label>
<textarea name="puntos" rows="8" style="width:100%" required><?= e($pts) ?></textarea>
<label style="font-weight:normal"><input type="checkbox" name="ajustar" value="1" <?= $r ? '' : 'checked' ?>> Ajustar la línea a las calles al guardar (OSRM). Si agregas puntos intermedios, el bus pasará por ellos.</label><br>
<button>Guardar</button> <a href="?p=recorridos"><button type="button" class="gris">Cancelar</button></a></form></div>
<?php
} elseif ($p === 'usuarios') { ?>
<div class="caja"><table><tr><th>Usuario</th><th>Rol</th><th>Puntos</th><th>Estado</th><th>Acciones</th></tr>
<?php foreach (q($db, "SELECT id, nombre, correo, rol, puntos, bloqueado FROM usuarios ORDER BY puntos DESC, id LIMIT 200") as $u): ?>
<tr><td><?= e($u['nombre']) ?><br><small><?= e($u['correo']) ?></small></td>
<td><?= e($u['rol']) ?></td><td><?= (int)$u['puntos'] ?> <small>(<?= nivel((int)$u['puntos']) ?>)</small></td>
<td><?= $u['bloqueado'] ? '<span class="tag oculto">bloqueado</span>' : 'activo' ?></td>
<td><?php if ((int)$u['id'] !== $admin): ?>
<?php form_mini('usuario_bloquear', ['id' => $u['id'], 'valor' => $u['bloqueado'] ? 0 : 1], $u['bloqueado'] ? 'Desbloquear' : 'Bloquear', $u['bloqueado'] ? '' : 'rojo'); ?>
<?php form_mini('usuario_rol', ['id' => $u['id'], 'rol' => $u['rol'] === 'admin' ? 'registrado' : 'admin'], $u['rol'] === 'admin' ? 'Quitar admin' : 'Hacer admin', 'gris'); ?>
<?php endif; ?>
<form method="post" class="fila"><input type="hidden" name="csrf" value="<?= e(csrf()) ?>"><input type="hidden" name="accion" value="usuario_puntos"><input type="hidden" name="id" value="<?= $u['id'] ?>">
<input name="delta" type="number" min="-100" max="100" placeholder="±puntos" style="width:90px"><button class="gris">Ajustar</button></form></td></tr>
<?php endforeach; ?></table></div>
<?php
} elseif ($p === 'avisos') { ?>
<div class="caja"><table><tr><th>Cuándo (UTC)</th><th>Recorrido</th><th>Tipo</th><th>Autor</th><th>Votos</th><th></th></tr>
<?php foreach (q($db, "SELECT a.id, a.creado_en, a.tipo, a.minutos, a.votos_ok, a.votos_mal, r.nombre AS ruta, u.nombre AS autor FROM avisos a JOIN recorridos r ON r.id = a.recorrido_id JOIN usuarios u ON u.id = a.usuario_id ORDER BY a.creado_en DESC LIMIT 100") as $a): ?>
<tr><td><?= e($a['creado_en']) ?></td><td><?= e($a['ruta']) ?></td><td><?= e($a['tipo']) ?><?= $a['minutos'] ? ' ~' . (int)$a['minutos'] . ' min' : '' ?></td><td><?= e($a['autor']) ?></td>
<td><span class="ok"><?= $a['votos_ok'] ?></span> / <span class="mal"><?= $a['votos_mal'] ?></span></td>
<td><?php form_mini('aviso_borrar', ['id' => $a['id']], 'Eliminar', 'rojo'); ?></td></tr>
<?php endforeach; ?></table></div>
<?php
}
pie();
