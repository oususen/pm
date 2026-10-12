"""AI分析のテンプレート・実行履歴を、JSONへ書き出して復元するための純粋な関数群。

開発DBに本番ダンプをインポートすると、ai_analysis_template と ai_analysis_run が消える。
管理コマンド export_ai_analysis_data / import_ai_analysis_data が、このモジュールを使う。
このモジュールはDBへ書き込まない(DBの読み書きは管理コマンド側に置く)。仕様は
仕様書/AI分析_開発DB再取り込み手順.md。

- ユーザーへの外部キーは、ユーザーIDではなくログインID(username)で書き出す(インポートでIDが変わるため)。
- 自己参照の外部キー(refined_from_run・replaces)と、履歴の template_id は元のIDを保つ。
- 日時はISO文字列、Decimal・UUIDは文字列で書き、復元時はモデルのフィールド型で読み戻す。
"""
import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

FORMAT_VERSION = 1
TEMPLATES_FILE = 'templates.json'
RUNS_FILE = 'runs.json'
MANIFEST_FILE = 'manifest.json'

# 復元の対象。テンプレートを先に、履歴を後に入れる(通知・AIの設定は対象外)。
KIND_TEMPLATE = 'template'
KIND_RUN = 'run'

SKIP_USER_NOT_FOUND = 'user_not_found'
SKIP_ID_CONFLICT = 'id_conflict'
SKIP_UNIQUE_CONFLICT = 'unique_conflict'
SKIP_PARENT = 'parent_skipped_or_missing'
SKIP_MISSING_FIELD = 'missing_field'
SKIP_BAD_VALUE = 'bad_value'
SKIP_DUPLICATE_ID = 'duplicate_id_in_file'

SKIP_REASON_TEXT = {
    SKIP_USER_NOT_FOUND: 'ログインIDのユーザーが開発DBにない',
    SKIP_ID_CONFLICT: '同じIDの行が既にある(既存の行は上書きしない)',
    SKIP_UNIQUE_CONFLICT: '一意制約が既存の行(または先に入る行)と衝突する',
    SKIP_PARENT: '参照先の行(元の実行・置き換え元)がスキップされた、または存在しない',
    SKIP_MISSING_FIELD: 'ファイルに必須の項目がない',
    SKIP_BAD_VALUE: '値をフィールドの型へ変換できない',
    SKIP_DUPLICATE_ID: '同じIDの行がファイル内に複数ある',
}


def _is_user_fk(f):
    return f.is_relation and f.related_model._meta.label_lower == settings.AUTH_USER_MODEL.lower()


def field_specs(model):
    """モデルの全フィールドを [(フィールド, 種別, JSONのキー)] で返す。種別は user / fk / plain。"""
    specs = []
    for f in model._meta.concrete_fields:
        if _is_user_fk(f):
            specs.append((f, 'user', f'{f.name}_username'))
        elif f.is_relation:
            specs.append((f, 'fk', f.attname))
        else:
            specs.append((f, 'plain', f.attname))
    return specs


def row_keys(model):
    return [key for _f, _kind, key in field_specs(model)]


def self_fk_key(model):
    """自己参照の外部キーのJSONキー(なければNone)。"""
    for f, kind, key in field_specs(model):
        if kind == 'fk' and f.related_model is model:
            return key
    return None


def unique_field_sets(model):
    """UniqueConstraint のフィールド名の組(モデルの Meta.constraints から)。"""
    return [tuple(c.fields) for c in model._meta.constraints if isinstance(c, models.UniqueConstraint)]


def schema_fields(model_map):
    return {kind: sorted(row_keys(model)) for kind, model in model_map.items()}


def schema_hash(model_map):
    """書き出すフィールド名の一覧(モデルごと・名前順)のハッシュ。"""
    text = json.dumps(schema_fields(model_map), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# --- 書き出し ---

def serialize_value(value):
    """JSONに載せられる値へ変換する。日時はISO文字列、Decimal・UUIDは文字列。"""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    return value


def instance_to_row(model, obj, username_by_id):
    """モデルの1行を、JSONの辞書へ変換する。ユーザーはログインIDで書く。"""
    row = {}
    for f, kind, key in field_specs(model):
        raw = getattr(obj, f.attname)
        if kind == 'user':
            if raw is None:
                row[key] = None
            else:
                if raw not in username_by_id:
                    raise ValueError(f'ユーザーID {raw} のログインIDを取得できません({key})')
                row[key] = username_by_id[raw]
        else:
            row[key] = serialize_value(raw)
    return row


def user_ids_in(model, objs):
    ids = set()
    for f, kind, _key in field_specs(model):
        if kind == 'user':
            ids.update(v for v in (getattr(o, f.attname) for o in objs) if v is not None)
    return ids


def build_manifest(model_map, counts, db_name, exported_at):
    return {
        'format_version': FORMAT_VERSION,
        'exported_at': exported_at.isoformat(),
        'db_name': db_name,
        'counts': dict(counts),
        'schema_hash': schema_hash(model_map),
        'schema_fields': schema_fields(model_map),
    }


def dumps(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)


def write_backup(directory, manifest, templates, runs):
    """新しいフォルダへ書く。manifest は最後に書く(途中で失敗したフォルダは、復元の対象にならない)。"""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / TEMPLATES_FILE).write_text(dumps(templates), encoding='utf-8')
    (directory / RUNS_FILE).write_text(dumps(runs), encoding='utf-8')
    (directory / MANIFEST_FILE).write_text(dumps(manifest), encoding='utf-8')


