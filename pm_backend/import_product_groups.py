#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
product_groupsデータをm_product_groupテーブルにインポートするスクリプト
"""

import os
import sys
from pathlib import Path
import django

# Djangoの設定を読み込む
base_dir = Path(__file__).resolve().parent
apps_dir = base_dir / "apps"
for path in (base_dir, apps_dir):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from masters.models import ProductGroup


def import_product_group_data():
    """製品グループデータをインポート"""

    print("既存データを削除中...")
    ProductGroup.objects.all().delete()

    print("製品グループデータをインポート中...")

    groups = [
        {'id': 1, 'group_code': 'FLOOR', 'group_name': 'フロア', 'description': 'フロア製品群', 'is_active': True},
        {'id': 2, 'group_code': 'TANK', 'group_name': 'タンク', 'description': 'オイルタンク', 'is_active': True},
        {'id': 3, 'group_code': 'BLADE', 'group_name': 'ブレード', 'description': 'ブレード', 'is_active': True},
        {'id': 9, 'group_code': 'SEATBASE', 'group_name': 'シートベース', 'description': 'シートベース', 'is_active': True},
        {'id': 10, 'group_code': 'SIGA', 'group_name': '滋賀', 'description': 'リーデン　滋賀', 'is_active': True},
        {'id': 11, 'group_code': 'KANTATSU', 'group_name': '神立', 'description': 'リーデン　神立', 'is_active': True},
        {'id': 12, 'group_code': 'SUB_BLADE', 'group_name': 'サブブレード', 'description': None, 'is_active': True},
    ]

    for data in groups:
        group = ProductGroup(**data)
        group.save()
        print(f"  - {group.group_code}: {group.group_name} (ID: {group.id})")

    print(f"\n{len(groups)}件のデータをインポートしました")


if __name__ == '__main__':
    import_product_group_data()
