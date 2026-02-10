#!/usr/bin/env python
# -*- coding: utf-8 -*-

test_headers = ['発注番号', '発注先コード', '発注日', '品目', '品番', '納期', '発注数量', '納入先コード']

class MockService:
    def _normalize_header(self, name):
        if name is None:
            return ''
        normalized = str(name).strip().replace(' ', '').replace('\u3000', '')
        normalized = normalized.replace('_', '').replace('-', '').upper()
        normalized = normalized.lstrip('\ufeff')
        return normalized

    def _build_header_map(self, header_row):
        header_aliases = {
            'product_code': ['品目コード', '製品コード', '製品ｺｰﾄﾞ', '品番', '品目ｺｰﾄﾞ', '図番', '商品コード', '部品番号'],
            'due_date': ['納期', '納入日', '納品日', '納入指示日', '納期日', '納入予定日'],
            'quantity': ['数量', '注文数量', '発注数量', '発注数', '指示数', '納入指示数', '納品数量'],
        }
        
        alias_map = {}
        for key, aliases in header_aliases.items():
            for alias in aliases:
                alias_map[self._normalize_header(alias)] = key
        
        col_map = {}
        for idx, name in enumerate(header_row or []):
            key = alias_map.get(self._normalize_header(name))
            if key and key not in col_map:
                col_map[key] = idx
        
        return col_map

svc = MockService()
col_map = svc._build_header_map(test_headers)
print("Header map result:", col_map)
print("Expected: product_code at index 4, due_date at index 5, quantity at index 6")
print()
print("Test row:")
test_row = ['18429726', '509', '2026/02/09', 'ｸﾗﾝﾌﾟ;ﾎｰｽ', '4342692', '2026/03/11', '400', '000010']
print("Row:", test_row)
print("product_code (idx 4):", test_row[col_map.get('product_code', 4)] if col_map.get('product_code') is not None else 'NOT FOUND')
print("due_date (idx 5):", test_row[col_map.get('due_date', 5)] if col_map.get('due_date') is not None else 'NOT FOUND')
print("quantity (idx 6):", test_row[col_map.get('quantity', 6)] if col_map.get('quantity') is not None else 'NOT FOUND')
