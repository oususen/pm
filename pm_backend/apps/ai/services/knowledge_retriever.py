"""社内AI用のMarkdownナレッジ検索。

ベクトルDBへ全文を保存せず、リポジトリの正式原本を都度検索する。
設定画面のAIKnowledgeSourceで有効になっている区分だけを対象にする。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from ai.config.models import AIKnowledgeSource


PROJECT_ROOT = Path(__file__).resolve().parents[4]
MANUAL_ROOT = PROJECT_ROOT / 'pm-ui' / 'public' / 'manual'
SPEC_ROOT = PROJECT_ROOT / '仕様書'
LOCAL_KNOWLEDGE_ROOT = PROJECT_ROOT / 'pm_backend' / 'apps' / 'ai' / 'knowledge'
MAX_CHUNK_CHARS = 1400
SCREEN_KEYWORDS = {
    'orders': ('受注', '注文', 'ルーティング'),
    'production': ('生産', '工程', '実績', '作業'),
    'quality': ('品質', '仕損', '不良', '検査'),
    'overtime': ('勤務', '残業', '申請', '勤怠'),
    'purchase': ('仕入', '購買', '発注', '検収'),
    'shipping': ('出荷', '納入', '便'),
    'inventory': ('在庫', '棚卸', '進度'),
}


def _enabled_categories():
    """DB設定を読み、未登録時は何も検索しない。"""
    return set(
        AIKnowledgeSource.objects.filter(is_enabled=True).values_list('category', flat=True)
    )


def _paths_for_categories(categories):
    """区分に対応する正式原本だけを返す。READMEは案内文のため検索しない。"""
    paths = []
    if 'manual' in categories and MANUAL_ROOT.exists():
        paths.extend(path for path in MANUAL_ROOT.rglob('*.md') if path.name.lower() != 'readme.md')
    if 'pm_structure' in categories:
        for name in ('PMアプリ構造辞書.md', '社内AIチャット仕様書.md'):
            path = SPEC_ROOT / name
            if path.exists():
                paths.append(path)
    if 'security' in categories:
        path = SPEC_ROOT / '社内AI運用規約・AI用DB辞書.md'
        if path.exists():
            paths.append(path)
    if 'procedure' in categories:
        procedure_root = LOCAL_KNOWLEDGE_ROOT / 'procedures'
        if procedure_root.exists():
            paths.extend(path for path in procedure_root.rglob('*.md') if path.name.lower() != 'readme.md')
    return sorted(set(paths))


def _normalize(value):
    return re.sub(r'[^0-9a-zA-Zぁ-んァ-ヶ一-龠]', '', str(value).lower())


def _keywords(value):
    normalized = _normalize(value)
    terms = set(re.findall(r'[a-z0-9]{2,}', normalized))
    # 日本語は形態素解析に依存せず、2文字単位の一致で候補を絞る。
    terms.update(normalized[index:index + 2] for index in range(len(normalized) - 1))
    return {term for term in terms if term}


def _split_sections(text):
    sections = []
    heading = '本文'
    buffer = []
    for line in text.splitlines():
        if line.startswith('#'):
            if buffer:
                sections.append((heading, '\n'.join(buffer).strip()))
                buffer = []
            heading = line.lstrip('#').strip() or '本文'
        buffer.append(line)
    if buffer:
        sections.append((heading, '\n'.join(buffer).strip()))

    chunks = []
    for section_heading, body in sections:
        for start in range(0, max(len(body), 1), MAX_CHUNK_CHARS):
            chunk = body[start:start + MAX_CHUNK_CHARS].strip()
            if chunk:
                chunks.append((section_heading, chunk))
    return chunks


@lru_cache(maxsize=1024)
def _read_chunks(path_text, modified_ns):
    """更新時刻をキャッシュキーに含め、開発中のMarkdown編集を次回検索へ反映する。"""
    path = Path(path_text)
    try:
        return tuple(_split_sections(path.read_text(encoding='utf-8')))
    except (OSError, UnicodeDecodeError):
        return ()


def retrieve_knowledge(question, screen_context=None, limit=4, max_chars=5200):
    """質問と起点画面に近い正式原本の断片を返す。"""
    categories = _enabled_categories()
    if not categories:
        return []
    query_terms = _keywords(question)
    screen_id = (screen_context or {}).get('id', 'ai_home')
    screen_terms = set(SCREEN_KEYWORDS.get(screen_id, ()))
    candidates = []
    for path in _paths_for_categories(categories):
        try:
            modified_ns = path.stat().st_mtime_ns
        except OSError:
            continue
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        path_terms = _keywords(relative)
        for heading, content in _read_chunks(str(path), modified_ns):
            content_terms = _keywords(content)
            score = len(query_terms & content_terms) * 4 + len(query_terms & path_terms) * 7
            # 起点画面の用語が原本のパスまたは本文にあれば優先する。
            score += sum(5 for term in screen_terms if term in relative or term in content)
            if score <= 0:
                continue
            candidates.append({
                'path': relative,
                'heading': heading,
                'content': content,
                'score': score,
            })
    selected = []
    used_chars = 0
    per_path_count = {}
    for item in sorted(candidates, key=lambda value: (-value['score'], value['path'], value['heading'])):
        if (
            len(selected) >= limit
            or used_chars + len(item['content']) > max_chars
            or per_path_count.get(item['path'], 0) >= 2
        ):
            continue
        selected.append({key: item[key] for key in ('path', 'heading', 'content')})
        used_chars += len(item['content'])
        per_path_count[item['path']] = per_path_count.get(item['path'], 0) + 1
    return selected


def knowledge_prompt(chunks):
    """LLMへ渡す根拠付きコンテキストを作る。"""
    if not chunks:
        return ''
    sections = []
    for chunk in chunks:
        sections.append(
            f"[出典: {chunk['path']} / {chunk['heading']}]\n{chunk['content']}"
        )
    return (
        '\n\n以下は社内の正式ナレッジ原本から検索した参考情報です。'
        'この内容に根拠がある場合だけ回答に使い、根拠がないことは推測しないでください。'
        'DBの数値が必要な質問は、必ずDBツールまたはDB集計結果を優先してください。\n\n'
        + '\n\n---\n\n'.join(sections)
    )


def knowledge_source_label(chunks):
    """画面の根拠データ欄に表示する短い出典名。"""
    paths = []
    for chunk in chunks:
        if chunk['path'] not in paths:
            paths.append(chunk['path'])
    return 'ナレッジ: ' + '、'.join(paths[:2]) if paths else ''
