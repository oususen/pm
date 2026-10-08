"""承認済みの分析コードのテンプレート保存・一覧・詳細(第3段階3-A)。

取得元は、本人のRedis分析案だけ。ブラウザから送られたコード・承認者は信用しない。
保存条件は、手順承認・データ承認・コード承認が済み、承認時のハッシュが再計算で一致し、現行の検査に合格すること。
AI・launcherは呼ばない。実データ・結果・AIへ送った本文は保存しない。
共有範囲は、作成者と管理者(settings.ai/edit)にだけ全文、他の利用者には名称・目的・状態・作成者・日時だけ。
"""
import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid4

from django.db import IntegrityError, transaction
from django.db.models import F, Max, Q
from rest_framework.exceptions import PermissionDenied

from ai.models import AIAnalysisTemplate
from ai.services.analysis_codegen_service import bundle_from_plan, steps_text, validate_generated
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.services.analysis_template_notify_service import schedule_submitted, serialize_records
from ai.services.analysis_template_params import check_source, concrete_code, has_date_literal, resolve_values, validate_definitions
from ai.services.chat_service import _has_resource_permission

DELETED_USER_LABEL = '削除済みユーザー'
# 通常の一覧で、作成者・管理者以外に見せない状態(却下・置換済みは再利用候補から除く)
HIDDEN_STATUSES = ('rejected', 'superseded')


def is_template_admin(user):
    """管理者確認の権限。判定できない場合は管理者として扱わない(例外文は外に出さない)。"""
    try:
        return bool(_has_resource_permission(user, 'settings.ai', 'edit'))
    except Exception:
        return False


