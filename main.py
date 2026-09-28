import threading
import time
import urllib.request
import os

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

# Inicia o servidor Flask local em segundo plano
def run_flask():
    from app import app
    # Escuta apenas localmente na porta 5000
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

class MainApp(App):
    def build(self):
        # 1. Inicia a thread do Flask
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # 2. Aguarda que o servidor Flask esteja acessível
        url = "http://127.0.0.1:5000"
        for _ in range(30):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.5)

        # 3. Abre o WebView nativo no Android
        if platform == "android":
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            WebView = autoclass("android.webkit.WebView")
            WebViewClient = autoclass("android.webkit.WebViewClient")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity

            @run_on_ui_thread
            def create_webview():
                webview = WebView(activity)
                settings = webview.getSettings()
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                webview.setWebViewClient(WebViewClient())
                activity.setContentView(webview)
                webview.loadUrl(url)

            create_webview()

        return BoxLayout()

if __name__ == "__main__":
    MainApp().run()
