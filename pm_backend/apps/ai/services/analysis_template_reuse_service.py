"""テンプレートの再利用(第3段階3-D): 保存済みテンプレートから、新しい分析案を作り、実行の受付・開始前に状態を照合する。

AI・launcherは呼ばない。過去の承認・件数・結果・送信確認は持ち込まない(本人を所有者とする新しいRedis分析案を作る)。
再利用できる範囲(BOSS承認 2026-10-05): 正式=分析権限を持つ全員、管理者承認待ち=作成者と管理者だけ(実行前に明示の確認が必要)、却下・置換済み=不可。
外枠が古い場合も、現行の外枠でコードを組み立て、現行の検査に合格すれば再利用できる(試行とコード承認は取り直す)。
"""
from ai.config.service import get_analysis_execution_policy
from ai.models import AIAnalysisTemplate
from ai.services.analysis_codegen_service import make_bundle, validate_generated
from ai.services.analysis_data_service import validate_datasets
from ai.services.analysis_plan_store import AnalysisError, AnalysisPlanStore
from ai.services.analysis_template_review_service import _stored_hash, hash_mismatch_error
from ai.services.analysis_template_params import PERIOD_FROM, PERIOD_TO
from ai.services.analysis_template_service import concrete_for, get_visible_template, is_template_admin

REUSABLE_STATUSES = ('approved', 'pending_admin')


class TemplateUnavailable(AnalysisError):
    """テンプレートが再利用できない状態(却下・置換済み・内容の不一致・権限の喪失)。実行を開始しない。"""
    reason = 'template_unavailable'

    def __init__(self, message='テンプレートが再利用できない状態です。'):
        super().__init__(message, 409)


def can_reuse(template, user, admin):
    """正式は全員。管理者承認待ちは、作成者と管理者だけ(全文を見られる人だけが再利用できる)。"""
    if template.status == 'approved':
        return True
    if template.status == 'pending_admin':
        return admin or (template.approved_by_id is not None and template.approved_by_id == user.pk)
    return False


def _verified_bundle(template, supplied=None):
    """保存内容を再検証して、現行の外枠でコードを組み立てる。(コード一式, 変数の値)を返す。

    まず、保存時の値(変数の既定値)で組み立てた、承認済みのコードのハッシュが一致すること(保存内容が壊れていない)を確認する。
    値が指定されたら、その値で組み立て直したコードを、現行の検査に通す(コード承認は、毎回取り直す)。
    """
    if _stored_hash(template) != template.content_sha256:
        raise AnalysisError('保存内容のハッシュが一致しないため再利用できません。管理者へ確認してください。', 409)
    views = [dataset['view'] for dataset in template.datasets]
    steps, python, values = concrete_for(template)
    if validate_generated(steps, python, views):
        raise AnalysisError('現在の検査に合格しないコードは再利用できません。新しい分析として作り直してください。', 409)
    bundle = make_bundle(steps, python, views)
    if bundle.sql_sha256 != template.sql_sha256 or bundle.python_sha256 != template.python_sha256:
        raise hash_mismatch_error(template, '保存されたSQL・Pythonのハッシュが一致しないため再利用できません。')
    if not supplied:
        return bundle, values
    steps, python, values = concrete_for(template, supplied)
    if validate_generated(steps, python, views):
        raise AnalysisError('指定した値で作ったコードが、現在の検査に合格しません。値を見直してください。', 409)
    return make_bundle(steps, python, views), values


def create_plan_from_template(user, template_id, supplied=None):
    """テンプレートから、本人を所有者とする新しい分析案(手順の承認待ち)を作る。変数の値を指定できる(期間も、変数として定義されているときだけ)。"""
    if supplied is not None and not isinstance(supplied, dict):
        raise AnalysisError('変数の値の形式が不正です。')  # 0・空文字・空の配列・nullを、「指定なし」として通さない
    admin = is_template_admin(user)
    template = get_visible_template(template_id, user, admin)  # 見えない状態は、存在しないものとして404
    if template.status not in REUSABLE_STATUSES:
        raise AnalysisError('却下または置換済みのテンプレートは再利用できません。', 409)
    if not can_reuse(template, user, admin):
        raise AnalysisError('管理者承認前のテンプレートを再利用できるのは、作成者と管理者だけです。', 403)
    bundle, values = _verified_bundle(template, supplied)
    date_from, date_to = values.get(PERIOD_FROM, template.date_from.isoformat()), values.get(PERIOD_TO, template.date_to.isoformat())
    try:
        # 現行のビュー・列の公開定義に合うこと(ビューの削除・列の削除・未公開は拒否)。未承認の列を追加して補わない。
        # 列の型・ビューの計算の変更は検出できない(テンプレートに型を保存していない。後続でBOSSが判断する)
        validate_datasets(template.datasets, date_from, date_to)
    except AnalysisError:
        raise AnalysisError('現在のビュー・列の公開定義と一致しないため再利用できません。新しい分析として作り直してください。', 409) from None
    proposal = {
        'title': template.name, 'steps': template.procedure, 'outputs': template.output_spec, 'datasets': template.datasets,
        'purpose': template.purpose, 'date_from': date_from, 'date_to': date_to, 'materials': [],
        'conditions': template.conditions, 'provider': 'template', 'model': '',
    }
    extra = {
        'template': {'id': template.pk, 'version': template.version, 'family_id': str(template.family_id), 'name': template.name,
                     'status': template.status, 'content_sha256': template.content_sha256, 'values': values},
        # 保存済みのコードを、現行の外枠で組み立て直して入れる。試行・コード承認は取り直す(AIによる生成は行わない)
        'codegen': {
            'status': 'generated', 'attempts': 0, 'inflight': None, 'history': [], 'steps': bundle.steps, 'python': bundle.python,
            'sql_sha256': bundle.sql_sha256, 'python_sha256': bundle.python_sha256, 'executed_code_sha256': bundle.executed_code_sha256,
            'wrapper_version': bundle.wrapper_version, 'trial': None,
        },
    }
    store = AnalysisPlanStore()
    store.check_connection()
    return store.create(user.pk, proposal, get_analysis_execution_policy().plan_cache_ttl_minutes, extra=extra)


def check_plan_template(plan, user, confirmed=None, *, accepting):
    """テンプレート由来の分析案の、実行の受付時(accepting=True。明示の確認も照合)・ワーカーの開始前の確認。

    テンプレートが、まだ再利用できる状態で、内容が分析案の作成時と同じで、本人が再利用できること。
    管理者承認待ちは、受付時に、そのテンプレートのIDつきの確認(template_confirmed)が必要(別のテンプレートの確認を転用させない)。
    """
    info = plan.get('template')
    if info is None:
        if confirmed is not None:
            raise AnalysisError('テンプレートから作成した分析案ではありません。', 400)
        return None
    template = AIAnalysisTemplate.objects.filter(pk=info.get('id')).first()
    if template is None or template.status not in REUSABLE_STATUSES or template.content_sha256 != info.get('content_sha256'):
        raise TemplateUnavailable()
    if not can_reuse(template, user, is_template_admin(user)):
        raise TemplateUnavailable()
    if accepting:
        if template.status == 'pending_admin':
            if type(confirmed) is not int or confirmed != template.pk:
                raise AnalysisError('システム管理者未承認のテンプレートです。内容を確認し、そのテンプレートの確認を指定してください。', 409)
        elif confirmed is not None and (type(confirmed) is not int or confirmed != template.pk):
            raise AnalysisError('確認したテンプレートが一致しません。', 400)
    return template
