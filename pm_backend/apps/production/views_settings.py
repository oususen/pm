import json
from datetime import datetime

from django.db.models import Max
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from production.models_plan_lock_setting import ProductionPlanLockSetting
from production.models_record_inquiry_setting import ProductionRecordInquirySetting
from production.serializers import ProductionPlanLockSettingSerializer
from system_settings.models import SystemSetting


class ProductionPlanLockSettingView(APIView):
    def get(self, request):
        setting = ProductionPlanLockSetting.objects.first()
        if not setting:
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            setting = ProductionPlanLockSetting.objects.create(lock_days=0, updated_by=user)
        serializer = ProductionPlanLockSettingSerializer(setting)
        return Response(serializer.data)

    def post(self, request):
        raw_days = request.data.get('lock_days')
        try:
            lock_days = int(raw_days)
        except (TypeError, ValueError):
            return Response({'detail': 'lock_days must be integer'}, status=status.HTTP_400_BAD_REQUEST)
        if lock_days < 0:
            return Response({'detail': 'lock_days must be >= 0'}, status=status.HTTP_400_BAD_REQUEST)

        setting = ProductionPlanLockSetting.objects.first()
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        if not setting:
            setting = ProductionPlanLockSetting.objects.create(lock_days=lock_days, updated_by=user)
        else:
            setting.lock_days = lock_days
            setting.updated_by = user
            setting.save(update_fields=['lock_days', 'updated_at', 'updated_by'])

        serializer = ProductionPlanLockSettingSerializer(setting)
        return Response(serializer.data)


