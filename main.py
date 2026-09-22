import os
import threading
import time
import app as flask_module
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform

PORT = 5000
HOST = "127.0.0.1"


def iniciar_servidor_flask():
  flask_module.app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


# ================= SELETOR NATIVO DE GALERIA E CÂMERA DO ANDROID =================
def disparar_seletor_android():
  if platform != "android":
    return False
  try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    @run_on_ui_thread
    def _abrir():
      Intent = autoclass("android.content.Intent")
      PythonActivity = autoclass("org.kivy.android.PythonActivity")
      intent = Intent(Intent.ACTION_GET_CONTENT)
      intent.setType("image/*")
      PythonActivity.mActivity.startActivityForResult(
          Intent.createChooser(intent, "Selecionar Imagem"), 1002
      )

    _abrir()
    return True
  except Exception as err:
    print("Erro ao disparar seletor nativo Android:", err)
    return False


flask_module.DISPARAR_SELETOR = disparar_seletor_android


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
        from jnius import autoclass

        # Permissões de câmera e galeria
        permissoes = [
            "android.permission.CAMERA",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
        ]
        request_permissions(permissoes)

        # Captura o retorno da Galeria / Câmera nativa do Android
        def on_activity_result(request_code, result_code, intent):
          if (
              request_code == 1002
              and result_code == -1
              and intent is not None
          ):
            try:
              uri = intent.getData()
              PythonActivity = autoclass("org.kivy.android.PythonActivity")
              cr = PythonActivity.mActivity.getContentResolver()

              BitmapFactory = autoclass("android.graphics.BitmapFactory")
              CompressFormat = autoclass(
                  "android.graphics.Bitmap$CompressFormat"
              )
              ByteArrayOutputStream = autoclass(
                  "java.io.ByteArrayOutputStream"
              )
              Base64 = autoclass("android.util.Base64")

              bitmap = None
              if uri is not None:
                inputStream = cr.openInputStream(uri)
                bitmap = BitmapFactory.decodeStream(inputStream)
                inputStream.close()
              elif intent.getExtras() is not None:
                bitmap = intent.getExtras().get("data")

              if bitmap is not None:
                baos = ByteArrayOutputStream()
                bitmap.compress(CompressFormat.JPEG, 85, baos)
                b_bytes = baos.toByteArray()
                b64_str = Base64.encodeToString(b_bytes, Base64.NO_WRAP)
                flask_module.FOTO_CAPTURADA_PENDENTE = (
                    f"data:image/jpeg;base64,{b64_str}"
                )
            except Exception as e:
              print("Erro ao processar imagem da galeria:", e)

        activity.bind(on_activity_result=on_activity_result)
      except Exception as erro:
        print(f"Erro ao inicializar listeners Android: {erro}")

      Clock.schedule_once(self.carregar_webview_android, 2.5)
    else:
      import webbrowser

      Clock.schedule_once(
          lambda dt: webbrowser.open(f"http://{HOST}:{PORT}/"), 1.5
      )

    layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
    layout.add_widget(
        Label(
            text="Manutenção\n\nCarregando sistema, aguarde...",
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
        webview.loadUrl(f"http://{HOST}:{PORT}/")

      _criar_e_exibir()
    except Exception as erro:
      print(f"Erro ao injetar WebView Android: {erro}")


if __name__ == "__main__":
  ManutencaoMobileApp().run()
