[app]
title = Manutenção
package.name = manutencao
package.domain = org.manutencao

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,html,css,js

version = 1.0.0

# Inclusão explícita de pyjnius e android para suporte a WebView nativa
requirements = python3,kivy,flask,pyjnius,android,setuptools

android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.build_tools_version = 33.0.2
android.accept_sdk_license = True

# Apenas arquitetura 64-bit para evitar instabilidade na compilação
android.archs = arm64-v8a

entrypoint = main.py

[buildozer]
log_level = 2
warn_on_root = 1
