[app]

title = Manutencao Pro
package.name = manutencao
package.domain = org.manutencao

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE,CAMERA,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,READ_MEDIA_IMAGES

android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_path = 

android.accept_sdk_license = True
android.entrypoint = org.kivy.android.PythonActivity
android.apptheme = @android:style/Theme.NoTitleBar
android.archs = arm64-v8a
android.enable_androidx = True
android.copy_libs = 1
android.window = 1

p4a.branch = v2024.01.21

[buildozer]

log_level = 2
warn_on_root = 1
