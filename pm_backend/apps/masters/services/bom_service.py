"""BOM関連のビジネスロジックサービス"""
import math
from typing import Dict, Any, List, Optional
from masters.models import Product, BOM, BOMItem, Routing


class BOMService:
    """BOM関連のサービスクラス"""

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
        routing = Routing.objects.filter(
            product=product,
            is_default=True,
            is_active=True
        ).first()

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
            result['is_coproduct'] = bom.is_coproduct

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
        visited: Optional[set] = None
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

        if product_id in visited:
            return []

        visited.add(product_id)

        items = BOMItem.objects.filter(
            child_product_id=product_id,
            bom__is_active=True
        ).select_related('bom__parent_product', 'line', 'process', 'supplier')

        results = []
        for item in items:
            parent = item.bom.parent_product
            entry = {
                'parent_product_id': parent.id,
                'parent_product_code': parent.product_code,
                'parent_product_name': parent.product_name,
                'category': parent.category,
                'quantity': float(item.quantity),
                'sourcing_type': item.sourcing_type,
                'is_final_product': parent.is_final_product,
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
                    visited=visited.copy()
                )

            results.append(entry)

        return results
