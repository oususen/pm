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

    private static final String CHANNEL_ALARM = "incoming_calls_alarm";
    private static final String CHANNEL_NOTIFY = "incoming_calls_notify";
    private static final String WAKELOCK_TAG = "com.daiso.pm:incoming_call";

    @Override
    public void onCreate() {
        super.onCreate();
        ensureChannels();
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
            ensureChannels();

            String title = message.getData().getOrDefault("title", "着信");
            String body = message.getData().getOrDefault("body", "タップして通話画面を開いてください。");
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

            int baseId = tag.isEmpty() ? (int) System.currentTimeMillis() : tag.hashCode();

            // 通知1: アラーム音（大きい音）
            NotificationCompat.Builder alarmBuilder = new NotificationCompat.Builder(this, CHANNEL_ALARM)
                    .setSmallIcon(android.R.drawable.ic_menu_call)
                    .setContentTitle(title)
                    .setContentText(body)
                    .setPriority(NotificationCompat.PRIORITY_MAX)
                    .setCategory(NotificationCompat.CATEGORY_CALL)
                    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                    .setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM))
                    .setVibrate(new long[]{0, 500, 200, 500, 200, 500})
                    .setAutoCancel(true)
                    .setContentIntent(pendingIntent)
                    .setFullScreenIntent(pendingIntent, true)
                    .setOngoing(true);

            // 通知2: 通知音（通常の着信音）
            NotificationCompat.Builder notifyBuilder = new NotificationCompat.Builder(this, CHANNEL_NOTIFY)
                    .setSmallIcon(android.R.drawable.ic_menu_call)
                    .setContentTitle(title)
                    .setContentText(body)
                    .setPriority(NotificationCompat.PRIORITY_HIGH)
                    .setCategory(NotificationCompat.CATEGORY_CALL)
                    .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                    .setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE))
                    .setAutoCancel(true)
                    .setContentIntent(pendingIntent);

            NotificationManager manager = getSystemService(NotificationManager.class);
            manager.notify(baseId, alarmBuilder.build());
            manager.notify(baseId + 1, notifyBuilder.build());
        } finally {
            if (wakeLock.isHeld()) {
                wakeLock.release();
            }
        }
    }

    private void ensureChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;

        NotificationManager manager = getSystemService(NotificationManager.class);

        // アラーム音チャネル
        if (manager.getNotificationChannel(CHANNEL_ALARM) == null) {
            Uri alarmUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            AudioAttributes alarmAttr = new AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(AudioAttributes.USAGE_ALARM)
                    .build();

            NotificationChannel alarmChannel = new NotificationChannel(
                    CHANNEL_ALARM,
                    "社内通話着信（アラーム）",
                    NotificationManager.IMPORTANCE_MAX
            );
            alarmChannel.setDescription("社内通話の着信通知（アラーム音）");
            alarmChannel.setSound(alarmUri, alarmAttr);
            alarmChannel.enableVibration(true);
            alarmChannel.setVibrationPattern(new long[]{0, 500, 200, 500, 200, 500});
            alarmChannel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            alarmChannel.setBypassDnd(true);
            manager.createNotificationChannel(alarmChannel);
        }

        // 通知音チャネル
        if (manager.getNotificationChannel(CHANNEL_NOTIFY) == null) {
            Uri ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            AudioAttributes notifyAttr = new AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .build();

            NotificationChannel notifyChannel = new NotificationChannel(
                    CHANNEL_NOTIFY,
                    "社内通話着信（通知音）",
                    NotificationManager.IMPORTANCE_HIGH
            );
            notifyChannel.setDescription("社内通話の着信通知（通知音）");
            notifyChannel.setSound(ringtoneUri, notifyAttr);
            notifyChannel.enableVibration(true);
            notifyChannel.setVibrationPattern(new long[]{0, 500, 200, 500, 200, 500});
            notifyChannel.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            manager.createNotificationChannel(notifyChannel);
        }
    }
}
