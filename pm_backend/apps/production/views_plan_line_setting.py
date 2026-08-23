import json
from datetime import datetime

from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.response import Response

from system_settings.models import SystemSetting

from .models_plan_line_setting import ProductionPlanLineSetting


class ProductionPlanLineSettingView(APIView):
    """生産計画専用のライン設定API（実績照会テーブルとは分離）"""

    PROCESS_PREV_DAY_SHIFT_RULES_KEY = 'production.process_prev_day_shift_rules'
    PROCESS_GANTT_START_TIME_RULES_KEY = 'production.process_gantt_start_time_rules'
    PLANNED_STOCK_RULES_KEY = 'production.planned_stock_calc_rules'
    GANTT_EXCLUDED_PROCESS_RULES_KEY = 'production.gantt_excluded_process_rules'
    SUB_PROCESS_CANDIDATE_RULES_KEY = 'production.sub_process_candidate_product_rules'
    CHECKSHEET_PRODUCT_MAPPING_KEY = 'production.checksheet_product_mapping'
    AUTO_PLAN_TARGET_RULES_KEY = 'production.auto_plan_target_rules'

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
            normalized.append({'lineCode': line_code, 'processCode': process_code, 'shiftQty': shift_qty})
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
            normalized.append({'lineCode': line_code, 'processCode': process_code, 'startTime': start_time})
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
            normalized.append(
                {
                    'lineCode': line_code,
                    'processCode': process_code,
                    'calcTarget': calc_target,
                    'setting': setting,
                }
            )
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

    def _normalize_sub_process_candidate_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            process_code = self._normalize((row or {}).get('processCode'))
            product_codes_source = (row or {}).get('productCodes')
            if not process_code or not isinstance(product_codes_source, list):
                continue
            product_codes = []
            product_seen = set()
            for product_code in product_codes_source:
                normalized_code = self._normalize(product_code)
                if not normalized_code or normalized_code in product_seen:
                    continue
                product_seen.add(normalized_code)
                product_codes.append(normalized_code)
            if not product_codes or process_code in seen:
                continue
            seen.add(process_code)
            normalized.append({'processCode': process_code, 'productCodes': product_codes})
        return normalized

    def _normalize_checksheet_product_mapping(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            process_code = self._normalize((row or {}).get('processCode'))
            if not process_code or process_code in seen:
                continue
            mappings_source = (row or {}).get('mappings')
            if not isinstance(mappings_source, list):
                continue
            mappings = []
            sub_seen = set()
            for mapping in mappings_source:
                sub_code = self._normalize((mapping or {}).get('sub'))
                finished_codes_source = (mapping or {}).get('finished')
                if not sub_code or not isinstance(finished_codes_source, list) or sub_code in sub_seen:
                    continue
                finished_codes = []
                fin_seen = set()
                for finished_code in finished_codes_source:
                    normalized_finished_code = self._normalize(finished_code)
                    if not normalized_finished_code or normalized_finished_code in fin_seen:
                        continue
                    fin_seen.add(normalized_finished_code)
                    finished_codes.append(normalized_finished_code)
                if not finished_codes:
                    continue
                sub_seen.add(sub_code)
                mappings.append({'sub': sub_code, 'finished': finished_codes})
            if mappings:
                seen.add(process_code)
                normalized.append({'processCode': process_code, 'mappings': mappings})
        return normalized

    def _normalize_auto_plan_target_rules(self, rows):
        source = rows if isinstance(rows, list) else []
        normalized = []
        seen = set()
        for row in source:
            line_code = self._normalize((row or {}).get('lineCode'))
            if not line_code or line_code in seen:
                continue
            product_codes_source = (row or {}).get('productCodes')
            if not isinstance(product_codes_source, list):
                continue
            product_codes = []
            product_seen = set()
            for product_code in product_codes_source:
                normalized_code = self._normalize(product_code)
                if not normalized_code or normalized_code in product_seen:
                    continue
                product_seen.add(normalized_code)
                product_codes.append(normalized_code)
            if product_codes:
                seen.add(line_code)
                normalized.append({'lineCode': line_code, 'productCodes': product_codes})
        return normalized

    def _load_special_rules(self):
        special_rules = {
            'prev_day_shift_rules': [],
            'gantt_start_time_rules': [],
            'planned_stock_calc_rules': [],
            'gantt_excluded_process_rules': [],
            'sub_process_candidate_rules': [],
            'checksheet_product_mapping': [],
            'auto_plan_target_rules': [],
        }
        rules_row = SystemSetting.objects.filter(key=self.PROCESS_PREV_DAY_SHIFT_RULES_KEY).first()
        if rules_row:
            try:
                special_rules['prev_day_shift_rules'] = self._normalize_prev_day_shift_rules(json.loads(rules_row.value or '[]'))
            except Exception:
                pass
        start_time_row = SystemSetting.objects.filter(key=self.PROCESS_GANTT_START_TIME_RULES_KEY).first()
        if start_time_row:
            try:
                special_rules['gantt_start_time_rules'] = self._normalize_gantt_start_time_rules(json.loads(start_time_row.value or '[]'))
            except Exception:
                pass
        planned_stock_row = SystemSetting.objects.filter(key=self.PLANNED_STOCK_RULES_KEY).first()
        if planned_stock_row:
            try:
                special_rules['planned_stock_calc_rules'] = self._normalize_planned_stock_calc_rules(json.loads(planned_stock_row.value or '[]'))
            except Exception:
                pass
        gantt_excluded_row = SystemSetting.objects.filter(key=self.GANTT_EXCLUDED_PROCESS_RULES_KEY).first()
        if gantt_excluded_row:
            try:
                special_rules['gantt_excluded_process_rules'] = self._normalize_gantt_excluded_process_rules(json.loads(gantt_excluded_row.value or '[]'))
            except Exception:
                pass
        sub_process_candidate_row = SystemSetting.objects.filter(key=self.SUB_PROCESS_CANDIDATE_RULES_KEY).first()
        if sub_process_candidate_row:
            try:
                special_rules['sub_process_candidate_rules'] = self._normalize_sub_process_candidate_rules(json.loads(sub_process_candidate_row.value or '[]'))
            except Exception:
                pass
        checksheet_mapping_row = SystemSetting.objects.filter(key=self.CHECKSHEET_PRODUCT_MAPPING_KEY).first()
        if checksheet_mapping_row:
            try:
                special_rules['checksheet_product_mapping'] = self._normalize_checksheet_product_mapping(json.loads(checksheet_mapping_row.value or '[]'))
            except Exception:
                pass
        auto_plan_row = SystemSetting.objects.filter(key=self.AUTO_PLAN_TARGET_RULES_KEY).first()
        if auto_plan_row:
            try:
                special_rules['auto_plan_target_rules'] = self._normalize_auto_plan_target_rules(json.loads(auto_plan_row.value or '[]'))
            except Exception:
                pass
        return special_rules

    def _build_response(self):
        rows = ProductionPlanLineSetting.objects.all()
        tabs = [{'key': r.tab_key, 'label': r.tab_name or r.tab_key, 'sort_order': r.sort_order} for r in rows]
        target_line_codes_by_tab = {
            r.tab_key: self._normalize_line_codes(r.target_line_codes)
            for r in rows
        }
        return {
            'tabs': tabs,
            'target_line_codes_by_tab': target_line_codes_by_tab,
            'special_rules': self._load_special_rules(),
        }

    def get(self, request):
        return Response(self._build_response())

    def post(self, request):
        payload = request.data if isinstance(request.data, dict) else {}
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        new_tab = payload.get('create_tab')
        if isinstance(new_tab, dict):
            tab_key = str(new_tab.get('key') or '').strip().lower()
            tab_name = str(new_tab.get('label') or '').strip()
            if tab_key and tab_name:
                max_order = ProductionPlanLineSetting.objects.aggregate(m=Max('sort_order'))['m'] or 0
                ProductionPlanLineSetting.objects.update_or_create(
                    tab_key=tab_key,
                    defaults={
                        'tab_name': tab_name,
                        'sort_order': max_order + 1,
                        'target_line_codes': [],
                        'updated_by': user,
                    },
                )
            return Response(self._build_response())

        rename_tab = payload.get('rename_tab')
        if isinstance(rename_tab, dict):
            tab_key = str(rename_tab.get('key') or '').strip().lower()
            new_name = str(rename_tab.get('label') or '').strip()
            if tab_key and new_name:
                ProductionPlanLineSetting.objects.filter(tab_key=tab_key).update(
                    tab_name=new_name,
                    updated_by=user,
                )
            return Response(self._build_response())

        delete_tab_key = payload.get('delete_tab')
        if delete_tab_key:
            tab_key = str(delete_tab_key).strip().lower()
            ProductionPlanLineSetting.objects.filter(tab_key=tab_key).delete()
            return Response(self._build_response())

        raw_target = (
            payload.get('target_line_codes_by_tab')
            if isinstance(payload.get('target_line_codes_by_tab'), dict)
            else {}
        )
        raw_special_rules = (
            payload.get('special_rules')
            if isinstance(payload.get('special_rules'), dict)
            else {}
        )

        existing_rows = {row.tab_key: row for row in ProductionPlanLineSetting.objects.all()}
        for tab_key, row in existing_rows.items():
            target_source = raw_target[tab_key] if tab_key in raw_target else row.target_line_codes
            row.target_line_codes = self._normalize_line_codes(target_source)
            row.updated_by = user
            row.save(update_fields=['target_line_codes', 'updated_by', 'updated_at'])

        if 'prev_day_shift_rules' in raw_special_rules:
            rules = self._normalize_prev_day_shift_rules(raw_special_rules['prev_day_shift_rules'])
            SystemSetting.objects.update_or_create(
                key=self.PROCESS_PREV_DAY_SHIFT_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別の前日シフト台数設定',
                    'updated_by': user,
                },
            )
        if 'gantt_start_time_rules' in raw_special_rules:
            rules = self._normalize_gantt_start_time_rules(raw_special_rules['gantt_start_time_rules'])
            SystemSetting.objects.update_or_create(
                key=self.PROCESS_GANTT_START_TIME_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別のガント開始時刻設定',
                    'updated_by': user,
                },
            )
        if 'planned_stock_calc_rules' in raw_special_rules:
            rules = self._normalize_planned_stock_calc_rules(raw_special_rules['planned_stock_calc_rules'])
            SystemSetting.objects.update_or_create(
                key=self.PLANNED_STOCK_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別の計画在庫計算特例設定',
                    'updated_by': user,
                },
            )
        if 'gantt_excluded_process_rules' in raw_special_rules:
            rules = self._normalize_gantt_excluded_process_rules(raw_special_rules['gantt_excluded_process_rules'])
            SystemSetting.objects.update_or_create(
                key=self.GANTT_EXCLUDED_PROCESS_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'ライン工程別のガント展開除外設定',
                    'updated_by': user,
                },
            )
        if 'sub_process_candidate_rules' in raw_special_rules:
            rules = self._normalize_sub_process_candidate_rules(raw_special_rules['sub_process_candidate_rules'])
            SystemSetting.objects.update_or_create(
                key=self.SUB_PROCESS_CANDIDATE_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'サブ工程計画の工程別候補製品設定',
                    'updated_by': user,
                },
            )
        if 'checksheet_product_mapping' in raw_special_rules:
            rules = self._normalize_checksheet_product_mapping(raw_special_rules['checksheet_product_mapping'])
            SystemSetting.objects.update_or_create(
                key=self.CHECKSHEET_PRODUCT_MAPPING_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': 'サブ工程→完成品のチェックシート用製品マッピング',
                    'updated_by': user,
                },
            )
        if 'auto_plan_target_rules' in raw_special_rules:
            rules = self._normalize_auto_plan_target_rules(raw_special_rules['auto_plan_target_rules'])
            SystemSetting.objects.update_or_create(
                key=self.AUTO_PLAN_TARGET_RULES_KEY,
                defaults={
                    'value': json.dumps(rules, ensure_ascii=False),
                    'description': '自動計画適用ライン×製品設定',
                    'updated_by': user,
                },
            )

        return Response(self._build_response())
