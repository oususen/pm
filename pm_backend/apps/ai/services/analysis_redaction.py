"""分析目的の登録済み名称を実コードへ置換する。検索AIの一時ID方式とは分離する。"""
import re

from django.contrib.auth import get_user_model

from masters.models import Customer, Supplier
from production.models_process_realtime import ProcessRealtimeRecord
from ai.services.analysis_plan_store import AnalysisError
from ai.services.query_common import AI_DB_ALIAS


class AnalysisCodeRedactor:
    def __init__(self):
        self.codes = {}

    def add(self, name, code):
        name = str(name or '').strip()
        code = str(code or '').strip() or None
        if name:
            self.codes.setdefault(name, set()).add(code)

    def redact_text(self, text, keep=(), collect=None):
        """登録名称を、コードへ置換する。

        collect: 置換で入れたコードを集める集合。keep: そのまま残す文字列(今回の送信で、置換が入れたコード)。
        keepは、AIの返事の中のコードを、再置換しないために使う(登録名称とコードが衝突しても、同じ対象のコードが変わらない)。
        keepにない名称は、返事の中でも、置換する(置換できなければ、拒否する)。
        """
        keep = {item for item in keep if item}
        table = {**self.codes, **{item: {item} for item in keep}} if keep else self.codes  # keepは、同じ文字列へ(衝突した名称より優先)

        def replace(match):
            codes = table[match.group()]
            if None in codes or len(codes) != 1:
                raise AnalysisError('目的文の名称に対応するコードが未登録、または同名で特定できません。目的を登録コードで書き直してください。外部AIへは送信していません。')
            code = next(iter(codes))
            if collect is not None:
                collect.add(code)
            return code

        # 一度だけ置換し、生成したコードを別の名称として再置換しない。
        if table:
            pattern = '|'.join(re.escape(name) for name in sorted(table, key=len, reverse=True))
            text = re.sub(pattern, replace, text)
        return re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', '[メールアドレス]', text)


def build_analysis_code_redactor():
    """有効・無効を問わず取得する。対応表はリクエスト内だけで保持し、DBへ保存しない。"""
    redactor = AnalysisCodeRedactor()
    users = get_user_model().objects.using(AI_DB_ALIAS).values(
        'username', 'first_name', 'last_name', 'profile__employee_code',
    )
    for user in users:
        code = user['profile__employee_code']
        redactor.add(user['username'], code)
        for separator in ('', ' ', '\u3000'):
            redactor.add(separator.join(filter(None, (user['last_name'], user['first_name']))), code)

    # 自由入力された実績作業者名も、登録ユーザーへ解決できなければ送信を止める。
    user_codes = {}
    for name, codes in redactor.codes.items():
        user_codes.setdefault(re.sub(r'\s+', '', name), set()).update(codes)
    for name in ProcessRealtimeRecord.objects.using(AI_DB_ALIAS).exclude(
        operator_name__isnull=True,
    ).exclude(operator_name='').values_list('operator_name', flat=True).distinct():
        codes = user_codes.get(re.sub(r'\s+', '', name), {None})
        for code in codes:
            redactor.add(name, code)

    for customer in Customer.objects.using(AI_DB_ALIAS).values('customer_name', 'short_name', 'customer_code'):
        redactor.add(customer['customer_name'], customer['customer_code'])
        redactor.add(customer['short_name'], customer['customer_code'])
    for supplier in Supplier.objects.using(AI_DB_ALIAS).values('supplier_name', 'supplier_code'):
        redactor.add(supplier['supplier_name'], supplier['supplier_code'])
    return redactor
