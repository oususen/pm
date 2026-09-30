"""OCR・文書読取アプリのローカル文字認識サービス。"""
from __future__ import annotations

import atexit
import os
import json
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OCR_EXECUTABLE = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
DEFAULT_OCR_TESSDATA_DIR = PROJECT_ROOT / 'pm_backend' / 'ocr_data'
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
ENGINE_CHOICES = {
    'tesseract': 'Tesseract（軽量・活字向け）',
    'paddle': 'PaddleOCR（高精度・手書き対応）',
}
PADDLE_VENV_PYTHON = PROJECT_ROOT / 'pm_backend' / 'ocr_data' / 'venv' / 'Scripts' / 'python.exe'
_PADDLE_WORKER = None
_PADDLE_WORKER_LOCK = threading.Lock()
_PADDLE_REQUEST_LOCK = threading.Lock()


class OCRRecognitionError(RuntimeError):
    """OCRエンジンが認識を完了できなかった場合のエラー。"""


def _paddle_environment():
    """隔離PaddleOCRがモデルを開発PC内だけで使用する環境変数を返す。"""
    cache_dir = PROJECT_ROOT / 'pm_backend' / 'ocr_data'
    environment = os.environ.copy()
    environment.update({
        'USERPROFILE': str(cache_dir / 'profile'),
        'HOME': str(cache_dir / 'profile'),
        'PADDLE_PDX_CACHE_HOME': str(cache_dir / 'models'),
        'PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK': 'True',
        'PYTHONIOENCODING': 'utf-8',
    })
    return environment


