"""
サービス系API（CRP、BOM展開等）のビュー
"""
from datetime import datetime, date
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .services.crp_service import CRPService
from .services.line_load_service import LineLoadService
from masters.services.bom_service import BOMService


class CRPViewSet(viewsets.ViewSet):
    """
    CRP（能力所要量計画）API
    """
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crp_service = CRPService()

    @action(detail=False, methods=['post'], url_path='calculate-line-load')
    def calculate_line_load(self, request):
        """
        ライン別負荷計算

        POST /api/orders/crp/calculate-line-load/
        payload: {
            "line_id": 1,
            "target_date": "2025-12-15"
        }
        """
        line_id = request.data.get('line_id')
        target_date = request.data.get('target_date')

        if not line_id or not target_date:
            return Response({
                'detail': 'line_id and target_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

            result = self.crp_service.calculate_line_load(line_id, target_date)
            return Response(result)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='check-capacity')
    def check_capacity(self, request):
        """
        期間内のキャパシティチェック

        POST /api/orders/crp/check-capacity/
        payload: {
            "line_id": 1,
            "start_date": "2025-12-15",
            "end_date": "2025-12-20"
        }
        """
        line_id = request.data.get('line_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not all([line_id, start_date, end_date]):
            return Response({
                'detail': 'line_id, start_date, and end_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = self.crp_service.check_capacity(line_id, start_date, end_date)
            return Response(result)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='get-bottleneck')
    def get_bottleneck(self, request):
        """
        ボトルネック工程の特定

        POST /api/orders/crp/get-bottleneck/
        payload: {
            "line_id": 1,
            "target_date": "2025-12-15"
        }
        """
        line_id = request.data.get('line_id')
        target_date = request.data.get('target_date')

        if not line_id or not target_date:
            return Response({
                'detail': 'line_id and target_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

            result = self.crp_service.get_bottleneck_process(line_id, target_date)
            return Response(result if result else {'detail': 'No bottleneck found'})

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='analyze-multi-line')
    def analyze_multi_line(self, request):
        """
        複数ライン比較分析

        POST /api/orders/crp/analyze-multi-line/
        payload: {
            "line_ids": [1, 2, 3],
            "target_date": "2025-12-15"
        }
        """
        line_ids = request.data.get('line_ids')
        target_date = request.data.get('target_date')

        if not line_ids or not target_date:
            return Response({
                'detail': 'line_ids and target_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

            result = self.crp_service.analyze_multi_line_load(line_ids, target_date)
            return Response(result)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='analyze-process-trend')
    def analyze_process_trend(self, request):
        """
        工程別負荷推移分析

        POST /api/orders/crp/analyze-process-trend/
        payload: {
            "process_id": 1,
            "start_date": "2025-12-15",
            "end_date": "2025-12-20"
        }
        """
        process_id = request.data.get('process_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        if not all([process_id, start_date, end_date]):
            return Response({
                'detail': 'process_id, start_date, and end_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = self.crp_service.analyze_process_trend(process_id, start_date, end_date)
            return Response(result)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='simulate-improvement')
    def simulate_improvement(self, request):
        """
        ボトルネック改善シミュレーション

        POST /api/orders/crp/simulate-improvement/
        payload: {
            "line_id": 1,
            "target_date": "2025-12-15",
            "improvement_rate": 0.1  // 10%改善
        }
        """
        line_id = request.data.get('line_id')
        target_date = request.data.get('target_date')
        improvement_rate = request.data.get('improvement_rate', 0.1)

        if not line_id or not target_date:
            return Response({
                'detail': 'line_id and target_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

            result = self.crp_service.simulate_bottleneck_improvement(
                line_id,
                target_date,
                float(improvement_rate)
            )
            return Response(result)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='suggest-leveling')
    def suggest_leveling(self, request):
        """
        負荷平準化提案

        POST /api/orders/crp/suggest-leveling/
        payload: {
            "line_ids": [1, 2, 3],
            "target_date": "2025-12-15"
        }
        """
        line_ids = request.data.get('line_ids')
        target_date = request.data.get('target_date')

        if not line_ids or not target_date:
            return Response({
                'detail': 'line_ids and target_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

            result = self.crp_service.suggest_load_leveling(line_ids, target_date)
            return Response(result)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class LineLoadViewSet(viewsets.ViewSet):
    """長期負荷計算API"""
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = LineLoadService()

    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate(self, request):
        """
        POST /api/production/line-load/calculate/
        payload: {
            "line_ids": [1, 2, 3],
            "start_date": "2026-07-21",
            "end_date": "2026-08-31",
            "aggregate": "daily" | "weekly"
        }
        """
        line_ids = request.data.get('line_ids', [])
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        aggregate = request.data.get('aggregate', 'daily')

        if not line_ids or not start_date or not end_date:
            return Response(
                {'detail': 'line_ids, start_date, end_date are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = self.service.calculate(line_ids, start_date, end_date, aggregate)
            return Response(result)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='coverage')
    def coverage(self, request):
        """
        POST /api/production/line-load/coverage/
        payload: { "line_ids": [1, 2, 3] }
        """
        line_ids = request.data.get('line_ids', [])
        if not line_ids:
            return Response(
                {'detail': 'line_ids is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = self.service.get_coverage_summary(line_ids)
            return Response(result)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BOMServiceViewSet(viewsets.ViewSet):
    """
    BOM関連サービスAPI
    """
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bom_service = BOMService()

    @action(detail=False, methods=['post'], url_path='calculate-lt')
    def calculate_lt(self, request):
        """
        製品リードタイム計算

        POST /api/orders/bom-service/calculate-lt/
        payload: {
            "product_id": 1
        }
        """
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({
                'detail': 'product_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            lt = self.bom_service.calculate_intermediate_lt(product_id)
            return Response({
                'product_id': product_id,
                'standard_lt_days': lt,
                'status': 'success'
            })

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='batch-calculate-lt')
    def batch_calculate_lt(self, request):
        """
        全製品リードタイム一括計算

        POST /api/orders/bom-service/batch-calculate-lt/
        """
        try:
            results = self.bom_service.batch_calculate_all_lt()
            success_count = sum(1 for r in results if r['status'] == 'success')
            error_count = sum(1 for r in results if r['status'] == 'error')

            return Response({
                'total': len(results),
                'success': success_count,
                'error': error_count,
                'results': results
            })

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='bom-tree/(?P<product_id>[^/.]+)')
    def bom_tree(self, request, product_id=None):
        """
        BOMツリー取得

        GET /api/orders/bom-service/bom-tree/1/
        """
        if not product_id:
            return Response({
                'detail': 'product_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            reference_raw = request.query_params.get('reference_date')
            reference_date = None
            if reference_raw:
                reference_date = parse_datetime(reference_raw)
                if reference_date is None:
                    reference_date = parse_date(reference_raw)
                if reference_date is None:
                    return Response({
                        'detail': 'reference_date は YYYY-MM-DD または ISO日時で指定してください。'
                    }, status=status.HTTP_400_BAD_REQUEST)

            tree = self.bom_service.get_bom_tree(
                int(product_id),
                reference_date=reference_date,
            )
            return Response(tree)

        except Exception as e:
            return Response({
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
