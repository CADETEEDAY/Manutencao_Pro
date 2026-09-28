package org.cadeteeday.manutencaopro;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import org.kivy.android.PythonActivity;

public class CustomWebChromeClient extends WebChromeClient {
    private Activity activity;
    public ValueCallback<Uri[]> filePathCallback;
    public static final int REQUEST_CODE = 1001;

    public CustomWebChromeClient(Activity activity) {
        this.activity = activity;
        if (activity instanceof PythonActivity) {
            ((PythonActivity) activity).registerActivityResultListener(new PythonActivity.ActivityResultListener() {
                @Override
                public void onActivityResult(int requestCode, int resultCode, Intent data) {
                    if (requestCode == REQUEST_CODE) {
                        if (filePathCallback == null) return;
                        Uri[] results = null;
                        if (resultCode == Activity.RESULT_OK && data != null) {
                            if (data.getData() != null) {
                                results = new Uri[]{data.getData()};
                            } else if (data.getClipData() != null) {
                                int count = data.getClipData().getItemCount();
                                results = new Uri[count];
                                for (int i = 0; i < count; i++) {
                                    results[i] = data.getClipData().getItemAt(i).getUri();
                                }
                            }
                        }
                        filePathCallback.onReceiveValue(results);
                        filePathCallback = null;
                    }
                }
            });
        }
    }

    @Override
    public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
        if (this.filePathCallback != null) {
            this.filePathCallback.onReceiveValue(null);
        }
        this.filePathCallback = filePathCallback;

        try {
            // Abre o seletor nativo do sistema (permitindo escolher entre Câmera e Galeria)
            Intent intent = fileChooserParams.createIntent();
            activity.startActivityForResult(intent, REQUEST_CODE);
            return true;
        } catch (Exception e) {
            Intent fallbackIntent = new Intent(Intent.ACTION_GET_CONTENT);
            fallbackIntent.addCategory(Intent.CATEGORY_OPENABLE);
            fallbackIntent.setType("image/*");
            try {
                activity.startActivityForResult(Intent.createChooser(fallbackIntent, "Selecionar Imagem"), REQUEST_CODE);
                return true;
            } catch (Exception ex) {
                this.filePathCallback = null;
                return false;
            }
        }
    }
}
