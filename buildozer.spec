[app]

# (str) Título da aplicação
title = Manutencao Pro

# (str) Nome do pacote
package.name = manutencao

# (str) Domínio do pacote
package.domain = org.manutencao

# (str) Diretório onde se encontra o código fonte
source.dir = .

# (list) Extensões a incluir no pacote
source.include_exts = py,png,jpg,kv,atlas

# (str) Versão da aplicação
version = 1.0.0

# (list) Dependências da aplicação
requirements = python3,kivy==2.3.0,pyjnius

# (str) Orientação suportada
orientation = portrait

# (bool) Ecrã inteiro (0 = barra de estado visível)
fullscreen = 0

# (list) Permissões do Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# (int) Versão da API de destino do Android
android.api = 33

# (int) Versão mínima da API suportada
android.minapi = 21

# (int) Versão da API do NDK
android.ndk_api = 21

# (str) Versão estável obrigatória do NDK (impede o download do r28c)
android.ndk = 25b

# (bool) Aceitar automaticamente as licenças do SDK
android.accept_sdk_license = True

# (str) Ponto de entrada nativo do Kivy
android.entrypoint = org.kivy.android.PythonActivity

# (str) Tema visual nativo sem dependência de AndroidX
android.apptheme = @android:style/Theme.NoTitleBar

# (list) Arquitetura suportada (64 bits moderna)
android.archs = arm64-v8a

# (bool) Desativado para evitar conflitos de tema e dependências no Gradle
android.enable_androidx = False

# (bool) Copiar bibliotecas compiladas
android.copy_libs = 1

# (bool) Manter janela ativa
android.window = 1

[buildozer]

# (int) Nível de registos detalhado
log_level = 2

# (int) Aviso de root
warn_on_root = 1