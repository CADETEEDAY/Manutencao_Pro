[app]

# (str) Titulo da aplicacao
title = Manutencao Pro

# (str) Nome do pacote
package.name = manutencaopro

# (str) Dominio do pacote
package.domain = org.cadeteeday

# (str) Diretorio raiz do codigo
source.dir = .

# (list) Extensoes incluidas no pacote
source.include_exts = py,png,jpg,kv,atlas,html,css,js,db,sqlite3

# (str) Versao atualizada para permitir instalacao direta
version = 1.0.1

# (list) Dependencias da aplicacao
requirements = python3,kivy,flask,jinja2,werkzeug,markupsafe,itsdangerous,pyjnius,android

# (str) Orientacao do ecra
orientation = portrait

# (list) Permissoes do Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# (str) Diretorio contendo arquivos Java auxiliares (Camera, Galeria, WhatsApp e Impressao)
android.add_src = src

# (int) APIs do Android (34 compativel com as exigencias recentes do sistema)
android.minapi = 21
android.api = 34

# (str) Versao compativel do NDK
android.ndk = 25b

# (list) Arquitetura suportada (64 bits moderna)
android.archs = arm64-v8a

# (bool) Manter tela ligada
android.wakelock = False

# (bool) Aceitar licenca do SDK Android
android.accept_sdk_license = True

# (bool) Tela cheia
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 0
