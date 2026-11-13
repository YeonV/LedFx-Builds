package com.ledfx.nowplaying;

import android.content.ComponentName;
import android.graphics.Bitmap;
import android.media.MediaMetadata;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.os.SystemClock;
import android.service.notification.NotificationListenerService;
import android.util.Log;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.List;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * The addon's whole job: watch the device's media sessions and forward the
 * current track to the LedFx core as song_info.
 *
 * Android only allows getActiveSessions() for a component of the calling app
 * that the user enabled as notification listener (MediaSessionService
 * verifySessionsRequest enforces the package), so this service is both the
 * grant and the reader. It stays bound while access is granted: that binding
 * is what keeps the process alive without a foreground service. Notifications
 * themselves are never read - none of the onNotification* callbacks is
 * overridden.
 *
 * Everything is event-driven: MediaSessionManager reports session changes,
 * MediaController.Callback reports metadata and playback changes. Nothing
 * polls.
 */
public class NowPlayingListenerService extends NotificationListenerService {

    private static final String TAG = "LedFxNowPlaying";
    /** Asset path of the uploaded cover, at the assets root. */
    private static final String COVER_ASSET = "ledfx_nowplaying_addon.png";
    /** Long edge of the uploaded cover; plenty for gradients and the UI. */
    private static final int COVER_MAX_EDGE = 512;
    private static final String[] ART_KEYS = {
        MediaMetadata.METADATA_KEY_ALBUM_ART,
        MediaMetadata.METADATA_KEY_ART,
        MediaMetadata.METADATA_KEY_DISPLAY_ICON,
    };

    private final Handler main = new Handler(Looper.getMainLooper());
    private final List<MediaController> watched = new ArrayList<>();
    private MediaSessionManager manager;
    private ComponentName component;
    private HandlerThread senderThread;
    // Written on the main thread, read on the sender thread.
    private volatile Handler sender;
    private volatile LedFxClient client;
    private boolean started = false;

    // Sender-thread state: what the core has already been told.
    private String sentIdentity;
    private boolean coverSent;

    // VERIFIED-SAFE(callbacks): the same three public, non-final
    // MediaController.Callback methods (API 21) as the main app's
    // MediaSessionWatcher, which compiled and ran in the LedFx APK.
    private final MediaController.Callback controllerCallback =
        new MediaController.Callback() {
            @Override
            public void onMetadataChanged(MediaMetadata metadata) {
                onMediaChanged();
            }

            @Override
            public void onPlaybackStateChanged(PlaybackState state) {
                onMediaChanged();
            }

            @Override
            public void onSessionDestroyed() {
                onMediaChanged();
            }
        };

    private final MediaSessionManager.OnActiveSessionsChangedListener sessionsListener =
        new MediaSessionManager.OnActiveSessionsChangedListener() {
            @Override
            public void onActiveSessionsChanged(List<MediaController> controllers) {
                watch(controllers);
                onMediaChanged();
            }
        };

    // VERIFIED-SAFE(onListenerConnected): public, non-final, API 21 on
    // NotificationListenerService; the main app overrides it the same way.
    @Override
    public void onListenerConnected() {
        super.onListenerConnected();
        start();
    }

    // VERIFIED-SAFE(onListenerDisconnected): public, non-final, API 24
    // (minSdk is 26).
    @Override
    public void onListenerDisconnected() {
        stop();
        super.onListenerDisconnected();
    }

    @Override
    public void onDestroy() {
        stop();
        super.onDestroy();
    }

    // ------------------------------------------------------------------
    // Lifecycle (main thread)
    // ------------------------------------------------------------------

    private void start() {
        if (started) {
            return;
        }
        manager = (MediaSessionManager) getSystemService(MEDIA_SESSION_SERVICE);
        component = new ComponentName(this, NowPlayingListenerService.class);
        senderThread = new HandlerThread("LedFxNowPlayingSender");
        senderThread.start();
        sender = new Handler(senderThread.getLooper());
        client = new LedFxClient();
        try {
            manager.addOnActiveSessionsChangedListener(sessionsListener, component, main);
            watch(manager.getActiveSessions(component));
        } catch (SecurityException e) {
            // Access was revoked between connect and here.
            Log.w(TAG, "Media sessions not accessible", e);
        }
        started = true;
        Log.i(TAG, "Watching media sessions");
        onMediaChanged();
    }

    private void stop() {
        if (!started) {
            return;
        }
        started = false;
        try {
            manager.removeOnActiveSessionsChangedListener(sessionsListener);
        } catch (Exception e) {
            Log.w(TAG, "Could not remove the sessions listener", e);
        }
        unwatchAll();
        final LedFxClient oldClient = client;
        final HandlerThread oldThread = senderThread;
        sender.post(new Runnable() {
            @Override
            public void run() {
                oldClient.close();
                oldThread.quitSafely();
            }
        });
        sender = null;
        senderThread = null;
        client = null;
    }

    private void watch(List<MediaController> controllers) {
        unwatchAll();
        if (controllers == null) {
            return;
        }
        for (MediaController controller : controllers) {
            try {
                controller.registerCallback(controllerCallback, main);
                watched.add(controller);
            } catch (Exception e) {
                Log.w(TAG, "Could not watch " + controller.getPackageName(), e);
            }
        }
    }

    private void unwatchAll() {
        for (MediaController controller : watched) {
            try {
                controller.unregisterCallback(controllerCallback);
            } catch (Exception e) {
                Log.w(TAG, "Could not unwatch " + controller.getPackageName(), e);
            }
        }
        watched.clear();
    }

