"""
CRP（能力所要量計画）計算サービス

ライン負荷と工程負荷を計算し、キャパシティチェックを行います。
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any
from masters.models import Process, Line, CalendarDay, ProcessCycleTime
from ..models_production import ProductionOrder


class CRPService:
    """CRP計算サービス"""

    def calculate_line_load(self, line_id: int, target_date) -> Dict[str, Any]:
        """
        ライン別負荷計算（ボトルネック方式）

        Args:
            line_id: ライ

ID
            target_date: 対象日（date または str）

        Returns:
            dict: ライン負荷情報
                - line_id: ラインID
                - line_code: ラインコード
                - target_date: 対象日
                - line_load_minutes: ライン負荷（分）
                - process_loads: 各工程の負荷辞書
                - available_minutes: 稼働時間（分）
                - utilization_rate: 負荷率（%）
                - is_over_capacity: キャパシティ超過フラグ
        """
        line = Line.objects.get(id=line_id)

        # 1. 対象ラインのすべての工程を取得
        processes = Process.objects.filter(line_id=line_id, is_active=True)

        # 2. 各工程の負荷を計算
        process_loads = {}
        for process in processes:
            # その工程での全製品の所要工数を合計
            total_min = 0
            for order in ProductionOrder.objects.filter(
                scheduled_start_date=target_date,
                line_id=line_id,
                status__in=['PLANNED', 'RELEASED', 'IN_PROGRESS']
            ):
                # ProcessCycleTime から取得
                try:
                    cycle_time = ProcessCycleTime.objects.get(
                        product=order.product,
                        process=process,
                        is_active=True
                    )
                    # 所要工数 = 数量 × サイクルタイム + 段取り時間
                    order_time = (
                        float(order.order_qty) * float(cycle_time.cycle_time_min)
                        + float(cycle_time.setup_time_min)
                    )
                    total_min += order_time
                except ProcessCycleTime.DoesNotExist:
                    pass

            process_loads[process.id] = {
                'process_code': process.process_code,
                'process_name': process.process_name,
                'load_minutes': total_min
            }

        # 3. ライン全体の負荷 = ボトルネック工程の負荷
        line_load = max([p['load_minutes'] for p in process_loads.values()]) if process_loads else 0

        # 4. 稼働時間と比較
        try:
            calendar_day = CalendarDay.objects.get(
                calendar=line.calendar,
                target_date=target_date,
                is_working_day=True
            )
            available_minutes = calendar_day.work_minutes or 480
        except CalendarDay.DoesNotExist:
            available_minutes = 480  # デフォルト

        # 5. 負荷率を計算
        utilization_rate = (line_load / available_minutes * 100) if available_minutes > 0 else 0

        return {
            'line_id': line_id,
            'line_code': line.line_code,
            'target_date': target_date,
            'line_load_minutes': line_load,
            'process_loads': process_loads,  # 各工程の負荷も返す
            'available_minutes': available_minutes,
            'utilization_rate': round(utilization_rate, 2),
            'is_over_capacity': utilization_rate > 100
        }

    def check_capacity(self, line_id: int, start_date, end_date) -> Dict[str, Any]:
        """
        期間内のキャパシティチェック

        Args:
            line_id: ラインID
            start_date: 開始日
            end_date: 終了日

        Returns:
            dict: キャパシティチェック結果
                - daily_results: 日別の負荷情報リスト
                - over_capacity_count: 超過日数
                - over_capacity_days: 超過した日のリスト
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        results = []
        current_date = start_date

        while current_date <= end_date:
            result = self.calculate_line_load(line_id, current_date)
            results.append(result)
            current_date += timedelta(days=1)

        # 100%超過の日を抽出
        over_capacity_days = [r for r in results if r['is_over_capacity']]

        return {
            'daily_results': results,
            'over_capacity_count': len(over_capacity_days),
            'over_capacity_days': over_capacity_days
        }

    def get_bottleneck_process(self, line_id: int, target_date) -> Dict[str, Any]:
        """
        ボトルネック工程を特定

        Args:
            line_id: ラインID
            target_date: 対象日

        Returns:
            dict: ボトルネック工程情報
                - process_code: 工程コード
                - process_name: 工程名
                - load_minutes: 負荷（分）
                - utilization_rate: 負荷率（%）
        """
        result = self.calculate_line_load(line_id, target_date)
        process_loads = result['process_loads']
        
        if not process_loads:
            return None
        
        # 最大負荷の工程を特定
        bottleneck_process_id = max(
            process_loads.keys(),
            key=lambda pid: process_loads[pid]['load_minutes']
        )
        
        bottleneck = process_loads[bottleneck_process_id]
        bottleneck['utilization_rate'] = round(
            (bottleneck['load_minutes'] / result['available_minutes'] * 100),
            2
        )
        
        return bottleneck

    def analyze_multi_line_load(
        self,
        line_ids: List[int],
        target_date
    ) -> Dict[str, Any]:
        """
        複数ラインの負荷を比較分析

        Args:
            line_ids: ラインIDのリスト
            target_date: 対象日

        Returns:
            dict: 複数ライン分析結果
                - lines: ライン別負荷情報のリスト
                - max_load_line: 最大負荷のライン情報
                - min_load_line: 最小負荷のライン情報
                - average_utilization: 平均負荷率
        """
        line_results = []

        for line_id in line_ids:
            try:
                result = self.calculate_line_load(line_id, target_date)
                line_results.append(result)
            except Exception as e:
                line_results.append({
                    'line_id': line_id,
                    'error': str(e),
                    'utilization_rate': 0
                })

        # 最大・最小負荷のライン
        valid_results = [r for r in line_results if 'error' not in r]

        if not valid_results:
            return {
                'lines': line_results,
                'max_load_line': None,
                'min_load_line': None,
                'average_utilization': 0
            }

        max_load_line = max(valid_results, key=lambda r: r['utilization_rate'])
        min_load_line = min(valid_results, key=lambda r: r['utilization_rate'])

        # 平均負荷率
        avg_utilization = sum(r['utilization_rate'] for r in valid_results) / len(valid_results)

        return {
            'lines': line_results,
            'max_load_line': max_load_line,
            'min_load_line': min_load_line,
            'average_utilization': round(avg_utilization, 2)
        }

    def analyze_process_trend(
        self,
        process_id: int,
        start_date,
        end_date
    ) -> Dict[str, Any]:
        """
        工程別の負荷推移を分析

        Args:
            process_id: 工程ID
            start_date: 開始日
            end_date: 終了日

        Returns:
            dict: 工程負荷推移分析
                - process_code: 工程コード
                - process_name: 工程名
                - daily_loads: 日別負荷リスト
                - max_load_day: 最大負荷の日
                - min_load_day: 最小負荷の日
                - average_load: 平均負荷
        """
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        process = Process.objects.get(id=process_id)
        daily_loads = []
        current_date = start_date

        while current_date <= end_date:
            # その日の工程負荷を計算
            total_min = 0
            for order in ProductionOrder.objects.filter(
                scheduled_start_date=current_date,
                status__in=['PLANNED', 'RELEASED', 'IN_PROGRESS']
            ):
                try:
                    cycle_time = ProcessCycleTime.objects.get(
                        product=order.product,
                        process=process,
                        is_active=True
                    )
                    order_time = (
                        float(order.order_qty) * float(cycle_time.cycle_time_min)
                        + float(cycle_time.setup_time_min)
                    )
                    total_min += order_time
                except ProcessCycleTime.DoesNotExist:
                    pass

            daily_loads.append({
                'date': current_date,
                'load_minutes': total_min
            })
            current_date += timedelta(days=1)

        # 統計情報
        loads = [d['load_minutes'] for d in daily_loads]
        max_load_day = max(daily_loads, key=lambda d: d['load_minutes']) if daily_loads else None
        min_load_day = min(daily_loads, key=lambda d: d['load_minutes']) if daily_loads else None
        average_load = sum(loads) / len(loads) if loads else 0

        return {
            'process_code': process.process_code,
            'process_name': process.process_name,
            'daily_loads': daily_loads,
            'max_load_day': max_load_day,
            'min_load_day': min_load_day,
            'average_load': round(average_load, 2)
        }

    def simulate_bottleneck_improvement(
        self,
        line_id: int,
        target_date,
        improvement_rate: float
    ) -> Dict[str, Any]:
        """
        ボトルネック工程の改善シミュレーション

        Args:
            line_id: ラインID
            target_date: 対象日
            improvement_rate: 改善率（0.1 = 10%改善）

        Returns:
            dict: シミュレーション結果
                - current_state: 現在の状態
                - bottleneck_process: ボトルネック工程
                - improved_state: 改善後の状態
                - expected_utilization: 改善後の予想負荷率
        """
        # 現在の状態を取得
        current_state = self.calculate_line_load(line_id, target_date)
        bottleneck = self.get_bottleneck_process(line_id, target_date)

        if not bottleneck:
            return {
                'error': 'ボトルネック工程が見つかりません'
            }

        # ボトルネック工程の改善をシミュレート
        improved_load = bottleneck['load_minutes'] * (1 - improvement_rate)

        # 新しいライン負荷を計算（他の工程と比較）
        other_loads = [
            p['load_minutes']
            for pid, p in current_state['process_loads'].items()
            if p['process_code'] != bottleneck['process_code']
        ]

        # 新しいライン負荷 = MAX(改善後ボトルネック, 他工程の最大負荷)
        new_line_load = max([improved_load] + (other_loads or [0]))
        new_utilization = (
            new_line_load / current_state['available_minutes'] * 100
        ) if current_state['available_minutes'] > 0 else 0

        return {
            'current_state': {
                'line_load_minutes': current_state['line_load_minutes'],
                'utilization_rate': current_state['utilization_rate']
            },
            'bottleneck_process': bottleneck,
            'improved_state': {
                'bottleneck_load_minutes': round(improved_load, 2),
                'line_load_minutes': round(new_line_load, 2),
                'utilization_rate': round(new_utilization, 2)
            },
            'improvement_rate': improvement_rate * 100,
            'utilization_reduction': round(
                current_state['utilization_rate'] - new_utilization,
                2
            )
        }

    def suggest_load_leveling(
        self,
        line_ids: List[int],
        target_date
    ) -> Dict[str, Any]:
        """
        負荷平準化の提案

        複数ライン間で負荷の偏りがある場合、
        負荷が高いラインから低いラインへの移動を提案

        Args:
            line_ids: ラインIDのリスト
            target_date: 対象日

        Returns:
            dict: 負荷平準化提案
                - current_loads: 現在の負荷状況
                - suggestions: 移動提案リスト
                - expected_balance: 平準化後の予想バランス
        """
        # 各ラインの負荷を取得
        multi_line_result = self.analyze_multi_line_load(line_ids, target_date)

        if not multi_line_result['max_load_line'] or not multi_line_result['min_load_line']:
            return {
                'error': '分析できるラインがありません'
            }

        max_line = multi_line_result['max_load_line']
        min_line = multi_line_result['min_load_line']

        # 負荷差を計算
        load_diff = max_line['line_load_minutes'] - min_line['line_load_minutes']

        suggestions = []

        if load_diff > 60:  # 1時間以上の差がある場合
            # 移動可能な製造指示を検索
            movable_orders = ProductionOrder.objects.filter(
                scheduled_start_date=target_date,
                line_id=max_line['line_id'],
                status='PLANNED'  # 計画段階のもののみ移動可能
            ).order_by('order_qty')[:5]  # 小ロット優先で5件まで

            for order in movable_orders:
                suggestions.append({
                    'order_no': order.order_no,
                    'product_code': order.product.product_code,
                    'order_qty': float(order.order_qty),
                    'from_line': max_line['line_code'],
                    'to_line': min_line['line_code'],
                    'reason': f'負荷差 {round(load_diff / 60, 1)}時間の平準化'
                })

        return {
            'current_loads': {
                'max_load_line': {
                    'line_code': max_line['line_code'],
                    'utilization_rate': max_line['utilization_rate']
                },
                'min_load_line': {
                    'line_code': min_line['line_code'],
                    'utilization_rate': min_line['utilization_rate']
                },
                'load_diff_hours': round(load_diff / 60, 2)
            },
            'suggestions': suggestions,
            'expected_balance': '提案実施により負荷が平準化されます' if suggestions else '移動可能な製造指示がありません'
        }
