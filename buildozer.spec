[app]

# (str) Title of your application
title = Proyecto GPS

# (str) Package name
package.name = proyectogps

# (str) Package domain (needed for android/ios packaging)
package.domain = org.loschupa

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,json

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, .venv, .git, __pycache__

# (list) List of exclusions using pattern matching
# Do not prefix with './'
source.exclude_patterns = usuarios.json, precios_globales.json, listas_*.json, listas.json

# (str) Application versioning (method 1)
version = 0.1.3

# (list) Application requirements
# Notas:
#  - KivyMD 2.x depende de pillow y materialyoucolor, que NO tienen wheels para
#    Android. Hay que declararlos aqui para que p4a use sus recetas; si no, pip
#    falla con "ResolutionImpossible" al resolver kivymd.
#  - No se fija la version de python3/hostpython3: p4a develop usa 3.14.x por
#    defecto. Para 3.13 anade al inicio: hostpython3==3.13.9,python3==3.13.9,
#    (cualquier 3.13.x que exista en python.org) y prueba que compile.
#  - Tras cambiar requirements ejecuta: buildozer android clean
requirements = python3,kivy==2.3.1,kivymd==2.0.0,pillow,materialyoucolor,asynckivy,asyncgui,exceptiongroup,plyer,pyjnius

# (str) Custom source folders for requirements
# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (list) Supported orientations
# Valid options are: landscape, portrait, portrait-reverse or landscape-reverse
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
#android.presplash_color = #0A0B0F

#
# Android specific
#

# (list) Permissions
# POST_NOTIFICATIONS es obligatorio en Android 13+ para mostrar avisos.
android.permissions = POST_NOTIFICATIONS

# (int) Target Android API, should be as high as possible.
android.api = 36

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 29

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = False

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

#
# Python for android (p4a) specific
#

# (str) python-for-android branch to use, defaults to master
p4a.branch = develop

# (str) python-for-android bootstrap (sdl2 es el predeterminado para Kivy)
p4a.bootstrap = sdl2

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 0
