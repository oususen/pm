"""
工程実時間記録用のSerializer
"""
from decimal import Decimal
from datetime import timedelta, time

from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from masters.models import Process, Product, BOM, Line, Supplier
from orders.utils.calendar_utils import DAY_BOUNDARY_HOUR
from .models_process_realtime import ProcessRealtimeRecord
from .models_line_backlog import LineBacklog
from .models_production import StockAllocation
from quality.models_scrap import ScrapRecord, ScrapRecordDetail


def build_scrap_multiplier_map(root_product_id: int, root_qty: Decimal) -> dict:
    """
    BOMを最下層まで展開し、各製品に必要な仕損数量を集計する。
    歩留まり・副産物は考慮しない（現仕様）。
    """
    if not root_product_id or root_qty is None:
        return {}

    multipliers = {}
    stack = [(root_product_id, Decimal(root_qty), None)]

    while stack:
        pid, qty, sourcing_type = stack.pop()
        if qty == 0:
            continue
        multipliers[pid] = multipliers.get(pid, Decimal('0')) + qty

        st = (sourcing_type or '').upper()
        if st == 'BUY':
            continue

        bom = BOM.objects.filter(parent_product_id=pid, is_active=True).order_by('-valid_from', '-id').first()
        if not bom:
            continue
        for item in bom.items.all():
            if item.quantity is None:
                continue
            child_qty = qty * Decimal(item.quantity)
            stack.append((item.child_product_id, child_qty, item.sourcing_type))

    return multipliers


def build_scrap_multiplier_details(root_product_id: int, root_qty: Decimal):
    """
    BOMを最下層まで展開し、各製品ごとの仕損数量と加工先工程/ライン情報を返す。
    （process_id/line_id は BOM 明細に設定されていれば一緒に返す）
    同じ製品でも異なる工程/サプライヤからの調達は別明細として扱う。
    """
    if not root_product_id or root_qty is None:
        return []

    stack = [(root_product_id, Decimal(root_qty), None, None, None, None)]
    detail_map = {}
    purchase_process = Process.objects.filter(process_code='PURCHASE').first()
    purchase_line_id = purchase_process.line_id if purchase_process else None

    def resolve_purchase_line_id(supplier_id):
        if not supplier_id:
            return purchase_line_id
        supplier = Supplier.objects.filter(id=supplier_id).first()
        if not supplier:
            return purchase_line_id
        line_code = f"SUP-{supplier.id:06d}"
        line_name = f"仕入:{supplier.supplier_code} {supplier.supplier_name}"
        if len(line_name) > 50:
            line_name = line_name[:50]
        line_obj, created = Line.objects.get_or_create(
            line_code=line_code,
            defaults={
                'line_name': line_name,
                'line_type': 'PURCHASE',
                'is_active': False,
            }
        )
        if not created and line_obj.line_type != 'PURCHASE':
            line_obj.line_type = 'PURCHASE'
            line_obj.save(update_fields=['line_type'])
        return line_obj.id

    while stack:
        pid, qty, proc_id, line_id, supplier_id, sourcing_type = stack.pop()
        if qty == 0:
            continue

        st = (sourcing_type or '').upper()
        if st in ('BUY', 'SUBCON') and purchase_process:
            proc_id = purchase_process.id
            line_id = resolve_purchase_line_id(supplier_id)

        # 同じ製品でも工程/サプライヤが異なれば別明細とする
        key = (pid, proc_id, supplier_id)
        if key not in detail_map:
            detail_map[key] = {
                'qty': Decimal('0'),
                'process_id': proc_id,
                'line_id': line_id,
                'supplier_id': supplier_id,
                'sourcing_type': sourcing_type,
            }
        detail_map[key]['qty'] += qty
        if detail_map[key]['line_id'] is None and line_id is not None:
            detail_map[key]['line_id'] = line_id
        if detail_map[key]['sourcing_type'] is None and sourcing_type is not None:
            detail_map[key]['sourcing_type'] = sourcing_type

        if st == 'BUY':
            continue

        bom = BOM.objects.filter(parent_product_id=pid, is_active=True).order_by('-valid_from', '-id').first()
        if not bom:
            continue
        for item in bom.items.all():
            if item.quantity is None:
                continue
            child_qty = qty * Decimal(item.quantity)
            stack.append((
                item.child_product_id,
                child_qty,
                item.process_id or proc_id,
                item.line_id or line_id,
                item.supplier_id or supplier_id,
                item.sourcing_type or sourcing_type,
            ))

    result = []
    for (pid, proc_id, supplier_id), info in detail_map.items():
        result.append({
            'product_id': pid,
            'qty': info['qty'],
            'process_id': info['process_id'],
            'line_id': info['line_id'],
            'supplier_id': info['supplier_id'],
            'sourcing_type': info['sourcing_type'],
        })
    return result


