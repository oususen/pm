"""テンプレートの管理者による承認・却下(第3段階3-B)。

権限(settings.ai / can_edit)はビューで判定する。ここでは、状態・版・内容ハッシュを照合し、
DBの条件付き更新だけで状態を変える(競合した操作は成立させない)。メール・PM通知は3-Cで扱い、ここでは行わない。
訂正版の承認は、元の却下版の置換済みへの変更と同じトランザクションで確定する。
"""
from datetime import datetime

from django.db import transaction
from django.db.models import F

from ai.models import AIAnalysisTemplate
from ai.services.analysis_codegen_service import validate_generated
from ai.services.analysis_plan_store import AnalysisError
from ai.services.analysis_template_service import _content_sha256

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
        'executed_code_sha256': template.executed_code_sha256,
    })


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
        problems = validate_generated(template.sql_steps, template.python_code, [d['view'] for d in template.datasets])
    except (KeyError, TypeError, AttributeError, ValueError):
        problems = ['unreadable']
    if problems:
        raise AnalysisError('現在の検査に合格しないコードは承認できません。却下して、コードを作り直してください。', 409)
    with transaction.atomic():
        now = _conditional_update(template, 'approved', reviewed_by=admin, reviewed_at=datetime.now())
        if template.replaces_id:
            replaced = AIAnalysisTemplate.objects.filter(pk=template.replaces_id, status='rejected').update(
                status='superseded', state_revision=F('state_revision') + 1, updated_at=now,
            )
            if replaced != 1:
                raise AnalysisError('置き換える却下版の状態が変わったため、承認できません。', 409)
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
    return AIAnalysisTemplate.objects.select_related('approved_by', 'reviewed_by').get(pk=template.pk)