class ProductionRecordInquirySettingView(APIView):
    PROCESS_PREV_DAY_SHIFT_RULES_KEY = 'production.process_prev_day_shift_rules'
    PROCESS_GANTT_START_TIME_RULES_KEY = 'production.process_gantt_start_time_rules'
    PLANNED_STOCK_RULES_KEY = 'production.planned_stock_calc_rules'
    GANTT_EXCLUDED_PROCESS_RULES_KEY = 'production.gantt_excluded_process_rules'
    PRODUCT_MAPPINGS_KEY = 'production.product_mappings'

    def _normalize(self, value):
        return str(value or '').strip().upper()

    def _normalize_line_codes(self, values):
        source = values if isinstance(values, list) else []
        result = []
        seen = set()
        for item in source:
            code = self._normalize(item)
            if not code or code in seen:
                continue
            seen.add(code)
            result.append(code)
        return result

    def _normalize_mapping_rows(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        for row in source:
            app_product_code = self._normalize((row or {}).get('appProductCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            core_product_code = str((row or {}).get('coreProductCode') or '').strip()
            core_process_order = str((row or {}).get('coreProcessOrder') or '').strip()
            enter_count_raw = (row or {}).get('enterCount')
            enter_count = 2
            try:
                if enter_count_raw is not None and str(enter_count_raw).strip() != '':
                    value = int(float(enter_count_raw))
                    if 1 <= value <= 20:
                        enter_count = value
                    else:
                        enter_count = 2
            except (TypeError, ValueError):
                enter_count = 2
            if not app_product_code or not core_product_code:
                continue
            normalized.append({
                'appProductCode': app_product_code,
                'processCode': process_code,
                'coreProductCode': core_product_code,
                'coreProcessOrder': core_process_order,
                'enterCount': enter_count,
            })
        return normalized

    def _normalize_prev_day_shift_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            shift_qty_raw = (row or {}).get('shiftQty', 0)
            try:
                shift_qty = int(float(shift_qty_raw))
            except (TypeError, ValueError):
                shift_qty = 0
            if not line_code or not process_code or shift_qty <= 0:
                continue
            key = f'{line_code}|{process_code}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                'lineCode': line_code,
                'processCode': process_code,
                'shiftQty': shift_qty,
            })
        return normalized

    def _normalize_gantt_start_time_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            start_time = str((row or {}).get('startTime') or '').strip()
            if not line_code or not process_code:
                continue
            try:
                parsed = datetime.strptime(start_time, '%H:%M').time()
                start_time = parsed.strftime('%H:%M')
            except (TypeError, ValueError):
                continue
            key = f'{line_code}|{process_code}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                'lineCode': line_code,
                'processCode': process_code,
                'startTime': start_time,
            })
        return normalized

    def _normalize_planned_stock_calc_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        allowed_targets = {'STOCK', 'PLANNED_STOCK', 'DEMAND'}
        allowed_settings = {'ORDER_QTY', 'ACTUAL_OR_PLAN'}
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            calc_target = self._normalize((row or {}).get('calcTarget') or 'PLANNED_STOCK')
            setting = self._normalize((row or {}).get('setting'))
            old_item = self._normalize((row or {}).get('item'))
            old_mode = self._normalize((row or {}).get('mode'))
            if old_item == 'PARENT_SHIPMENT_SOURCE' and old_mode == 'PLAN':
                setting = 'ORDER_QTY'
            if setting == 'PARENT_PLAN':
                setting = 'ORDER_QTY'
            if old_item == 'PARENT_SHIPMENT_SOURCE' and calc_target not in allowed_targets:
                calc_target = 'PLANNED_STOCK'
            if not line_code or not process_code:
                continue
            if calc_target not in allowed_targets or setting not in allowed_settings:
                continue
            key = f'{line_code}|{process_code}|{calc_target}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                'lineCode': line_code,
                'processCode': process_code,
                'calcTarget': calc_target,
                'setting': setting,
            })
        return normalized

    def _normalize_gantt_excluded_process_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            process_code = self._normalize((row or {}).get('processCode'))
            if not line_code or not process_code:
                continue
            key = f'{line_code}|{process_code}'
            if key in seen:
                continue
            seen.add(key)
            normalized.append({'lineCode': line_code, 'processCode': process_code})
        return normalized

    def _build_response_payload(self):
        rows = ProductionRecordInquirySetting.objects.all()
        tabs = [{'key': r.tab_key, 'label': r.tab_name or r.tab_key, 'sort_order': r.sort_order} for r in rows]
        target_line_codes_by_tab = {r.tab_key: self._normalize_line_codes(r.target_line_codes) for r in rows}

        flat_row = SystemSetting.objects.filter(key=self.PRODUCT_MAPPINGS_KEY).first()
        if flat_row:
            try:
                product_mappings = self._normalize_mapping_rows(json.loads(flat_row.value or '[]'))
            except Exception:
                product_mappings = []
        else:
            seen = set()
            product_mappings = []
            for row in rows:
                for mapping in self._normalize_mapping_rows(row.product_mappings):
                    key = f"{mapping['appProductCode']}__{mapping['processCode']}"
                    if key not in seen:
                        seen.add(key)
                        product_mappings.append(mapping)

        special_rules = {
            'prev_day_shift_rules': [],
            'gantt_start_time_rules': [],
            'planned_stock_calc_rules': [],
            'gantt_excluded_process_rules': [],
        }
        rules_row = SystemSetting.objects.filter(key=self.PROCESS_PREV_DAY_SHIFT_RULES_KEY).first()
        if rules_row:
            try:
                parsed = json.loads(rules_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['prev_day_shift_rules'] = self._normalize_prev_day_shift_rules(parsed)
        start_time_row = SystemSetting.objects.filter(key=self.PROCESS_GANTT_START_TIME_RULES_KEY).first()
        if start_time_row:
            try:
                parsed = json.loads(start_time_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['gantt_start_time_rules'] = self._normalize_gantt_start_time_rules(parsed)
        planned_stock_row = SystemSetting.objects.filter(key=self.PLANNED_STOCK_RULES_KEY).first()
        if planned_stock_row:
            try:
                parsed = json.loads(planned_stock_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['planned_stock_calc_rules'] = self._normalize_planned_stock_calc_rules(parsed)
        gantt_excluded_row = SystemSetting.objects.filter(key=self.GANTT_EXCLUDED_PROCESS_RULES_KEY).first()
        if gantt_excluded_row:
            try:
                parsed = json.loads(gantt_excluded_row.value or '[]')
            except Exception:
                parsed = []
            special_rules['gantt_excluded_process_rules'] = self._normalize_gantt_excluded_process_rules(parsed)

        return {
            'tabs': tabs,
            'target_line_codes_by_tab': target_line_codes_by_tab,
            'product_mappings': product_mappings,
            'special_rules': special_rules,
        }

    def get(self, request):
        return Response(self._build_response_payload())

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        new_tab = payload.get('create_tab')
        if isinstance(new_tab, dict):
            tab_key = str(new_tab.get('key') or '').strip().lower()
            tab_name = str(new_tab.get('label') or '').strip()
            if tab_key and tab_name:
                max_order = ProductionRecordInquirySetting.objects.aggregate(m=Max('sort_order'))['m'] or 0
                ProductionRecordInquirySetting.objects.update_or_create(
                    tab_key=tab_key,
                    defaults={
                        'tab_name': tab_name,
                        'sort_order': max_order + 1,
                        'target_line_codes': [],
                        'updated_by': user,
                    },
                )
            return Response(self._build_response_payload())

        rename_tab = payload.get('rename_tab')
        if isinstance(rename_tab, dict):
            tab_key = str(rename_tab.get('key') or '').strip().lower()
            new_name = str(rename_tab.get('label') or '').strip()
            if tab_key and new_name:
                ProductionRecordInquirySetting.objects.filter(tab_key=tab_key).update(tab_name=new_name, updated_by=user)
            return Response(self._build_response_payload())

        delete_tab_key = payload.get('delete_tab')
        if delete_tab_key:
            tab_key = str(delete_tab_key).strip().lower()
            ProductionRecordInquirySetting.objects.filter(tab_key=tab_key).delete()
            return Response(self._build_response_payload())

        raw_target = payload.get('target_line_codes_by_tab') if isinstance(payload.get('target_line_codes_by_tab'), dict) else {}
        raw_special_rules = payload.get('special_rules') if isinstance(payload.get('special_rules'), dict) else {}

        existing_rows = {row.tab_key: row for row in ProductionRecordInquirySetting.objects.all()}
        for tab_key, row in existing_rows.items():
            target_source = raw_target[tab_key] if tab_key in raw_target else row.target_line_codes
            row.target_line_codes = self._normalize_line_codes(target_source)
            row.updated_by = user
            row.save(update_fields=['target_line_codes', 'updated_by', 'updated_at'])

        if 'product_mappings' in payload:
            raw_product_mappings = payload.get('product_mappings', [])
            flat_mappings = self._normalize_mapping_rows(
                raw_product_mappings if isinstance(raw_product_mappings, list) else []
            )
            SystemSetting.objects.update_or_create(
                key=self.PRODUCT_MAPPINGS_KEY,
                defaults={
                    'value': json.dumps(flat_mappings, ensure_ascii=False),
                    'description': '生産実績照会 品番マッピング',
                    'updated_by': user,
                },
            )

        if 'prev_day_shift_rules' in raw_special_rules:
            rules = self._normalize_prev_day_shift_rules(raw_special_rules.get('prev_day_shift_rules'))
            SystemSetting.objects.update_or_create(
                key=self.PROCESS_PREV_DAY_SHIFT_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別の前日シフト台数設定',
                    'updated_by': user,
                },
            )
        if 'gantt_start_time_rules' in raw_special_rules:
            rules = self._normalize_gantt_start_time_rules(raw_special_rules.get('gantt_start_time_rules'))
            SystemSetting.objects.update_or_create(
                key=self.PROCESS_GANTT_START_TIME_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別のガント開始時刻設定',
                    'updated_by': user,
                },
            )
        if 'planned_stock_calc_rules' in raw_special_rules:
            rules = self._normalize_planned_stock_calc_rules(raw_special_rules.get('planned_stock_calc_rules'))
            SystemSetting.objects.update_or_create(
                key=self.PLANNED_STOCK_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別の計画在庫計算特例設定',
                    'updated_by': user,
                },
            )
        if 'gantt_excluded_process_rules' in raw_special_rules:
            rules = self._normalize_gantt_excluded_process_rules(raw_special_rules.get('gantt_excluded_process_rules'))
            SystemSetting.objects.update_or_create(
                key=self.GANTT_EXCLUDED_PROCESS_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別のガント展開除外設定',
                    'updated_by': user,
                },
            )

        return Response(self._build_response_payload())
