[app]

# (str) Title of your application (SEM ACENTOS PARA NÃO TRAVAR O GRADLE)
title = Manutencao Pro

# (str) Package name
package.name = manutencao

# (str) Package domain (needed for android/ios packaging)
package.domain = org.manutencao

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas

# (list) List of directory to exclude (evita estouro de memória no GitHub Actions)
source.exclude_dirs = tests, bin, venv, .venv, .git, .github, .buildozer

# (str) Application versioning
version = 1.0.0

# (list) Application requirements
# O APK funciona como WebView conectado ao Render; nao compile psycopg2 ou flask aqui
requirements = python3,kivy,urllib3

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET, ACCESS_NETWORK_STATE, CAMERA, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, READ_MEDIA_IMAGES

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK will support
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Enable AndroidX support
android.enable_androidx = True

# (list) Architectures to build for
android.archs = arm64-v8a

# (bool) Allow backup
android.allow_backup = True
