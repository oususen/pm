#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
container_capacityデータをm_container_capacityテーブルにインポートするスクリプト
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

from masters.models import ContainerCapacity


def import_container_data():
    """容器データをインポート"""

    print("既存データを削除中...")
    ContainerCapacity.objects.all().delete()

    print("容器データをインポート中...")

    containers = [
        {'id': 1, 'name': 'f_r', 'container_code': 'f_r', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': True, 'max_stack': 2, 'capacity': None},
        {'id': 2, 'name': '4-5T', 'container_code': '4-5T', 'width': 2300, 'depth': 1600, 'height': 2000, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': 3},
        {'id': 3, 'name': '17U', 'container_code': '17U', 'width': 2300, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 4, 'name': '20U', 'container_code': '20U', 'width': 2300, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 5, 'name': '26U', 'container_code': '26U', 'width': 2300, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 6, 'name': '390', 'container_code': '390', 'width': 1000, 'depth': 700, 'height': 700, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 7, 'name': '19-6', 'container_code': '19-6', 'width': 1200, 'depth': 1000, 'height': 700, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 8, 'name': 'SUS', 'container_code': 'SUS', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': False, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 9, 'name': 'PAN', 'container_code': 'PAN', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': False, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 10, 'name': '6ENSUS', 'container_code': '6ENSUS', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': False, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 11, 'name': '17U-5T', 'container_code': '17U-5T', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': False, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 12, 'name': '19-6T', 'container_code': '19-6T', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': False, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 13, 'name': '6T', 'container_code': '6T', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 14, 'name': '7T7A', 'container_code': '7T7A', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 15, 'name': '7T7B', 'container_code': '7T7B', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 16, 'name': '7T5E', 'container_code': '7T5E', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 17, 'name': '7T5F', 'container_code': '7T5F', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 19, 'name': '19-6ENT', 'container_code': '19-6ENT', 'width': 2350, 'depth': 1200, 'height': 1150, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 20, 'name': '7T5A', 'container_code': '7T5A', 'width': 2300, 'depth': 1150, 'height': 1100, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 21, 'name': 'KONPARU', 'container_code': 'KONPARU', 'width': 800, 'depth': 600, 'height': 600, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
        {'id': 22, 'name': '8458', 'container_code': '8458', 'width': 800, 'depth': 600, 'height': 600, 'max_weight': 100, 'can_mix': True, 'stackable': False, 'max_stack': 1, 'capacity': None},
    ]

    for data in containers:
        container = ContainerCapacity(**data)
        container.save()
        print(f"  - {container.name} (ID: {container.id})")

    print(f"\n✓ {len(containers)}件のデータをインポートしました")


if __name__ == '__main__':
    import_container_data()