# --- 読み込み ---

def resolve_input_dir(path):
    """manifest.json があるフォルダならそれ、なければ直下で名前が最新の manifest.json つきサブフォルダ。"""
    path = Path(path)
    if (path / MANIFEST_FILE).is_file():
        return path
    candidates = sorted(p for p in path.iterdir() if p.is_dir() and (p / MANIFEST_FILE).is_file()) if path.is_dir() else []
    if not candidates:
        raise ValueError(f'書き出しファイル({MANIFEST_FILE})が見つかりません: {path}')
    return candidates[-1]


def load_backup(directory):
    directory = Path(directory)
    manifest = json.loads((directory / MANIFEST_FILE).read_text(encoding='utf-8'))
    templates = json.loads((directory / TEMPLATES_FILE).read_text(encoding='utf-8'))
    runs = json.loads((directory / RUNS_FILE).read_text(encoding='utf-8'))
    counts = manifest.get('counts') or {}
    if counts.get(KIND_TEMPLATE) != len(templates) or counts.get(KIND_RUN) != len(runs):
        raise ValueError(
            f'manifest の件数(テンプレート {counts.get(KIND_TEMPLATE)}・履歴 {counts.get(KIND_RUN)})と'
            f'ファイルの件数(テンプレート {len(templates)}・履歴 {len(runs)})が一致しません')
    return manifest, templates, runs


def check_schema(manifest, model_map):
    """版が違えば、理由の文(違う項目名のみ。実データは含めない)を返す。同じならNone。"""
    current_hash = schema_hash(model_map)
    if manifest.get('schema_hash') == current_hash:
        return None
    old = manifest.get('schema_fields') or {}
    new = schema_fields(model_map)
    parts = []
    for kind in sorted(set(old) | set(new)):
        old_set, new_set = set(old.get(kind) or []), set(new.get(kind) or [])
        if old_set - new_set:
            parts.append(f'{kind}: 書き出しにあって現在のモデルにない項目 {sorted(old_set - new_set)}')
        if new_set - old_set:
            parts.append(f'{kind}: 現在のモデルにあって書き出しにない項目 {sorted(new_set - old_set)}')
    detail = ' / '.join(parts) if parts else '項目名の一覧は同じですが、版(ハッシュ)が一致しません'
    return (f'スキーマの版が違います(書き出し時 {str(manifest.get("schema_hash"))[:12]}・現在 {current_hash[:12]})。'
            f'{detail}')


# --- 復元の計画 ---

@dataclass
class Skip:
    kind: str
    row_id: object
    reason: str
    detail: str = ''


@dataclass
class RestorePlan:
    templates: list = field(default_factory=list)   # [(id, kwargs)] 挿入順
    runs: list = field(default_factory=list)
    skipped: list = field(default_factory=list)     # [Skip]
    warnings: list = field(default_factory=list)


def row_to_kwargs(model, row, user_id_by_name):
    """JSONの1行を、モデルのkwargsへ変換する。変換できなければ (None, reason, detail)。"""
    kwargs = {}
    for f, kind, key in field_specs(model):
        if key not in row:
            # ファイルにない項目は、既定値やNULLで埋めない(スキーマの版が同じなら、通常は起こらない)
            return None, SKIP_MISSING_FIELD, key
        value = row[key]
        if kind == 'user':
            if value is None:
                kwargs[f.attname] = None
            elif value in user_id_by_name:
                kwargs[f.attname] = user_id_by_name[value]
            else:
                return None, SKIP_USER_NOT_FOUND, f'{f.name}={value}'
        elif kind == 'fk':
            kwargs[f.attname] = value
        else:
            if value is None:
                kwargs[f.attname] = None
                continue
            try:
                kwargs[f.attname] = f.to_python(value)
            except (ValidationError, ValueError, TypeError):
                return None, SKIP_BAD_VALUE, key
    return kwargs, None, ''


