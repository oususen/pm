from datetime import date

from django.db.models import Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import BOMItem, Product
from production.models_line_backlog import LineBacklog
from production.inventory.inventory_calculator import recalculate_inventory_for_line

from .models import EngineeringChangeCase, EngineeringChangePart, PurchasePlanLockSetting
from .serializers import PurchasePlanLockSettingSerializer


class PurchasePlanLockSettingView(APIView):
    def get(self, request):
        setting = PurchasePlanLockSetting.objects.first()
        if not setting:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            setting = PurchasePlanLockSetting.objects.create(lock_days=0, updated_by=user)
        serializer = PurchasePlanLockSettingSerializer(setting)
        return Response(serializer.data)


class EngineeringChangeView(APIView):
    def get(self, request):
        today = date.today()
        parts = (
            EngineeringChangePart.objects
            .select_related('case__final_product', 'old_part', 'new_part')
            .order_by('-id')
        )
        old_part_ids = list({part.old_part_id for part in parts})
        parent_map = {}
        if old_part_ids:
            bom_items = (
                BOMItem.objects.filter(child_product_id__in=old_part_ids, bom__is_active=True)
                .select_related('bom__parent_product')
            )
            for bi in bom_items:
                parent = bi.bom.parent_product
                if not parent:
                    continue
                key = bi.child_product_id
                if key not in parent_map:
                    parent_map[key] = {}
                parent_map[key][parent.product_code] = {
                    'product_code': parent.product_code,
                    'product_name': parent.product_name,
                }

        rows = []
        for part in parts:
            switch_date = part.switch_date or part.case.switch_date or today
            start_date = today
            end_date = switch_date if switch_date >= today else today

            base_qs = LineBacklog.objects.filter(
                product=part.old_part,
                plan_date__gte=start_date,
                plan_date__lte=end_date,
            )
            has_prod = base_qs.filter(line__line_type='PROD').exists()
            target_line_type = 'PROD' if has_prod else 'PURCHASE'
            purchase_plan_qty = base_qs.filter(line__line_type='PURCHASE').aggregate(v=Sum('plan_qty'))['v'] or 0
            production_plan_qty = base_qs.filter(line__line_type='PROD').aggregate(v=Sum('plan_qty'))['v'] or 0
            target_base_qs = base_qs.filter(line__line_type=target_line_type)
            required_until_switch_qty = target_base_qs.aggregate(v=Sum('order_qty'))['v'] or 0
            # 購買BACKLOG運用で order_qty が未計算/0 の場合に備えて plan_qty をフォールバック
            if required_until_switch_qty == 0:
                required_until_switch_qty = target_base_qs.aggregate(v=Sum('plan_qty'))['v'] or 0

            today_qs = LineBacklog.objects.filter(product=part.old_part, plan_date=today)
            stock_qty = today_qs.aggregate(v=Sum('stock_qty'))['v'] or 0
            progress_qty = today_qs.aggregate(v=Sum('progress_qty'))['v'] or 0
            switch_day_prod_qs = LineBacklog.objects.filter(
                product=part.old_part,
                plan_date=switch_date,
                line__line_type=target_line_type,
            )
            switch_prod_planned_stock_qty = switch_day_prod_qs.aggregate(v=Sum('planned_stock_qty'))['v'] or 0
            switch_prod_progress_qty = switch_day_prod_qs.aggregate(v=Sum('progress_qty'))['v'] or 0
            switch_prod_planned_progress_qty = switch_day_prod_qs.aggregate(v=Sum('planned_progress_qty'))['v'] or 0
            # 切替日当日に行がない場合、切替日以前の直近バックログ値を採用
            if (
                switch_prod_planned_stock_qty == 0
                and switch_prod_progress_qty == 0
                and switch_prod_planned_progress_qty == 0
            ):
                latest_qs = (
                    LineBacklog.objects.filter(
                        product=part.old_part,
                        plan_date__lte=switch_date,
                        line__line_type=target_line_type,
                    )
                    .order_by('-plan_date')
                )
                latest = latest_qs.first()
                if latest:
                    latest_day_qs = latest_qs.filter(plan_date=latest.plan_date)
                    switch_prod_planned_stock_qty = latest_day_qs.aggregate(v=Sum('planned_stock_qty'))['v'] or 0
                    switch_prod_progress_qty = latest_day_qs.aggregate(v=Sum('progress_qty'))['v'] or 0
                    switch_prod_planned_progress_qty = latest_day_qs.aggregate(v=Sum('planned_progress_qty'))['v'] or 0

            required = int(part.required_qty_after_eol or 0)
            parent_products = list((parent_map.get(part.old_part_id) or {}).values())
            parent_products.sort(key=lambda x: x['product_code'])
            rows.append({
                'id': part.id,
                'case_id': part.case_id,
                'case_code': part.case.case_code or f'EC-{part.case_id:06d}',
                'case_name': part.case.case_name or '',
                'final_product_code': part.case.final_product.product_code if part.case.final_product else '',
                'final_product_name': part.case.final_product.product_name if part.case.final_product else '',
                'switch_date': switch_date,
                'old_part_code': part.old_part.product_code,
                'old_part_name': part.old_part.product_name,
                'parent_products': parent_products,
                'parent_products_text': ', '.join([f"{x['product_code']} {x['product_name']}" for x in parent_products]),
                'new_part_code': part.new_part.product_code if part.new_part else '',
                'required_qty_after_eol': required,
                'purchase_plan_qty': purchase_plan_qty,
                'production_plan_qty': production_plan_qty,
                'required_until_switch_qty': required_until_switch_qty,
                'switch_prod_planned_stock_qty': switch_prod_planned_stock_qty,
                'switch_prod_progress_qty': switch_prod_progress_qty,
                'switch_prod_planned_progress_qty': switch_prod_planned_progress_qty,
                'stock_qty': stock_qty,
                'progress_qty': progress_qty,
                'excess_purchase_qty': purchase_plan_qty - required_until_switch_qty,
                'excess_production_qty': production_plan_qty - required,
            })
        return Response(rows)

    def post(self, request):
        final_product_code = (request.data.get('final_product_code') or '').strip()
        parts = request.data.get('parts') or []
        if not isinstance(parts, list) or not parts:
            return Response({'detail': 'parts is required'}, status=status.HTTP_400_BAD_REQUEST)

        final_product = None
        if final_product_code:
            try:
                final_product = Product.objects.get(product_code=final_product_code)
            except Product.DoesNotExist:
                return Response({'detail': f'final product not found: {final_product_code}'}, status=status.HTTP_400_BAD_REQUEST)

        case = EngineeringChangeCase.objects.create(
            case_name=(request.data.get('case_name') or '').strip() or None,
            final_product=final_product,
            switch_date=None,
            note=(request.data.get('note') or '').strip() or None,
        )
        case.case_code = f'EC-{case.id:06d}'
        case.save(update_fields=['case_code', 'updated_at'])

        created = 0
        for part in parts:
            old_code = (part.get('old_part_code') or '').strip()
            if not old_code:
                continue
            try:
                old_part = Product.objects.get(product_code=old_code)
            except Product.DoesNotExist:
                continue

            new_part = None
            new_code = (part.get('new_part_code') or '').strip()
            if new_code:
                new_part = Product.objects.filter(product_code=new_code).first()

            EngineeringChangePart.objects.create(
                case=case,
                switch_date=part.get('switch_date') or request.data.get('switch_date') or None,
                old_part=old_part,
                new_part=new_part,
                required_qty_after_eol=int(part.get('required_qty_after_eol') or 0),
                remark=(part.get('remark') or '').strip() or None,
            )
            created += 1

        if created == 0:
            case.delete()
            return Response({'detail': 'valid parts not found'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'detail': 'created', 'case_id': case.id, 'case_code': case.case_code, 'created_parts': created},
            status=status.HTTP_201_CREATED
        )


