package com.daiso.pm;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;

import androidx.core.app.NotificationCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class IncomingCallService extends FirebaseMessagingService {

    private static final String CHANNEL_ID = "incoming_calls";
    private static final String WAKELOCK_TAG = "com.daiso.pm:incoming_call";

    @Override
    public void onCreate() {
        super.onCreate();
        ensureChannel();
    }

    @Override
    public void onMessageReceived(RemoteMessage message) {
        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        PowerManager.WakeLock wakeLock = pm.newWakeLock(
                PowerManager.FULL_WAKE_LOCK
                        | PowerManager.ACQUIRE_CAUSES_WAKEUP
                        | PowerManager.ON_AFTER_RELEASE,
                WAKELOCK_TAG
        );
        wakeLock.acquire(30_000);

        try {
            ensureChannel();

            String title = "";
            String body = "";

            RemoteMessage.Notification notification = message.getNotification();
            if (notification != null) {
                title = notification.getTitle() != null ? notification.getTitle() : "";
                body = notification.getBody() != null ? notification.getBody() : "";
            }

            if (title.isEmpty()) {
                title = message.getData().getOrDefault("title", "着信");
            }
            if (body.isEmpty()) {
                body = message.getData().getOrDefault("body", "タップして通話画面を開いてください。");
            }

            String tag = message.getData().getOrDefault("tag", "");

            Intent intent = getPackageManager().getLaunchIntentForPackage(getPackageName());
            if (intent == null) {
                intent = new Intent();
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            String sessionId = message.getData().get("session_id");
            if (sessionId != null) {
                intent.putExtra("session_id", sessionId);
            }

            PendingIntent pendingIntent = PendingIntent.getActivity(
                    this, 0, intent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            );

            Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);

            NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.ic_menu_call)
                    .setContentTitle(title)
                    .setContentText(body)
                    .setPriority(NotificationCompat.PRIORITY_MAX)
                    .setCategory(NotificationCompat.CATEGORY_CALL)
                    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                    .setSound(soundUri)
                    .setVibrate(new long[]{0, 500, 200, 500, 200, 500})
                    .setAutoCancel(true)
                    .setContentIntent(pendingIntent)
                    .setFullScreenIntent(pendingIntent, true)
                    .setOngoing(true);

            NotificationManager manager = getSystemService(NotificationManager.class);
            int notificationId = tag.isEmpty() ? (int) System.currentTimeMillis() : tag.hashCode();
            manager.notify(notificationId, builder.build());
        } finally {
            if (wakeLock.isHeld()) {
                wakeLock.release();
            }
        }
    }

    private void ensureChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;

        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return;

        Uri soundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
        AudioAttributes audioAttributes = new AudioAttributes.Builder()
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                .build();

        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "社内通話着信",
                NotificationManager.IMPORTANCE_HIGH
        );
        channel.setDescription("社内通話の着信通知");
        channel.setSound(soundUri, audioAttributes);
        channel.enableVibration(true);
        channel.setVibrationPattern(new long[]{0, 500, 200, 500, 200, 500});
        channel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
        channel.setBypassDnd(true);

        manager.createNotificationChannel(channel);
    }
}