    // ------------------------------------------------------------------
    // Reading (main thread) and sending (sender thread)
    // ------------------------------------------------------------------

    /** Snapshot the active session and hand it to the sender thread. */
    private void onMediaChanged() {
        if (!started) {
            return;
        }
        MediaController controller = activeController();
        if (controller == null) {
            return;
        }
        MediaMetadata metadata = controller.getMetadata();
        if (metadata == null) {
            return;
        }
        final String title = metadata.getString(MediaMetadata.METADATA_KEY_TITLE);
        String artistValue = metadata.getString(MediaMetadata.METADATA_KEY_ARTIST);
        if (artistValue == null || artistValue.isEmpty()) {
            artistValue = metadata.getString(MediaMetadata.METADATA_KEY_ALBUM_ARTIST);
        }
        final String artist = artistValue;
        final String album = metadata.getString(MediaMetadata.METADATA_KEY_ALBUM);
        if (isEmpty(title) && isEmpty(artist)) {
            return;
        }
        long durationMs = metadata.getLong(MediaMetadata.METADATA_KEY_DURATION);
        final double duration = durationMs > 0 ? durationMs / 1000.0 : -1;

        PlaybackState state = controller.getPlaybackState();
        final boolean hasState = state != null;
        final boolean playing = hasState && state.getState() == PlaybackState.STATE_PLAYING;
        final double position = hasState ? positionSeconds(state, playing) : -1;
        final Bitmap cover = cover(metadata);

        final Handler target = sender;
        if (target == null) {
            return;
        }
        target.post(new Runnable() {
            @Override
            public void run() {
                send(title, artist, album, duration, hasState, playing, position, cover);
            }
        });
    }

    private void send(String title, String artist, String album, double duration,
            boolean hasState, boolean playing, double position, Bitmap cover) {
        LedFxClient c = client;
        if (c == null) {
            return;
        }
        String identity = title + "\u0000" + artist + "\u0000" + album;
        boolean newTrack = !identity.equals(sentIdentity);
        if (newTrack) {
            coverSent = false;
        }

        // Upload a cover once per track: on the track change, or when the
        // player fills it in later (browsers publish the title first).
        String thumbnail = null;
        if (cover != null && !coverSent) {
            byte[] png = encodeCover(cover);
            if (png != null) {
                thumbnail = c.uploadCover(png, COVER_ASSET);
                coverSent = thumbnail != null;
            }
        } else if (coverSent) {
            thumbnail = COVER_ASSET;
        }

        JSONObject message = new JSONObject();
        try {
            message.put("id", 1);
            message.put("type", "song_info");
            message.put("title", title == null ? "" : title);
            message.put("artist", artist == null ? "" : artist);
            message.put("album", album == null ? "" : album);
            if (thumbnail != null) {
                message.put("thumbnail", thumbnail);
            }
            if (duration >= 0) {
                message.put("duration", duration);
            }
            if (hasState) {
                message.put("playing", playing);
                if (position >= 0) {
                    message.put("position", position);
                }
            }
        } catch (JSONException e) {
            Log.w(TAG, "Could not build song_info", e);
            return;
        }
        if (c.sendSongInfo(message)) {
            sentIdentity = identity;
        }
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /** The playing session, else the first one that exists. */
    private MediaController activeController() {
        MediaController fallback = null;
        for (MediaController controller : watched) {
            PlaybackState state = controller.getPlaybackState();
            if (state != null && state.getState() == PlaybackState.STATE_PLAYING) {
                return controller;
            }
            if (fallback == null) {
                fallback = controller;
            }
        }
        return fallback;
    }

    /**
     * Seconds into the track, or -1 if unknown. PlaybackState holds the
     * position at its last update; while playing it has moved on by the
     * elapsed real time times the speed.
     */
    private static double positionSeconds(PlaybackState state, boolean playing) {
        long positionMs = state.getPosition();
        if (positionMs == PlaybackState.PLAYBACK_POSITION_UNKNOWN) {
            return -1;
        }
        double ms = positionMs;
        long updated = state.getLastPositionUpdateTime();
        if (playing && updated > 0) {
            ms += (SystemClock.elapsedRealtime() - updated) * state.getPlaybackSpeed();
        }
        return Math.max(ms, 0) / 1000.0;
    }

    private static Bitmap cover(MediaMetadata metadata) {
        for (String key : ART_KEYS) {
            try {
                Bitmap bitmap = metadata.getBitmap(key);
                if (bitmap != null) {
                    return bitmap;
                }
            } catch (Exception e) {
                // Try the next key.
            }
        }
        return null;
    }

    /** PNG, scaled down to COVER_MAX_EDGE. PNG keeps the colours exact. */
    private static byte[] encodeCover(Bitmap bitmap) {
        try {
            int width = bitmap.getWidth();
            int height = bitmap.getHeight();
            int edge = Math.max(width, height);
            Bitmap scaled = bitmap;
            if (edge > COVER_MAX_EDGE) {
                float factor = COVER_MAX_EDGE / (float) edge;
                scaled = Bitmap.createScaledBitmap(bitmap,
                    Math.max(1, Math.round(width * factor)),
                    Math.max(1, Math.round(height * factor)), true);
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            if (!scaled.compress(Bitmap.CompressFormat.PNG, 100, out)) {
                return null;
            }
            return out.toByteArray();
        } catch (Exception e) {
            Log.w(TAG, "Could not encode the cover", e);
            return null;
        }
    }

    private static boolean isEmpty(String value) {
        return value == null || value.isEmpty();
    }
}
