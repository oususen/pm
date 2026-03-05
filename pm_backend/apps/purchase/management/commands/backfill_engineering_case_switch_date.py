from collections import Counter
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from purchase.models import EngineeringChangeCase


class Command(BaseCommand):
    help = (
        "EngineeringChangePart.switch_date から "
        "EngineeringChangeCase.switch_date を一括補完します。"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--case-code",
            action="append",
            default=[],
            help="対象案件コード（複数指定可。例: --case-code EC-000001）",
        )
        parser.add_argument(
            "--strategy",
            choices=["max", "min", "mode"],
            default="max",
            help="部品切替日の集約方式（既定: max）",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="既に案件切替日が設定済みでも上書きする",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="実際に更新を反映する（未指定時は dry-run）",
        )

    def _pick_date(self, part_dates, strategy: str) -> date:
        if strategy == "max":
            return max(part_dates)
        if strategy == "min":
            return min(part_dates)
        if strategy == "mode":
            counter = Counter(part_dates)
            top_count = max(counter.values())
            top_dates = [d for d, cnt in counter.items() if cnt == top_count]
            # 最頻値が同率の場合は、旧ロジック互換を優先して遅い日付を採用
            return max(top_dates)
        raise CommandError(f"unsupported strategy: {strategy}")

    def handle(self, *args, **options):
        strategy = options["strategy"]
        force = bool(options["force"])
        apply_changes = bool(options["apply"])
        case_codes = [str(c).strip() for c in options["case_code"] if str(c).strip()]
        dry_run = not apply_changes

        qs = EngineeringChangeCase.objects.prefetch_related("parts").order_by("id")
        if case_codes:
            qs = qs.filter(case_code__in=case_codes)
            existing = set(qs.values_list("case_code", flat=True))
            missing = [c for c in case_codes if c not in existing]
            if missing:
                raise CommandError(f"case_code not found: {', '.join(missing)}")

        candidates = []
        skipped_no_part_date = 0
        skipped_already_set = 0
        conflict_cases = 0

        for case in qs:
            if case.switch_date and not force:
                skipped_already_set += 1
                continue

            part_dates = [p.switch_date for p in case.parts.all() if p.switch_date]
            if not part_dates:
                skipped_no_part_date += 1
                continue

            unique_dates = sorted(set(part_dates))
            if len(unique_dates) > 1:
                conflict_cases += 1

            target_date = self._pick_date(part_dates, strategy)
            candidates.append((case, target_date, unique_dates))

        updated = 0
        if apply_changes and candidates:
            with transaction.atomic():
                for case, target_date, _unique_dates in candidates:
                    if case.switch_date == target_date:
                        continue
                    case.switch_date = target_date
                    case.save(update_fields=["switch_date", "updated_at"])
                    updated += 1
        else:
            updated = sum(1 for case, target_date, _ in candidates if case.switch_date != target_date)

        mode_text = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(
            f"[{mode_text}] strategy={strategy} force={force} "
            f"targets={len(candidates)} update_count={updated} "
            f"skipped_already_set={skipped_already_set} skipped_no_part_date={skipped_no_part_date} "
            f"conflict_cases={conflict_cases}"
        )

        for case, target_date, unique_dates in candidates:
            before = case.switch_date
            marker = " CONFLICT" if len(unique_dates) > 1 else ""
            self.stdout.write(
                f"- {case.case_code or f'EC-{case.id:06d}'}: "
                f"{before} -> {target_date} "
                f"(part_dates={','.join([str(d) for d in unique_dates])}){marker}"
            )