class _PersistentPaddleWorker:
    """隔離PaddleOCRを常駐させ、読み込んだモデルを次の要求でも再利用する。"""

    def __init__(self, paddle_python):
        worker = Path(__file__).with_name('paddle_worker.py')
        self.process = subprocess.Popen(
            [str(paddle_python), str(worker), '--server'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=_paddle_environment(),
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        self.responses = queue.Queue()
        self.reader = threading.Thread(target=self._read_responses, daemon=True, name='pm-ocr-paddle-reader')
        self.reader.start()

    @property
    def running(self):
        return self.process.poll() is None

    def _read_responses(self):
        try:
            for line in self.process.stdout:
                self.responses.put(line)
        finally:
            self.responses.put(None)

    def request(self, mode, paths):
        if not self.running or not self.process.stdin:
            raise OCRRecognitionError('常駐PaddleOCRが停止しています。')
        request_id = uuid.uuid4().hex
        try:
            self.process.stdin.write(json.dumps({
                'id': request_id,
                'mode': mode,
                'paths': [str(path) for path in paths],
            }, ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            response_line = self.responses.get(timeout=900)
        except queue.Empty as exc:
            raise OCRRecognitionError('PaddleOCRの処理が15分でタイムアウトしました。') from exc
        except (BrokenPipeError, OSError) as exc:
            raise OCRRecognitionError('常駐PaddleOCRへ要求を送信できません。') from exc
        if response_line is None:
            raise OCRRecognitionError('常駐PaddleOCRが予期せず停止しました。')
        try:
            response = json.loads(response_line)
        except (json.JSONDecodeError, TypeError) as exc:
            raise OCRRecognitionError('PaddleOCRの結果を読み取れませんでした。') from exc
        if response.get('id') != request_id or not response.get('ok'):
            raise OCRRecognitionError('PaddleOCRの画像認識に失敗しました。')
        return response.get('pages')

    def stop(self):
        if not self.running:
            return False
        try:
            if self.process.stdin:
                self.process.stdin.write(json.dumps({'id': uuid.uuid4().hex, 'mode': 'shutdown'}) + '\n')
                self.process.stdin.flush()
            self.process.wait(timeout=10)
        except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        return True


def stop_paddle_worker():
    """常駐PaddleOCRを停止してメモリを解放する。"""
    global _PADDLE_WORKER
    with _PADDLE_REQUEST_LOCK:
        with _PADDLE_WORKER_LOCK:
            worker = _PADDLE_WORKER
            _PADDLE_WORKER = None
        return worker.stop() if worker else False


def paddle_worker_status():
    """常駐PaddleOCRプロセスの状態を返す。"""
    with _PADDLE_WORKER_LOCK:
        running = bool(_PADDLE_WORKER and _PADDLE_WORKER.running)
    return {'running': running}


atexit.register(stop_paddle_worker)


def _paddle_python():
    """開発PC用の隔離PaddleOCR環境があればそのPythonを返す。"""
    configured = os.environ.get('OCR_PADDLE_PYTHON')
    if configured:
        executable = Path(configured)
        return executable if executable.is_file() else None
    if PADDLE_VENV_PYTHON.is_file():
        return PADDLE_VENV_PYTHON
    return None


def _ocr_executable():
    """環境ごとのTesseract実行ファイルを返す。環境変数で上書きできる。"""
    configured = os.environ.get('OCR_TESSERACT_PATH')
    if configured:
        return Path(configured)
    discovered = shutil.which('tesseract')
    return Path(discovered) if discovered else Path(DEFAULT_OCR_EXECUTABLE)


def _ocr_tessdata_dir():
    """明示設定時だけ言語データの場所をTesseractへ渡す。"""
    configured = os.environ.get('OCR_TESSDATA_DIR')
    if configured:
        return Path(configured)
    if DEFAULT_OCR_TESSDATA_DIR.exists():
        return DEFAULT_OCR_TESSDATA_DIR
    return None


def status():
    """OCRアプリが日本語・英語を認識できるか返す。"""
    executable = _ocr_executable()
    if not executable.exists():
        return {'available': False, 'message': 'Tesseract OCR本体が見つかりません。', 'languages': []}
    try:
        command = [str(executable), '--list-langs']
        tessdata_dir = _ocr_tessdata_dir()
        if tessdata_dir:
            command.extend(['--tessdata-dir', str(tessdata_dir)])
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=10, check=False)
        languages = [line.strip() for line in result.stdout.splitlines() if line.strip() and not line.startswith('List of available languages')]
    except (OSError, subprocess.SubprocessError):
        return {'available': False, 'message': 'Tesseract OCRの状態を確認できません。', 'languages': []}
    available = result.returncode == 0 and {'jpn', 'eng'}.issubset(languages)
    return {
        'available': available,
        'message': '日本語・英語のOCRを利用できます。' if available else '日本語または英語の言語データが見つかりません。',
        'languages': languages,
    }


def paddle_status():
    """PaddleOCRの高精度モードを利用できるか返す。"""
    paddle_python = _paddle_python()
    if paddle_python:
        try:
            check = subprocess.run(
                [str(paddle_python), '-c', "from importlib.metadata import version; print(version('paddleocr')); print(version('paddlepaddle'))"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=10,
                check=False,
            )
            versions = check.stdout.strip().splitlines()
            available = check.returncode == 0 and len(versions) == 2
            version_label = f'PaddleOCR {versions[0]} / PaddlePaddle {versions[1]}' if available else ''
        except (OSError, subprocess.SubprocessError):
            available = False
            version_label = ''
        return {
            'available': available,
            'message': '高精度のPaddleOCRを利用できます。' if available else '開発用PaddleOCR環境を確認できません。',
            'version': version_label,
        }
    available = find_spec('paddle') is not None and find_spec('paddleocr') is not None
    return {
        'available': available,
        'message': '高精度のPaddleOCRを利用できます。' if available else 'PaddleOCRを準備中です。',
    }


def paddle_table_status():
    """表認識は開発PC専用の隔離環境だけで有効にする。"""
    if not PADDLE_VENV_PYTHON.is_file():
        return {
            'available': False,
            'message': '表認識は開発PCの隔離PaddleOCR環境でのみ利用できます。',
        }
    try:
        check = subprocess.run(
            [
                str(PADDLE_VENV_PYTHON), '-c',
                (
                    "from importlib.metadata import version; from importlib.util import find_spec; "
                    "required=('bs4','einops','ftfy','jinja2','latex2mathml','lxml','openpyxl',"
                    "'premailer','regex','sklearn','scipy','sentencepiece','tiktoken','tokenizers'); "
                    "assert all(find_spec(name) is not None for name in required); "
                    "print(version('paddleocr')); print(version('paddlepaddle'))"
                ),
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=10,
            check=False,
        )
        versions = check.stdout.strip().splitlines()
        major = int(versions[0].split('.', 1)[0]) if versions and versions[0].split('.', 1)[0].isdigit() else 0
        available = check.returncode == 0 and len(versions) == 2 and major >= 3
    except (OSError, subprocess.SubprocessError, ValueError):
        available = False
    return {
        'available': available,
        'message': (
            '開発PC内のPP-StructureV3で表認識できます。追加モデルは開発PCのOCR用領域に保存します。'
            if available else '開発PCのPaddleOCR 3系・表認識依存を確認できません。'
        ),
    }


def all_status():
    """画面で選択できるOCRエンジンの状態を返す。"""
    return {
        'tesseract': status(),
        'paddle': paddle_status(),
        'table_recognition': paddle_table_status(),
        'paddle_worker': paddle_worker_status(),
        'engines': ENGINE_CHOICES,
    }


def extract_image_text(path, engine='tesseract', keep_alive=False):
    """画像をローカルTesseractで文字化する。画像は外部へ送信しない。"""
    if engine == 'paddle':
        return _extract_paddle_text(path, keep_alive=keep_alive)
    if not status()['available']:
        return ''
    command = [str(_ocr_executable()), str(path), 'stdout', '-l', 'jpn+eng']
    tessdata_dir = _ocr_tessdata_dir()
    if tessdata_dir:
        command.extend(['--tessdata-dir', str(tessdata_dir)])
    command.extend(['--psm', '6'])
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=30, check=False)
    return result.stdout.strip() if result.returncode == 0 else ''


def extract_images_text(paths, engine='tesseract', keep_alive=False):
    """複数のPDFページ画像を読み取り、PaddleOCRは1回の起動で処理する。"""
    image_paths = [str(path) for path in paths]
    if engine == 'paddle':
        return _extract_paddle_texts(image_paths, keep_alive=keep_alive)
    return [extract_image_text(path, engine=engine) for path in image_paths]


def extract_image_tables(path, table_mode='accurate', keep_alive=False):
    """開発PC内のPaddleOCRで画像内の表を行列として認識する。"""
    return _extract_paddle_outputs([str(path)], mode=f'table_{table_mode}', keep_alive=keep_alive)[0]


def extract_images_tables(paths, table_mode='accurate', keep_alive=False):
    """PDFの全ページを一度のPaddle起動で表認識する。"""
    return _extract_paddle_outputs(
        [str(path) for path in paths],
        mode=f'table_{table_mode}',
        keep_alive=keep_alive,
    )


@lru_cache(maxsize=1)
def _paddle_ocr():
    """高精度モードの日本語モデルをプロセス内で一度だけ初期化する。"""
    from paddleocr import PaddleOCR
    return PaddleOCR(
        text_detection_model_name='PP-OCRv5_mobile_det',
        text_recognition_model_name='PP-OCRv5_mobile_rec',
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )


def _extract_paddle_text(path, keep_alive=False):
    """PaddleOCRの結果から認識済みテキスト行だけを取り出す。"""
    return _extract_paddle_texts([path], keep_alive=keep_alive)[0]


def _extract_paddle_texts(paths, keep_alive=False):
    """複数画像から認識した行を画像ごとに返す。"""
    if not paddle_status()['available']:
        raise OCRRecognitionError('PaddleOCRが利用できません。開発環境のOCR設定を確認してください。')
    paddle_python = _paddle_python()
    if paddle_python and paddle_python.resolve() != Path(sys.executable).resolve():
        return _extract_paddle_outputs(
            paths,
            mode='text',
            paddle_python=paddle_python,
            keep_alive=keep_alive,
        )
    pages = []
    try:
        ocr = _paddle_ocr()
        for path in paths:
            lines = []
            for page in ocr.predict(str(path)):
                data = page.json if hasattr(page, 'json') else page
                data = data() if callable(data) else data
                if isinstance(data, dict):
                    result = data.get('res', data)
                    texts = result.get('rec_texts', []) if isinstance(result, dict) else []
                    lines.extend(str(text).strip() for text in texts if str(text).strip())
            pages.append('\n'.join(lines))
    except Exception as exc:
        raise OCRRecognitionError('PaddleOCRの画像認識に失敗しました。') from exc
    return pages


def _validate_paddle_outputs(outputs, paths, mode):
    """隔離プロセスのJSON結果が要求件数・形式と一致するか確認する。"""
    if not isinstance(outputs, list) or len(outputs) != len(paths):
        raise OCRRecognitionError('PaddleOCRの結果を読み取れませんでした。')
    if mode.startswith('table_'):
        if any(not isinstance(page, list) for page in outputs):
            raise OCRRecognitionError('PaddleOCRの表認識結果を読み取れませんでした。')
        return outputs
    return ['\n'.join(str(text).strip() for text in page if str(text).strip()) for page in outputs]


def _extract_persistent_paddle_outputs(paths, mode, paddle_python):
    """常駐プロセスへ直列で要求し、読み込んだモデルを再利用する。"""
    global _PADDLE_WORKER
    with _PADDLE_REQUEST_LOCK:
        with _PADDLE_WORKER_LOCK:
            if not _PADDLE_WORKER or not _PADDLE_WORKER.running:
                _PADDLE_WORKER = _PersistentPaddleWorker(paddle_python)
            worker = _PADDLE_WORKER
        return worker.request(mode, paths)


def _extract_paddle_outputs(paths, mode, paddle_python=None, keep_alive=False):
    """開発用の隔離環境で複数画像を一括処理し、JSON結果だけを受け取る。"""
    if mode.startswith('table_') and not paddle_table_status()['available']:
        raise OCRRecognitionError('表認識は開発PCのPaddleOCR 3系隔離環境でのみ利用できます。')
    paddle_python = paddle_python or PADDLE_VENV_PYTHON
    if keep_alive:
        outputs = _extract_persistent_paddle_outputs(paths, mode, paddle_python)
        return _validate_paddle_outputs(outputs, paths, mode)
    stop_paddle_worker()
    worker = Path(__file__).with_name('paddle_worker.py')
    manifest_descriptor, manifest_path = tempfile.mkstemp(prefix='pm-ocr-', suffix='.json')
    try:
        with os.fdopen(manifest_descriptor, 'w', encoding='utf-8') as manifest:
            json.dump({'mode': mode, 'paths': [str(path) for path in paths]}, manifest, ensure_ascii=False)
        result = subprocess.run(
            [str(paddle_python), str(worker), manifest_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=900,
            check=False,
            env=_paddle_environment(),
        )
    except subprocess.TimeoutExpired as exc:
        raise OCRRecognitionError('PaddleOCRの処理が15分でタイムアウトしました。') from exc
    except OSError as exc:
        raise OCRRecognitionError('開発用PaddleOCRを起動できません。') from exc
    finally:
        Path(manifest_path).unlink(missing_ok=True)
    if result.returncode != 0:
        raise OCRRecognitionError('PaddleOCRの画像認識に失敗しました。')
    try:
        outputs = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise OCRRecognitionError('PaddleOCRの結果を読み取れませんでした。') from exc
    return _validate_paddle_outputs(outputs, paths, mode)
