"""外作注文書PDFと進度表PDF/Excelの比較Excel生成サービス。"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


def _load_compare_script():
    root = Path(__file__).resolve().parents[4]
    script_path = root / "scripts" / "compare_outsource_progress.py"
    spec = importlib.util.spec_from_file_location("outsource_progress_compare_script", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("比較スクリプトを読み込めません。")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def generate_compare_excel(order_pdf_file, progress_pdf_file=None, progress_excel_file=None):
    """外作注文書PDFと進度表PDFまたはExcelを比較し、openpyxl Workbookを返す。"""
    compare = _load_compare_script()

    if progress_pdf_file is None and progress_excel_file is None:
        raise RuntimeError("progress_pdf または progress_excel が必要です。")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        order_path = tmp_path / "order.pdf"
        order_path.write_bytes(order_pdf_file.read())

        order_items = compare._extract_items(str(order_path), "order")
        if progress_excel_file is not None:
            progress_path = tmp_path / "progress.xlsx"
            progress_path.write_bytes(progress_excel_file.read())
            progress_items = compare._extract_progress_excel_items(str(progress_path))
        else:
            progress_path = tmp_path / "progress.pdf"
            progress_path.write_bytes(progress_pdf_file.read())
            progress_items = compare._extract_items(str(progress_path), "progress")
        return compare._build_workbook(order_items, progress_items)
