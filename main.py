import os
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.utils import platform

URL_RENDER = "https://manutencao-pro.onrender.com/"


class ManutencaoMobileApp(App):

  def build(self):
    self.webview = None

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
        print(f"Erro permissoes: {erro}")

      Clock.schedule_once(self.carregar_webview_android, 0.8)
    else:
      import webbrowser

      Clock.schedule_once(lambda dt: webbrowser.open(URL_RENDER), 0.8)

    layout = BoxLayout(orientation="vertical", padding=40, spacing=20)
    layout.add_widget(
        Label(
            text="Manutenção Predial\n\nConectando aos servidores...",
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
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        WebChromeClient = autoclass("android.webkit.WebChromeClient")
        WebSettings = autoclass("android.webkit.WebSettings")

        self.webview = WebView(activity)
        settings = self.webview.getSettings()

        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        settings.setDatabaseEnabled(True)
        settings.setAllowFileAccess(True)
        settings.setAllowContentAccess(True)
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE)
        self.webview.clearCache(True)
        settings.setMediaPlaybackRequiresUserGesture(False)

        # Utiliza clientes nativos diretos (sem subclasses que quebram o PyJNIus)
        self.webview.setWebViewClient(WebViewClient())
        self.webview.setWebChromeClient(WebChromeClient())

        # Exibe a interface web imediatamente
        activity.setContentView(self.webview)
        self.webview.loadUrl(URL_RENDER)

        # Inicia o monitor de links para disparar WhatsApp e Chrome externamente
        Clock.schedule_interval(self.monitorar_links_externos, 0.4)

      _criar_e_exibir()
    except Exception as erro:
      print(f"Erro fatal WebView: {erro}")

  def monitorar_links_externos(self, dt):
    """Monitora a navegação da WebView e redireciona WhatsApp e Impressão para os apps nativos."""
    if not self.webview:
      return
    try:
      url_java = self.webview.getUrl()
      if not url_java:
        return
      url = str(url_java)

      # 1. Dispara o aplicativo do WhatsApp instalado no celular
      if "whatsapp.com" in url or "wa.me" in url or "whatsapp:" in url:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity

        if self.webview.canGoBack():
          self.webview.goBack()

        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        activity.startActivity(intent)

      # 2. Dispara o Chrome para impressão e download de PDF com spooler nativo
      elif "abrir-chrome=1" in url:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity

        if self.webview.canGoBack():
          self.webview.goBack()

        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        activity.startActivity(intent)

    except Exception as e:
      print(f"Erro no monitor de links: {e}")


if __name__ == "__main__":
  ManutencaoMobileApp().run()
