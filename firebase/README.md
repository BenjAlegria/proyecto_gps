# EnRuta Ya! — Firebase Authentication + Realtime Database

La app utiliza **Firebase Authentication (correo y contraseña)** y
**Realtime Database** para avisos comunitarios. El mapa sigue utilizando
Kivy Garden MapView y OpenStreetMap; no envía coordenadas GPS a Firebase.

## 1. Configuración de Firebase Console

1. En [Firebase Console](https://console.firebase.google.com/), selecciona
   el proyecto **EnRuta Ya!**.
2. **Authentication → Sign-in method → Correo electrónico/Contraseña**:
   habilita el proveedor y guarda. **Anonymous** ya no es necesario;
   puedes deshabilitarlo una vez confirmada la migración.
3. **Realtime Database → Reglas**: reemplaza las reglas por el contenido
   de `firebase/database.rules.json` de esta rama y pulsa **Publicar**.
   Estas reglas exigen tokens de cuentas con `sign_in_provider == 'password'`
   y comprueban autor, tipo de aviso, antigüedad y los campos permitidos.
4. Obtén tu clave web desde **Configuración del proyecto → General →
   Tus apps → Configuración del SDK → apiKey**. La URL de Realtime Database
   aparece en **Realtime Database → Datos**.
5. En PowerShell, dentro del proyecto:

   ```powershell
   $env:ENRUTA_FIREBASE_API_KEY = "TU_WEB_API_KEY"
   $env:ENRUTA_FIREBASE_DATABASE_URL = "https://TU_BASE.firebasedatabase.app"
   python main.py
   ```

   La URL debe coincidir con la región y proyecto reales; también puede
   terminar en `firebaseio.com`.

## 2. Comportamiento de la aplicación

- Al abrir, muestra una pantalla de bienvenida mientras prepara la UI.
- Al **registrarse o ingresar con correo y contraseña**, muestra una
  pantalla de carga de autenticación mientras realiza la solicitud REST.
- Tras iniciar sesión, **comienza automáticamente** a consultar los avisos.
  No existe interruptor de Firebase en Ajustes.
- Si la conexión falla, permite seguir consultando el mapa y los datos
  guardados localmente. Los avisos publicados en modo remoto se envían
  de manera asíncrona; no hay cola de reintentos offline garantizada.
- Los reportes se actualizan cada 90 s aproximadamente, no se trata de
  una transmisión en tiempo real por WebSocket.
- Los ID y refresh tokens están **solo en memoria**. Al volver a abrir
  la app debes iniciar sesión nuevamente. No se guarda contraseña.

## 3. Datos y migración desde la versión anterior

Las cuentas anteriores de `data/usuarios.json` no son equivalentes a las
cuentas de Firebase. **No se migran automáticamente ni se borran**.
Al activar Firebase, crea una cuenta con correo y contraseña; se genera
un UID distinto. Las favoritas y preferencias todavía permanecen en
JSON local, identificadas por UID, por lo que **no se sincronizan entre
dispositivos** en esta etapa. La sincronización automática actual
es de **avisos comunitarios**, no de perfiles ni de telemetría GPS.

Si se ejecuta sin variables de Firebase, se permite el login local
heredado para pruebas y recuperación de cuentas antiguas.

## 4. Seguridad y limitaciones

- No subas contraseñas, ID tokens ni refresh tokens a GitHub.
- La clave web de Firebase identifica el proyecto pero no es un
  secreto de administrador; las reglas controlan el acceso a la BD.
- El usuario remoto firma reportes con su UID, no con correo o nombre.
- Los reportes no transmiten GPS, IP, nombre ni email; se necesita
  mitigación antiabuso adicional antes de producción.
- La app académica no tiene todavía recuperación de contraseña,
  verificación de correo ni moderación. Esas son mejoras pendientes.
- No edites las reglas para permitir `.read:true` o `.write:true`.
- Para comprobar la sincronización real, probar dos instalaciones con
  directorios locales independientes y correos de Firebase distintos.

Documentación: https://firebase.google.com/docs/reference/rest/auth
y https://firebase.google.com/docs/database/security .
