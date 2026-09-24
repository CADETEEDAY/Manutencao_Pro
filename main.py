import os
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform

URL_RENDER = "https://manutencao-pro.onrender.com/"


class ManutencaoMobileApp(App):

  def build(self):
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
        print(f"Erro de permissoes: {erro}")

      Clock.schedule_once(self.carregar_webview_android, 1.2)
    else:
      import webbrowser

      Clock.schedule_once(lambda dt: webbrowser.open(URL_RENDER), 0.8)

    layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
    layout.add_widget(
        Label(
            text="Manutenção Predial\n\nSincronizando com a nuvem...",
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
        WebChromeClient = autoclass("android.webkit.WebChromeClient")
        WebSettings = autoclass("android.webkit.WebSettings")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity

        webview = WebView(activity)
        settings = webview.getSettings()

        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setAllowFileAccess(True)
        settings.setAllowContentAccess(True)

        # Força o aplicativo a sempre buscar a versão mais recente sem travar no cache
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE)
        webview.clearCache(True)

        # Permite tocar os alarmes sonoros automaticamente
        settings.setMediaPlaybackRequiresUserGesture(False)

        webview.setWebViewClient(WebViewClient())
        webview.setWebChromeClient(WebChromeClient())

        activity.setContentView(webview)
        webview.loadUrl(URL_RENDER)

      _criar_e_exibir()
    except Exception as erro:
      print(f"Erro ao injetar WebView Android: {erro}")


if __name__ == "__main__":
  ManutencaoMobileApp().run()
