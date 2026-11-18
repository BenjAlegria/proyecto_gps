[app]
title = EnRuta Ya!
package.name = enrutaya
package.domain = cl.enrutaya
version = 0.3.0

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,ttf,otf
source.exclude_dirs = .git,.github,.vscode,backend,docs,tests,tools,.venv,venv,myenv,.buildozer,bin

# Pin Python and host Python to avoid p4a defaulting to 3.14.
# Kivy 2.3.1 and KivyMD 2.0.0 are compatible with Python 3.12.
requirements = python3==3.12.9,hostpython3==3.12.9,kivy==2.3.1,kivymd==2.0.0,kivy-garden.mapview==1.0.6,plyer,requests,pillow,pyjnius,certifi

orientation = portrait
fullscreen = 0

# Android settings MUST be in [app], not in [buildozer].
android.permissions = android.permission.INTERNET,android.permission.ACCESS_COARSE_LOCATION,android.permission.ACCESS_FINE_LOCATION
android.api = 35
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.debug_artifact = apk
p4a.bootstrap = sdl2

[buildozer]
log_level = 2
warn_on_root = 0
