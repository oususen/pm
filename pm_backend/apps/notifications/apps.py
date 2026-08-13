import os
import threading

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return
        threading.Thread(target=self._startup_tasks, daemon=True).start()

    @staticmethod
    def _startup_tasks():
        try:
            from .transcription import _get_model, transcribe_recording_async
            _get_model()
        except Exception:
            pass

        try:
            from .models import CallRecording
            stale = CallRecording.objects.filter(
                transcript_status__in=['pending', 'processing'],
                file__isnull=False,
            ).exclude(file='').values_list('id', flat=True)
            for rid in stale:
                transcribe_recording_async(rid)
        except Exception:
            pass
