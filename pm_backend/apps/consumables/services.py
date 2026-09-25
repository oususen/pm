"""消耗品管理の共通処理"""
import csv
import io
import re
from datetime import datetime, time, timedelta

from .models import ConsumableRequest


def display_user_name(user):
    """ユーザーの表示名（姓 名。未設定ならログインID）"""
    if not user:
        return ''
    full_name = f'{user.last_name} {user.first_name}'.strip()
    return full_name or user.username


def org_snapshot(user):
    """ユーザーの事業部・係・班・グループ名を返す。各階層は独立して取得する（班→係を辿らない）"""
    names = {'division_name': '', 'group_name': '', 'team_name': '', 'unit_name': ''}
    profile = getattr(user, 'profile', None) if user else None
    if not profile:
        return names
    for field in ('division', 'group', 'team', 'unit'):
        department = getattr(profile, field, None)
        if department:
            names[f'{field}_name'] = department.name
    return names


def open_request_status_map(consumable_ids=None):
    """消耗品ID → 未完了依頼のうち最も進んだ状態。注文状態を保存せず依頼から導出する"""
    qs = ConsumableRequest.objects.filter(status__in=ConsumableRequest.OPEN_STATUSES)
    if consumable_ids is not None:
        qs = qs.filter(consumable_id__in=consumable_ids)
    rank = {status: i for i, status in enumerate(ConsumableRequest.OPEN_STATUSES)}
    result = {}
    for consumable_id, status in qs.values_list('consumable_id', 'status'):
        current = result.get(consumable_id)
        if current is None or rank[status] > rank[current]:
            result[consumable_id] = status
    return result


def business_day_range(date_from, date_to):
    """業務日（日替わり8時）の期間を実日時の範囲 [開始, 終了) に変換する"""
    start = datetime.combine(date_from, time(8, 0)) if date_from else None
    end = datetime.combine(date_to + timedelta(days=1), time(8, 0)) if date_to else None
    return start, end


def normalize_qr_code_value(raw_value):
    """
    QR文字列を検索用の消耗品コードに正規化する（syomohin から移植）。
    既存の貼付ラベルには次の書式が混在しているため、すべてに対応する。
    - 「管理番号：<コード> 品名：...」
    - 「code=<コード>name=...」（区切り不備を含む）
    - 「6 MASINA-00178 日東 ...」のように先頭に不要文字がある1行ラベル
    """
    if not raw_value:
        return ''
    value = raw_value.strip()

    match = re.search(r'管理番号\s*[：:]\s*(.*?)\s*品名', value, flags=re.DOTALL)
    if match:
        return re.sub(r'\s+', '', match.group(1).strip())

    match = re.search(r'code\s*[=＝]\s*(.+?)(?:name\s*[=＝]|$)', value, flags=re.IGNORECASE | re.DOTALL)
    if match:
        extracted = re.sub(r'\s+', '', match.group(1).strip())
        if extracted:
            return extracted

    # 英字と数字を両方含むトークンをコードとして優先採用する
    tokens = [t.strip('.,;:：') for t in re.split(r'\s+', value) if t.strip()]
    for token in tokens:
        if re.search(r'[A-Za-z]', token) and re.search(r'\d', token):
            return token
    if tokens:
        return tokens[0]
    return re.sub(r'\s+', '', value)


# CSV列名 → モデル項目（syomohin の CSV_FIELD_ALIASES を移植）
CONSUMABLE_CSV_ALIASES = {
    'code': 'code', 'コード': 'code', '品目コード': 'code',
    'order_code': 'order_code', '注文コード': 'order_code', '発注コード': 'order_code',
    'name': 'name', '品名': 'name',
    'category': 'category', 'カテゴリ': 'category',
    'unit': 'unit', '単位': 'unit',
    'stock_quantity': 'stock_quantity', '在庫数': 'stock_quantity',
    'safety_stock': 'safety_stock', '安全在庫': 'safety_stock',
    'unit_price': 'unit_price', '単価': 'unit_price',
    'order_unit': 'order_unit', '発注単位': 'order_unit',
    'supplier': 'supplier_name', 'supplier_name': 'supplier_name', '仕入先': 'supplier_name', '購入先': 'supplier_name',
    'storage_location': 'storage_location', '保管場所': 'storage_location',
    'note': 'note', '備考': 'note',
    'image_path': 'image_file', '画像パス': 'image_file', '画像URL': 'image_file', '画像ファイル': 'image_file',
}

SUPPLIER_CSV_ALIASES = {
    'name': 'name', '名称': 'name', '購入先名': 'name', '購入先': 'name',
    'contact_person': 'contact_person', '担当者': 'contact_person',
    'phone': 'phone', '電話番号': 'phone',
    'email': 'email', 'メールアドレス': 'email',
    'address': 'address', '住所': 'address',
    'note': 'note', '備考': 'note',
}


def read_csv_rows(uploaded_file, aliases):
    """アップロードCSVを読み、列名を正規化した dict のリストを返す（UTF-8 BOM / CP932 対応）"""
    raw = uploaded_file.read()
    for encoding in ('utf-8-sig', 'cp932'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('CSVの文字コードを判別できません（UTF-8 または Shift_JIS で保存してください）')

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for raw_row in reader:
        row = {}
        for key, value in raw_row.items():
            field = aliases.get((key or '').strip())
            if field:
                row[field] = (value or '').strip()
        if any(row.values()):
            rows.append(row)
    return rows
