"""進度PDF突合API — PDFとDBの指定日進度を比較し、差異を調整する"""
import re
from datetime import date
from io import BytesIO

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from masters.models import Line, Product, Process
from .models_line_backlog import LineBacklog
from .models_line_backlog_adjustment import LineBacklogAdjustment


def _parse_progress_pdf(file_bytes):
    """
    生産進度照会PDFを解析し、品番ごとの日付別進度値を返す。
    """
    import pdfplumber

    pdf = pdfplumber.open(BytesIO(file_bytes))

    year = None
    month = None
    supplier_code = None
    supplier_name = None
    date_columns = []
    products = []
    current_product = None

    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        for line_text in text.split('\n'):
            stripped = line_text.strip()
            if not stripped:
                continue

            if year is None:
                ym_match = re.search(r'(\d{4})年(\d{1,2})月度', stripped)
                if ym_match:
                    year = int(ym_match.group(1))
                    month = int(ym_match.group(2))

            if not supplier_code:
                sup_match = re.search(r':(\d{6})\s+(.+?)(?:\s+品|\s*$)', stripped)
                if sup_match:
                    supplier_code = sup_match.group(1)
                    supplier_name = sup_match.group(2).strip()

            if not date_columns and year and month:
                day_matches = re.findall(r'(\d{1,2})日', stripped)
                if len(day_matches) >= 10:
                    has_kurikoshi = '繰越' in stripped
                    dates = []
                    current_month = month
                    current_year = year
                    prev_day = 0
                    for d_str in day_matches:
                        day = int(d_str)
                        if day < prev_day:
                            current_month += 1
                            if current_month > 12:
                                current_month = 1
                                current_year += 1
                        try:
                            dates.append(date(current_year, current_month, day))
                        except ValueError:
                            pass
                        prev_day = day
                    date_columns = [None] + dates if has_kurikoshi else dates
                    continue

            if re.match(r'^[A-Za-z0-9]', stripped) and '(' in stripped and ')' in stripped:
                parts = stripped.split()
                if len(parts) >= 2:
                    current_product = {'code': parts[0], 'progress': {}}
                    products.append(current_product)
                continue

            if stripped.startswith('進度'):
                if current_product and date_columns:
                    nums = re.findall(r'-?\d+', stripped[2:].strip())
                    for i, val_str in enumerate(nums):
                        if i < len(date_columns) and date_columns[i] is not None:
                            current_product['progress'][date_columns[i]] = int(val_str)
                continue

    pdf.close()
    actual_dates = [d for d in date_columns if d is not None]
    return {
        'dates': actual_dates,
        'products': products,
        'year': year,
        'month': month,
        'supplier_code': supplier_code or '',
        'supplier_name': supplier_name or '',
    }


