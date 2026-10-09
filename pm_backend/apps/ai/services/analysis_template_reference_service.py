"""テンプレートを参考にした生成(BOSS承認 2026-10-09)。

保存済みテンプレート(承認済み・管理者承認待ち)を、AIへ見せる「参考資料」にする。参考にしても、承認は引き継がない。元のテンプレートは変更しない。
参考にできるのは、本人が全文を見られるテンプレートだけ(正式=分析権限のある全員、管理者承認待ち=作成者と管理者。却下・置換済みは不可)。
ここでは、参考にできるかの判定・AIへ渡す内容の組み立て・外部AIへ送る前の置換・分析案へ残す記録だけを扱う(DBへの書き込みはしない)。
再利用(保存済みコードをそのまま使う)の判定・照合を、そのまま使う。
"""
from django.contrib.auth import get_user_model
from django.db import DatabaseError

from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_redaction import build_analysis_code_redactor
from ai.services import analysis_template_params as template_params
from ai.services.analysis_template_params import PLACEHOLDER_PATTERN
from ai.services.analysis_template_reuse_service import REUSABLE_STATUSES, can_reuse
from ai.services.analysis_template_review_service import _stored_hash
from ai.services.analysis_template_service import get_visible_template, is_template_admin


def load_reference(owner_id, template_id):
    """参考にするテンプレートを、権限・状態・保存内容の整合を確認して返す。確認できなければ、参考なしで続けず、停止する。"""
    if type(template_id) is not int or template_id < 1:
        raise AnalysisError('参考にするテンプレートの指定が不正です。')
    user = get_user_model().objects.filter(pk=owner_id).first()
    if user is None:
        raise AnalysisError('テンプレートが見つかりません。', 404)
    admin = is_template_admin(user)
    template = get_visible_template(template_id, user, admin)  # 見えないテンプレートは、存在しないものとして404
    if template.status not in REUSABLE_STATUSES:
        raise AnalysisError('却下または置換済みのテンプレートは、参考にできません。', 409)
    if not can_reuse(template, user, admin):
        raise AnalysisError('管理者承認前のテンプレートを参考にできるのは、作成者と管理者だけです。', 403)
    if _stored_hash(template) != template.content_sha256:
        raise AnalysisError('保存内容のハッシュが一致しないため、参考にできません。管理者へ確認してください。', 409)
    return template


def plan_payload(template):
    """分析案の作成でAIへ渡す参考の内容(置換前)。コード(SQL・Python)・却下理由・確認者などは含めない(コードは、コード生成の段階で渡す)。"""
    return {
        'name': template.name, 'purpose': template.purpose, 'steps': list(template.procedure), 'outputs': list(template.output_spec),
        'conditions': template.conditions,
        'datasets': [{'view': item['view'], 'fields': list(item['fields'])} for item in template.datasets],
        'date_from': template.date_from.isoformat(), 'date_to': template.date_to.isoformat(),
    }


def code_payload(template):
    """コード生成でAIへ渡す参考の内容(置換前)。分析案の作成の内容に、変数の形のSQL・Python・変数の定義を足す。

    保存されているSQL・Pythonは、変数の形(`{{名前}}`)のまま。置換済みの実行用コードは使わない。
    """
    return {
        **plan_payload(template),
        'sql_steps': [{'name': step['name'], 'query': step['query']} for step in template.sql_steps],
        'python_code': template.python_code,
        'parameters': [{'name': item['name'], 'type': item['type'], 'label': item['label'], 'default': item['default']} for item in (template.parameters or [])],
    }


class _IdentifierMismatch(Exception):
    """識別子(変数名・手順名)が置換で変わる、または、置換後のコードと変数の定義が一致しない(固定の文で停止するための内部の印)。"""


def redact_code_payload(payload):
    """コード生成で外部AIへ送る前に、登録名称をコードへ置換する(分析案の作成の内容に加え、SQL・Python・変数のラベル・既定値)。置換できなければ、停止して送らない。

    識別子(変数名・手順名)は、置換しない。登録名称と衝突して、置換で変わるなら、コード本文だけが置換されて、変数の定義と食い違うため、停止する。
    置換の後に、コードの{{名前}}が、変数の定義と一致していることも確認する(別のレビューの指摘 P2)。
    """
    converted = redact_payload(payload)
    try:
        redact = build_analysis_code_redactor().redact_text
        for identifier in [item['name'] for item in payload['parameters']] + [step['name'] for step in payload['sql_steps']]:
            if redact(identifier) != identifier:
                raise _IdentifierMismatch()
        result = {
            **converted,
            'sql_steps': [{'name': step['name'], 'query': redact(step['query'])} for step in payload['sql_steps']],
            'python_code': redact(payload['python_code']),
            'parameters': [{**item, 'label': redact(item['label']), 'default': redact(item['default']) if isinstance(item['default'], str) else item['default']}
                           for item in payload['parameters']],
        }
        used = set()
        for text in [step['query'] for step in result['sql_steps']] + [result['python_code']]:
            used.update(PLACEHOLDER_PATTERN.findall(text))
        if used != {item['name'] for item in payload['parameters']}:
            raise _IdentifierMismatch()
        return result
    except _IdentifierMismatch:
        raise AnalysisError('参考にするテンプレートの変数名・手順名が、登録名称と衝突しているため、置換の後に、コードと変数の定義が一致しません。'
                            '別のテンプレートを選ぶか、参考なしで作成してください。外部AIへは送信していません。', 409) from None
    except AnalysisError as exc:
        raise AnalysisError('参考にするテンプレートのコードに、置換できない名称(登録コードが未登録、または同名で特定できない名称)が含まれています。'
                            '別のテンプレートを選ぶか、参考なしで作成してください。外部AIへは送信していません。', 409) from exc
    except DatabaseError as exc:
        raise AnalysisError('コード置換に必要な識別子を取得できませんでした。外部AIへは送信していません。', 503) from exc


