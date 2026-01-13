import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


def iter_sql_statements(sql_text):
    statement = []
    in_single = False
    in_double = False
    in_line_comment = False
    in_block_comment = False
    prev_char = ''

    for ch in sql_text:
        if in_line_comment:
            if ch == '\n':
                in_line_comment = False
            prev_char = ch
            continue

        if in_block_comment:
            if prev_char == '*' and ch == '/':
                in_block_comment = False
            prev_char = ch
            continue

        if not in_single and not in_double:
            if prev_char == '-' and ch == '-':
                if statement:
                    statement.pop()
                in_line_comment = True
                prev_char = ch
                continue
            if prev_char == '/' and ch == '*':
                if statement:
                    statement.pop()
                in_block_comment = True
                prev_char = ch
                continue

        if ch == "'" and not in_double and prev_char != '\\':
            in_single = not in_single
        elif ch == '"' and not in_single and prev_char != '\\':
            in_double = not in_double

        if ch == ';' and not in_single and not in_double:
            sql = ''.join(statement).strip()
            if sql:
                yield sql
            statement = []
        else:
            statement.append(ch)

        prev_char = ch

    tail = ''.join(statement).strip()
    if tail:
        yield tail


class Command(BaseCommand):
    help = "Import proposals SQL dump into the current database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default="",
            help="Path to the SQL dump file (default: pm_backend/data/proposals_dump.sql).",
        )
        parser.add_argument(
            "--allow-drop",
            action="store_true",
            help="Allow DROP TABLE statements from the dump.",
        )
        parser.add_argument(
            "--tables",
            type=str,
            default="proposals_department,proposals_employee",
            help="Comma-separated table names to import (use * for all tables).",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Ignore errors when tables already exist.",
        )

    def handle(self, *args, **options):
        path = options["path"].strip()
        if path:
            dump_path = Path(path)
        else:
            dump_path = Path(settings.BASE_DIR) / "data" / "proposals_dump.sql"

        if not dump_path.exists():
            raise CommandError(f"SQLファイルが見つかりません: {dump_path}")

        sql_text = dump_path.read_text(encoding="utf-8")
        statements = list(iter_sql_statements(sql_text))
        if not statements:
            raise CommandError("SQL文が見つかりません。")

        allow_drop = options["allow_drop"]
        skip_existing = options["skip_existing"]
        table_filter_raw = options["tables"].strip()
        if table_filter_raw and table_filter_raw != "*":
            allowed_tables = {
                name.strip()
                for name in table_filter_raw.split(",")
                if name.strip()
            }
        else:
            allowed_tables = None

        table_matcher = re.compile(
            r"^(drop table if exists|create table|insert into)\s+`?([a-zA-Z0-9_]+)`?",
            re.IGNORECASE,
        )

        with connection.cursor() as cursor:
            for index, stmt in enumerate(statements, start=1):
                normalized = stmt.strip()
                if not normalized:
                    continue

                match = table_matcher.match(normalized)
                if match and allowed_tables is not None:
                    table_name = match.group(2)
                    if table_name not in allowed_tables:
                        self.stdout.write(
                            self.style.WARNING(
                                f"対象外テーブルをスキップ: {table_name}"
                            )
                        )
                        continue
                lowered = normalized.lower()
                if lowered.startswith("drop table") and not allow_drop:
                    self.stdout.write(self.style.WARNING(f"DROP文をスキップ: {normalized.splitlines()[0]}"))
                    continue

                try:
                    cursor.execute(normalized)
                except Exception as exc:
                    message = str(exc)
                    if skip_existing and "already exists" in message.lower():
                        self.stdout.write(self.style.WARNING(f"既存テーブルをスキップ: {normalized.splitlines()[0]}"))
                        continue
                    raise CommandError(f"SQL実行失敗 (#{index}): {message}") from exc

        self.stdout.write(self.style.SUCCESS("proposals データのインポートが完了しました。"))
