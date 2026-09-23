import os
import threading
import time
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform

# =========================================================================
# COLOQUE AQUI O SEU LINK REAL COPIADO DO PAINEL DO RENDER:
# (Certifique-se de que substitui este valor pelo link do seu serviço)
# =========================================================================
URL_RENDER = "https://SEU-APP.onrender.com/"

PORTA_LOCAL = 5000
HOST_LOCAL = "127.0.0.1"


def iniciar_servidor_interno():
  """Mantém o servidor local ativo caso o telemóvel fique offline ou o Render falhe."""
  try:
    import app as flask_module

    flask_module.app.run(
        host=HOST_LOCAL, port=PORTA_LOCAL, debug=False, use_reloader=False
    )
  except Exception as erro:
    print(f"Erro ao iniciar servidor local: {erro}")


class ManutencaoMobileApp(App):

  def build(self):
    # Inicia o servidor local como garantia de funcionamento
    thread = threading.Thread(target=iniciar_servidor_interno, daemon=True)
    thread.start()

    if platform == "android":
      try:
        from android.permissions import request_permissions

        permissoes = [
            "android.permission.INTERNET",
            "android.permission.ACCESS_NETWORK_STATE",
            "android.permission.CAMERA",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.READ_MEDIA_IMAGES",
        ]
        request_permissions(permissoes)
      except Exception as erro:
        print(f"Erro ao solicitar permissões: {erro}")

      Clock.schedule_once(self.carregar_interface, 2.0)
    else:
      import webbrowser

      destino = (
          URL_RENDER
          if "SEU-APP" not in URL_RENDER
          else f"http://{HOST_LOCAL}:{PORTA_LOCAL}/"
      )
      Clock.schedule_once(lambda dt: webbrowser.open(destino), 1.0)

    layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
    layout.add_widget(
        Label(
            text="Manutenção Predial\n\nA carregar o sistema...",
            halign="center",
            valign="middle",
            font_size="20sp",
        )
    )
    return layout

  def carregar_interface(self, dt):
    try:
      from android.runnable import run_on_ui_thread
      from jnius import autoclass

      @run_on_ui_thread
      def _injetar_webview():
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        WebChromeClient = autoclass("android.webkit.WebChromeClient")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity

        webview = WebView(activity)
        settings = webview.getSettings()

        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setAllowFileAccess(True)
        settings.setAllowContentAccess(True)
        settings.setMediaPlaybackRequiresUserGesture(False)

        webview.setWebViewClient(WebViewClient())
        webview.setWebChromeClient(WebChromeClient())

        activity.setContentView(webview)

        # Se o link não tiver sido configurado, abre a versão local sem bloquear o utilizador
        if "SEU-APP" in URL_RENDER or not URL_RENDER.startswith("http"):
          webview.loadUrl(f"http://{HOST_LOCAL}:{PORTA_LOCAL}/")
        else:
          webview.loadUrl(URL_RENDER)

      _injetar_webview()
    except Exception as erro:
      print(f"Erro ao configurar WebView: {erro}")


if __name__ == "__main__":
  ManutencaoMobileApp().run()