class ProgressPdfCompareView(APIView):
    """進度PDFをアップロードし、指定日のDBの進度と突合して結果を返す"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        pdf_file = request.FILES.get('file')
        if not pdf_file:
            return Response({'detail': 'PDFファイルが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        target_date_str = request.data.get('target_date', '').strip()
        line_code = request.data.get('line_code', '').strip()

        if not line_code:
            return Response({'detail': 'line_codeが必要です'}, status=status.HTTP_400_BAD_REQUEST)
        if not target_date_str:
            return Response({'detail': 'target_dateが必要です'}, status=status.HTTP_400_BAD_REQUEST)

        line = Line.objects.filter(line_code=line_code).first()
        if not line:
            return Response({'detail': f'ライン {line_code} が見つかりません'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            return Response({'detail': '日付の形式が不正です (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pdf_data = _parse_progress_pdf(pdf_file.read())
        except Exception as e:
            return Response({'detail': f'PDF解析エラー: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if not pdf_data['dates']:
            return Response({'detail': 'PDFから日付を検出できませんでした'}, status=status.HTTP_400_BAD_REQUEST)

        if target_date not in pdf_data['dates']:
            available = [d.isoformat() for d in pdf_data['dates']]
            return Response({
                'detail': f'{target_date} はPDFに含まれていません',
                'available_dates': available,
            }, status=status.HTTP_400_BAD_REQUEST)

        # DB側: 指定日・指定ラインのsequence_no=0行を取得
        backlogs = LineBacklog.objects.filter(
            plan_date=target_date,
            line=line,
            sequence_no=0,
        ).select_related('product', 'process')

        db_data = {}
        db_by_stripped = {}
        for b in backlogs:
            code = b.product.product_code
            entry = {
                'product_code': code,
                'product_name': b.product.product_name,
                'process_code': b.process.process_code if b.process else '',
                'progress_qty': b.progress_qty or 0,
                'planned_progress_qty': b.planned_progress_qty or 0,
            }
            db_data[code] = entry
            stripped = code.rstrip('G')
            if stripped != code:
                db_by_stripped.setdefault(stripped, []).append(entry)

        match_list = []
        mismatch_list = []
        pdf_only_list = []
        matched_db_codes = set()

        for p in pdf_data['products']:
            code = p['code']
            pdf_val = p['progress'].get(target_date, 0)

            d = db_data.get(code)
            db_code = code
            if not d:
                code_g = code + 'G'
                if code_g in db_data:
                    d = db_data[code_g]
                    db_code = code_g
            if not d:
                entries = db_by_stripped.get(code, [])
                if entries:
                    d = entries[0]
                    db_code = d['product_code']

            if d:
                matched_db_codes.add(db_code)
                diff = pdf_val - d['progress_qty']
                rec = {
                    'pdf_code': code,
                    'db_code': db_code,
                    'product_name': d['product_name'],
                    'process_code': d['process_code'],
                    'progress_pdf': pdf_val,
                    'progress_db': d['progress_qty'],
                    'planned_progress_db': d['planned_progress_qty'],
                    'diff': diff,
                }
                if diff == 0:
                    match_list.append(rec)
                else:
                    mismatch_list.append(rec)
            else:
                pdf_only_list.append({'pdf_code': code, 'progress_pdf': pdf_val})

        db_only_list = []
        for code, d in sorted(db_data.items()):
            if code not in matched_db_codes:
                db_only_list.append({
                    'db_code': code,
                    'product_name': d['product_name'],
                    'process_code': d['process_code'],
                    'progress_db': d['progress_qty'],
                })

        mismatch_list.sort(key=lambda x: abs(x['diff']), reverse=True)

        return Response({
            'target_date': target_date.isoformat(),
            'available_dates': [d.isoformat() for d in pdf_data['dates']],
            'line_code': line_code,
            'line_name': line.line_name,
            'supplier_code': pdf_data['supplier_code'],
            'supplier_name': pdf_data['supplier_name'],
            'summary': {
                'match': len(match_list),
                'mismatch': len(mismatch_list),
                'pdf_only': len(pdf_only_list),
                'db_only': len(db_only_list),
            },
            'mismatch': mismatch_list,
            'match': match_list,
            'pdf_only': pdf_only_list,
            'db_only': db_only_list,
        })


class ProgressPdfAdjustView(APIView):
    """突合せ不一致の差異分をLineBacklogAdjustment(PROGRESS)として一括登録"""

    def _resolve_common(self, request):
        line_code = (request.data.get('line_code') or '').strip()
        target_date_str = (request.data.get('target_date') or '').strip()
        items = request.data.get('items', [])

        if not line_code or not target_date_str or not items:
            return None, None, None, None, Response(
                {'detail': 'line_code, target_date, items は必須です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line = Line.objects.filter(line_code=line_code).first()
        if not line:
            return None, None, None, None, Response(
                {'detail': f'ライン {line_code} が見つかりません'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target_date = date.fromisoformat(target_date_str)
        except ValueError:
            return None, None, None, None, Response(
                {'detail': '日付の形式が不正です'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resolved = []
        errors = []
        for item in items:
            db_code = (item.get('db_code') or '').strip()
            process_code = (item.get('process_code') or '').strip()
            diff = item.get('diff')

            if not db_code or diff is None:
                continue

            try:
                diff = int(diff)
            except (TypeError, ValueError):
                errors.append(f'{db_code}: diff が不正です')
                continue

            if diff == 0:
                continue

            product = Product.objects.filter(product_code=db_code).first()
            if not product:
                errors.append(f'{db_code}: 品番が見つかりません')
                continue

            if not process_code:
                errors.append(f'{db_code}: 工程コードが空です')
                continue
            process = Process.objects.filter(process_code=process_code).first()
            if not process:
                errors.append(f'{db_code}: 工程 {process_code} が見つかりません')
                continue

            resolved.append({'product': product, 'process': process, 'diff': diff})

        if errors:
            return None, None, None, None, Response(
                {'detail': 'バリデーションエラー', 'errors': errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return line, target_date, resolved, errors, None

    def put(self, request):
        """登録前の事前チェック: 既存調整レコードの有無を返す"""
        line, target_date, resolved, errors, err_resp = self._resolve_common(request)
        if err_resp:
            return err_resp

        existing = []
        for r in resolved:
            adj = LineBacklogAdjustment.objects.filter(
                line=line,
                product=r['product'],
                process=r['process'],
                plan_date=target_date,
                adjust_type='PROGRESS',
            ).first()
            if adj:
                existing.append({
                    'product_code': r['product'].product_code,
                    'process_code': r['process'].process_code,
                    'current_qty': adj.adjust_qty,
                    'current_reason': adj.reason,
                    'new_qty': r['diff'],
                })

        return Response({'existing_count': len(existing), 'existing': existing})

    def post(self, request):
        line, target_date, resolved, errors, err_resp = self._resolve_common(request)
        if err_resp:
            return err_resp

        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None

        from django.db import transaction
        created = 0
        updated = 0
        with transaction.atomic():
            for r in resolved:
                _, is_created = LineBacklogAdjustment.objects.update_or_create(
                    line=line,
                    product=r['product'],
                    process=r['process'],
                    plan_date=target_date,
                    adjust_type='PROGRESS',
                    defaults={
                        'adjust_qty': r['diff'],
                        'reason': 'PDF突合せ調整',
                        'updated_by': user,
                    },
                )
                if is_created:
                    created += 1
                else:
                    updated += 1

        return Response({'created': created, 'updated': updated})
