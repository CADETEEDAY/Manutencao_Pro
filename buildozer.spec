[app]

# (str) Título da aplicação
title = Manutencao Pro

# (str) Nome do pacote
package.name = manutencao

# (str) Domínio do pacote
package.domain = org.manutencao

# (str) Diretório onde se encontra o main.py
source.dir = .

# (list) Extensões de ficheiros a incluir
source.include_exts = py,png,jpg,kv,atlas

# (str) Versão da aplicação
version = 1.0.0

# (list) Dependências da aplicação (Python e Kivy com PyJNIus para chamadas nativas)
requirements = python3,kivy==2.3.0,pyjnius

# (str) Orientação suportada (ecrã na vertical)
orientation = portrait

# (bool) Ecrã inteiro (0 = barra de estado visível, 1 = ecrã inteiro)
fullscreen = 0

# (list) Permissões Android necessárias para rede, câmara e galeria
android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

# (int) Versão da API de destino do Android
android.api = 33

# (int) Versão mínima da API do Android suportada
android.minapi = 21

# (int) Versão da API do NDK a utilizar
android.ndk_api = 21

# (bool) Aceitar automaticamente as licenças do SDK
android.accept_sdk_license = True

# (str) Ponto de entrada nativo do Kivy
android.entrypoint = org.kivy.android.PythonActivity

# (str) Tema visual da aplicação
android.apptheme = @android:style/Theme.NoTitleBar

# (list) Arquiteturas suportadas (focada em telemóveis modernos de 64 bits)
android.archs = arm64-v8a

# (bool) Ativar suporte ao AndroidX
android.enable_androidx = True

# (bool) Copiar bibliotecas em vez de criar diretório de ligação
android.copy_libs = 1

# (bool) Manter a barra de navegação/janela
android.window = 1

[buildozer]

# (int) Nível de registos (2 = detalhado para depuração no GitHub Actions)
log_level = 2

# (int) Apresentar aviso caso seja executado como root
warn_on_root = 1
