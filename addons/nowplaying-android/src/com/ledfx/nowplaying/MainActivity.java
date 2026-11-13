package com.ledfx.nowplaying;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * The addon's only screen: whether notification access is granted, and the
 * two places to grant it. Built in code - there is nothing to lay out.
 */
public class MainActivity extends Activity {

    private TextView status;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        int pad = Math.round(24 * getResources().getDisplayMetrics().density);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(pad, pad, pad, pad);

        TextView intro = new TextView(this);
        intro.setText("Sends the song playing on this device to LedFx, so Now Playing works "
            + "in the LedFx app. LedFx must be running on this device.");
        layout.addView(intro);

        status = new TextView(this);
        status.setPadding(0, pad, 0, pad);
        layout.addView(status);

        Button access = new Button(this);
        access.setText("Open notification access");
        access.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
            }
        });
        layout.addView(access);

        TextView restricted = new TextView(this);
        restricted.setPadding(0, pad, 0, 0);
        restricted.setText("Installed from a file or browser? Android then blocks the grant "
            + "(\"restricted setting\"). Open App info, tap the menu at the top right, choose "
            + "\"Allow restricted settings\", then grant access again.");
        layout.addView(restricted);

        Button appInfo = new Button(this);
        appInfo.setText("Open app info");
        appInfo.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                intent.setData(Uri.fromParts("package", getPackageName(), null));
                startActivity(intent);
            }
        });
        layout.addView(appInfo);

        setContentView(layout);
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Re-read when the user comes back from the settings screens.
        status.setText(accessGranted()
            ? "Notification access: granted. Now Playing is sent to LedFx."
            : "Notification access: not granted.");
    }

    private boolean accessGranted() {
        String enabled = Settings.Secure.getString(
            getContentResolver(), "enabled_notification_listeners");
        if (enabled == null) {
            return false;
        }
        String self = new ComponentName(this, NowPlayingListenerService.class).flattenToString();
        for (String entry : enabled.split(":")) {
            if (self.equals(entry)) {
                return true;
            }
        }
        return false;
    }
}
