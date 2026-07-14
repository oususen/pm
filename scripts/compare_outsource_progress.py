"""外作注文書PDFと進度表PDFを突合せ、比較Excelを出力するCLIツール。

実体のロジックは pm_backend/apps/purchase/services/outsource_progress_compare.py にある。
（本番Dockerは pm_backend のみをビルドコンテキストとするため、本番から使われる
ロジックは pm_backend 側に置き、本スクリプトはローカル確認用の薄いラッパーとする）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_APPS_DIR = Path(__file__).resolve().parents[1] / "pm_backend" / "apps"
if str(_APPS_DIR) not in sys.path:
    sys.path.insert(0, str(_APPS_DIR))

from purchase.services.outsource_progress_compare import (  # noqa: E402
    _extract_items,
    _extract_progress_excel_items,
    _build_workbook,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="外作注文書PDFと進度表PDFを突合せ、品番差分・数量差分・その他差分をExcel出力します。",
    )
    parser.add_argument(
        "--order-pdf",
        default="外作注文書000095_20260605084453.pdf",
        help="外作注文書PDFのパス",
    )
    parser.add_argument(
        "--progress-pdf",
        default="進度表_000095_2026-06-05 (3).pdf",
        help="進度表PDFのパス",
    )
    parser.add_argument(
        "--progress-excel",
        default=None,
        help="進度表ExcelのパスPDFの代わりに使う場合）",
    )
    parser.add_argument(
        "--output",
        default="比較表_外作注文書_進度表_000095_需要確認_G列分け.xlsx",
        help="出力Excelのパス",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    order_pdf = Path(args.order_pdf)
    output_xlsx = Path(args.output)

    order_items = _extract_items(str(order_pdf), "order")
    if args.progress_excel:
        progress_items = _extract_progress_excel_items(str(Path(args.progress_excel)))
    else:
        progress_pdf = Path(args.progress_pdf)
        progress_items = _extract_items(str(progress_pdf), "progress")

    wb = _build_workbook(order_items, progress_items)
    wb.save(output_xlsx)
    print(f"saved: {output_xlsx}")
    print(f"order items: {len(order_items)}")
    print(f"progress items: {len(progress_items)}")


if __name__ == "__main__":
    main()
