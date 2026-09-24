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
      from jnius import PythonJavaClass, autoclass, java_method

      activity = autoclass("org.kivy.android.PythonActivity").mActivity
      WebView = autoclass("android.webkit.WebView")
      WebChromeClient = autoclass("android.webkit.WebChromeClient")
      WebSettings = autoclass("android.webkit.WebSettings")
      Intent = autoclass("android.content.Intent")
      Uri = autoclass("android.net.Uri")

      webview = WebView(activity)
      settings = webview.getSettings()

      settings.setJavaScriptEnabled(True)
      settings.setDomStorageEnabled(True)
      settings.setDatabaseEnabled(True)
      settings.setAllowFileAccess(True)
      settings.setAllowContentAccess(True)
      settings.setCacheMode(WebSettings.LOAD_NO_CACHE)
      webview.clearCache(True)
      settings.setMediaPlaybackRequiresUserGesture(False)

      # INTERCEPTADOR DE URL: Resolve WhatsApp e Impressão no APK
      class AppWebViewClient(PythonJavaClass):
        __javainterfaces__ = ["android/webkit/WebViewClient"]
        __javacontext__ = "app"

        def __init__(self, act, wv):
          super().__init__()
          self.act = act
          self.wv = wv

        @java_method("(Landroid/webkit/WebView;Ljava/lang/String;)Z")
        def shouldOverrideUrlLoading(self, view, url):
          # 1. Abre o WhatsApp no aplicativo instalado
          if (
              "whatsapp.com" in url
              or "wa.me" in url
              or url.startswith("whatsapp:")
          ):
            try:
              intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
              self.act.startActivity(intent)
              return True
            except Exception as e:
              print(f"Erro ao abrir WhatsApp: {e}")
              return False

          # 2. Aciona a impressão nativa do Android
          if "/acao/imprimir" in url:
            try:

              @run_on_ui_thread
              def _chamar_print():
                Context = autoclass("android.content.Context")
                MediaSize = autoclass("android.print.PrintAttributes$MediaSize")
                Builder = autoclass("android.print.PrintAttributes$Builder")

                printManager = self.act.getSystemService(Context.PRINT_SERVICE)
                job_name = "Recibo_OS"
                printAdapter = self.wv.createPrintDocumentAdapter(job_name)

                builder = Builder()
                builder.setMediaSize(MediaSize.ISO_A4)
                printManager.print(job_name, printAdapter, builder.build())

              _chamar_print()
              return True
            except Exception as e:
              print(f"Erro PrintManager: {e}")
              return False

          # 3. Permite abrir links externos no Chrome
          if "abrir-chrome=1" in url:
            try:
              intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
              self.act.startActivity(intent)
              return True
            except Exception as e:
              print(f"Erro ao abrir Chrome: {e}")
              return False

          return False

      client = AppWebViewClient(activity, webview)
      webview.setWebViewClient(client)
      webview.setWebChromeClient(WebChromeClient())

      activity.setContentView(webview)
      webview.loadUrl(URL_RENDER)

    except Exception as erro:
      print(f"Erro ao injetar WebView Android: {erro}")


if __name__ == "__main__":
  ManutencaoMobileApp().run()
