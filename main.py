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
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

class MainApp(App):
    def build(self):
        # 1. Solicita permissoes nativas em tempo de execucao no Android
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

        # 2. Inicia a execucao do Flask numa thread paralela
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        # 3. Aguarda que o servidor local esteja pronto
        url = "http://127.0.0.1:5000"
        for _ in range(30):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except Exception:
                time.sleep(0.5)

        # 4. Configura o WebView nativo com suporte a media, camera e ficheiros
        if platform == "android":
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            WebView = autoclass("android.webkit.WebView")
            WebViewClient = autoclass("android.webkit.WebViewClient")
            WebChromeClient = autoclass("android.webkit.WebChromeClient")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity

            @run_on_ui_thread
            def create_webview():
                webview = WebView(activity)
                settings = webview.getSettings()
                
                # Execucao de scripts e armazenamento
                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setDatabaseEnabled(True)
                
                # Permissoes de leitura de ficheiros locais e upload
                settings.setAllowFileAccess(True)
                settings.setAllowContentAccess(True)
                settings.setAllowFileAccessFromFileURLs(True)
                settings.setAllowUniversalAccessFromFileURLs(True)
                settings.setMediaPlaybackRequiresUserGesture(False)
                
                # Clientes necessarios para renderizacao e operacoes de ficheiros/camera
                webview.setWebViewClient(WebViewClient())
                webview.setWebChromeClient(WebChromeClient())
                
                activity.setContentView(webview)
                webview.loadUrl(url)

            create_webview()

        return BoxLayout()

if __name__ == "__main__":
    MainApp().run()
