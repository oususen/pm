"""隔離された開発用Python環境でPaddleOCRを実行する。"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from html.parser import HTMLParser


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


def main():
    if len(sys.argv) != 2:
        raise SystemExit('画像ファイルのパスが必要です。')
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if isinstance(manifest, list):
        mode, image_paths = 'text', manifest
    else:
        mode = manifest.get('mode', 'text')
        image_paths = manifest.get('paths', [])
    if not isinstance(image_paths, list) or not image_paths:
        raise SystemExit('画像ファイルの一覧が空です。')
    if mode not in {'text', 'table'}:
        raise SystemExit('認識モードが不正です。')

    # キャッシュと初回モデル取得先を開発プロジェクト内に限定する。
    project_root = Path(__file__).resolve().parents[3]
    ocr_data = project_root / 'pm_backend' / 'ocr_data'
    os.environ.setdefault('USERPROFILE', str(ocr_data / 'profile'))
    os.environ.setdefault('HOME', str(ocr_data / 'profile'))
    os.environ.setdefault('PADDLE_PDX_CACHE_HOME', str(ocr_data / 'models'))
    os.environ.setdefault('PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK', 'True')

    # Paddle/PaddleXの進捗ログは標準エラーに分離し、標準出力はJSON専用にする。
    with contextlib.redirect_stdout(sys.stderr):
        if mode == 'table':
            from paddleocr import PPStructureV3

            recognizer = PPStructureV3(
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
            pages = []
            for image_path in image_paths:
                page_tables = []
                for page in recognizer.predict(
                    image_path,
                    use_wired_table_cells_trans_to_html=True,
                    use_wireless_table_cells_trans_to_html=True,
                ):
                    data = page.json if hasattr(page, 'json') else page
                    data = data() if callable(data) else data
                    if isinstance(data, dict):
                        result = data.get('res', data)
                        tables = result.get('table_res_list', []) if isinstance(result, dict) else []
                        for table in tables:
                            rows = _table_html_to_rows(table.get('pred_html', ''))
                            if rows:
                                page_tables.append(rows)
                pages.append(page_tables)
        else:
            from paddleocr import PaddleOCR

            recognizer = PaddleOCR(
                text_detection_model_name='PP-OCRv5_mobile_det',
                text_recognition_model_name='PP-OCRv5_mobile_rec',
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
            pages = []
            for image_path in image_paths:
                lines = []
                for page in recognizer.predict(image_path):
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
