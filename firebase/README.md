# Firebase opcional (sin datos GPS)

Este módulo utiliza Realtime Database, no Firestore ni MySQL.
La app sigue funcionando localmente sin Firebase.

1. Crear proyecto en https://console.firebase.google.com/ (Spark gratuito).
2. Authentication → Sign-in method → habilitar **Anonymous**.
3. Realtime Database → crear BD (preferir región cercana a Chile), modo bloqueado.
4. Realtime Database → Rules: pegar **database.rules.json** de esta carpeta.
5. Settings → General → Web API Key y Realtime Database → URL HTTPS.
6. En PowerShell, antes de iniciar Kivy:
   ```powershell
   $env:ENRUTA_FIREBASE_API_KEY = "TU_WEB_API_KEY"
   $env:ENRUTA_FIREBASE_DATABASE_URL = "https://TU_BD-default-rtdb.firebaseio.com"
   python main.py
   ```
7. En la app: **Ajustes → Avisos compartidos por Firebase** (desactivado por defecto).

**Limitaciones y seguridad**: Las cuentas de Login/Registro continúan
siendo locales. Firebase Anonymous Auth identifica la conexión remota,
pero NO vincula la cuenta de Kivy a una cuenta real de Firebase.
Los avisos compartidos no contienen nombres, correos, IP ni lat/lon.
La consulta es por sondeo, no tiempo real por WebSocket; se obtienen
hasta 100 reportes recientes. Si falla Firebase, el registro local
continúa funcionando. Las reglas minimizan riesgos, pero una persona
puede crear muchas cuentas anónimas: no está listo para producción
pública sin App Check, rate limit y moderación.

La Web API Key no es una contraseña maestra de Firebase. No poner nunca
archivos de cuenta de servicio/admin en el cliente o en GitHub.
**Las reglas son la barrera real de seguridad**; nunca permitir lectura
y escritura públicas. <https://firebase.google.com/docs/database/security>

Spark ofrece cuotas gratuitas sin método de pago, sujetas a límites:
<https://firebase.google.com/pricing>.
