"""隔離された開発用Python環境でPaddleOCRを実行する。"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from html.parser import HTMLParser
from pathlib import Path


_TEXT_RECOGNIZER = None
_TABLE_RECOGNIZER = None


class _TableRowsParser(HTMLParser):
    """PP-StructureV3の表HTMLから編集用の行列を抽出する。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell_parts = None
        self.cell_colspan = 1
        self.cell_rowspan = 1
        self.column = 0
        self.rowspan_slots = {}
        self.previous_rowspan_slots = set()
        self.new_rowspan_slots = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'tr':
            occupied = set(self.rowspan_slots)
            self.row = [''] * (max(occupied) + 1 if occupied else 0)
            self.column = 0
            self.previous_rowspan_slots = occupied
            self.new_rowspan_slots = set()
        elif tag in {'td', 'th'} and self.row is not None:
            while self.column in self.previous_rowspan_slots:
                self.column += 1
            self.cell_parts = []
            try:
                self.cell_colspan = max(1, int(attributes.get('colspan', '1')))
                self.cell_rowspan = max(1, int(attributes.get('rowspan', '1')))
            except ValueError:
                self.cell_colspan = self.cell_rowspan = 1
        elif tag == 'br' and self.cell_parts is not None:
            self.cell_parts.append('\n')

    def handle_data(self, data):
        if self.cell_parts is not None:
            self.cell_parts.append(data)

    def handle_endtag(self, tag):
        if tag in {'td', 'th'} and self.cell_parts is not None and self.row is not None:
            text = ' '.join(''.join(self.cell_parts).split())
            start = self.column
            end = start + self.cell_colspan
            if len(self.row) < end:
                self.row.extend([''] * (end - len(self.row)))
            self.row[start] = text
            if self.cell_rowspan > 1:
                for column in range(start, end):
                    self.rowspan_slots[column] = self.cell_rowspan - 1
                    self.new_rowspan_slots.add(column)
            self.column = end
            self.cell_parts = None
        elif tag == 'tr' and self.row is not None:
            while self.row and not self.row[-1]:
                self.row.pop()
            if any(cell for cell in self.row):
                self.rows.append(self.row)
            self.row = None
            for column in self.previous_rowspan_slots - self.new_rowspan_slots:
                remaining = self.rowspan_slots.get(column, 0) - 1
                if remaining <= 0:
                    self.rowspan_slots.pop(column, None)
                else:
                    self.rowspan_slots[column] = remaining


def _table_html_to_rows(table_html):
    parser = _TableRowsParser()
    parser.feed(table_html or '')
    parser.close()
    column_count = max((len(row) for row in parser.rows), default=0)
    return [row + [''] * (column_count - len(row)) for row in parser.rows]


def _json_result(page):
    data = page.json if hasattr(page, 'json') else page
    data = data() if callable(data) else data
    return data.get('res', data) if isinstance(data, dict) else {}


def _text_recognizer():
    global _TEXT_RECOGNIZER
    if _TEXT_RECOGNIZER is None:
        from paddleocr import PaddleOCR

        _TEXT_RECOGNIZER = PaddleOCR(
            text_detection_model_name='PP-OCRv5_mobile_det',
            text_recognition_model_name='PP-OCRv5_mobile_rec',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )
    return _TEXT_RECOGNIZER


def _table_recognizer():
    global _TABLE_RECOGNIZER
    if _TABLE_RECOGNIZER is None:
        from paddleocr import PPStructureV3

        _TABLE_RECOGNIZER = PPStructureV3(
            text_detection_model_name='PP-OCRv5_mobile_det',
            text_recognition_model_name='PP-OCRv5_mobile_rec',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            use_seal_recognition=False,
            use_formula_recognition=False,
            use_chart_recognition=False,
            use_region_detection=False,
            use_table_recognition=True,
        )
    return _TABLE_RECOGNIZER


def _recognize_text(image_paths):
    recognizer = _text_recognizer()
    pages = []
    for image_path in image_paths:
        lines = []
        for page in recognizer.predict(image_path):
            result = _json_result(page)
            texts = result.get('rec_texts', []) if isinstance(result, dict) else []
            lines.extend(str(text).strip() for text in texts if str(text).strip())
        pages.append(lines)
    return pages


def _recognize_tables_accurate(image_paths):
    recognizer = _table_recognizer()
    pages = []
    for image_path in image_paths:
        page_tables = []
        for page in recognizer.predict(
            image_path,
            use_wired_table_cells_trans_to_html=True,
            use_wireless_table_cells_trans_to_html=True,
        ):
            result = _json_result(page)
            tables = result.get('table_res_list', []) if isinstance(result, dict) else []
            for table in tables:
                rows = _table_html_to_rows(table.get('pred_html', ''))
                if rows:
                    page_tables.append(rows)
        pages.append(page_tables)
    return pages


def _cluster_line_positions(indices, maximum_gap=4):
    """太さのある罫線を1本の座標へまとめる。"""
    if not len(indices):
        return []
    clusters = [[int(indices[0])]]
    for value in indices[1:]:
        value = int(value)
        if value - clusters[-1][-1] <= maximum_gap:
            clusters[-1].append(value)
        else:
            clusters.append([value])
    return [round(sum(cluster) / len(cluster)) for cluster in clusters]


