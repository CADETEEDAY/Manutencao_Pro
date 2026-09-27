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
            text="Manutenção Predial\n\nA ligar aos servidores...",
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

        self.webview.setWebViewClient(WebViewClient())
        self.webview.setWebChromeClient(WebChromeClient())

        activity.setContentView(self.webview)
        self.webview.loadUrl(URL_RENDER)

        # Monitor de chamadas nativas do WhatsApp e Impressão
        Clock.schedule_interval(self.checar_comandos_nativos, 0.25)

      _criar_e_exibir()
    except Exception as erro:
      print(f"Erro fatal WebView: {erro}")

  def checar_comandos_nativos(self, dt):
    if not self.webview:
      return

    from android.runnable import run_on_ui_thread
    from jnius import autoclass

    @run_on_ui_thread
    def _verificar():
      try:
        title_java = self.webview.getTitle()
        if not title_java:
          return
        title = str(title_java)

        # 1. DISPARAR APLICATIVO DO WHATSAPP VIA INTENT NATIVO
        if title.startswith("CMD_WHATSAPP:"):
          self.webview.evaluateJavascript("document.title = 'Recibo';", None)
          texto_enc = title.replace("CMD_WHATSAPP:", "")
          import urllib.parse

          texto = urllib.parse.unquote(texto_enc)

          Intent = autoclass("android.content.Intent")
          activity = autoclass("org.kivy.android.PythonActivity").mActivity

          intent = Intent(Intent.ACTION_SEND)
          intent.setType("text/plain")
          intent.putExtra(Intent.EXTRA_TEXT, texto)
          intent.setPackage("com.whatsapp")
          try:
            activity.startActivity(intent)
          except Exception:
            intent.setPackage(None)
            activity.startActivity(
                Intent.createChooser(intent, "Partilhar Recibo via")
            )

        # 2. DISPARAR O PRINTMANAGER NATIVO DO ANDROID (A4 / PDF)
        elif title.startswith("CMD_PRINT:"):
          self.webview.evaluateJavascript("document.title = 'Recibo';", None)
          Context = autoclass("android.content.Context")
          Builder = autoclass("android.print.PrintAttributes$Builder")
          activity = autoclass("org.kivy.android.PythonActivity").mActivity

          printManager = activity.getSystemService(Context.PRINT_SERVICE)
          job_name = "Recibo_OS"
          printAdapter = self.webview.createPrintDocumentAdapter(job_name)

          builder = Builder()
          printManager.print(job_name, printAdapter, builder.build())

      except Exception as e:
        pass

    _verificar()


if __name__ == "__main__":
  ManutencaoMobileApp().run()
