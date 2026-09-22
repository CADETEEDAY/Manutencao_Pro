[app]
title = Manutenção
package.name = manutencao
package.domain = org.manutencao

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,html,css,js

version = 1.0.0

# Deixe apenas estes pacotes essenciais
requirements = python3,kivy,flask,setuptools

android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True

# Apenas arm64 para compilação rápida e sem conflito de arquitetura
android.archs = arm64-v8a

entrypoint = main.py

[buildozer]
log_level = 2
warn_on_root = 1
