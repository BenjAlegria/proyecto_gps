[app]
title = EnRuta Ya!
package.name = enrutaya
package.domain = cl.enrutaya
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,ttf,otf
source.exclude_dirs = .git,.github,.vscode,backend,docs,tests,tools,.venv,venv,myenv,.buildozer,bin
version = 0.3.0
requirements = python3,kivy==2.3.1,kivymd==2.0.0,kivy-garden.mapview==1.0.6,plyer,requests,pillow,pyjnius,certifi
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 0

# Android configuration for test builds (not for publishing to the Play Store)
# Android OS permissions; runtime location permission must also be requested by app code.
android.permissions = INTERNET,ACCESS_COARSE_LOCATION,ACCESS_FINE_LOCATION
android.api = 35
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = apk
android.debug_artifact = apk
p4a.bootstrap = sdl2
