"""旧親品コードを正規FKへ一括移行する。既定は照合のみ。運用停止中に実行する。"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from masters.models import BOMItem, Product, Routing, RoutingStep, RoutingStepMaterial


MAPPING_PATH = Path(__file__).resolve().parents[2] / 'services' / 'routing_parent_approved_mapping.json'


class Command(BaseCommand):
    help = '全件照合後に親品IDを一括移行（既定は読取照合、--applyで更新。旧remarkは保持）'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='BOSS承認後、全件照合成功時のみ更新')

    def handle(self, *args, **options):
        approved = {r['step_id']: r for r in json.loads(MAPPING_PATH.read_text(encoding='utf-8'))}
        # 件数スナップショットは固定しない。更新時は同じトランザクション内で直前に全関連行をロックする。
        with transaction.atomic():
            def current_rows(model):
                qs = model.objects.order_by('pk')
                return list(qs.select_for_update() if options['apply'] else qs)

            products = {p.id: p for p in current_rows(Product)}
            by_code = {p.product_code: p for p in products.values()}
            routings = {r.id: r for r in current_rows(Routing)}
            steps = current_rows(RoutingStep)
            materials = current_rows(RoutingStepMaterial)
            # BOMヘッダも親品変更と競合しないようロックする。
            from masters.models import BOM
            boms = {b.id: b for b in current_rows(BOM)}
            items = current_rows(BOMItem)
            items_by_id = {i.id: i for i in items}
            bom_pairs = {(boms[i.bom_id].parent_product_id, i.child_product_id) for i in items}
            material_pairs = {(m.routing_step_id, m.component_id) for m in materials}
            by_path = {}
            for s in steps:
                by_path.setdefault((s.routing_id, s.hierarchy_path), []).append(s)

            errors, changes = [], []
            # 切替後の新規入力/編集を旧値から上書きしない。再実行は照合だけとし、適用を拒否する。
            initial_migration = not any(s.parent_product_id is not None for s in steps)
            if options['apply'] and not initial_migration:
                raise CommandError('親品IDが既に存在します。部分移行/切替後の再実行は不可です。現状を確認してください。')

            # 初回移行では承認全対象が存在し、承認時の文脈を維持することを先に確認する。
            # 登録済み別コードや空へ変わった行も迂回させない。
            if initial_migration:
                by_id = {s.id: s for s in steps}
                for row in approved.values():
                    step = by_id.get(row['step_id'])
                    if not step:
                        errors.append({'step_id': row['step_id'], 'reason': '承認対象工程が欠落'})
                        continue
                    routing = routings.get(step.routing_id)
                    output = products.get(step.output_product_id)
                    routing_product = products.get(routing.product_id) if routing else None
                    context = (
                        (step.remark or '').strip() in (row['current_parent_code'], row['hierarchy_parent_code'])
                        and step.routing_id == row['routing_id']
                        and step.output_product_id == row['output_product_id']
                        and step.hierarchy_path == row['hierarchy_path']
                        and output is not None and output.product_code == row['output_product_code']
                        and routing_product is not None and routing_product.product_code == row['routing_product_code']
                        and routing is not None and routing.routing_code == row['routing_code']
                    )
                    if not context:
                        errors.append({'step_id': step.id, 'reason': '承認対象の旧親品/業務文脈が変更されている'})
                if errors:
                    for row in errors:
                        self.stderr.write(json.dumps(row, ensure_ascii=False))
                    raise CommandError(f'承認全対象の照合エラー{len(errors)}件。全件更新を中止しました。')

            for step in steps:
                # FKがある状態の読取点検は、NULLも正規値として扱い旧remarkから復元しない。
                old_code = (step.remark or '').strip() if initial_migration else ''
                parent = by_code.get(old_code) if initial_migration else products.get(step.parent_product_id)
                row = approved.get(step.id) if initial_migration else None
                expected_code = row['hierarchy_parent_code'] if row else None
                corrected = False
                if not parent and old_code:
                    if not row or old_code != row['current_parent_code']:
                        errors.append({'step_id': step.id, 'old_code': old_code, 'reason': '未承認の未登録親品'})
                        continue
                    parent = by_code.get(expected_code)
                    corrected = True
                # 元33SQLを既に適用した場合も、承認対象の文脈を再照合する。
                if row:
                    if not parent or parent.product_code != expected_code:
                        errors.append({'step_id': step.id, 'reason': '承認対応表の業務文脈/候補コードが不一致'})
                        continue
                    corrected = True
                if old_code and not parent:
                    errors.append({'step_id': step.id, 'old_code': old_code, 'reason': '親品を解決できない'})
                    continue
                if step.parent_product_id and not parent:
                    errors.append({'step_id': step.id, 'reason': '親品IDが存在しない'})
                    continue
                if not parent:
                    # 元から親品未指定の工程だけはNULLを維持する。
                    continue
                source = items_by_id.get(step.source_bom_item_id)
                if source and (boms[source.bom_id].parent_product_id != parent.id or source.child_product_id != step.output_product_id):
                    errors.append({'step_id': step.id, 'reason': '元BOM親子品と不一致'})
                    continue
                parents = []
                if '.' in step.hierarchy_path:
                    parents = by_path.get((step.routing_id, step.hierarchy_path.rsplit('.', 1)[0]), [])
                # 自己親の中間工程は維持する。直上工程が無い最上位/既存例外を補完しない。
                if parents and step.output_product_id != parent.id and not any(p.output_product_id == parent.id for p in parents):
                    errors.append({'step_id': step.id, 'reason': '実在する直上工程の加工後品と不一致'})
                    continue
                if corrected:
                    matching_parents = [p for p in parents if p.output_product_id == parent.id]
                    if not matching_parents or not any((p.id, step.output_product_id) in material_pairs for p in matching_parents):
                        errors.append({'step_id': step.id, 'reason': '補正候補の親工程材料を確認できない'})
                        continue
                    if (parent.id, step.output_product_id) not in bom_pairs:
                        errors.append({'step_id': step.id, 'reason': '補正候補の親子BOMを確認できない'})
                        continue
                if step.parent_product_id is None:
                    changes.append((step, parent.id, old_code, parent.product_code))

            for row in errors:
                self.stderr.write(json.dumps(row, ensure_ascii=False))
            if errors:
                raise CommandError(f'照合エラー{len(errors)}件。全件更新を中止しました。')
            for step, parent_id, before, after in changes:
                self.stdout.write(json.dumps({'step_id': step.id, 'old_code': before, 'parent_product_id': parent_id, 'parent_product_code': after}, ensure_ascii=False))
            if options['apply']:
                for step, parent_id, _, _ in changes:
                    step.parent_product_id = parent_id
                RoutingStep.objects.bulk_update([r[0] for r in changes], ['parent_product'])
            mode = '初回移行' if initial_migration else 'FK状態読取点検（旧値参照なし）'
            self.stdout.write(f"モード={mode} 工程数={len(steps)} 移行対象={len(changes)} エラー=0 {'更新済み' if options['apply'] else '未更新（照合のみ）'}")
