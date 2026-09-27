[app]

# (str) Título da aplicação
title = Manutencao Pro

# (str) Nome do pacote
package.name = manutencao

# (str) Domínio do pacote
package.domain = org.manutencao

# (str) Diretório do código-fonte
source.dir = .

# (list) Extensões incluídas
source.include_exts = py,png,jpg,kv,atlas

# (str) Versão da aplicação
version = 1.0.0

# (list) Dependências da aplicação (o Kivy já inclui pyjnius e sdl2 automaticamente)
requirements = python3,kivy==2.3.0

# (str) Orientação
orientation = portrait

# (bool) Ecrã inteiro
fullscreen = 0

# (list) Permissões necessárias
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# (int) Versão da API de destino do Android
android.api = 33

# (int) Versão mínima da API suportada
android.minapi = 21

# (int) Versão da API do NDK
android.ndk_api = 21

# (str) Versão do NDK compatível
android.ndk = 25b

# (bool) Aceitar licenças automaticamente
android.accept_sdk_license = True

# (str) Ponto de entrada nativo do Kivy
android.entrypoint = org.kivy.android.PythonActivity

# (str) Tema visual nativo estável
android.apptheme = @android:style/Theme.NoTitleBar

# (list) Arquitetura suportada
android.archs = arm64-v8a

# (bool) Desativado para compatibilidade com o tema nativo
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