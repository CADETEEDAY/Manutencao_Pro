[app]

# (str) Titulo da aplicacao
title = Manutencao Pro

# (str) Nome do pacote
package.name = manutencao

# (str) Dominio do pacote
package.domain = org.manutencao

# (str) Diretorio do codigo-fonte
source.dir = .

# (list) Extensoes incluidas
source.include_exts = py,png,jpg,kv,atlas

# (str) Versao da aplicacao
version = 1.0.0

# (list) Dependencias da aplicacao
requirements = python3,kivy

# (str) Orientacao
orientation = portrait

# (bool) Ecra inteiro
fullscreen = 0

# (list) Permissoes do Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# (int) Versao da API de destino do Android
android.api = 33

# (int) Versao minima da API suportada
android.minapi = 21

# (str) Versao estavel e compativel do NDK
android.ndk = 25b

# (bool) Aceitar licencas automaticamente
android.accept_sdk_license = True

# (str) Ponto de entrada nativo do Kivy
android.entrypoint = org.kivy.android.PythonActivity

# (str) Tema visual nativo compativel
android.apptheme = @android:style/Theme.NoTitleBar

# (list) Arquitetura suportada (64 bits)
android.archs = arm64-v8a

# (bool) Ativado para compatibilidade com o p4a v2024.01.21
android.enable_androidx = True

# (bool) Copiar bibliotecas compiladas
android.copy_libs = 1

# (bool) Manter janela ativa
android.window = 1

# (str) Versao estavel do python-for-android
p4a.branch = v2024.01.21

[buildozer]

# (int) Nivel de registos
log_level = 2

# (int) Aviso de root
warn_on_root = 1