def verify_plan_reference(owner_id, plan):
    """分析案に残した参考が、いまも使えること(権限・状態・保存内容)と、分析案の作成のときと同じ版・内容であることを、毎回確認して、テンプレートを返す。

    参考のない分析案は、Noneを返す。却下・置換・権限喪失・内容の変更(名称の変更を含む)は、停止する。参考なしでは続けない。
    """
    recorded = plan.get('template_reference')
    if recorded is None:
        return None
    template = load_reference(owner_id, recorded['id'])
    if template.version != recorded['version'] or template.content_sha256 != recorded['content_sha256']:
        raise AnalysisError('参考にしたテンプレートが変更されました。分析案を作り直してください。外部AIへは送信していません。', 409)
    return template


def stale_value_warnings(template, current_texts, proposal_texts):
    """参考のテンプレートにある値(品番・顧客コードなどの数字を含む値と、日付)が、今回の目的・期間にないのに、AIが作った分析案の手順・出力案に入っていれば、警告の文を返す。

    機械的な文字列の確認だけ(DBは見ない)。警告だけで、承認は妨げない(2026-10-09、BOSS指摘: 参考の品番が、今回の分析案へ入る恐れ)。
    """
    pattern = template_params.COPY_TOKEN_PATTERN
    def values(texts):
        return {token for token in pattern.findall(' '.join(str(text) for text in texts))
                if any(char.isdigit() for char in token)}
    reference = values([template.purpose, *template.procedure, *template.output_spec, template.conditions])
    stale = sorted(token for token in reference - values(current_texts) if any(token in str(text) for text in proposal_texts))
    if not stale:
        return []
    return [f"参考のテンプレートにある値（{'、'.join(stale)}）が、分析案の手順・出力案に入っています。今回の目的の値でない場合は、"
            '次の操作: 画面右下の「目的・期間を変更して作り直す」を押し、目的に、今回の値をはっきり書いて、分析案を作り直してください。']


def literal_texts(template):
    """コードに直接書かれていないかを確かめる値の元(参考の目的・手順・出力案・変数の既定値)。"""
    texts = [template.purpose, *template.procedure, *template.output_spec]
    texts += [item['default'] for item in (template.parameters or []) if isinstance(item.get('default'), str)]
    return texts


def redact_payload(payload):
    """外部AIへ送る前に、登録名称をコードへ置換する。置換できない名称(同名・未登録)があれば、AnalysisErrorで止まり、送らない。"""
    try:
        redactor = build_analysis_code_redactor()
        redact = redactor.redact_text
        return {
            **payload, 'name': redact(payload['name']), 'purpose': redact(payload['purpose']),
            'steps': [redact(text) for text in payload['steps']], 'outputs': [redact(text) for text in payload['outputs']],
            'conditions': redact(payload['conditions']),
        }
    except AnalysisError as exc:
        # 置換できない名称は、利用者が直せる目的文ではなく、参考にするテンプレートの文にある(テンプレートは、版ごとに不変)。目的の書き直しを案内しない
        raise AnalysisError('参考にするテンプレートの文に、置換できない名称(登録コードが未登録、または同名で特定できない名称)が含まれています。'
                            '別のテンプレートを選ぶか、参考なしで作成してください。外部AIへは送信していません。', 409) from exc
    except DatabaseError as exc:
        raise AnalysisError('コード置換に必要な識別子を取得できませんでした。外部AIへは送信していません。', 503) from exc


def record(template):
    """分析案へ残す記録。参考にしたテンプレートの識別だけ(本文は残さない)。`plan['template']`(再利用の目印)とは別のキーで保存する。"""
    return {'id': template.pk, 'version': template.version, 'content_sha256': template.content_sha256, 'name': template.name,
            'status': template.status}


def confirmation_part(template, converted_payload):
    """外部AIへ送る確認コードに含める、参考の識別と、置換後の内容(名称の変更・内容の変更で、確認が無効になる)。"""
    return [template.pk, template.version, template.content_sha256, converted_payload]
