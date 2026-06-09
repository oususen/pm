from datetime import datetime

from django.db.models import Q, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasResourcePermissionOrReadOnly
from masters.models import Line, Process, Product, ProductStockLocation

from .models_stocktake_record import StocktakeRecord, StocktakeRecorder, StocktakeLayoutConfig, StocktakeArea
from .models_line_backlog import LineBacklog


class StocktakeRecordView(APIView):
    permission_classes = [IsAuthenticated, HasResourcePermissionOrReadOnly]
    PROCESSING_AREA_LABELS = {
        'LASER': 'レーザ',
        'BRAKE': 'ブレーキ',
        'NUT': 'ナット',
        'WELD': '溶接',
        'SPOT': 'スポット',
        'ASSY': '組立',
        'OTHER': 'その他',
    }

    @classmethod
    def _resolve_processing_area_from_process(cls, process_obj):
        if not process_obj:
            return None

        source = f'{process_obj.process_code or ""} {process_obj.process_name or ""}'.upper()
        if 'LASER' in source or 'レーザ' in source:
            return 'LASER'
        if 'BRAKE' in source or 'BEND' in source or 'ブレーキ' in source:
            return 'BRAKE'
        if 'NUT' in source or 'ナット' in source:
            return 'NUT'
        if 'SPOT' in source or 'スポット' in source:
            return 'SPOT'
        if 'WELD' in source or '溶接' in source:
            return 'WELD'
        if 'ASSY' in source or 'ASSEMBLY' in source or '組立' in source:
            return 'ASSY'
        if 'OTHER' in source or 'その他' in source:
            return 'OTHER'
        return None

    @staticmethod
    def _parse_date(value):
        try:
            return datetime.strptime(str(value), '%Y-%m-%d').date()
        except Exception:
            return None

    def get(self, request):
        stocktake_date = self._parse_date(request.query_params.get('stocktake_date'))
        if not stocktake_date:
            return Response({'detail': 'stocktake_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        if request.query_params.get('masters_only') == 'true':
            loc_names = sorted(
                ProductStockLocation.objects.filter(product__is_active=True)
                .order_by()
                .values_list('location_name', flat=True).distinct()
            )
            lines = list(
                Line.objects.filter(product__is_active=True)
                .distinct().order_by('line_code')
                .values('id', 'line_code', 'line_name')
            )
            return Response({
                'rows': [],
                'locations': loc_names,
                'lines': [{'id': l['id'], 'line_code': l['line_code'], 'line_name': l['line_name']} for l in lines],
            })

        qs = Product.objects.filter(is_active=True)

        line_id = request.query_params.get('line_id')
        if line_id:
            qs = qs.filter(line_id=line_id)

        stock_location = str(request.query_params.get('stock_location') or '').strip()
        if stock_location:
            loc_product_ids = ProductStockLocation.objects.filter(
                location_name=stock_location
            ).values_list('product_id', flat=True)
            qs = qs.filter(Q(stock_location=stock_location) | Q(id__in=loc_product_ids))

        product_code = str(request.query_params.get('product_code') or '').strip()
        if product_code:
            qs = qs.filter(product_code__icontains=product_code)

        product_name = str(request.query_params.get('product_name') or '').strip()
        if product_name:
            qs = qs.filter(product_name__icontains=product_name)

        has_image = request.query_params.get('has_image')
        if has_image == 'true':
            qs = qs.exclude(image_url__isnull=True).exclude(image_url__exact='')

        products = list(
            qs.select_related('line', 'process').prefetch_related('stock_locations').order_by(
                'process__process_code', 'stock_location', 'product_code'
            )[:5000]
        )
        product_ids = [product.id for product in products]

        backlog_map = {
            row['product_id']: int(row['system_stock_qty'] or 0)
            for row in (
                LineBacklog.objects.filter(
                    plan_date=stocktake_date,
                    sequence_no=0,
                    product_id__in=product_ids,
                )
                .values('product_id')
                .annotate(system_stock_qty=Sum('stock_qty'))
            )
        }
        records_by_product = {}
        for row in StocktakeRecord.objects.filter(
            stocktake_date=stocktake_date,
            product_id__in=product_ids,
        ).select_related('updated_by').order_by('-updated_at'):
            records_by_product.setdefault(row.product_id, []).append(row)

        rows = []
        for product in products:
            system_stock_qty = backlog_map.get(product.id, 0)
            records = records_by_product.get(product.id, [])
            actual_stock_qty = sum(r.actual_stock_qty for r in records) if records else None
            diff_qty = (actual_stock_qty - system_stock_qty) if actual_stock_qty is not None else None
            latest_record = records[0] if records else None
            record_count = len(records)
            processing_area_label = self.PROCESSING_AREA_LABELS.get(product.processing_area or '', '')
            display_process_name = getattr(product.process, 'process_name', '') if product.process_id else processing_area_label
            display_process_code = getattr(product.process, 'process_code', '') if product.process_id else (product.processing_area or '')
            row = {
                'product_id': product.id,
                'product_code': product.product_code,
                'product_name': product.product_name,
                'processing_area': product.processing_area or '',
                'processing_area_label': processing_area_label,
                'stock_location': product.stock_location or '',
                'stock_locations': [sl.location_name for sl in product.stock_locations.all()],
                'image_url': product.image_url or '',
                'line_id': product.line_id,
                'line_code': getattr(product.line, 'line_code', '') if product.line_id else '',
                'line_name': getattr(product.line, 'line_name', '') if product.line_id else '',
                'process_id': product.process_id,
                'process_code': display_process_code,
                'process_name': display_process_name,
                'system_stock_qty': system_stock_qty,
                'actual_stock_qty': actual_stock_qty,
                'diff_qty': diff_qty,
                'note': latest_record.note if latest_record else '',
                'record_count': record_count,
                'updated_by_name': (
                    latest_record.updated_by.get_full_name() or latest_record.updated_by.username
                ) if latest_record and latest_record.updated_by else '',
                'updated_at': latest_record.updated_at.isoformat() if latest_record else None,
            }
            rows.append(row)

        diff_only = request.query_params.get('diff_only') == 'true'
        if diff_only:
            rows = [row for row in rows if row['diff_qty'] not in (None, 0)]

        loc_set = set()
        for product in products:
            if product.stock_location:
                loc_set.add(product.stock_location)
            for sl in product.stock_locations.all():
                loc_set.add(sl.location_name)
        locations = sorted(loc_set)
        seen_line_ids = set()
        unique_lines = []
        for product in products:
            if product.line_id and product.line and product.line_id not in seen_line_ids:
                seen_line_ids.add(product.line_id)
                unique_lines.append({
                    'id': product.line_id,
                    'line_code': product.line.line_code,
                    'line_name': product.line.line_name,
                })
        unique_lines.sort(key=lambda x: x['line_code'])

        return Response({
            'rows': rows,
            'locations': locations,
            'lines': unique_lines,
        })

    def post(self, request):
        stocktake_date = self._parse_date(request.data.get('stocktake_date'))
        if not stocktake_date:
            return Response({'detail': 'stocktake_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        items = request.data.get('items')
        if not isinstance(items, list) or not items:
            return Response({'detail': 'items は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        product_ids = [item.get('product_id') for item in items if item.get('product_id')]
        products = {
            product.id: product
            for product in Product.objects.filter(id__in=product_ids).select_related('line', 'process')
        }

        saved = 0
        for item in items:
            product_id = item.get('product_id')
            product = products.get(product_id)
            if not product:
                continue

            actual_stock_qty = int(item.get('actual_stock_qty') or 0)
            system_stock_qty = int(item.get('system_stock_qty') or 0)
            note = str(item.get('note') or '').strip()
            recorder_name = str(item.get('recorder_name') or '').strip()

            StocktakeRecord.objects.create(
                stocktake_date=stocktake_date,
                product=product,
                line=product.line,
                process=product.process,
                system_stock_qty=system_stock_qty,
                actual_stock_qty=actual_stock_qty,
                note=note,
                recorder_name=recorder_name,
                updated_by=request.user if request.user.is_authenticated else None,
            )
            saved += 1

        return Response({'saved': saved})


class StocktakeHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        stocktake_date = request.query_params.get('stocktake_date')
        if not stocktake_date:
            return Response({'detail': 'stocktake_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        records = StocktakeRecord.objects.filter(
            stocktake_date=stocktake_date,
            product_id=product_id,
        ).select_related('updated_by').order_by('-updated_at')

        items = []
        for r in records:
            items.append({
                'id': r.id,
                'actual_stock_qty': r.actual_stock_qty,
                'note': r.note,
                'recorder_name': r.recorder_name or '',
                'updated_by_name': (
                    r.updated_by.get_full_name() or r.updated_by.username
                ) if r.updated_by else '',
                'updated_at': r.updated_at.isoformat() if r.updated_at else None,
            })

        return Response({'items': items})

    def delete(self, request, product_id):
        record_id = request.query_params.get('record_id')
        if not record_id:
            return Response({'detail': 'record_id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = StocktakeRecord.objects.filter(id=record_id, product_id=product_id).delete()
        return Response({'deleted': deleted})


class StocktakeRecorderView(APIView):
    permission_classes = [IsAuthenticated]

    @staticmethod
    def _parse_date(value):
        try:
            return datetime.strptime(str(value), '%Y-%m-%d').date()
        except Exception:
            return None

    def get(self, request):
        stocktake_date = self._parse_date(request.query_params.get('stocktake_date'))
        if not stocktake_date:
            return Response({'detail': 'stocktake_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        recorders = StocktakeRecorder.objects.filter(stocktake_date=stocktake_date).order_by('name')
        return Response({
            'recorders': [{'id': r.id, 'name': r.name} for r in recorders]
        })

    def post(self, request):
        stocktake_date = self._parse_date(request.data.get('stocktake_date'))
        if not stocktake_date:
            return Response({'detail': 'stocktake_date は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        name = str(request.data.get('name') or '').strip()
        if not name:
            return Response({'detail': '名前は必須です'}, status=status.HTTP_400_BAD_REQUEST)

        recorder, created = StocktakeRecorder.objects.get_or_create(
            stocktake_date=stocktake_date, name=name,
        )
        return Response({'id': recorder.id, 'name': recorder.name, 'created': created})

    def delete(self, request):
        recorder_id = request.data.get('id')
        if not recorder_id:
            return Response({'detail': 'id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = StocktakeRecorder.objects.filter(id=recorder_id).delete()
        return Response({'deleted': deleted})


class StocktakeLayoutConfigView(APIView):
    permission_classes = [IsAuthenticated]

    def _config_name(self, area_id):
        if area_id:
            return f'area_{area_id}'
        return 'default'

    def get(self, request):
        area_id = request.query_params.get('area_id', '')
        config_name = self._config_name(area_id)
        config = StocktakeLayoutConfig.objects.filter(name=config_name).first()
        if not config:
            return Response({'cols': 8, 'rows': 6, 'cells': {}})
        return Response({'cols': config.cols, 'rows': config.row_count, 'cells': config.cells})

    def post(self, request):
        area_id = request.data.get('area_id', '')
        config_name = self._config_name(area_id)
        cols = int(request.data.get('cols', 8))
        row_count = int(request.data.get('rows', 6))
        cells = request.data.get('cells', {})

        config, _ = StocktakeLayoutConfig.objects.update_or_create(
            name=config_name,
            defaults={'cols': cols, 'row_count': row_count, 'cells': cells},
        )
        return Response({'cols': config.cols, 'rows': config.row_count, 'cells': config.cells})


class StocktakeAreaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        areas = StocktakeArea.objects.all()
        return Response({
            'areas': [
                {'id': a.id, 'name': a.name, 'locations': a.locations, 'sort_order': a.sort_order}
                for a in areas
            ]
        })

    def post(self, request):
        name = str(request.data.get('name', '')).strip()
        if not name:
            return Response({'detail': 'エリア名は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        locations = request.data.get('locations', [])
        sort_order = int(request.data.get('sort_order', 0))
        area_id = request.data.get('id')
        if area_id:
            try:
                area = StocktakeArea.objects.get(id=area_id)
                area.name = name
                area.locations = locations
                area.sort_order = sort_order
                area.save()
            except StocktakeArea.DoesNotExist:
                return Response({'detail': 'エリアが見つかりません'}, status=status.HTTP_404_NOT_FOUND)
        else:
            area = StocktakeArea.objects.create(name=name, locations=locations, sort_order=sort_order)
        return Response({'id': area.id, 'name': area.name, 'locations': area.locations, 'sort_order': area.sort_order})

    def delete(self, request):
        area_id = request.data.get('id')
        if not area_id:
            return Response({'detail': 'id は必須です'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = StocktakeArea.objects.filter(id=area_id).delete()
        return Response({'deleted': deleted})
