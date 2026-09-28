[app]

# (str) Título da aplicação
title = Manutencao Pro

# (str) Nome do pacote (apenas letras minúsculas e sem espaços)
package.name = manutencaopro

# (str) Domínio do pacote (inverso)
package.domain = org.cadeteeday

# (str) Diretoria onde se encontra o código-fonte (raiz)
source.dir = .

# (list) Extensões de ficheiros a incluir no pacote final
source.include_exts = py,png,jpg,kv,atlas,html,css,js,db,sqlite3

# (str) Versão da aplicação
version = 1.0.0

# (list) Dependências da aplicação
# Nota: weasyprint e psycopg2 ficam de fora para evitar erros de compilação C/NDK
requirements = python3,kivy,flask,jinja2,werkzeug,markupsafe,itsdangerous,pyjnius,android

# (str) Orientação suportada (portrait, landscape ou all)
orientation = portrait

# (list) Permissões do Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# (int) Versão mínima da API do Android
android.minapi = 21

# (int) Versão alvo da API do Android
android.api = 33

# (list) Arquiteturas suportadas
android.archs = arm64-v8a, armeabi-v7a

# (bool) Se o ecrã deve manter-se sempre ativo
android.wakelock = False

# (bool) Aceitar automaticamente as licenças do SDK do Android
android.accept_sdk_license = True

# (bool) Ecrã inteiro
fullscreen = 0

[buildozer]

# (int) Nível de registo / detalhe da consola (2 = detalhado para depuração)
log_level = 2

# (int) Aviso ao executar como superutilizador (0 = desativado)
warn_on_root = 0
