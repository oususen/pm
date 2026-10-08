"""実行時の内部依存として time の import だけを許可する(2026-10-08、BOSS承認、Codex意見)を検証する。

実機で、生成コードの month.strftime('%Y-%m') が、外枠のimport制限により GuardError(import_not_allowed) で失敗した。
日付のstrftime・format(d, '%Y-%m')・timetuple()は、内部でtimeをimportする。生成コードの直接のimport timeは、静的検査で拒否したまま。
"""
import datetime

from django.test import SimpleTestCase

from ai.services import analysis_codegen_service as cg
from ai.services.analysis_guard_runtime import (
    ALLOWED_IMPORTS, RUNTIME_INTERNAL_IMPORTS, GuardError, _safe_builtins, validate_python,
)


def run(source, **names):
    scope = {'__builtins__': _safe_builtins(), '__name__': 'ai_python', **names}
    exec(compile(source, 'ai_python', 'exec'), scope)
    return scope


class RuntimeTimeImportTests(SimpleTestCase):
    D = datetime.date(2026, 8, 1)

    def test_date_formatting_works_at_runtime(self):
        for source, expected in (("r = d.strftime('%Y-%m')", '2026-08'), ("r = f'{d:%Y-%m}'", '2026-08'), ("r = format(d, '%Y-%m')", '2026-08'),
                                 ("r = '{:%Y-%m}'.format(d)", '2026-08'), ("r = d.timetuple().tm_mon", 8), ("r = str(d)[:7]", '2026-08'),
                                 ("r = d.isoformat()", '2026-08-01')):
            with self.subTest(source=source):
                self.assertEqual(run(source, d=self.D)['r'], expected)

    def test_strptime_stays_rejected_and_fromisoformat_works(self):
        with self.assertRaises(GuardError) as caught:
            run("import datetime\nr = datetime.datetime.strptime('2026-08-01', '%Y-%m-%d')")
        self.assertEqual(caught.exception.code, 'import_not_allowed')
        self.assertEqual(run("import datetime\nr = datetime.date.fromisoformat('2026-08-01')")['r'], self.D)

    def test_direct_imports_of_time_are_still_rejected_statically(self):
        for source in ('import time\nemit_report("x")', 'from time import sleep\nemit_report("x")', 'import _strptime\nemit_report("x")',
                       'import time as t\nemit_report("x")'):
            with self.subTest(source=source):
                self.assertIn('import_not_allowed', validate_python(source))

    def test_the_runtime_allowance_is_separate_from_the_static_list(self):
        self.assertEqual(RUNTIME_INTERNAL_IMPORTS, ('time',))
        self.assertNotIn('time', ALLOWED_IMPORTS)  # 共通の許可リストへ足さない(静的検査も同じ一覧を使うため)
        self.assertIn('datetime', ALLOWED_IMPORTS)  # 既存の許可は、置き換えていない
        self.assertEqual(len(ALLOWED_IMPORTS), 8)

    def test_other_modules_and_relative_imports_are_still_rejected_at_runtime(self):
        for name in ('os', 'sys', 'subprocess', '_strptime', 'importlib', 'time.sleep'):
            with self.subTest(name=name):
                with self.assertRaises(GuardError):
                    _safe_builtins()['__import__'](name)
        with self.assertRaises(GuardError):
            _safe_builtins()['__import__']('time', level=1)


class DateFormatRuleTests(SimpleTestCase):
    def test_the_rule_tells_the_ai_how_to_format_dates(self):
        rule = cg.PARAMETER_RULE
        self.assertIn("SQLで文字列にするのが基本(strftime(日付, '%Y-%m') など)", rule)
        self.assertIn('日付の strptime は、実行側で使えない', rule)
        self.assertIn('datetime.date.fromisoformat(文字列)', rule)
        self.assertNotIn('Pythonのdatetime)', rule)
