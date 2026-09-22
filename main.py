import os
import threading
import time
from app import app
from kivy.app import App
from kivy.clock import Clock
from kivy.utils import platform

PORT = 5000
HOST = "127.0.0.1"


def iniciar_flask():
  app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


class ManutencaoMobileApp(App):

  def build(self):
    server_thread = threading.Thread(target=iniciar_flask, daemon=True)
    server_thread.start()

    if platform == "android":
      from android.runnable import run_on_ui_thread
      from jnius import autoclass

      @run_on_ui_thread
      def abrir_webview():
        WebView = autoclass("android.webkit.WebView")
        WebViewClient = autoclass("android.webkit.WebViewClient")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity

        webview = WebView(activity)
        settings = webview.getSettings()
        settings.setJavaScriptEnabled(True)
        settings.setDomStorageEnabled(True)
        webview.setWebViewClient(WebViewClient())
        activity.setContentView(webview)
        webview.loadUrl(f"http://{HOST}:{PORT}/")

      Clock.schedule_once(lambda dt: abrir_webview(), 1.0)
    else:
      import webbrowser

      Clock.schedule_once(
          lambda dt: webbrowser.open(f"http://{HOST}:{PORT}/"), 1.0
      )

    return None


if __name__ == "__main__":
  ManutencaoMobileApp().run()
