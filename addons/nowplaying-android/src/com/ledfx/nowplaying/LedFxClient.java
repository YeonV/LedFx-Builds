package com.ledfx.nowplaying;

import android.util.Base64;
import android.util.Log;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import org.json.JSONObject;

/**
 * Talks to the LedFx core on this device: song_info over its websocket, the
 * cover over POST /api/assets.
 *
 * A minimal RFC 6455 client on a plain socket, so the addon needs no library:
 * it only ever sends masked text frames and answers pings. Frames from the core
 * are read and dropped (nothing is subscribed, so there are hardly any).
 *
 * Not thread-safe by design: every call comes from the one sender thread in
 * NowPlayingListenerService. Connecting is lazy - a failed send closes the
 * socket and the next update connects again, so nothing here retries on a
 * timer.
 */
final class LedFxClient {

    private static final String TAG = "LedFxNowPlaying";
    static final String HOST = "127.0.0.1";
    static final int PORT = 8888;
    private static final int CONNECT_TIMEOUT_MS = 3000;

    private final SecureRandom random = new SecureRandom();
    private Socket socket;
    private OutputStream out;
    private final Object writeLock = new Object();

    /** Send one song_info message; false if the core is not reachable. */
    boolean sendSongInfo(JSONObject message) {
        byte[] payload = message.toString().getBytes(StandardCharsets.UTF_8);
        for (int attempt = 0; attempt < 2; attempt++) {
            try {
                if (socket == null) {
                    connect();
                }
                writeFrame(0x1, payload);
                return true;
            } catch (IOException e) {
                // A core restart leaves a dead socket behind; one fresh
                // connection is tried before giving up on this update.
                Log.d(TAG, "song_info send failed: " + e);
                close();
            }
        }
        return false;
    }