def apply_scrap_to_stock(multipliers: dict):
    """
    仕損数量を在庫に転嫁する。既存の在庫引当テーブルを使用。
    location が複数ある場合は最初のレコードを使用し、無ければ DEFAULT ロケーションで作成。
    """
    for pid, qty in multipliers.items():
        if qty == 0:
            continue
        allocation = StockAllocation.objects.filter(product_id=pid).order_by('id').first()
        if allocation:
            allocation.current_stock = (allocation.current_stock or Decimal('0')) - qty
            allocation.save()
        else:
            StockAllocation.objects.create(
                product_id=pid,
                location='DEFAULT',
                current_stock=-qty,
                reserved_qty=Decimal('0'),
                min_stock_qty=Decimal('0'),
                is_bottleneck=False,
            )


def apply_scrap_return_to_stock(multipliers: dict):
    """
    仕損の戻し数量を在庫に反映する。location が複数ある場合は最初のレコードを使用。
    """
    for pid, qty in multipliers.items():
        if qty == 0:
            continue
        allocation = StockAllocation.objects.filter(product_id=pid).order_by('id').first()
        if allocation:
            allocation.current_stock = (allocation.current_stock or Decimal('0')) + qty
            allocation.save()
        else:
            StockAllocation.objects.create(
                product_id=pid,
                location='DEFAULT',
                current_stock=qty,
                reserved_qty=Decimal('0'),
                min_stock_qty=Decimal('0'),
                is_bottleneck=False,
            )


def update_line_backlog_production(process, product, qty, plan_date):
    """
    生産実績をLineBacklogのactual_qtyに反映する

    Args:
        process: Process オブジェクト
        product: Product オブジェクト (Noneの場合はスキップ)
        qty: 生産数量 (Decimal)
        plan_date: 計画日 (date)
    """
    if not product or not qty or qty <= 0:
        return

    line = getattr(process, 'line', None)
    if not line:
        return

    # 該当するLineBacklogレコードを取得または作成
    # 実績は sequence_no=0 の基礎データレコードに保存
    backlog, created = LineBacklog.objects.get_or_create(
        line=line,
        process=process,
        product=product,
        plan_date=plan_date,
        sequence_no=0,  # 実績は sequence_no=0 に保存
        defaults={
            'actual_qty': int(qty),
        }
    )

    if not created:
        # 既存レコードに実績を加算
        backlog.actual_qty = (backlog.actual_qty or 0) + int(qty)
        backlog.save(update_fields=['actual_qty'])


def resolve_workday_date_for_process(process, dt):
    """
    勤務カレンダに基づいて計画日を決定する。
    夜勤で日付を跨ぐ場合は前日扱いにする。
    日替わり時刻（8時）より前は前日扱いにする。
    """
    if dt.time() < time(DAY_BOUNDARY_HOUR, 0):
        return (dt - timedelta(days=1)).date()
    if not process:
        return dt.date()
    line = getattr(process, 'line', None)
    if not line:
        return dt.date()
    try:
        from .services.gantt_planning import LineWorkCalendar
        calendar = LineWorkCalendar(line)
        segments = calendar.get_segments(dt.date())
        if not segments or dt < segments[0][0]:
            prev_date = dt.date() - timedelta(days=1)
            prev_segments = calendar.get_segments(prev_date)
            if prev_segments and prev_segments[-1][1] >= dt:
                return prev_date
        return dt.date()
    except Exception:
        return dt.date()


