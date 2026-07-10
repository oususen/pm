"""BOM関連のビジネスロジックサービス"""
import math
from typing import Dict, Any, List, Optional
from django.db.models import Q
from masters.models import Product, BOM, BOMItem, Routing, RoutingStep
from masters.services.routing_service import resolve_effective_routing, build_effective_routing_q


class BOMService:
    """BOM関連のサービスクラス"""

    def _resolve_effective_parent_routing(
        self,
        parent_product_id: Optional[int],
        step_cache: Optional[Dict[Any, Any]] = None,
        reference_date=None,
    ):
        """親製品の有効ルーティングを1本解決する。"""
        if not parent_product_id:
            return None

        cache_key = ('where_used_effective_parent_routing', parent_product_id, reference_date)
        if step_cache is not None and cache_key in step_cache:
            return step_cache[cache_key]

        routing = resolve_effective_routing(parent_product_id, reference=reference_date)
        if step_cache is not None:
            step_cache[cache_key] = routing
        return routing

    def _resolve_where_used_edge_lt_days(
        self,
        bom_item: BOMItem,
        step_cache: Optional[Dict[Any, Any]] = None,
        reference_date=None,
    ) -> int:
        """
        where-used（子→親の1エッジ）向けLT解決。

        統一ルール:
        - 投入LT は RoutingStep.lead_time_days を使用（0 は有効値）
        - 未設定時のみ Line.lead_time_days にフォールバック
        - duration_min はサイクルタイム専用のため使用しない
        - time_unit (DAY / MINUTE) による分岐を持たない
        - 親製品が最終品の特殊経路（親側のラインLT参照）は互換のため維持
        """
        parent_product = getattr(getattr(bom_item, 'bom', None), 'parent_product', None)
        is_final_parent = bool(parent_product and getattr(parent_product, 'is_final_product', False))
        parent_id = getattr(parent_product, 'id', None)
        parent_routing = self._resolve_effective_parent_routing(
            parent_id,
            step_cache=step_cache,
            reference_date=reference_date,
        )

        if is_final_parent:
            # 親製品（最終品）のルーティングからラインLTを取得
            if parent_id and parent_routing:
                cache_key = ('final_parent', parent_routing.id, parent_id, reference_date)
                if step_cache is not None and cache_key in step_cache:
                    parent_step = step_cache[cache_key]
                else:
                    parent_step = (
                        RoutingStep.objects
                        .filter(routing_id=parent_routing.id)
                        .filter(
                            Q(output_product_id=parent_id)
                            | Q(output_product_id__isnull=True)
                        )
                        .select_related('line')
                        .order_by('-step_no', '-id')
                        .first()
                    )
                    if parent_step is None:
                        parent_step = (
                            RoutingStep.objects
                            .filter(routing_id=parent_routing.id)
                            .select_related('line')
                            .order_by('-step_no', '-id')
                            .first()
                        )
                    if step_cache is not None:
                        step_cache[cache_key] = parent_step
                if parent_step:
                    step_line = getattr(parent_step, 'line', None)
                    line_lt = int(getattr(step_line, 'lead_time_days', 0) or 0)
                    if line_lt > 0:
                        return line_lt
            # フォールバック: BOMItemのラインLT
            line_obj = getattr(bom_item, 'line', None)
            return max(int(getattr(line_obj, 'lead_time_days', 0) or 0), 0)

        step = None
        line_id = getattr(bom_item, 'line_id', None)
        child_product_id = getattr(bom_item, 'child_product_id', None)

        if line_id and child_product_id:
            cache_key = ('where_used_edge_step', parent_routing.id if parent_routing else None, line_id, child_product_id, reference_date)
            if step_cache is not None and cache_key in step_cache:
                step = step_cache[cache_key]
            else:
                step_qs = RoutingStep.objects.filter(line_id=line_id)
                if parent_routing is not None:
                    step_qs = step_qs.filter(routing_id=parent_routing.id)
                else:
                    step_qs = step_qs.filter(build_effective_routing_q(reference_date, prefix='routing__'))

                step = (
                    step_qs
                    .filter(
                        (
                            # output_productが設定されている場合
                            # 子品目の工程ステップを優先
                            Q(output_product_id=child_product_id)
                        ) | (
                            # output_product未設定の場合はrouting.productで解決
                            Q(output_product_id__isnull=True, routing__product_id=child_product_id)
                        )
                    )
                    .select_related('line')
                    .order_by('step_no', 'id')
                    .first()
                )
                if step_cache is not None:
                    step_cache[cache_key] = step

        if step is not None:
            step_lt_raw = getattr(step, 'lead_time_days', None)
            if step_lt_raw is not None:
                return max(int(step_lt_raw), 0)

            step_line = getattr(step, 'line', None)
            line_lt = int(getattr(step_line, 'lead_time_days', 0) or 0) if step_line else 0
            if line_lt > 0:
                return line_lt

        return max(int(getattr(bom_item, 'lead_time_days', 0) or 0), 0)

    def _resolve_where_used_parent_context(
        self,
        parent_product: Product,
        context_cache: Optional[Dict[Any, Any]] = None,
        reference_date=None,
    ) -> Dict[str, Any]:
        """
        where-used行で表示する親品の工程・ライン・自LTを解決する。

        優先順:
        1) 親品を子に持つ有効BOMItem（最も信頼できるデータソース）
        2) 親品を出力する有効RoutingStep
        3) Productマスタ（最終フォールバック）
        """
        parent_id = getattr(parent_product, 'id', None)
        cache_key = ('where_used_parent_ctx', parent_id, reference_date)
        if context_cache is not None and cache_key in context_cache:
            return context_cache[cache_key]

        context = {
            'line_id': None,
            'line_code': None,
            'line_name': None,
            'line_type': None,
            'process_id': None,
            'process_code': None,
            'process_name': None,
            'self_lt_days': None,
        }

        # 1) 親品を子に持つBOMItem（最優先）
        parent_item_key = ('where_used_parent_item', parent_id)
        if context_cache is not None and parent_item_key in context_cache:
            parent_as_child_item = context_cache[parent_item_key]
        else:
            parent_as_child_item = (
                BOMItem.objects
                .filter(child_product_id=parent_id, bom__is_active=True)
                .select_related('line', 'process')
                .order_by('-bom__valid_from', '-bom_id', '-id')
                .first()
            )
            if context_cache is not None:
                context_cache[parent_item_key] = parent_as_child_item

        if parent_as_child_item is not None:
            item_line = getattr(parent_as_child_item, 'line', None)
            item_process = getattr(parent_as_child_item, 'process', None)
            if item_line is not None:
                context['line_id'] = parent_as_child_item.line_id
                context['line_code'] = item_line.line_code
                context['line_name'] = item_line.line_name
                context['line_type'] = item_line.line_type
            if item_process is not None:
                context['process_id'] = parent_as_child_item.process_id
                context['process_code'] = item_process.process_code
                context['process_name'] = item_process.process_name
            context['self_lt_days'] = max(int(getattr(parent_as_child_item, 'lead_time_days', 0) or 0), 0)

        # 2) 親品の有効RoutingStep（BOMItemで未解決の場合）
        parent_routing_key = ('where_used_parent_routing', parent_id, reference_date)
        if context_cache is not None and parent_routing_key in context_cache:
            parent_routing = context_cache[parent_routing_key]
        else:
            parent_routing = resolve_effective_routing(parent_id, reference=reference_date)
            if context_cache is not None:
                context_cache[parent_routing_key] = parent_routing

        parent_step_key = ('where_used_parent_step', parent_id, reference_date)
        if context_cache is not None and parent_step_key in context_cache:
            parent_step = context_cache[parent_step_key]
        else:
            parent_step = None
            if parent_routing is not None:
                parent_step = (
                    RoutingStep.objects
                    .filter(routing_id=parent_routing.id)
                    .filter(
                        Q(output_product_id=parent_id)
                        | Q(output_product_id__isnull=True)
                    )
                    .select_related('line', 'process')
                    .order_by('-step_no', '-id')
                    .first()
                )
                if parent_step is None:
                    parent_step = (
                        RoutingStep.objects
                        .filter(routing_id=parent_routing.id)
                        .select_related('line', 'process')
                        .order_by('-step_no', '-id')
                        .first()
                    )
            if context_cache is not None:
                context_cache[parent_step_key] = parent_step

        if parent_step is not None:
            step_line = getattr(parent_step, 'line', None)
            step_process = getattr(parent_step, 'process', None)
            if not context.get('line_id') and step_line is not None:
                context['line_id'] = parent_step.line_id
                context['line_code'] = step_line.line_code
                context['line_name'] = step_line.line_name
                context['line_type'] = step_line.line_type
            if not context.get('process_id') and step_process is not None:
                context['process_id'] = parent_step.process_id
                context['process_code'] = step_process.process_code
                context['process_name'] = step_process.process_name
            if context['self_lt_days'] is None:
                context['self_lt_days'] = max(int(getattr(parent_step, 'lead_time_days', 0) or 0), 0)

        # 3) Productマスタ（最終フォールバック）
        if not context.get('line_id') and getattr(parent_product, 'line_id', None):
            p_line = getattr(parent_product, 'line', None)
            context['line_id'] = parent_product.line_id
            context['line_code'] = getattr(p_line, 'line_code', None)
            context['line_name'] = getattr(p_line, 'line_name', None)
            context['line_type'] = getattr(p_line, 'line_type', None)
        if not context.get('process_id') and getattr(parent_product, 'process_id', None):
            p_process = getattr(parent_product, 'process', None)
            context['process_id'] = parent_product.process_id
            context['process_code'] = getattr(p_process, 'process_code', None)
            context['process_name'] = getattr(p_process, 'process_name', None)

        # 4) Product.self_lt_days（既存保持値）をフォールバックで利用
        if context['self_lt_days'] is None and getattr(parent_product, 'self_lt_days', None) is not None:
            context['self_lt_days'] = max(int(parent_product.self_lt_days or 0), 0)

        # 5) まだ未設定なら有効ルーティング全体のLT(日)合計を推定値として利用
        if context['self_lt_days'] is None:
            if parent_routing is not None:
                total_self_lt = 0
                has_step = False
                for step in parent_routing.steps.all():
                    step_lt = max(int(getattr(step, 'lead_time_days', 0) or 0), 0)
                    has_step = True
                    total_self_lt += step_lt
                if has_step:
                    context['self_lt_days'] = max(int(total_self_lt), 0)

        # 6) 最終フォールバック
        if context['self_lt_days'] is None and getattr(parent_product, 'standard_lt_days', None) is not None:
            context['self_lt_days'] = max(int(parent_product.standard_lt_days or 0), 0)

        if context_cache is not None:
            context_cache[cache_key] = context
        return context

    def calculate_intermediate_lt(
        self,
        product_id: int,
        cache: Optional[Dict[int, float]] = None
    ) -> float:
        """
        中間品リードタイムの動的計算（再帰的ボトムアップ）

        Args:
            product_id: 製品ID
            cache: 計算済みのL/Tキャッシュ（再帰呼び出しで使用）

        Returns:
            float: 計算されたリードタイム（日）

        計算ロジック:
            standard_lt_days = MAX(子部品のL/T) + 自工程の加工日数 + 固定待ち時間
        """
        if cache is None:
            cache = {}

        # キャッシュチェック
        if product_id in cache:
            return cache[product_id]

        product = Product.objects.get(id=product_id)

        # 購入品の場合、設定されているL/Tを返す
        if product.category == 'PURCHASED':
            lt = product.standard_lt_days or 0
            cache[product_id] = lt
            return lt

        # BOMを取得（有効で最新のもの）
        bom = BOM.objects.filter(
            parent_product=product,
            is_active=True
        ).order_by('-valid_from').first()

        if not bom:
            # BOMがない場合は0を返す
            cache[product_id] = 0
            return 0

        # 1. 子部品のL/Tの最大値を取得（並行調達のため）
        child_lt_max = 0
        for item in bom.items.all():
            child_lt = self.calculate_intermediate_lt(
                item.child_product_id,
                cache
            )
            child_lt_max = max(child_lt_max, child_lt)

        # 2. 工程時間を日換算して合計
        routing = resolve_effective_routing(product.id if product else None)

        process_days = 0
        if routing:
            for step in routing.steps.all():
                # フェーズ2以降: ProcessCycleTime から取得も可能
                # 現在: RoutingStep.duration_min から取得
                duration_min = step.duration_min or 0

                # ライン稼働時間を取得
                # TODO: CalendarDay から動的に取得（現在は固定値480分/日）
                work_minutes_per_day = 480

                # 日換算
                process_days += duration_min / work_minutes_per_day

        # 3. 固定待ち時間（今は0、将来的に設定可能）
        wait_days = 0

        # 4. 合計（切り上げ）
        total_lt = math.ceil(child_lt_max + process_days + wait_days)

        # 5. 自工程L/Tも計算
        self_lt = math.ceil(process_days)

        # キャッシュに保存
        cache[product_id] = total_lt

        # 6. Productテーブルを更新
        product.standard_lt_days = total_lt
        product.self_lt_days = self_lt
        product.save(update_fields=['standard_lt_days', 'self_lt_days', 'updated_at'])

        return total_lt

    def batch_calculate_all_lt(self) -> List[Dict[str, Any]]:
        """
        全製品のL/Tを一括計算

        Returns:
            List[Dict]: 計算結果のリスト
                - product_code: 品番コード
                - standard_lt_days: トータルL/T
                - self_lt_days: 自工程L/T
                - status: 'success' or 'error'
                - error: エラーメッセージ（エラー時のみ）
        """
        # 購入品以外のすべての製品を対象
        products = Product.objects.exclude(
            category='PURCHASED'
        ).filter(is_active=True)

        cache = {}
        results = []

        for product in products:
            try:
                lt = self.calculate_intermediate_lt(product.id, cache)
                results.append({
                    'product_code': product.product_code,
                    'product_name': product.product_name,
                    'standard_lt_days': lt,
                    'self_lt_days': product.self_lt_days,
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'product_code': product.product_code,
                    'product_name': product.product_name,
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def get_bom_tree(
        self,
        product_id: int,
        level: int = 0,
        visited: Optional[set] = None
    ) -> Dict[str, Any]:
        """
        BOM構造をツリー形式で取得（循環参照対応）

        Args:
            product_id: 製品ID
            level: 階層レベル
            visited: 訪問済み製品IDのセット

        Returns:
            Dict: BOMツリー構造
        """
        if visited is None:
            visited = set()

        if product_id in visited:
            return {
                'error': 'circular_reference',
                'message': '循環参照が検出されました'
            }

        visited.add(product_id)
        product = Product.objects.get(id=product_id)

        # BOMを取得
        bom = BOM.objects.filter(
            parent_product=product,
            is_active=True
        ).order_by('-valid_from').first()

        result = {
            'product_id': product.id,
            'product_code': product.product_code,
            'product_name': product.product_name,
            'category': product.category,
            'standard_lt_days': product.standard_lt_days,
            'self_lt_days': product.self_lt_days,
            'level': level,
            'children': []
        }

        if bom:
            result['bom_id'] = bom.id
            result['bom_version'] = bom.version
            result['is_coproduct'] = bool(bom.is_coproduct or getattr(bom.parent_product, 'is_virtual_set', False))

            for item in bom.items.select_related(
                'child_product',
                'line',
                'process',
                'supplier'
            ).all():
                child_tree = self.get_bom_tree(
                    item.child_product_id,
                    level + 1,
                    visited.copy()  # 各ブランチで独立したvisitedセット
                )
                child_tree['quantity'] = float(item.quantity)
                child_tree['sourcing_type'] = item.sourcing_type
                child_tree['line_id'] = item.line_id
                child_tree['line_code'] = item.line.line_code if item.line else None
                child_tree['line_name'] = item.line.line_name if item.line else None
                child_tree['process_id'] = item.process_id
                child_tree['process_code'] = item.process.process_code if item.process else None
                child_tree['process_name'] = item.process.process_name if item.process else None
                child_tree['supplier_id'] = item.supplier_id
                child_tree['supplier_code'] = item.supplier.supplier_code if item.supplier else None
                child_tree['supplier_name'] = item.supplier.supplier_name if item.supplier else None
                result['children'].append(child_tree)

        return result

    def get_where_used(
        self,
        product_id: int,
        recursive: bool = False,
        visited: Optional[set] = None,
        step_cache: Optional[Dict[Any, Any]] = None,
        reference_date=None,
    ) -> List[Dict[str, Any]]:
        """
        逆展開：指定した製品がどの親製品で使われているかを取得

        Args:
            product_id: 子製品ID
            recursive: 再帰的に上位階層まで辿るか
            visited: 訪問済み製品IDのセット（循環参照防止）

        Returns:
            List: この製品を使用している親製品のリスト
        """
        if visited is None:
            visited = set()
        if step_cache is None:
            step_cache = {}

        if product_id in visited:
            return []

        visited.add(product_id)

        items = BOMItem.objects.filter(
            child_product_id=product_id,
            bom__is_active=True
        ).select_related(
            'bom__parent_product',
            'bom__parent_product__line',
            'bom__parent_product__process',
            'line',
            'process',
            'supplier',
        )

        results = []
        for item in items:
            parent = item.bom.parent_product
            parent_context = self._resolve_where_used_parent_context(
                parent,
                context_cache=step_cache,
                reference_date=reference_date,
            )
            resolved_lt_days = self._resolve_where_used_edge_lt_days(
                item,
                step_cache=step_cache,
                reference_date=reference_date,
            )
            entry = {
                'parent_product_id': parent.id,
                'parent_product_code': parent.product_code,
                'parent_product_name': parent.product_name,
                'category': parent.category,
                'parent_self_lt_days': parent_context.get('self_lt_days'),
                'quantity': float(item.quantity),
                'lead_time_days': int(item.lead_time_days or 0),
                'resolved_lead_time_days': int(resolved_lt_days or 0),
                'time_unit': item.time_unit,
                'sourcing_type': item.sourcing_type,
                'is_final_product': parent.is_final_product,
                'parent_line_id': parent_context.get('line_id'),
                'parent_line_code': parent_context.get('line_code'),
                'parent_line_name': parent_context.get('line_name'),
                'parent_line_type': parent_context.get('line_type'),
                'parent_process_id': parent_context.get('process_id'),
                'parent_process_code': parent_context.get('process_code'),
                'parent_process_name': parent_context.get('process_name'),
                'line_id': item.line_id,
                'line_code': item.line.line_code if item.line else None,
                'line_name': item.line.line_name if item.line else None,
                'process_id': item.process_id,
                'process_code': item.process.process_code if item.process else None,
                'process_name': item.process.process_name if item.process else None,
                'supplier_id': item.supplier_id,
                'supplier_code': item.supplier.supplier_code if item.supplier else None,
                'supplier_name': item.supplier.supplier_name if item.supplier else None,
            }

            if recursive:
                # 再帰的に上位階層を取得
                entry['parents'] = self.get_where_used(
                    parent.id,
                    recursive=True,
                    visited=visited.copy(),
                    step_cache=step_cache,
                    reference_date=reference_date,
                )

            results.append(entry)

        return results

    def get_where_used_self_info(
        self,
        product_id: int,
        context_cache: Optional[Dict[Any, Any]] = None,
        reference_date=None,
    ) -> Optional[Dict[str, Any]]:
        """where-used表示用に検索対象製品自身の情報を返す。
        検索品自身を output_product とする全ルーティングのステップから工程・ラインを取得する。
        """
        product = (
            Product.objects
            .filter(id=product_id)
            .select_related('line', 'process')
            .first()
        )
        if product is None:
            return None

        if context_cache is None:
            context_cache = {}

        # 検索品自身を output_product とするステップを探す（全ルーティングから）
        self_step = (
            RoutingStep.objects
            .filter(output_product_id=product_id)
            .filter(build_effective_routing_q(reference_date, prefix='routing__'))
            .select_related('line', 'process')
            .order_by('-routing__valid_from_datetime', '-step_no', '-id')
            .first()
        )

        # 見つからない場合は自分のルーティングから取得
        if self_step is None:
            own_routing = resolve_effective_routing(product_id, reference=reference_date)
            if own_routing:
                self_step = (
                    RoutingStep.objects
                    .filter(routing_id=own_routing.id)
                    .select_related('line', 'process')
                    .order_by('-step_no', '-id')
                    .first()
                )

        # それでもない場合は _resolve_where_used_parent_context にフォールバック
        if self_step is None:
            context = self._resolve_where_used_parent_context(
                product,
                context_cache=context_cache,
                reference_date=reference_date,
            )
        else:
            step_line = getattr(self_step, 'line', None)
            step_process = getattr(self_step, 'process', None)
            context = {
                'line_id': self_step.line_id if step_line else getattr(product, 'line_id', None),
                'line_code': getattr(step_line, 'line_code', None) or getattr(getattr(product, 'line', None), 'line_code', None),
                'line_name': getattr(step_line, 'line_name', None) or getattr(getattr(product, 'line', None), 'line_name', None),
                'line_type': getattr(step_line, 'line_type', None) or getattr(getattr(product, 'line', None), 'line_type', None),
                'process_id': self_step.process_id if step_process else getattr(product, 'process_id', None),
                'process_code': getattr(step_process, 'process_code', None) or getattr(getattr(product, 'process', None), 'process_code', None),
                'process_name': getattr(step_process, 'process_name', None) or getattr(getattr(product, 'process', None), 'process_name', None),
                'self_lt_days': max(int(getattr(self_step, 'lead_time_days', 0) or 0), 0),
            }

        # BOMItemのsourcing_typeを一次情報として使用（正しい調達区分はBOMに記録されている）
        bom_sourcing = (
            BOMItem.objects
            .filter(child_product_id=product_id, bom__is_active=True)
            .order_by('-bom__valid_from', '-id')
            .values_list('sourcing_type', flat=True)
            .first()
        )
        if bom_sourcing:
            sourcing_type = bom_sourcing
        else:
            line_type = context.get('line_type')
            if line_type == 'PURCHASE' or product.category == 'PURCHASED':
                sourcing_type = 'BUY'
            elif line_type == 'OUTSOURCE':
                sourcing_type = 'SUBCON'
            else:
                sourcing_type = 'MAKE'

        return {
            'product_id': product.id,
            'product_code': product.product_code,
            'product_name': product.product_name,
            'category': product.category,
            'is_final_product': bool(product.is_final_product),
            'sourcing_type': sourcing_type,
            'line_id': context.get('line_id'),
            'line_code': context.get('line_code'),
            'line_name': context.get('line_name'),
            'line_type': context.get('line_type'),
            'process_id': context.get('process_id'),
            'process_code': context.get('process_code'),
            'process_name': context.get('process_name'),
            'self_lt_days': context.get('self_lt_days'),
        }