    /**
     * Upload a cover into the core's assets directory.
     *
     * @return the asset path the core stored it under, or null on failure.
     */
    String uploadCover(byte[] png, String assetPath) {
        String boundary = "ledfx" + Long.toHexString(random.nextLong());
        HttpURLConnection connection = null;
        try {
            URL url = new URL("http://" + HOST + ":" + PORT + "/api/assets");
            connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(CONNECT_TIMEOUT_MS);
            connection.setReadTimeout(CONNECT_TIMEOUT_MS);
            connection.setDoOutput(true);
            connection.setRequestMethod("POST");
            connection.setRequestProperty(
                "Content-Type", "multipart/form-data; boundary=" + boundary);

            ByteArrayOutputStream body = new ByteArrayOutputStream(png.length + 512);
            writeText(body, "--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"path\"\r\n\r\n"
                + assetPath + "\r\n");
            writeText(body, "--" + boundary + "\r\n"
                + "Content-Disposition: form-data; name=\"file\"; filename=\"cover.png\"\r\n"
                + "Content-Type: image/png\r\n\r\n");
            body.write(png);
            writeText(body, "\r\n--" + boundary + "--\r\n");

            byte[] bytes = body.toByteArray();
            connection.setFixedLengthStreamingMode(bytes.length);
            OutputStream stream = connection.getOutputStream();
            stream.write(bytes);
            stream.close();

            // The core answers 200 even on errors; the body's status decides.
            InputStream in = connection.getInputStream();
            String response = new String(readAll(in), StandardCharsets.UTF_8);
            in.close();
            JSONObject json = new JSONObject(response);
            if (!"success".equals(json.optString("status"))) {
                Log.w(TAG, "Cover upload rejected: " + response);
                return null;
            }
            return assetPath;
        } catch (Exception e) {
            Log.d(TAG, "Cover upload failed: " + e);
            return null;
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    void close() {
        Socket old = socket;
        socket = null;
        out = null;
        if (old != null) {
            try {
                old.close();
            } catch (IOException ignored) {
                // Already gone.
            }
        }
    }

    // ------------------------------------------------------------------
    // Websocket
    // ------------------------------------------------------------------

    private void connect() throws IOException {
        Socket s = new Socket();
        s.connect(new InetSocketAddress(HOST, PORT), CONNECT_TIMEOUT_MS);
        s.setTcpNoDelay(true);
        byte[] keyBytes = new byte[16];
        random.nextBytes(keyBytes);
        String key = Base64.encodeToString(keyBytes, Base64.NO_WRAP);
        OutputStream o = s.getOutputStream();
        String request = "GET /api/websocket HTTP/1.1\r\n"
            + "Host: " + HOST + ":" + PORT + "\r\n"
            + "Upgrade: websocket\r\n"
            + "Connection: Upgrade\r\n"
            + "Sec-WebSocket-Key: " + key + "\r\n"
            + "Sec-WebSocket-Version: 13\r\n\r\n";
        o.write(request.getBytes(StandardCharsets.US_ASCII));
        o.flush();

        InputStream in = s.getInputStream();
        String status = readLine(in);
        if (status == null || !status.contains(" 101")) {
            s.close();
            throw new IOException("Websocket upgrade refused: " + status);
        }
        String line;
        do {
            line = readLine(in);
        } while (line != null && !line.isEmpty());

        socket = s;
        out = o;
        startReader(s, in);
        Log.i(TAG, "Connected to LedFx at " + HOST + ":" + PORT);
    }

    /** Drain frames from the core, answer pings, notice a close. */
    private void startReader(final Socket s, final InputStream in) {
        Thread reader = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    while (true) {
                        int b0 = in.read();
                        int b1 = in.read();
                        if (b0 < 0 || b1 < 0) {
                            break;
                        }
                        int opcode = b0 & 0x0F;
                        long length = b1 & 0x7F;
                        if (length == 126) {
                            length = ((long) readByte(in) << 8) | readByte(in);
                        } else if (length == 127) {
                            length = 0;
                            for (int i = 0; i < 8; i++) {
                                length = (length << 8) | readByte(in);
                            }
                        }
                        byte[] mask = null;
                        if ((b1 & 0x80) != 0) {
                            mask = new byte[4];
                            readFully(in, mask);
                        }
                        if (length > 16 * 1024 * 1024) {
                            break;
                        }
                        byte[] data = new byte[(int) length];
                        readFully(in, data);
                        if (mask != null) {
                            for (int i = 0; i < data.length; i++) {
                                data[i] ^= mask[i % 4];
                            }
                        }
                        if (opcode == 0x8) {
                            break;
                        }
                        if (opcode == 0x9) {
                            writeFrame(0xA, data);
                        }
                    }
                } catch (IOException e) {
                    // Socket closed - by us or by the core.
                }
                if (socket == s) {
                    close();
                }
            }
        }, "LedFxNowPlayingReader");
        reader.setDaemon(true);
        reader.start();
    }

    private void writeFrame(int opcode, byte[] payload) throws IOException {
        synchronized (writeLock) {
            OutputStream o = out;
            if (o == null) {
                throw new IOException("not connected");
            }
            ByteArrayOutputStream frame = new ByteArrayOutputStream(payload.length + 14);
            frame.write(0x80 | opcode);
            int length = payload.length;
            if (length < 126) {
                frame.write(0x80 | length);
            } else if (length <= 0xFFFF) {
                frame.write(0x80 | 126);
                frame.write((length >> 8) & 0xFF);
                frame.write(length & 0xFF);
            } else {
                frame.write(0x80 | 127);
                for (int i = 7; i >= 0; i--) {
                    frame.write((int) (((long) length >> (8 * i)) & 0xFF));
                }
            }
            byte[] mask = new byte[4];
            random.nextBytes(mask);
            frame.write(mask, 0, 4);
            for (int i = 0; i < length; i++) {
                frame.write(payload[i] ^ mask[i % 4]);
            }
            o.write(frame.toByteArray());
            o.flush();
        }
    }

    // ------------------------------------------------------------------
    // Stream helpers
    // ------------------------------------------------------------------

    private static int readByte(InputStream in) throws IOException {
        int b = in.read();
        if (b < 0) {
            throw new IOException("end of stream");
        }
        return b;
    }

    private static void readFully(InputStream in, byte[] buffer) throws IOException {
        int offset = 0;
        while (offset < buffer.length) {
            int n = in.read(buffer, offset, buffer.length - offset);
            if (n < 0) {
                throw new IOException("end of stream");
            }
            offset += n;
        }
    }

    /** One CRLF-terminated header line, without the line break. */
    private static String readLine(InputStream in) throws IOException {
        ByteArrayOutputStream line = new ByteArrayOutputStream(128);
        int previous = -1;
        while (true) {
            int b = in.read();
            if (b < 0) {
                return line.size() == 0 ? null : line.toString("US-ASCII");
            }
            if (b == '\n' && previous == '\r') {
                byte[] raw = line.toByteArray();
                return new String(raw, 0, raw.length - 1, StandardCharsets.US_ASCII);
            }
            line.write(b);
            previous = b;
            if (line.size() > 8192) {
                throw new IOException("header line too long");
            }
        }
    }

    private static byte[] readAll(InputStream in) throws IOException {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        byte[] chunk = new byte[4096];
        int n;
        while ((n = in.read(chunk)) >= 0) {
            buffer.write(chunk, 0, n);
        }
        return buffer.toByteArray();
    }

    private static void writeText(ByteArrayOutputStream out, String text) throws IOException {
        out.write(text.getBytes(StandardCharsets.UTF_8));
    }
}