class EngineeringChangePartDetailView(APIView):
    def put(self, request, pk: int):
        part = EngineeringChangePart.objects.select_related('case').filter(pk=pk).first()
        if not part:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if 'final_product_code' in request.data:
            final_product_code = (request.data.get('final_product_code') or '').strip()
            if final_product_code:
                final_product = Product.objects.filter(product_code=final_product_code).first()
                if not final_product:
                    return Response({'detail': f'final product not found: {final_product_code}'}, status=status.HTTP_400_BAD_REQUEST)
                part.case.final_product = final_product
            else:
                part.case.final_product = None
        if 'case_name' in request.data:
            part.case.case_name = (request.data.get('case_name') or '').strip() or None

        part.case.save(update_fields=['final_product', 'case_name', 'updated_at'])

        old_part_code = (request.data.get('old_part_code') or '').strip()
        if old_part_code:
            old_part = Product.objects.filter(product_code=old_part_code).first()
            if not old_part:
                return Response({'detail': f'old part not found: {old_part_code}'}, status=status.HTTP_400_BAD_REQUEST)
            part.old_part = old_part

        if 'new_part_code' in request.data:
            new_part_code = (request.data.get('new_part_code') or '').strip()
            new_part = Product.objects.filter(product_code=new_part_code).first() if new_part_code else None
            if new_part_code and not new_part:
                return Response({'detail': f'new part not found: {new_part_code}'}, status=status.HTTP_400_BAD_REQUEST)
            part.new_part = new_part

        if 'required_qty_after_eol' in request.data:
            part.required_qty_after_eol = int(request.data.get('required_qty_after_eol') or 0)
        if 'switch_date' in request.data:
            part.switch_date = request.data.get('switch_date') or None

        part.save(update_fields=['switch_date', 'old_part', 'new_part', 'required_qty_after_eol', 'updated_at'])
        return Response({'detail': 'updated'})

    def delete(self, request, pk: int):
        part = EngineeringChangePart.objects.filter(pk=pk).first()
        if not part:
            return Response(status=status.HTTP_404_NOT_FOUND)
        case_id = part.case_id
        part.delete()
        if not EngineeringChangePart.objects.filter(case_id=case_id).exists():
            EngineeringChangeCase.objects.filter(pk=case_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def post(self, request):
        raw_days = request.data.get('lock_days')
        try:
            lock_days = int(raw_days)
        except (TypeError, ValueError):
            return Response({'detail': 'lock_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lock_days < 0:
            return Response({'detail': 'lock_days must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)

        setting = PurchasePlanLockSetting.objects.first()
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not setting:
            setting = PurchasePlanLockSetting.objects.create(lock_days=lock_days, updated_by=user)
        else:
            setting.lock_days = lock_days
            setting.updated_by = user
            setting.save(update_fields=['lock_days', 'updated_at', 'updated_by'])

        serializer = PurchasePlanLockSettingSerializer(setting)
        return Response(serializer.data)


class EngineeringChangeCaseRecalculateView(APIView):
    def post(self, request, case_id: int):
        today = date.today()
        parts = list(
            EngineeringChangePart.objects
            .select_related('old_part')
            .filter(case_id=case_id)
        )
        if not parts:
            return Response({'detail': 'case not found or no parts'}, status=status.HTTP_404_NOT_FOUND)

        switch_dates = [p.switch_date for p in parts if p.switch_date]
        end_date = max(switch_dates) if switch_dates else today
        if end_date < today:
            end_date = today

        old_part_ids = [p.old_part_id for p in parts]
        line_ids = {p.old_part.line_id for p in parts if getattr(p.old_part, 'line_id', None)}
        if not line_ids:
            line_ids = set(
                LineBacklog.objects.filter(
                    product_id__in=old_part_ids,
                    plan_date__gte=today,
                    plan_date__lte=end_date,
                ).values_list('line_id', flat=True)
            )
            line_ids.discard(None)

        recalculated = 0
        for line_id in sorted(line_ids):
            recalculate_inventory_for_line(
                line_id=line_id,
                start_date=today,
                end_date=end_date,
                include_progress=True,
                line_final_only=False,
            )
            recalculated += 1

        return Response({
            'detail': 'recalculated',
            'case_id': case_id,
            'line_count': recalculated,
            'start_date': str(today),
            'end_date': str(end_date),
        })
