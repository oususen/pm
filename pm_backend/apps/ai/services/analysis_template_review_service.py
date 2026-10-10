"""テンプレートの管理者による承認・却下(第3段階3-B)。

権限(settings.ai / can_edit)はビューで判定する。ここでは、状態・版・内容ハッシュを照合し、
DBの条件付き更新だけで状態を変える(競合した操作は成立させない)。メール・PM通知は3-Cで扱い、ここでは行わない。
訂正版の承認は、元の却下版の置換済みへの変更と同じトランザクションで確定する。
"""
from datetime import datetime

from django.db import transaction
from django.db.models import F

from ai.models import AIAnalysisTemplate
from ai.services.analysis_codegen_service import make_bundle, validate_generated
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_template_notify_service import schedule_result
from ai.services.analysis_template_params import _check_value
from ai.services.analysis_template_service import _content_sha256, concrete_for

REJECTION_REASON_MAX = 500  # BOSS承認(2026-10-05)。超えた場合は切り詰めず拒否する


def _target(template_id, state_revision):
    if type(state_revision) is not int or state_revision < 1:
        raise AnalysisError('状態の版が不正です。')
    template = AIAnalysisTemplate.objects.select_related('approved_by').filter(pk=template_id).first()
    if template is None:
        raise AnalysisError('テンプレートが見つかりません。', 404)
    if template.status != 'pending_admin' or template.state_revision != state_revision:
        raise AnalysisError('テンプレートの状態が変わりました。最新の内容を確認してください。', 409)
    return template


def _stored_hash(template):
    """保存された行を読み戻した値から、承認対象のハッシュを再計算する。"""
    return _content_sha256({
        'name': template.name, 'purpose': template.purpose, 'procedure': template.procedure, 'output_spec': template.output_spec,
        'conditions': template.conditions, 'datasets': template.datasets, 'date_from': template.date_from, 'date_to': template.date_to,
        'sql_steps': template.sql_steps, 'python_code': template.python_code, 'wrapper_version': template.wrapper_version,
        'executed_code_sha256': template.executed_code_sha256, 'parameters': template.parameters,
    })


NORMALIZED_MESSAGE = '保存時の表記と現在のマスタ表記が異なります。新しい分析として作り直し、試行・承認してください。'


def _normalization_changed(template):
    """保存済みの変数の default(コード系)を、現在のマスタの表記へ直すと、保存された default と異なるか。異なれば、ハッシュ不一致の原因は表記の正規化。

    DBの読み取りと既存の _check_value の再利用だけ。確認できない(登録なし・曖昧・形式不正など)場合は、原因を確認できたとは扱わない。
    """
    for item in template.parameters or []:
        try:
            if item['type'] != 'date' and _check_value(item['type'], item['default'], item['name']) != item['default']:
                return True
        except (AnalysisError, KeyError, TypeError):
            continue
    return False


def hash_mismatch_error(template, message):
    """保存済みのSQL・Pythonのハッシュ不一致の409。原因が表記の正規化と確認できたときだけ専用の文言にし、それ以外は渡された文言のまま。"""
    return AnalysisError(NORMALIZED_MESSAGE if _normalization_changed(template) else message, 409)


def _conditional_update(template, new_status, **extra):
    """期待する状態・版のときだけ更新する。1行でなければ競合として拒否する(呼び出し元のトランザクションを巻き戻す)。"""
    now = datetime.now()
    updated = AIAnalysisTemplate.objects.filter(
        pk=template.pk, status='pending_admin', state_revision=template.state_revision,
    ).update(status=new_status, state_revision=F('state_revision') + 1, updated_at=now, **extra)
    if updated != 1:
        raise AnalysisError('テンプレートの状態が変わりました。最新の内容を確認してください。', 409)
    return now


def approve_template(admin, template_id, state_revision):
    """管理者承認待ちを正式にする。訂正版なら、元の却下版を、同じトランザクションで置換済みにする。"""
    template = _target(template_id, state_revision)
    if _stored_hash(template) != template.content_sha256:
        raise AnalysisError('保存内容のハッシュが一致しないため承認できません。管理者へ確認してください。', 409)
    # 保存後に検査規則が強化された場合でも、旧コードを正式にしない。外枠の版の古さは承認時には拒否しない(再利用時の更新・確認は3-D)
    try:
        views = [d['view'] for d in template.datasets]
        steps, python, _values = concrete_for(template)  # 変数があれば、元の値で置き換えた、実行する形を検査する
        problems = validate_generated(steps, python, views)
    except (KeyError, TypeError, AttributeError, ValueError):
        problems = ['unreadable']
    if problems:
        raise AnalysisError('現在の検査に合格しないコードは承認できません。却下して、コードを作り直してください。', 409)
    # 再利用と同じ照合: 保存済みの default で組み立て直したコードが、保存済みのSQL・Pythonのハッシュと一致すること(一致しないものを正式にして、再利用できない状態にしない)
    bundle = make_bundle(steps, python, views)
    if bundle.sql_sha256 != template.sql_sha256 or bundle.python_sha256 != template.python_sha256:
        raise hash_mismatch_error(template, '保存されたSQL・Pythonのハッシュが一致しないため承認できません。却下して、コードを作り直してください。')
    with transaction.atomic():
        now = _conditional_update(template, 'approved', reviewed_by=admin, reviewed_at=datetime.now())
        if template.replaces_id:
            replaced = AIAnalysisTemplate.objects.filter(pk=template.replaces_id, status='rejected').update(
                status='superseded', state_revision=F('state_revision') + 1, updated_at=now,
            )
            if replaced != 1:
                raise AnalysisError('置き換える却下版の状態が変わったため、承認できません。', 409)
    # 確定の後に、作成者へ結果を通知する(メール・PM通知。失敗しても承認は取り消さない)。訂正版の承認では、置き換えられた元の版の作成者にも通知する
    schedule_result(template.pk, 'approved', admin.pk)
    if template.replaces_id:
        schedule_result(template.replaces_id, 'superseded', admin.pk, template.pk)
    return AIAnalysisTemplate.objects.select_related('approved_by', 'reviewed_by').get(pk=template.pk)


def reject_template(admin, template_id, state_revision, reason):
    """管理者承認待ちを却下する。却下理由は必須。理由は作成者と管理者だけが閲覧できる。"""
    if not isinstance(reason, str) or not reason.strip():
        raise AnalysisError('却下理由を入力してください。')
    reason = reason.strip()
    if len(reason) > REJECTION_REASON_MAX:
        raise AnalysisError(f'却下理由は{REJECTION_REASON_MAX}文字以内で入力してください。')
    template = _target(template_id, state_revision)
    with transaction.atomic():
        _conditional_update(template, 'rejected', reviewed_by=admin, reviewed_at=datetime.now(), rejection_reason=reason)
    schedule_result(template.pk, 'rejected', admin.pk)
    return AIAnalysisTemplate.objects.select_related('approved_by', 'reviewed_by').get(pk=template.pk)
