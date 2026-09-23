import os
import socket
import threading
import time
import app as flask_module
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform

PORT = 5000
HOST = "0.0.0.0"


def obter_ip_local():
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
  except Exception:
    return "127.0.0.1"


flask_module.LOCAL_IP = obter_ip_local()


def iniciar_servidor_flask():
  flask_module.app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


# ================= SELETORES NATIVOS ANDROID (GALERIA E CÂMERA) =================
def disparar_galeria_android():
  if platform != "android":
    return False
  try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    @run_on_ui_thread
    def _abrir_galeria():
      Intent = autoclass("android.content.Intent")
      PythonActivity = autoclass("org.kivy.android.PythonActivity")
      intent = Intent(Intent.ACTION_GET_CONTENT)
      intent.setType("image/*")
      PythonActivity.mActivity.startActivityForResult(intent, 1002)

    _abrir_galeria()
    return True
  except Exception as e:
    print("Erro ao abrir galeria:", e)
    return False


def disparar_camera_android():
  if platform != "android":
    return False
  try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    @run_on_ui_thread
    def _abrir_camera():
      Intent = autoclass("android.content.Intent")
      MediaStore = autoclass("android.provider.MediaStore")
      PythonActivity = autoclass("org.kivy.android.PythonActivity")
      intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
      PythonActivity.mActivity.startActivityForResult(intent, 1002)

    _abrir_camera()
    return True
  except Exception as e:
    print("Erro ao abrir camera:", e)
    return False


flask_module.DISPARAR_GALERIA = disparar_galeria_android
flask_module.DISPARAR_CAMERA = disparar_camera_android


def processar_imagem_resultado(intent):
  from jnius import autoclass

  PythonActivity = autoclass("org.kivy.android.PythonActivity")
  BitmapFactory = autoclass("android.graphics.BitmapFactory")
  BitmapFactory_Options = autoclass("android.graphics.BitmapFactory$Options")
  CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
  ByteArrayOutputStream = autoclass("java.io.ByteArrayOutputStream")
  Base64 = autoclass("android.util.Base64")

  bitmap = None

  uri = intent.getData() if intent is not None else None
  if uri is not None:
    cr = PythonActivity.mActivity.getContentResolver()
    inputStream = cr.openInputStream(uri)
    # Reduz em 4x o uso de memória na decodificação para evitar OutOfMemoryError
    options = BitmapFactory_Options()
    options.inSampleSize = 2
    bitmap = BitmapFactory.decodeStream(inputStream, None, options)
    inputStream.close()
  elif intent is not None and intent.getExtras() is not None:
    bitmap = intent.getExtras().get("data")

  if bitmap is not None:
    baos = ByteArrayOutputStream()
    formato_jpeg = CompressFormat.valueOf("JPEG")
    bitmap.compress(formato_jpeg, 85, baos)
    b_bytes = baos.toByteArray()
    b64_str = Base64.encodeToString(b_bytes, Base64.NO_WRAP)
    return f"data:image/jpeg;base64,{b64_str}"
  return None


class ManutencaoMobileApp(App):

  def build(self):
    thread_servidor = threading.Thread(
        target=iniciar_servidor_flask, daemon=True
    )
    thread_servidor.start()

    if platform == "android":
      try:
        from android import activity
        from android.permissions import request_permissions

        permissoes = [
            "android.permission.CAMERA",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
        ]
        request_permissions(permissoes)

        def on_activity_result(request_code, result_code, intent):
          if request_code == 1002 and result_code == -1:
            try:
              b64 = processar_imagem_resultado(intent)
              if b64:
                flask_module.FOTO_CAPTURADA_PENDENTE = b64
            except Exception as e:
              print("Erro ao processar imagem capturada:", e)

        activity.bind(on_activity_result=on_activity_result)
      except Exception as erro:
        print(f"Erro nos listeners: {erro}")

      Clock.schedule_once(self.carregar_webview_android, 2.5)
    else:
      import webbrowser

      Clock.schedule_once(
          lambda dt: webbrowser.open(f"http://127.0.0.1:{PORT}/"), 1.5
      )

    layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
    layout.add_widget(
        Label(
            text="Manutenção Conectada\n\nCarregando sistema...",
            halign="center",
            valign="middle",
            font_size="20sp",
        )
    )
    return layout

  def carregar_webview_android(self, dt):
    try:
      from android.runnable import run_on_ui_thread
      from jnius import autoclass

      @run_on_ui_thread
      def _criar_e_exibir():
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity

        webview = WebView(activity)
        settings = webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setAllowFileAccess(True)

        flask_module.GLOBAL_WEBVIEW = webview
        flask_module.GLOBAL_ACTIVITY = activity

        webview.setWebViewClient(WebViewClient())
        activity.setContentView(webview)
        # Se desejar apontar o APK diretamente para o Render na nuvem, mude para:
        # webview.loadUrl("https://SEU-APP.onrender.com/")
        webview.loadUrl(f"http://127.0.0.1:{PORT}/")

      _criar_e_exibir()
    except Exception as erro:
      print(f"Erro ao injetar WebView Android: {erro}")


if __name__ == "__main__":
  ManutencaoMobileApp().run()