def plan_model(kind, model, rows, user_id_by_name, existing_ids, existing_unique):
    """1つのモデルの復元計画。(挿入順の [(id, kwargs)], [Skip]) を返す。

    existing_unique: {フィールド名の組: 既存の値の組の集合}
    """
    skipped = []
    accepted = {}
    order = []
    seen_unique = {k: set(v) for k, v in existing_unique.items()}
    parent_key = self_fk_key(model)
    for row in rows:
        row_id = row.get('id')
        kwargs, reason, detail = row_to_kwargs(model, row, user_id_by_name)
        if kwargs is None:
            skipped.append(Skip(kind, row_id, reason, detail))
            continue
        if row_id in accepted:
            skipped.append(Skip(kind, row_id, SKIP_DUPLICATE_ID))
            continue
        if row_id in existing_ids:
            skipped.append(Skip(kind, row_id, SKIP_ID_CONFLICT))
            continue
        conflict = None
        keys = {}
        for names in seen_unique:
            value = tuple(kwargs.get(n) for n in names)
            keys[names] = value
            if value in seen_unique[names]:
                conflict = ','.join(names)
                break
        if conflict:
            skipped.append(Skip(kind, row_id, SKIP_UNIQUE_CONFLICT, conflict))
            continue
        for names, value in keys.items():
            seen_unique[names].add(value)
        accepted[row_id] = kwargs
        order.append(row_id)

    # 自己参照は、参照先を先に入れる。参照先が既存の行か、先に入る行になければ、スキップする。
    placed = []
    placed_set = set()
    remaining = list(order)
    while remaining:
        progressed = False
        rest = []
        for row_id in remaining:
            parent = accepted[row_id].get(parent_key) if parent_key else None
            if parent is None or parent in placed_set or parent in existing_ids:
                placed.append(row_id)
                placed_set.add(row_id)
                progressed = True
            else:
                rest.append(row_id)
        remaining = rest
        if not progressed:
            break
    for row_id in remaining:
        skipped.append(Skip(kind, row_id, SKIP_PARENT, f'{parent_key}={accepted[row_id].get(parent_key)}'))
    return [(row_id, accepted[row_id]) for row_id in placed], skipped


def build_plan(model_map, templates, runs, user_id_by_name, existing, existing_unique):
    """全体の復元計画。existing: {kind: 既存IDの集合}。existing_unique: {kind: {名前の組: 値の組の集合}}。"""
    plan = RestorePlan()
    plan.templates, skipped_t = plan_model(
        KIND_TEMPLATE, model_map[KIND_TEMPLATE], templates, user_id_by_name,
        existing[KIND_TEMPLATE], existing_unique[KIND_TEMPLATE])
    plan.runs, skipped_r = plan_model(
        KIND_RUN, model_map[KIND_RUN], runs, user_id_by_name,
        existing[KIND_RUN], existing_unique[KIND_RUN])
    plan.skipped = skipped_t + skipped_r
    known_templates = set(existing[KIND_TEMPLATE]) | {i for i, _k in plan.templates}
    dangling = sum(1 for _i, k in plan.runs if k.get('template_id') is not None and k['template_id'] not in known_templates)
    if dangling:
        plan.warnings.append(
            f'履歴 {dangling} 件の template_id が、復元後のテンプレートに存在しません(スキップされたテンプレートなど)。'
            'template_id は外部キーではないため値はそのまま復元します。')
    return plan


def execute_plan(plan, insert):
    """計画の順に insert(kind, kwargs) を呼ぶ。トランザクションは呼び出し側で張る。"""
    for _row_id, kwargs in plan.templates:
        insert(KIND_TEMPLATE, kwargs)
    for _row_id, kwargs in plan.runs:
        insert(KIND_RUN, kwargs)
    return {KIND_TEMPLATE: len(plan.templates), KIND_RUN: len(plan.runs)}


@contextmanager
def suspended_auto_now(model):
    """auto_now / auto_now_add を一時的に止める(書き出した作成・更新日時をそのまま戻すため)。"""
    saved = []
    for f in model._meta.concrete_fields:
        if getattr(f, 'auto_now', False) or getattr(f, 'auto_now_add', False):
            saved.append((f, f.auto_now, f.auto_now_add))
            f.auto_now = False
            f.auto_now_add = False
    try:
        yield
    finally:
        for f, auto_now, auto_now_add in saved:
            f.auto_now = auto_now
            f.auto_now_add = auto_now_add


def summarize_skips(skipped):
    """(kind, reason) ごとの件数。"""
    summary = {}
    for s in skipped:
        summary[(s.kind, s.reason)] = summary.get((s.kind, s.reason), 0) + 1
    return summary
