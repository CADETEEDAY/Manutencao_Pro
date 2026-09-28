package org.cadeteeday.manutencaopro;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class CustomWebViewClient extends WebViewClient {
    private Activity activity;

    public CustomWebViewClient(Activity activity) {
        this.activity = activity;
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView view, String url) {
        return handleUrl(url);
    }

    @Override
    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
        return handleUrl(request.getUrl().toString());
    }

    private boolean handleUrl(String url) {
        if (url.startsWith("http://127.0.0.1") || url.startsWith("http://localhost")) {
            return false;
        }

        if (url.startsWith("whatsapp:") || 
            url.startsWith("https://api.whatsapp.com") || 
            url.startsWith("https://wa.me") || 
            url.startsWith("tel:") || 
            url.startsWith("mailto:") || 
            url.startsWith("intent:")) {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                activity.startActivity(intent);
                return true;
            } catch (Exception e) {
                return true;
            }
        }

        return false;
    }
}
