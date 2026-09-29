import threading
import time
import urllib.request
import os

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

def run_flask():
    from app import app
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

class MainApp(App):
    def build(self):
        # 1. Permissoes em tempo de execucao no Android
        if platform == "android":
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

        # 2. Inicia o Flask em background
        flask_thread = threading.Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()

        url = "http://127.0.0.1:5000"

        # 3. Configura e exibe o WebView de imediato
        if platform == "android":
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            WebView = autoclass("android.webkit.WebView")
            CustomWebViewClient = autoclass("org.cadeteeday.manutencaopro.CustomWebViewClient")
            CustomWebChromeClient = autoclass("org.cadeteeday.manutencaopro.CustomWebChromeClient")
            PrintBridge = autoclass("org.cadeteeday.manutencaopro.PrintBridge")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity

            @run_on_ui_thread
            def setup_webview():
                webview = WebView(activity)
                settings = webview.getSettings()

                settings.setJavaScriptEnabled(True)
                settings.setDomStorageEnabled(True)
                settings.setDatabaseEnabled(True)
                settings.setAllowFileAccess(True)
                settings.setAllowContentAccess(True)
                settings.setAllowFileAccessFromFileURLs(True)
                settings.setAllowUniversalAccessFromFileURLs(True)
                settings.setMediaPlaybackRequiresUserGesture(False)

                # Mantem o suporte a impressao, whatsapp e camara/galeria
                webview.setWebViewClient(CustomWebViewClient(activity))
                webview.setWebChromeClient(CustomWebChromeClient(activity))
                webview.addJavascriptInterface(PrintBridge(activity, webview), "AndroidPrint")

                # Exibe um ecra de arranque rapido enquanto o Flask termina de subir
                loading_screen = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {
                            margin: 0;
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            background-color: #121212;
                            color: #ffffff;
                            font-family: -apple-system, sans-serif;
                        }
                        .loader {
                            width: 38px;
                            height: 38px;
                            border: 3px solid rgba(255, 255, 255, 0.15);
                            border-top-color: #2563eb;
                            border-radius: 50%;
                            animation: spin 0.75s linear infinite;
                            margin-bottom: 14px;
                        }
                        @keyframes spin {
                            to { transform: rotate(360deg); }
                        }
                        p { font-size: 14px; opacity: 0.8; letter-spacing: 0.3px; }
                    </style>
                </head>
                <body>
                    <div class="loader"></div>
                    <p>A iniciar o Manutenção Pro...</p>
                </body>
                </html>
                """
                webview.loadDataWithBaseURL(None, loading_screen, "text/html", "UTF-8", None)
                activity.setContentView(webview)

                # Thread de verificacao que nao congela a interface grafica
                def check_server_and_open():
                    for _ in range(60):
                        try:
                            urllib.request.urlopen(url, timeout=0.5)
                            
                            @run_on_ui_thread
                            def load_final_page():
                                webview.loadUrl(url)
                            load_final_page()
                            return
                        except Exception:
                            time.sleep(0.15)

                poll_thread = threading.Thread(target=check_server_and_open)
                poll_thread.daemon = True
                poll_thread.start()

            setup_webview()

        return BoxLayout()

if __name__ == "__main__":
    MainApp().run()