def _content_sha256(fields):
    """承認対象全体のハッシュ。状態・通知・日時の保存時刻は含めない。DBのJSON表現に依存しない正規化JSONから計算する。"""
    material = {
        'name': fields['name'], 'purpose': fields['purpose'], 'procedure': fields['procedure'],
        'output_spec': fields['output_spec'], 'conditions': fields['conditions'], 'datasets': fields['datasets'],
        'date_from': fields['date_from'].isoformat(), 'date_to': fields['date_to'].isoformat(),
        'sql_steps': fields['sql_steps'], 'python_code': fields['python_code'],
        'wrapper_version': fields['wrapper_version'], 'executed_code_sha256': fields['executed_code_sha256'],
    }
    if fields.get('parameters'):
        material['parameters'] = fields['parameters']  # 変数がないテンプレートは、従来どおりのハッシュ(既存の行を変えない)
    return hashlib.sha256(json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _approved_at(plan, key):
    value = plan.get(key)
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise AnalysisError('承認日時を確認できません。分析案を最新の内容で承認し直してください。', 409) from None


def _date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise AnalysisError('分析案の期間を確認できません。', 409) from None


def _text(value, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise AnalysisError('分析案の内容を確認できません。分析案を作り直してください。', 409)
    return value


def _text_list(value):
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise AnalysisError('分析案の内容を確認できません。分析案を作り直してください。', 409)
    return value


def validate_template_name(name):
    """テンプレートの名称(利用者が入力する)。空・文字列以外・制御文字・列の上限(300文字)超は不可。前後の空白は除く(BOSS承認 2026-10-08)。"""
    if type(name) is not str:
        raise AnalysisError('テンプレート名を文字列で入力してください。')
    name = name.strip()
    if not name or any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise AnalysisError('テンプレート名を入力してください(改行・制御文字は使えません)。')
    if len(name) > AIAnalysisTemplate._meta.get_field('name').max_length:
        raise AnalysisError('テンプレート名が長すぎます(300文字以内)。')
    return name


def _fields_from_plan(plan, check_dates=True, name=None):
    """保存対象の列を、承認済みの分析案から組み立てる。保存できない状態・欠けた内容は、固定文で拒否する。"""
    if plan.get('status') != 'data_approved' or not plan.get('method_approved_at') or not plan.get('data_approved_at'):
        raise AnalysisError('手順とデータ範囲の承認後に保存してください。', 409)
    try:
        expires_at = plan.get('expires_at')
        expired = bool(expires_at) and datetime.fromisoformat(expires_at) <= datetime.now()
    except (TypeError, ValueError):
        raise AnalysisError('分析案の期限を確認できません。', 409) from None
    if expired:
        raise AnalysisError('分析案の期限が切れました。再作成してください。', 410)
    codegen = plan.get('codegen') or {}
    proposal = plan.get('proposal')
    if not isinstance(proposal, dict) or not isinstance(proposal.get('datasets'), list) or not all(
            isinstance(item, dict) and isinstance(item.get('view'), str) for item in proposal['datasets']):
        raise AnalysisError('分析案の内容を確認できません。分析案を作り直してください。', 409)
    # 承認時のコードから実行コード・ハッシュを再計算し、承認時の内容と一致しなければ保存しない
    try:
        bundle = bundle_from_plan(plan)
    except (KeyError, TypeError):
        raise AnalysisError('承認したコードを確認できません。コードを作り直してください。', 409) from None
    if validate_generated(bundle.steps, bundle.python, [d['view'] for d in proposal['datasets']]):
        raise AnalysisError('現在の検査に合格しないコードは保存できません。コードを作り直してください。', 409)
    sql_steps, python_code, parameters = bundle.steps, bundle.python, []
    source = codegen.get('template_source')
    if check_dates and source is None and has_date_literal(bundle.steps, bundle.python):
        # 変数を使っていないコードに、日付が直接書かれている: 期間を変えて再利用できないため、テンプレートにしない
        raise AnalysisError('コードに固定の日付が直接書かれているため、テンプレートとして保存できません。期間は変数({{period_from}}・{{period_to}})にして、コードを作り直してください。', 409)
    if source is not None:
        # 変数の形のコード: 定義・使用・直書きを確認し、既定値で置き換えた結果が、承認したコードと一致すること
        try:
            parameters = validate_definitions(source['parameters'])
            check_source(source['steps'], source['python'], parameters)
            steps_now, python_now = concrete_code(source['steps'], source['python'],
                                                  resolve_values(parameters, {}, outer=(proposal.get('date_from'), proposal.get('date_to'))))
        except (KeyError, TypeError, AttributeError):
            raise AnalysisError('変数の形のコードを確認できません。コードを作り直してください。', 409) from None
        defaults = {item['name']: item['default'] for item in parameters}
        if 'period_from' in defaults and (defaults['period_from'], defaults['period_to']) != (proposal.get('date_from'), proposal.get('date_to')):
            raise AnalysisError('期間の変数の元の値が、承認した分析期間と一致しません。コードを作り直してください。', 409)
        if steps_now != bundle.steps or python_now != bundle.python:
            raise AnalysisError('変数の形のコードと、承認したコードが一致しません。コードを作り直してください。', 409)
        sql_steps, python_code = source['steps'], source['python']
    name = validate_template_name(name) if name is not None else _text(proposal.get('title')).strip()  # 名称の指定がなければ、分析案の題名(従来どおり)
    if len(name) > AIAnalysisTemplate._meta.get_field('name').max_length:
        raise AnalysisError('名称が長すぎるため保存できません。分析案を作り直してください。', 409)
    fields = {
        'name': name, 'purpose': _text(proposal.get('purpose')), 'procedure': _text_list(proposal.get('steps')),
        'output_spec': _text_list(proposal.get('outputs')), 'conditions': _text(proposal.get('conditions', ''), allow_empty=True),
        'datasets': proposal['datasets'],
        'date_from': _date(proposal.get('date_from')), 'date_to': _date(proposal.get('date_to')),
        'sql_steps': sql_steps, 'python_code': python_code, 'parameters': parameters, 'wrapper_version': bundle.wrapper_version,
        'sql_sha256': bundle.sql_sha256, 'python_sha256': bundle.python_sha256,
        'executed_code_sha256': bundle.executed_code_sha256,
        'method_approved_at': _approved_at(plan, 'method_approved_at'),
        'data_approved_at': _approved_at(plan, 'data_approved_at'),
        'code_approved_at': _approved_at(codegen, 'code_approved_at'),
    }
    fields['content_sha256'] = _content_sha256(fields)
    return fields


def _find_existing(plan_id, revision, content_sha256):
    """同じ分析案の同じ版、または同じ内容(版が進んでいても)の保存済みの行。重複保存と同時要求の判定に使う。

    前提: 分析案の内容は版(revision)で決まる。通常は両条件が同じ行になるため、idの小さい方を返す。
    版を変えずに内容が変わる経路を足す場合は、この選び方を見直すこと(訂正版の保存は、呼び出し側のsame_requestで置き換え元の一致を確認する)。
    """
    return AIAnalysisTemplate.objects.filter(
        Q(source_plan_id=plan_id, source_plan_revision=revision) | Q(source_plan_id=plan_id, content_sha256=content_sha256),
    ).order_by('id').first()


def _check_correction_request(user, replaces):
    """訂正版の保存要求の形式と権限(管理者だけ)。保存済みの行の確認より先に行う。"""
    if type(replaces) is not int or replaces < 1:
        raise AnalysisError('置き換える版の指定が不正です。')
    if not is_template_admin(user):
        raise PermissionDenied('AIテンプレートの訂正版を保存する権限がありません。')


def _replaced_template(replaces, content_sha256):
    """訂正版の置き換え元。却下された版に対して、内容が違う場合だけ保存できる。"""
    old = AIAnalysisTemplate.objects.filter(pk=replaces).first()
    if old is None:
        raise AnalysisError('置き換える版が見つかりません。', 404)
    if old.status != 'rejected':
        raise AnalysisError('訂正版を保存できるのは、却下された版だけです。', 409)
    if old.content_sha256 == content_sha256:
        raise AnalysisError('却下された版と同じ内容は、訂正版として保存できません。', 409)
    return old


def validate_category(category):
    """カテゴリは固定の6つ(入荷・出荷・在庫・生産・品質・その他)。内容のハッシュには含めない(整理のための印)。"""
    if type(category) is not str or category not in dict(AIAnalysisTemplate.CATEGORY_CHOICES):
        raise AnalysisError('カテゴリを入荷・出荷・在庫・生産・品質・その他から選んでください。')
    return category


def save_template(user, plan_id, revision, replaces=None, category=None, name=None):
    """本人の承認済み分析案から保存する。(テンプレート, 新規作成か)を返す。同じ内容の再送は、既存の行を返す。

    replacesを指定すると、却下された版の訂正版(同じ系統の次の版)として保存する(管理者のみ)。
    """
    if type(revision) is not int or revision < 1:
        raise AnalysisError('分析案の版が不正です。')
    category = validate_category(category)
    plan = AnalysisPlanStore().get(str(plan_id), user.pk)
    if plan['revision'] != revision:
        raise AnalysisError('分析案が別の操作で更新されました。最新の内容を確認してください。', 409)
    if plan.get('template') is not None:
        # 保存済みのコードをそのまま使う分析案のため、保存すると同じ内容のテンプレートが重複する(元の分析案が違うだけ)。訂正版も同じ
        raise AnalysisError('テンプレートから作成した分析案は、テンプレートとして保存できません(内容が同じため重複します)。コードを変えた新しい分析を作成してください。', 409)
    fields = _fields_from_plan(plan, check_dates=False, name=name)  # 日付の直書きの確認は、既存の行を探した後に行う(再送は、既存の行を返す)
    if replaces is not None:
        _check_correction_request(user, replaces)
    key = {'source_plan_id': str(plan_id), 'source_plan_revision': revision}

    def same_request(row):
        # 同じ分析案の保存済みの行を返す。ただし訂正版として保存する要求が、別の保存(置き換えなし・別の置き換え元)に当たったら拒否する
        if replaces != row.replaces_id:
            raise AnalysisError('この分析案は、すでに別のテンプレートとして保存されています。', 409)
        return row, False

    # 保存済みの行の確認を先に行う: 訂正版の承認後(元が置換済み)の再送も、既存の行を返す
    existing = _find_existing(key['source_plan_id'], revision, fields['content_sha256'])
    if existing is not None:
        return same_request(existing)
    if not fields['parameters'] and has_date_literal(fields['sql_steps'], fields['python_code']):
        # 変数を使っていないコードに、日付が直接書かれている: 期間を変えて再利用できないため、新しいテンプレートにしない
        raise AnalysisError('コードに固定の日付が直接書かれているため、テンプレートとして保存できません。期間は変数({{period_from}}・{{period_to}})にして、コードを作り直してください。', 409)
    old = _replaced_template(replaces, fields['content_sha256']) if replaces is not None else None
    try:
        with transaction.atomic():
            if old is None:
                family_id, version = uuid4(), 1
            else:
                # 元の却下版をロックして、状態と「承認待ちの訂正版がすでにあるか」を確認する(同時の訂正版保存でも片方だけが成立する)。
                # 承認待ちの訂正版がある間は、次の訂正版を保存できない。先の訂正版を承認または却下してから保存する
                locked = AIAnalysisTemplate.objects.select_for_update().get(pk=old.pk)
                if locked.status != 'rejected':
                    raise AnalysisError('訂正版を保存できるのは、却下された版だけです。', 409)
                if AIAnalysisTemplate.objects.filter(replaces=locked, status='pending_admin').exists():
                    raise AnalysisError('この却下版には、承認待ちの訂正版がすでにあります。先に承認または却下してください。', 409)
                # 同じ系統の次の版。同時の訂正版は(family_id, version)の一意制約でも保護される
                family_id = old.family_id
                version = AIAnalysisTemplate.objects.filter(family_id=family_id).aggregate(top=Max('version'))['top'] + 1
            template = AIAnalysisTemplate.objects.create(
                family_id=family_id, version=version, approved_by=user, replaces=old, category=category, **key, **fields,
            )
    except IntegrityError:
        # 同時の保存要求に負けた場合は、先に成立した行を返す(別内容を作らない。見つからなければ固定文で拒否)
        existing = _find_existing(key['source_plan_id'], revision, fields['content_sha256'])
        if existing is None:
            raise AnalysisError('テンプレートを保存できませんでした。時間をおいて再度お試しください。', 409) from None
        return same_request(existing)
    schedule_submitted(template.pk)  # 状態の確定の後に、別スレッドでシステム管理者へ確認依頼のメールを送る(失敗しても保存は取り消さない)
    return template, True


def content_visible(template, user, admin):
    """全文(SQL・Python・手順・条件など)を見られるのは、正式のテンプレートなら分析権限を持つ全員。
    管理者承認前・却下・置換済みは、作成者と管理者だけ。"""
    return template.status == 'approved' or admin or (template.approved_by_id is not None and template.approved_by_id == user.pk)


def concrete_for(template, supplied=None):
    """保存されたコードを、実行する形(変数を確認済みの値へ置き換えた形)にする。(手順, Python, 値)を返す。変数がなければ、そのまま。"""
    if not template.parameters:
        if supplied:
            raise AnalysisError('このテンプレートには変数がありません。')
        return template.sql_steps, template.python_code, {}
    values = resolve_values(template.parameters, supplied or {}, outer=(template.date_from.isoformat(), template.date_to.isoformat()))
    steps, python = concrete_code(template.sql_steps, template.python_code, values)
    return steps, python, values


def _creator(template):
    return template.approved_by.get_username() if template.approved_by_id else DELETED_USER_LABEL


def serialize_template(template, user, admin, detail):
    visible = content_visible(template, user, admin)
    data = {
        'id': template.pk, 'family_id': str(template.family_id), 'version': template.version,
        'name': template.name, 'purpose': template.purpose, 'category': template.category, 'category_label': template.get_category_display(),
        'status': template.status, 'status_label': template.get_status_display(),
        'created_by': _creator(template), 'created_at': template.created_at.isoformat(),
        'content_visible': visible,
    }
    # 確認者・確認日時・却下理由・状態の版・置き換え関係は、正式でも作成者と管理者だけに返す(全文より狭い範囲)
    review_visible = admin or (template.approved_by_id is not None and template.approved_by_id == user.pk)
    if visible:
        if review_visible:
            data.update({'state_revision': template.state_revision, 'replaces': template.replaces_id})
        data.update({
            'date_from': template.date_from.isoformat(), 'date_to': template.date_to.isoformat(),
            'wrapper_version': template.wrapper_version, 'executed_code_sha256': template.executed_code_sha256,
            'content_sha256': template.content_sha256,
            'parameters': template.parameters,
        })
        if detail:
            # 却下理由・確認者は、作成者と管理者だけ(visibleと同じ範囲)に返す。置換先は、承認された訂正版
            replacement = template.corrections.filter(status='approved').order_by('id').first() if template.status == 'superseded' else None
            if review_visible:
                data['can_change_category'] = True  # 作成者と管理者は、カテゴリを後から変えられる
                data['can_rename'] = template.status == 'pending_admin'  # 名称は、管理者承認前だけ変えられる
                data['notifications'] = serialize_records(template)
                data.update({
                    'reviewed_by': (template.reviewed_by.get_username() if template.reviewed_by_id else DELETED_USER_LABEL) if template.reviewed_at else None,
                    'reviewed_at': template.reviewed_at.isoformat() if template.reviewed_at else None,
                    'rejection_reason': template.rejection_reason, 'replacement_id': replacement.pk if replacement else None,
                })
            data.update({
                'procedure': template.procedure, 'output_spec': template.output_spec, 'conditions': template.conditions,
                'datasets': template.datasets, 'sql_steps': template.sql_steps, 'python_code': template.python_code,
                'sql_sha256': template.sql_sha256, 'python_sha256': template.python_sha256,
                'method_approved_at': template.method_approved_at.isoformat(),
                'data_approved_at': template.data_approved_at.isoformat(),
                'code_approved_at': template.code_approved_at.isoformat(),
            })
    return data


def visible_templates(user, admin):
    """一覧の対象。却下・置換済みは、作成者と管理者だけに見せる。新しい順、同時刻はidの降順。"""
    queryset = AIAnalysisTemplate.objects.select_related('approved_by').order_by('-created_at', '-id')
    if admin:
        return queryset
    return queryset.filter(Q(approved_by=user) | ~Q(status__in=HIDDEN_STATUSES))


def get_visible_template(template_id, user, admin):
    template = visible_templates(user, admin).filter(pk=template_id).first()
    if template is None:
        raise AnalysisError('テンプレートが見つかりません。', 404)
    return template


def parse_plan_id(value):
    """UUID形式の文字列だけを受け付ける。"""
    if not isinstance(value, str):
        raise AnalysisError('分析案のIDが不正です。')
    try:
        return str(UUID(value))
    except ValueError:
        raise AnalysisError('分析案のIDが不正です。') from None


def same_name_count(user, admin, name, exclude_id=None):
    """同じ名称のテンプレートの件数。利用者が見える範囲だけを数える(見えないテンプレートの名前の存在を、漏らさない)。"""
    rows = visible_templates(user, admin).filter(name=validate_template_name(name))
    return (rows.exclude(pk=exclude_id) if exclude_id is not None else rows).count()


def rename_template(user, template_id, name, admin):
    """作成者と管理者が、管理者承認前(pending_admin)のテンプレートの名称を変える。名称は承認対象のハッシュに入るため、ハッシュを計算し直す。

    状態の版(state_revision)を進める(管理者が古い内容を見たまま承認する、という事故を、409で防ぐ)。承認後・却下・置換済みは変えられない(409)。
    """
    name = validate_template_name(name)
    with transaction.atomic():
        template = AIAnalysisTemplate.objects.select_for_update().filter(pk=template_id).first()
        if template is None or not (admin or (template.approved_by_id is not None and template.approved_by_id == user.pk)):
            raise AnalysisError('テンプレートが見つかりません。', 404)
        if template.status != 'pending_admin':
            raise AnalysisError('名称を変えられるのは、管理者承認前のテンプレートだけです。', 409)
        template.name = name
        new_hash = _content_sha256({
            'name': template.name, 'purpose': template.purpose, 'procedure': template.procedure, 'output_spec': template.output_spec,
            'conditions': template.conditions, 'datasets': template.datasets, 'date_from': template.date_from, 'date_to': template.date_to,
            'sql_steps': template.sql_steps, 'python_code': template.python_code, 'wrapper_version': template.wrapper_version,
            'executed_code_sha256': template.executed_code_sha256, 'parameters': template.parameters,
        })
        AIAnalysisTemplate.objects.filter(pk=template.pk).update(
            name=name, content_sha256=new_hash, state_revision=F('state_revision') + 1, updated_at=datetime.now())
    template.refresh_from_db()
    return template


def change_category(user, template_id, category, admin):
    """作成者と管理者が、カテゴリを後から変える。内容・ハッシュ・状態・状態の版は変えない(整理のための印)。それ以外には存在も見せない(404)。"""
    category = validate_category(category)
    template = AIAnalysisTemplate.objects.select_related('approved_by').filter(pk=template_id).first()
    if template is None or not (admin or (template.approved_by_id is not None and template.approved_by_id == user.pk)):
        raise AnalysisError('テンプレートが見つかりません。', 404)
    AIAnalysisTemplate.objects.filter(pk=template.pk).update(category=category, updated_at=datetime.now())
    template.refresh_from_db()
    return template
