"""子のPythonが異常終了したとき、失敗の説明へ、例外の種類名だけを足す(2026-10-08、BOSS承認)を検証する。"""
from django.test import SimpleTestCase

from ai.services.analysis_run_service import child_failure_detail, outcome_from_result


def failed(stderr, reason='child_exit_nonzero'):
    return {'status': 'failed', 'reason': reason, 'launcher': {'diagnostics': {'stderr': stderr}}}


class ChildFailureDetailTests(SimpleTestCase):
    def test_only_the_exception_type_is_taken(self):
        stderr = 'Traceback (most recent call last):\n  File "ai_python", line 3\nAttributeError: \'str\' has no attribute \'strftime\' V053504641 2026-08-01\n'
        self.assertEqual(child_failure_detail({'stderr': stderr}), '例外: AttributeError')

    def test_guard_code_is_kept_only_in_the_fixed_form(self):
        self.assertEqual(child_failure_detail({'stderr': 'GuardError: chart_x_not_list'}), '例外: GuardError(chart_x_not_list)')
        self.assertEqual(child_failure_detail({'stderr': 'GuardError: V053504641 の行'}), '例外: GuardError')

    def test_unreadable_or_empty_stderr_adds_nothing(self):
        for stderr in ('', None, 'killed', 'abc def: x'):
            with self.subTest(stderr=stderr):
                self.assertEqual(child_failure_detail({'stderr': stderr}), '')

    def test_detail_is_added_only_for_child_exit_nonzero_and_has_no_data(self):
        stderr = 'KeyError: V053504641 2026-08-01'
        detail = outcome_from_result(failed(stderr))['detail']
        self.assertIn('例外: KeyError', detail)
        self.assertNotIn('V053504641', detail)
        self.assertNotIn('例外', outcome_from_result(failed(stderr, 'timeout'))['detail'])
        self.assertLessEqual(len(detail), 300)
        self.assertEqual(outcome_from_result({'status': 'ok'})['detail'], '')

    def test_only_builtin_exception_names_and_guard_error_are_allowed(self):
        # 名前に実データが混ざる形・独自の名前は、取り出さない(evaluator指摘)
        for stderr in ('V053504641Error', 'ProductV053504641Exception', 'X20260801Error: ok', 'MyCustomError: x', 'A' * 61 + 'Error'):
            with self.subTest(stderr=stderr):
                self.assertEqual(child_failure_detail({'stderr': stderr}), '')
        for name in ('ValueError', 'KeyError', 'ZeroDivisionError', 'SystemExit', 'KeyboardInterrupt'):
            with self.subTest(name=name):
                self.assertEqual(child_failure_detail({'stderr': f'{name}: x'}), f'例外: {name}')
