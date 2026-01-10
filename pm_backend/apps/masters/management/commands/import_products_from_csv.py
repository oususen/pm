import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from masters.models import Product


class Command(BaseCommand):
    help = (
        "CSVから製品マスタを取り込みます。"
        "指定列の製品コード・製品名・区分(任意)を m_product に update_or_create します。"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="取込元CSVのパス")
        parser.add_argument(
            "--encoding", default="cp932", help="CSVの文字コード (既定: cp932)"
        )
        parser.add_argument(
            "--code-col",
            type=int,
            default=7,
            help="製品コード列の1始まりインデックス (既定: 7列目)",
        )
        parser.add_argument(
            "--name-col",
            type=int,
            default=4,
            help="製品名列の1始まりインデックス (既定: 4列目)",
        )
        parser.add_argument(
            "--category-col",
            type=int,
            default=8,
            help="区分列の1始まりインデックス (既定: 8列目、空ならスキップ)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="登録せず件数のみ確認します",
        )

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.exists():
            raise CommandError(f"CSVが見つかりません: {path}")

        enc = options["encoding"]
        code_idx = options["code_col"] - 1
        name_idx = options["name_col"] - 1
        cat_idx = options["category_col"] - 1
        dry_run = options["dry_run"]

        # 区分→CATEGORY_CHOICES への簡易マッピング
        category_map = {
            "集合部品": "ASSEMBLY",
            "単体部品": "SINGLE",
            "材料": "MATERIAL",
            "購入品": "PURCHASED",
        }

        created = 0
        updated = 0
        skipped = 0

        with path.open("r", encoding=enc, errors="replace", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)  # ヘッダを読み捨て

            for lineno, row in enumerate(reader, start=2):
                try:
                    code = (row[code_idx] or "").strip()
                    name = (row[name_idx] or "").strip()
                    category_label = (row[cat_idx] or "").strip() if cat_idx < len(row) else ""
                except IndexError:
                    self.stderr.write(f"[WARN] {lineno} 行目: 列数が不足しています。スキップ")
                    skipped += 1
                    continue

                if not code:
                    skipped += 1
                    continue

                category = category_map.get(category_label) if category_label else None
                defaults = {
                    "product_name": name or code,
                }
                if category:
                    defaults["category"] = category

                if dry_run:
                    # 確認のみ
                    continue

                obj, created_flag = Product.objects.update_or_create(
                    product_code=code,
                    defaults=defaults,
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS("Import finished."))
        self.stdout.write(f"  created: {created}")
        self.stdout.write(f"  updated: {updated}")
        self.stdout.write(f"  skipped: {skipped}")
        if dry_run:
            self.stdout.write("  ※dry-runのためDB更新なし")
