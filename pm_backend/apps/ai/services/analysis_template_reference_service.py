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