class ProcessRealtimeRecordSerializer(serializers.ModelSerializer):
    """工程実時間記録Serializer"""

    process_code = serializers.CharField(source='process.process_code', read_only=True)
    process_name = serializers.CharField(source='process.process_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    equipment_state_display = serializers.CharField(source='get_equipment_state_display', read_only=True)
    product_code = serializers.CharField(read_only=True)
    product_name = serializers.CharField(read_only=True)
    scrap_record_id = serializers.SerializerMethodField()
    scrap_is_replenished = serializers.SerializerMethodField()
    scrap_replenished_at = serializers.SerializerMethodField()
    scrap_disposition_status = serializers.SerializerMethodField()
    scrap_disposition_display = serializers.SerializerMethodField()
    scrap_return_qty = serializers.SerializerMethodField()
    scrap_decided_at = serializers.SerializerMethodField()
    scrap_decided_by = serializers.SerializerMethodField()

    class Meta:
        model = ProcessRealtimeRecord
        fields = [
            'id',
            'process',
            'process_code',
            'process_name',
            'product',
            'product_code',
            'product_name',
            'timestamp',
            'record_type',
            'record_type_display',
            'qty',
            'equipment_state',
            'equipment_state_display',
            'event_data',
            'batch_no',
            'operator_name',
            'remarks',
            'scrap_record_id',
            'scrap_is_replenished',
            'scrap_replenished_at',
            'scrap_disposition_status',
            'scrap_disposition_display',
            'scrap_return_qty',
            'scrap_decided_at',
            'scrap_decided_by',
        ]
        read_only_fields = ['id', 'timestamp']

    def get_scrap_record_id(self, obj):
        return getattr(getattr(obj, 'scrap_detail', None), 'id', None)

    def get_scrap_is_replenished(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.is_replenished if sd else None

    def get_scrap_replenished_at(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.replenished_at if sd else None

    def get_scrap_disposition_status(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.disposition_status if sd else None

    def get_scrap_disposition_display(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.get_disposition_status_display() if sd else None

    def get_scrap_return_qty(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.return_qty if sd else None

    def get_scrap_decided_at(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.decided_at if sd else None

    def get_scrap_decided_by(self, obj):
        sd = getattr(obj, 'scrap_detail', None)
        return sd.decided_by if sd else None


class ProcessRealtimeCreateSerializer(serializers.Serializer):
    """工程実時間記録作成用Serializer（簡易入力）"""

    process_id = serializers.IntegerField()
    product_id = serializers.IntegerField(required=False, allow_null=True)
    product_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    product_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    record_type = serializers.ChoiceField(choices=ProcessRealtimeRecord.RECORD_TYPE_CHOICES)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, default=0)
    equipment_state = serializers.ChoiceField(
        choices=ProcessRealtimeRecord.EQUIPMENT_STATE_CHOICES,
        required=False,
        allow_null=True
    )
    batch_no = serializers.CharField(max_length=100, required=False, allow_blank=True)
    operator_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    remarks = serializers.CharField(required=False, allow_blank=True)
    event_data = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs.get('record_type') in ['PRODUCTION', 'SCRAP']:
            has_product_id = bool(attrs.get('product_id'))
            has_product_code = bool((attrs.get('product_code') or '').strip())
            if not has_product_id and not has_product_code:
                raise serializers.ValidationError({'product_id': '生産記録は製品（品番）の指定が必要です。'})
        return attrs

    def create(self, validated_data):
        process_id = validated_data.pop('process_id')
        try:
            process = Process.objects.get(id=process_id)
        except Process.DoesNotExist as exc:
            raise serializers.ValidationError({'process_id': '指定された工程が存在しません。'}) from exc

        now = timezone.now()
        if timezone.is_aware(now):
            now = timezone.localtime(now).replace(tzinfo=None)
        plan_date = resolve_workday_date_for_process(process, now)

        product = None
        product_id = validated_data.pop('product_id', None)
        product_code = (validated_data.pop('product_code', None) or '').strip() or None
        product_name = (validated_data.pop('product_name', None) or '').strip() or None
        scrap_event = (validated_data.get('event_data') or {}) if validated_data else {}

        if product_id:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist as exc:
                raise serializers.ValidationError({'product_id': '指定された製品が存在しません。'}) from exc
        elif product_code:
            product = Product.objects.filter(product_code=product_code).first()

        if product:
            product_code = product.product_code
            product_name = product.product_name

        with transaction.atomic():
            parent_record = ProcessRealtimeRecord.objects.create(
                process=process,
                product=product,
                product_code=product_code,
                product_name=product_name,
                **validated_data
            )

            # 生産実績の場合、LineBacklogに反映
            if validated_data.get('record_type') == 'PRODUCTION':
                qty_decimal = validated_data.get('qty', Decimal('0')) or Decimal('0')
                update_line_backlog_production(process, product, qty_decimal, plan_date)

            # 連産品（仮想セット品番）の場合、子製品にも実績を保存する
            if (
                validated_data.get('record_type') == 'PRODUCTION'
                and product
                and getattr(product, 'is_virtual_set', False)
            ):
                bom = BOM.objects.filter(parent_product=product, is_active=True).order_by('-valid_from').first()
                if bom and bom.is_coproduct:
                    parent_qty = validated_data.get('qty', Decimal('0')) or Decimal('0')
                    child_common = {
                        'record_type': 'PRODUCTION',
                        'equipment_state': None,
                        'batch_no': validated_data.get('batch_no', ''),
                        'operator_name': validated_data.get('operator_name', ''),
                        'remarks': validated_data.get('remarks', ''),
                        'event_data': {
                            'coproduct_parent_product_code': product.product_code,
                            'coproduct_parent_record_id': parent_record.id,
                        },
                    }
                    for item in bom.items.select_related('child_product').all():
                        child_product = item.child_product
                        child_qty = parent_qty * (item.quantity or Decimal('0'))
                        child_record = ProcessRealtimeRecord.objects.create(
                            process=process,
                            product=child_product,
                            product_code=child_product.product_code,
                            product_name=child_product.product_name,
                            qty=child_qty,
                            **child_common
                        )
                        # 子製品の実績もLineBacklogに反映
                        update_line_backlog_production(process, child_product, child_qty, plan_date)

            # 仕損は別テーブルにも保存
            if validated_data.get('record_type') == 'SCRAP':
                qty_decimal = validated_data.get('qty', Decimal('0')) or Decimal('0')
                status_raw = (scrap_event.get('disposition_status') or '').strip().upper()
                valid_statuses = {s for s, _ in ScrapRecord.DISPOSITION_STATUS_CHOICES}
                disposition_status = status_raw if status_raw in valid_statuses else 'REJECTED'
                decided_at = timezone.now() if disposition_status != 'PENDING' else None
                decided_by = validated_data.get('operator_name') if decided_at else None

                sr = ScrapRecord.objects.create(
                    process=process,
                    line=getattr(process, 'line', None),
                    product=product,
                    product_code=product_code,
                    product_name=product_name,
                    event_type='SCRAP',
                    qty=qty_decimal,
                    plan_date=plan_date,  # 勤務カレンダに合わせた計画日
                    reason=scrap_event.get('reason') or '',
                    reason_detail=scrap_event.get('reason_detail') or '',
                    batch_no=validated_data.get('batch_no', ''),
                    operator_name=validated_data.get('operator_name', ''),
                    remarks=validated_data.get('remarks', ''),
                    process_record=parent_record,
                    disposition_status=disposition_status,
                    decided_at=decided_at,
                    decided_by=decided_by,
                )

                # 明細を保存（BOM展開結果）
                details = build_scrap_multiplier_details(product.id if product else None, qty_decimal)
                if details:
                    products = {
                        p.id: p for p in Product.objects.filter(
                            id__in=[d['product_id'] for d in details if d.get('product_id')]
                        )
                    }
                    objs = []
                    for d in details:
                        pid = d.get('product_id')
                        prod = products.get(pid) if pid else None
                        objs.append(ScrapRecordDetail(
                            scrap_record=sr,
                            product=prod,
                            product_code=prod.product_code if prod else None,
                            product_name=prod.product_name if prod else None,
                            process_id=d.get('process_id'),
                            line_id=d.get('line_id'),
                            supplier_id=d.get('supplier_id'),
                            sourcing_type=d.get('sourcing_type'),
                            deduct_qty=d.get('qty') or Decimal('0'),
                        ))
                    ScrapRecordDetail.objects.bulk_create(objs)

                # 在庫への転嫁：BOMを最下層まで展開し、在庫引当テーブルに反映
                multipliers = build_scrap_multiplier_map(product.id if product else None, qty_decimal)
                if multipliers:
                    apply_scrap_to_stock(multipliers)

            return parent_record
