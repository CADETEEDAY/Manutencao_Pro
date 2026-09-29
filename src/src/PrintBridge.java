package org.cadeteeday.manutencaopro;

import android.app.Activity;
import android.content.Context;
import android.os.Build;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

public class PrintBridge {
    private Activity activity;
    private WebView webView;

    public PrintBridge(Activity activity, WebView webView) {
        this.activity = activity;
        this.webView = webView;
    }

    @JavascriptInterface
    public void print() {
        activity.runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                    PrintManager printManager = (PrintManager) activity.getSystemService(Context.PRINT_SERVICE);
                    String jobName = "Comprovativo_Manutencao";
                    PrintDocumentAdapter printAdapter = webView.createPrintDocumentAdapter(jobName);
                    if (printManager != null) {
                        printManager.print(jobName, printAdapter, new PrintAttributes.Builder().build());
                    }
                }
            }
        });
    }
}