def _detect_table_grid(image):
    """罫線付き表の縦横線からセル境界を検出する。"""
    import cv2
    import numpy as np

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    height, width = gray.shape
    horizontal = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, width // 30), 1)),
    )
    vertical = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(12, height // 30))),
    )
    x_indices = np.where((vertical > 0).sum(axis=0) >= height * 0.30)[0]
    y_indices = np.where((horizontal > 0).sum(axis=1) >= width * 0.30)[0]
    x_lines = _cluster_line_positions(x_indices)
    y_lines = _cluster_line_positions(y_indices)
    x_lines = [value for index, value in enumerate(x_lines) if index == 0 or value - x_lines[index - 1] >= 6]
    y_lines = [value for index, value in enumerate(y_lines) if index == 0 or value - y_lines[index - 1] >= 6]
    return x_lines, y_lines, gray


def _trim_fast_table(rows):
    rows = [row for row in rows if any(cell for cell in row)]
    if not rows:
        return []
    last_column = max(
        (column for row in rows for column, cell in enumerate(row) if cell),
        default=-1,
    )
    return [row[:last_column + 1] for row in rows] if last_column >= 0 else []


def _recognize_fast_table(image_path):
    """画像全体を1回だけOCRし、座標を罫線セルへ振り分ける。"""
    import cv2
    import numpy as np

    image = cv2.imdecode(np.frombuffer(Path(image_path).read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError('画像を読み込めません。')
    x_lines, y_lines, _ = _detect_table_grid(image)
    if len(x_lines) < 2 or len(y_lines) < 2:
        return []

    rows = [[''] * (len(x_lines) - 1) for _ in range(len(y_lines) - 1)]
    for page in _text_recognizer().predict(image):
        result = _json_result(page)
        texts = result.get('rec_texts', []) if isinstance(result, dict) else []
        boxes = result.get('rec_boxes', []) if isinstance(result, dict) else []
        positioned_texts = []
        for text, box in zip(texts, boxes):
            text = str(text).strip()
            if not text or len(box) < 4:
                continue
            left, top, right, bottom = (float(value) for value in box[:4])
            positioned_texts.append((top, left, (left + right) / 2, (top + bottom) / 2, text))
        for _, _, center_x, center_y, text in sorted(positioned_texts):
            column_index = next((index for index, (left, right) in enumerate(zip(x_lines, x_lines[1:])) if left <= center_x < right), None)
            row_index = next((index for index, (top, bottom) in enumerate(zip(y_lines, y_lines[1:])) if top <= center_y < bottom), None)
            if row_index is None or column_index is None:
                continue
            rows[row_index][column_index] = ' '.join(part for part in (rows[row_index][column_index], text) if part)
    return _trim_fast_table(rows)


def _recognize_tables_fast(image_paths):
    return [[rows] if rows else [] for rows in (_recognize_fast_table(path) for path in image_paths)]


def _process_request(manifest):
    mode = manifest.get('mode', 'text') if isinstance(manifest, dict) else 'text'
    image_paths = manifest.get('paths', []) if isinstance(manifest, dict) else manifest
    if mode == 'table':
        mode = 'table_accurate'
    if not isinstance(image_paths, list) or not image_paths:
        raise ValueError('画像ファイルの一覧が空です。')
    if mode not in {'text', 'table_fast', 'table_accurate'}:
        raise ValueError('認識モードが不正です。')
    if mode == 'table_fast':
        return _recognize_tables_fast(image_paths)
    if mode == 'table_accurate':
        return _recognize_tables_accurate(image_paths)
    return _recognize_text(image_paths)


def _configure_environment():
    project_root = Path(__file__).resolve().parents[3]
    ocr_data = project_root / 'pm_backend' / 'ocr_data'
    os.environ.setdefault('USERPROFILE', str(ocr_data / 'profile'))
    os.environ.setdefault('HOME', str(ocr_data / 'profile'))
    os.environ.setdefault('PADDLE_PDX_CACHE_HOME', str(ocr_data / 'models'))
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')


def _server_main():
    """JSON Linesで要求を受け、読み込んだモデルを次回要求でも再利用する。"""
    protocol_output = sys.stdout
    for line in sys.stdin:
        request = None
        try:
            request = json.loads(line)
            request_id = request.get('id') if isinstance(request, dict) else None
            if isinstance(request, dict) and request.get('mode') == 'shutdown':
                print(json.dumps({'id': request_id, 'ok': True}), file=protocol_output, flush=True)
                return
            with contextlib.redirect_stdout(sys.stderr):
                pages = _process_request(request)
            response = {'id': request_id, 'ok': True, 'pages': pages}
        except Exception as exc:
            response = {
                'id': request.get('id') if isinstance(request, dict) else None,
                'ok': False,
                'error': f'{type(exc).__name__}: {exc}',
            }
        print(json.dumps(response, ensure_ascii=False), file=protocol_output, flush=True)


def main():
    _configure_environment()
    if len(sys.argv) == 2 and sys.argv[1] == '--server':
        _server_main()
        return
    if len(sys.argv) != 2:
        raise SystemExit('要求ファイルのパスが必要です。')
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    with contextlib.redirect_stdout(sys.stderr):
        pages = _process_request(manifest)
    print(json.dumps(pages, ensure_ascii=False))


if __name__ == '__main__':
    main()
