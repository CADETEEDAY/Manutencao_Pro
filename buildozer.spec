[app]
title = Manutenção
package.name = manutencao
package.domain = org.manutencao

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,html,css,js

version = 1.0.0

requirements = python3,kivy,flask,pyjnius,android,setuptools

# Permissões de rede, câmera e galeria de fotos (legado + Android 13+)
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.2
android.accept_sdk_license = True

android.archs = arm64-v8a

entrypoint = main.py

[buildozer]
log_level = 2
warn_on_root = 1
