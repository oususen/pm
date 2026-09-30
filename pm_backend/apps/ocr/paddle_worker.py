"""隔離された開発用Python環境でPaddleOCRを実行する。"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit('画像ファイルのパスが必要です。')
    manifest_path = Path(sys.argv[1])
    image_paths = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(image_paths, list) or not image_paths:
        raise SystemExit('画像ファイルの一覧が空です。')

    # キャッシュと初回モデル取得先を開発プロジェクト内に限定する。
    project_root = Path(__file__).resolve().parents[3]
    ocr_data = project_root / 'pm_backend' / 'ocr_data'
    os.environ.setdefault('USERPROFILE', str(ocr_data / 'profile'))
    os.environ.setdefault('HOME', str(ocr_data / 'profile'))
    os.environ.setdefault('PADDLE_PDX_CACHE_HOME', str(ocr_data / 'models'))
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')

    # Paddle/PaddleXの進捗ログは標準エラーに分離し、標準出力はJSON専用にする。
    with contextlib.redirect_stdout(sys.stderr):
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(
            text_detection_model_name='PP-OCRv5_mobile_det',
            text_recognition_model_name='PP-OCRv5_mobile_rec',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        pages = []
        for image_path in image_paths:
            lines = []
            for page in ocr.predict(image_path):
                data = page.json if hasattr(page, 'json') else page
                data = data() if callable(data) else data
                if isinstance(data, dict):
                    result = data.get('res', data)
                    texts = result.get('rec_texts', []) if isinstance(result, dict) else []
                    lines.extend(str(text).strip() for text in texts if str(text).strip())
            pages.append(lines)

    print(json.dumps(pages, ensure_ascii=False))


if __name__ == '__main__':
    main()
