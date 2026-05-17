import csv
import io
from datetime import datetime

from outsource.models import OutsourceOrder, OutsourceItem


def import_fb_csv(file_content, encoding='utf-8-sig'):
    """
    FB受注CSVを取り込み、案件（OutsourceOrder）を生成する。

    CSVフォーマット:
        品目コード,品目名称,塗装名,塗装日,数量

    戻り値: { 'created': [...], 'skipped': [...], 'errors': [...] }
    """
    results = {'created': [], 'skipped': [], 'errors': []}

    if isinstance(file_content, bytes):
        # BOM付きUTF-8を自動検出
        if file_content.startswith(b'\xef\xbb\xbf'):
            text = file_content.decode('utf-8-sig')
        else:
            try:
                text = file_content.decode(encoding)
            except UnicodeDecodeError:
                text = file_content.decode('utf-8-sig')
    else:
        text = file_content

    reader = csv.DictReader(io.StringIO(text))

    for row_num, row in enumerate(reader, start=2):
        try:
            item_code = row.get('品目コード', '').strip()
            item_name = row.get('品目名称', '').strip()
            painting_name = row.get('塗装名', '').strip()
            painting_date_str = row.get('塗装日', '').strip()
            qty_str = row.get('数量', '').strip()

            if not all([item_code, item_name, painting_date_str, qty_str]):
                results['errors'].append({
                    'row': row_num,
                    'message': '必須項目が不足しています',
                    'data': row,
                })
                continue

            painting_date = datetime.strptime(painting_date_str, '%Y/%m/%d').date()
            order_qty = int(qty_str)

            # 案件番号 = 塗装日(YYYYMMDD) + 品目コード
            case_no = f"{painting_date.strftime('%Y%m%d')}-{item_code}"

            # 重複チェック
            if OutsourceOrder.objects.filter(case_no=case_no).exists():
                results['skipped'].append({
                    'row': row_num,
                    'case_no': case_no,
                    'message': '既に登録済み',
                })
                continue

            # 品目マスタとの紐付け（任意）
            item = OutsourceItem.objects.filter(item_code=item_code).first()

            order = OutsourceOrder.objects.create(
                case_no=case_no,
                item=item,
                item_code=item_code,
                item_name=item_name,
                order_qty=order_qty,
                painting_name=painting_name,
                painting_date=painting_date,
                status='IMPORTED',
            )

            # 受注取込時点では制約日を計算しない
            # （材料発注前のため、最早着手日は確定値として扱わない）

            results['created'].append({
                'row': row_num,
                'case_no': case_no,
                'item_code': item_code,
                'item_name': item_name,
                'qty': order_qty,
            })

        except Exception as e:
            results['errors'].append({
                'row': row_num,
                'message': f'{type(e).__name__}: {e}',
                'data': row,
            })

    return results
