import logging
import queue
import threading

from django.conf import settings

logger = logging.getLogger('production')

_model = None
_model_lock = threading.Lock()
_task_queue = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        from faster_whisper import WhisperModel
        model_size = getattr(settings, 'WHISPER_MODEL_SIZE', 'large-v3')
        _model = WhisperModel(model_size, device='cpu', compute_type='int8')
        logger.info('faster-whisper モデル(%s)をロードしました', model_size)
        return _model


def _worker():
    while True:
        recording_id = _task_queue.get()
        try:
            _transcribe_one(recording_id)
        except Exception:
            logger.exception('録音ID=%s の文字起こしワーカーで例外発生', recording_id)
        finally:
            _task_queue.task_done()


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        _worker_started = True


def _transcribe_one(recording_id):
    from .models import CallRecording
    try:
        recording = CallRecording.objects.get(pk=recording_id)
    except CallRecording.DoesNotExist:
        logger.warning('録音ID=%s が見つかりません', recording_id)
        return

    if not recording.file:
        logger.warning('録音ID=%s にファイルがありません', recording_id)
        return

    if recording.transcript_status not in ('pending', 'processing'):
        logger.info('録音ID=%s はステータス=%s のためスキップ', recording_id, recording.transcript_status)
        return

    recording.transcript_status = 'processing'
    recording.save(update_fields=['transcript_status', 'updated_at'])

    try:
        model = _get_model()
        recording = CallRecording.objects.get(pk=recording_id)
        if recording.transcript_status != 'processing':
            return
        file_path = recording.file.path
        initial_prompt = getattr(settings, 'WHISPER_INITIAL_PROMPT',
            '社内業務通話。レーザー、ブレーキ、パレット、ノズル、仕事がある、仕事がない、段取り、金型、出荷、品質、在庫、製造、生産管理。')
        segments, info = model.transcribe(
            file_path,
            beam_size=5,
            initial_prompt=initial_prompt,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text_parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        transcript = '\n'.join(text_parts)

        recording.transcript = transcript
        recording.transcript_status = 'done'
        recording.transcript_language = info.language or ''
        recording.save(update_fields=['transcript', 'transcript_status', 'transcript_language', 'updated_at'])
        logger.info('録音ID=%s の文字起こし完了 (言語=%s, キュー残=%s)',
                     recording_id, info.language, _task_queue.qsize())
    except Exception:
        logger.exception('録音ID=%s の文字起こしに失敗しました', recording_id)
        try:
            recording.transcript_status = 'failed'
            recording.save(update_fields=['transcript_status', 'updated_at'])
        except Exception:
            pass


def transcribe_recording_async(recording_id):
    _ensure_worker()
    _task_queue.put(recording_id)
    logger.info('録音ID=%s をキューに追加 (キュー残=%s)', recording_id, _task_queue.qsize())
