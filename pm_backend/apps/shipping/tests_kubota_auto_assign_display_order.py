"""DBへ接続せず、実際の自動振分の読取分岐と処理順を検証する。"""
import ast
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).with_name('views_kubota_sakai_trip_assignment.py')
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
VIEW = next(node for node in TREE.body if isinstance(node, ast.ClassDef) and node.name == 'KubotaSakaiTripAutoAssignViewNew')
POST = next(node for node in VIEW.body if isinstance(node, ast.FunctionDef) and node.name == 'post')


def execute_nodes(nodes, namespace):
    # 関連する実コードのみ抽出し、Django初期化や実DBアクセスを避ける。
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), namespace)


class AutoAssignDisplayOrderTests(unittest.TestCase):
    def settings_namespace(self, payload, settings=()):
        namespace = {
            'request': SimpleNamespace(data=payload),
            'product_codes': {'V01', 'V02'},
            'KubotaSakaiTripDisplaySetting': SimpleNamespace(objects=Mock()),
        }
        manager = namespace['KubotaSakaiTripDisplaySetting'].objects
        manager.filter.return_value = settings
        nodes = [node for node in POST.body if (
            isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in ('prioritize_product_display_order', 'product_display_orders')
                for target in node.targets
            )
        ) or (
            isinstance(node, ast.If) and isinstance(node.test, ast.Name)
            and node.test.id == 'prioritize_product_display_order'
        )]
        execute_nodes(nodes, namespace)
        return namespace, manager

    def sorter(self, enabled, rows, orders=None):
        namespace = {
            'Decimal': Decimal, 'ROUND_CEILING': ROUND_CEILING,
            'due_adjustment_map': {row.id: row for row in rows},
            'default_container_by_due': {},
            'candidate_trucks_for_due': lambda row: [None] * row.candidates,
            'resolve_allocation_capacity': lambda row, cid: Decimal(row.capacity),
            '_to_decimal': Decimal, '_to_int_qty': int,
            'prioritize_product_display_order': enabled,
            'product_display_orders': orders or {},
        }
        node = next(node for node in POST.body if isinstance(node, ast.FunctionDef) and node.name == 'sort_due_ids_for_auto_assign')
        execute_nodes([node], namespace)
        return namespace['sort_due_ids_for_auto_assign'](None, [row.id for row in rows])

    def row(self, id, product='V01', ship='ZGHC', candidates=2, qty=20, capacity=10):
        return SimpleNamespace(id=id, product_code=product, ship_to_code=ship,
                               candidates=candidates, delivery_qty=Decimal(qty), capacity=capacity)

    def test_omitted_and_false_do_not_read_display_settings(self):
        for payload in ({}, {'prioritize_product_display_order': False}):
            with self.subTest(payload=payload):
                namespace, manager = self.settings_namespace(payload)
                self.assertFalse(namespace['prioritize_product_display_order'])
                self.assertEqual(namespace['product_display_orders'], {})
                manager.filter.assert_not_called()

    def test_true_reads_settings_in_one_query(self):
        namespace, manager = self.settings_namespace(
            {'prioritize_product_display_order': True},
            [SimpleNamespace(product_code='V01', ship_to_code='ZGHC', display_order=0)],
        )
        manager.filter.assert_called_once_with(product_code__in={'V01', 'V02'})
        self.assertEqual(namespace['product_display_orders'], {('V01', 'ZGHC'): 0})

    def test_off_preserves_candidate_container_quantity_and_id_order(self):
        rows = [self.row(8, candidates=0), self.row(7, candidates=3, qty=100),
                self.row(6, qty=31), self.row(5, qty=40, capacity=20),
                self.row(4, qty=30), self.row(3, qty=30), self.row(2, candidates=1)]
        self.assertEqual(self.sorter(False, rows, {('V01', 'ZGHC'): 0}), [2, 6, 3, 4, 5, 7, 8])

    def test_on_prioritizes_product_rows_then_preserves_existing_order(self):
        rows = [self.row(1, product='V02', candidates=1, qty=100),
                self.row(2, candidates=3), self.row(3, candidates=1),
                self.row(4, candidates=3, qty=40)]
        orders = {('V01', 'ZGHC'): 0, ('V02', 'ZGHC'): 1}
        self.assertEqual(self.sorter(True, rows, orders), [3, 4, 2, 1])

    def test_missing_settings_equal_orders_and_ship_to_are_sorted_as_rows(self):
        rows = [self.row(1, product='V03'), self.row(2, product='V02', ship='ZGHC'),
                self.row(3, product='V02', ship='05476'), self.row(4, product='V01'),
                self.row(5, product='V04', ship=None)]
        orders = {('V02', 'ZGHC'): 1, ('V02', '05476'): 1, ('V03', 'ZGHC'): 0}
        self.assertEqual(self.sorter(True, rows, orders), [1, 3, 2, 4, 5])


if __name__ == '__main__':
    unittest.main()
