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


class ManutencaoMobileApp(App):

  def build(self):
    thread_servidor = threading.Thread(
        target=iniciar_servidor_flask, daemon=True
    )
    thread_servidor.start()

    if platform == "android":
      try:
        from android.permissions import request_permissions

        permissoes = [
            "android.permission.CAMERA",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
        ]
        request_permissions(permissoes)
      except Exception as erro:
        print(f"Erro ao solicitar permissoes: {erro}")

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

        # Guarda as referências necessárias para o serviço de impressão Android
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
