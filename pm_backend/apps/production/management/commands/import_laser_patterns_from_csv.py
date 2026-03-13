import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from masters.models import Equipment, Product
from production.models_laser_pattern import LaserPattern, LaserPatternComponent


class Command(BaseCommand):
    help = (
        "CSV（パターン,部番,取り数）からレーザパターン構成を一括取込します。"
        "既存パターンは構成部品を全置換します。"
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="取込元CSVパス")
        parser.add_argument("--encoding", default="utf-8-sig", help="CSV文字コード（既定: utf-8-sig）")
        parser.add_argument("--material-code", required=True, help="使用材料の品番コード（m_product.product_code）")
        parser.add_argument("--equipment-code", required=True, help="使用設備コード（m_equipment.equipment_code）")
        parser.add_argument(
            "--process-time-min",
            type=Decimal,
            default=Decimal("0"),
            help="加工時間（分/回、既定: 0）",
        )
        parser.add_argument(
            "--update-existing-header",
            action="store_true",
            help="既存パターンの材料/設備/加工時間も上書きします",
        )
        parser.add_argument(
            "--skip-missing-products",
            action="store_true",
            help="部番マスタ未登録の行をスキップして続行します",
        )
        parser.add_argument("--dry-run", action="store_true", help="更新せず件数のみ確認")

    @staticmethod
    def _resolve_columns(fieldnames):
        if not fieldnames:
            raise CommandError("CSVヘッダが取得できません。")
        normalized = {str(name).strip(): name for name in fieldnames if name is not None}

        def pick(*candidates):
            for c in candidates:
                if c in normalized:
                    return normalized[c]
            return None

        pattern_col = pick("パターン", "pattern")
        part_col = pick("部番", "part", "part_code")
        take_col = pick("取り数", "take_qty", "qty")
        if not pattern_col or not part_col or not take_col:
            raise CommandError(f"必要列が不足しています。ヘッダ: {fieldnames}")
        return pattern_col, part_col, take_col

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSVが見つかりません: {csv_path}")

        material_code = str(options["material_code"]).strip()
        equipment_code = str(options["equipment_code"]).strip()
        process_time_min = options["process_time_min"]
        dry_run = bool(options["dry_run"])
        update_existing_header = bool(options["update_existing_header"])
        skip_missing_products = bool(options["skip_missing_products"])

        material = Product.objects.filter(product_code=material_code).first()
        if not material:
            raise CommandError(f"使用材料が見つかりません: {material_code}")

        equipment = Equipment.objects.filter(equipment_code=equipment_code).first()
        if not equipment:
            raise CommandError(f"使用設備が見つかりません: {equipment_code}")

        grouped = defaultdict(lambda: defaultdict(Decimal))
        skipped_messages = []

        with csv_path.open("r", encoding=options["encoding"], errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            pattern_col, part_col, take_col = self._resolve_columns(reader.fieldnames)

            for lineno, row in enumerate(reader, start=2):
                pattern_no = str(row.get(pattern_col, "")).strip()
                part_code = str(row.get(part_col, "")).strip()
                take_raw = str(row.get(take_col, "")).strip()

                if not pattern_no or not part_code:
                    skipped_messages.append(f"{lineno}行目: パターンまたは部番が空のためスキップ")
                    continue
                try:
                    take_qty = Decimal(take_raw or "0")
                except InvalidOperation:
                    skipped_messages.append(f"{lineno}行目: 取り数が数値ではないためスキップ（{take_raw}）")
                    continue
                if take_qty <= 0:
                    skipped_messages.append(f"{lineno}行目: 取り数<=0のためスキップ（{take_raw}）")
                    continue

                grouped[pattern_no][part_code] += take_qty

        if not grouped:
            raise CommandError("取込対象データがありません。")

        part_codes = sorted({code for parts in grouped.values() for code in parts.keys()})
        product_map = {
            p.product_code: p
            for p in Product.objects.filter(product_code__in=part_codes)
        }
        missing_codes = [code for code in part_codes if code not in product_map]
        if missing_codes and not skip_missing_products:
            preview = ", ".join(missing_codes[:20])
            suffix = " ..." if len(missing_codes) > 20 else ""
            raise CommandError(
                f"部番マスタ未登録のため取込中断（{len(missing_codes)}件）: {preview}{suffix}"
            )
        if missing_codes and skip_missing_products:
            missing_set = set(missing_codes)
            for pattern_no in list(grouped.keys()):
                for code in list(grouped[pattern_no].keys()):
                    if code in missing_set:
                        del grouped[pattern_no][code]
                if not grouped[pattern_no]:
                    del grouped[pattern_no]
            self.stdout.write(
                self.style.WARNING(
                    f"未登録部番をスキップします（{len(missing_codes)}件）: {', '.join(missing_codes[:20])}"
                    + (" ..." if len(missing_codes) > 20 else "")
                )
            )
            if not grouped:
                raise CommandError("未登録部番を除外した結果、取込対象が0件になりました。")

        pattern_nos = sorted(grouped.keys(), key=lambda x: int(x) if str(x).isdigit() else str(x))
        existing_set = set(
            LaserPattern.objects.filter(pattern_no__in=pattern_nos).values_list("pattern_no", flat=True)
        )

        to_create = [p for p in pattern_nos if p not in existing_set]
        to_update = [p for p in pattern_nos if p in existing_set]
        total_components = sum(len(grouped[p]) for p in pattern_nos)

        self.stdout.write(self.style.NOTICE("=== 取込プレビュー ==="))
        self.stdout.write(f"パターン件数: {len(pattern_nos)}")
        self.stdout.write(f"新規作成: {len(to_create)}")
        self.stdout.write(f"既存更新(構成置換): {len(to_update)}")
        self.stdout.write(f"構成部品行(集約後): {total_components}")
        self.stdout.write(f"使用材料: {material.product_code} - {material.product_name}")
        self.stdout.write(f"使用設備: {equipment.equipment_code} - {equipment.equipment_name}")
        self.stdout.write(f"加工時間(分/回): {process_time_min}")
        if skipped_messages:
            self.stdout.write(self.style.WARNING(f"スキップ行: {len(skipped_messages)}"))
            preview = "\n".join(skipped_messages[:20])
            suffix = "\n..." if len(skipped_messages) > 20 else ""
            self.stdout.write(f"{preview}{suffix}")

        if dry_run:
            self.stdout.write(self.style.WARNING("dry-runのためDB更新は実行していません。"))
            return

        created_count = 0
        updated_count = 0
        replaced_rows = 0

        with transaction.atomic():
            for pattern_no in pattern_nos:
                defaults = {
                    "material": material,
                    "equipment": equipment,
                    "process_time_min": process_time_min,
                }
                pattern, created = LaserPattern.objects.get_or_create(
                    pattern_no=pattern_no,
                    defaults=defaults,
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    if update_existing_header:
                        pattern.material = material
                        pattern.equipment = equipment
                        pattern.process_time_min = process_time_min
                        pattern.save(update_fields=["material", "equipment", "process_time_min", "updated_at"])

                LaserPatternComponent.objects.filter(pattern=pattern).delete()
                component_rows = [
                    LaserPatternComponent(
                        pattern=pattern,
                        component_product=product_map[part_code],
                        take_qty=take_qty,
                    )
                    for part_code, take_qty in grouped[pattern_no].items()
                ]
                LaserPatternComponent.objects.bulk_create(component_rows)
                replaced_rows += len(component_rows)

        self.stdout.write(self.style.SUCCESS("=== 取込完了 ==="))
        self.stdout.write(f"新規作成パターン: {created_count}")
        self.stdout.write(f"既存更新パターン: {updated_count}")
        self.stdout.write(f"置換した構成行: {replaced_rows}")
