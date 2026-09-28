[app]

# (str) Titulo da aplicacao
title = Manutencao Pro

# (str) Nome do pacote (apenas minusculas e sem espacos)
package.name = manutencaopro

# (str) Dominio do pacote (inverso)
package.domain = org.cadeteeday

# (str) Diretoria onde se encontra o codigo-fonte
source.dir = .

# (list) Extensoes de ficheiros a incluir no pacote final
source.include_exts = py,png,jpg,kv,atlas,html,css,js,db,sqlite3

# (str) Versao da aplicacao
version = 1.0.0

# (list) Dependencias da aplicacao
requirements = python3,kivy,flask,jinja2,werkzeug,markupsafe,itsdangerous,pyjnius,android

# (str) Orientacao suportada (portrait, landscape ou all)
orientation = portrait

# (list) Permissoes do Android (inclui acesso a camera e ficheiros)
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# (int) Versao minima da API do Android
android.minapi = 21

# (int) Versao alvo da API do Android
android.api = 33

# (str) Versao compativel do NDK para compilacao estavel
android.ndk = 25b

# (list) Arquitetura suportada (64 bits moderna)
android.archs = arm64-v8a

# (bool) Manter o ecra sempre ligado
android.wakelock = False

# (bool) Aceitar automaticamente as licencas do SDK Android
android.accept_sdk_license = True

# (bool) Ecra inteiro
fullscreen = 0

[buildozer]

# (int) Nivel de registo da consola (2 = detalhado para depuracao)
log_level = 2

# (int) Aviso ao executar como superutilizador
warn_on_root = 0
