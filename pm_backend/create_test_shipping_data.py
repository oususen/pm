#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
出荷指示書のテストデータを作成するスクリプト
"""

import os
import sys
import django
from datetime import date, timedelta

# Djangoの設定を読み込む
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pm_backend.settings')
django.setup()

from orders.models import DeliveryProgress
from masters.models import Product, ProductGroup, ContainerCapacity


def create_test_data():
    """テストデータを作成"""

    # 1. 製品グループを作成
    print("製品グループを作成中...")
    seatbase_group, _ = ProductGroup.objects.get_or_create(
        group_code='SEATBASE',
        defaults={'group_name': 'シートベース', 'is_active': True}
    )

    tank_group, _ = ProductGroup.objects.get_or_create(
        group_code='TANK',
        defaults={'group_name': 'タンク', 'is_active': True}
    )

    blade_group, _ = ProductGroup.objects.get_or_create(
        group_code='BLADE',
        defaults={'group_name': 'ブレード', 'is_active': True}
    )

    siga_group, _ = ProductGroup.objects.get_or_create(
        group_code='SIGA',
        defaults={'group_name': '滋賀', 'is_active': True}
    )

    sub_blade_group, _ = ProductGroup.objects.get_or_create(
        group_code='SUB_BLADE',
        defaults={'group_name': 'SUBブレード', 'is_active': True}
    )

    print(f"  - {seatbase_group}")
    print(f"  - {tank_group}")
    print(f"  - {blade_group}")
    print(f"  - {siga_group}")
    print(f"  - {sub_blade_group}")

    # 2. 容器を作成
    print("\n容器を作成中...")
    container_4_5t, _ = ContainerCapacity.objects.get_or_create(
        name='4-5T',
        defaults={'capacity': 3, 'is_active': True}
    )

    container_normal, _ = ContainerCapacity.objects.get_or_create(
        name='通常容器',
        defaults={'capacity': 10, 'is_active': True}
    )

    print(f"  - {container_4_5t}")
    print(f"  - {container_normal}")

    # 3. 製品を作成
    print("\n製品を作成中...")

    # 1便目・4便目用（4-5T容器）
    product1, _ = Product.objects.get_or_create(
        product_code='YD40003001',
        defaults={
            'product_name': '4tブレードA',
            'model_name': '391',
            'product_group': blade_group,
            'used_container': container_4_5t,
            'capacity': 3,
            'is_active': True
        }
    )

    product2, _ = Product.objects.get_or_create(
        product_code='YD40003002',
        defaults={
            'product_name': '5tブレードB',
            'model_name': '17U',
            'product_group': blade_group,
            'used_container': container_4_5t,
            'capacity': 3,
            'is_active': True
        }
    )

    # 2便目用（特定機種名）
    product3, _ = Product.objects.get_or_create(
        product_code='YD40003003',
        defaults={
            'product_name': 'ブレードC',
            'model_name': '20U',
            'product_group': blade_group,
            'used_container': container_normal,
            'capacity': 10,
            'is_active': True
        }
    )

    product4, _ = Product.objects.get_or_create(
        product_code='YD40003004',
        defaults={
            'product_name': 'ブレードD',
            'model_name': 'KOTEIKYAKU',
            'product_group': blade_group,
            'used_container': container_normal,
            'capacity': 5,
            'is_active': True
        }
    )

    # SIGA製品
    product5, _ = Product.objects.get_or_create(
        product_code='YD40003005',
        defaults={
            'product_name': '滋賀製品A',
            'model_name': 'SIGA-01',
            'product_group': siga_group,
            'used_container': container_normal,
            'capacity': 8,
            'is_active': True
        }
    )

    # 3便目用（SEATBASE/TANK）
    product6, _ = Product.objects.get_or_create(
        product_code='YD40003006',
        defaults={
            'product_name': 'シートベースA',
            'model_name': 'SB-01',
            'product_group': seatbase_group,
            'used_container': container_normal,
            'capacity': 15,
            'is_active': True
        }
    )

    product7, _ = Product.objects.get_or_create(
        product_code='YD40003007',
        defaults={
            'product_name': 'オイルタンクA',
            'model_name': 'TK-01',
            'product_group': tank_group,
            'used_container': container_normal,
            'capacity': 12,
            'is_active': True
        }
    )

    # SUB_BLADE製品
    product8, _ = Product.objects.get_or_create(
        product_code='YD40003008',
        defaults={
            'product_name': 'SUBブレードL',
            'model_name': '17U-L',
            'product_group': sub_blade_group,
            'used_container': None,
            'capacity': None,
            'is_active': True
        }
    )

    # 注意製品
    product9, _ = Product.objects.get_or_create(
        product_code='YD40003261',
        defaults={
            'product_name': '付属品（YD40003117用）',
            'model_name': None,
            'product_group': None,
            'used_container': None,
            'capacity': None,
            'is_active': True
        }
    )

    print(f"  - {product1}")
    print(f"  - {product2}")
    print(f"  - {product3}")
    print(f"  - {product4}")
    print(f"  - {product5}")
    print(f"  - {product6}")
    print(f"  - {product7}")
    print(f"  - {product8}")
    print(f"  - {product9}")

    # 4. 出荷進捗データを作成（今日と明日）
    print("\n出荷進捗データを作成中...")

    today = date.today()
    tomorrow = today + timedelta(days=1)

    for target_date in [today, tomorrow]:
        print(f"\n  {target_date}のデータ:")

        # 1便目・4便目用データ
        dp1, created = DeliveryProgress.objects.get_or_create(
            product=product1,
            order_date=target_date,
            defaults={'order_quantity': 15, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product1.product_code}: {dp1.order_quantity}個")

        dp2, created = DeliveryProgress.objects.get_or_create(
            product=product2,
            order_date=target_date,
            defaults={'order_quantity': 12, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product2.product_code}: {dp2.order_quantity}個")

        # 2便目用データ
        dp3, created = DeliveryProgress.objects.get_or_create(
            product=product3,
            order_date=target_date,
            defaults={'order_quantity': 20, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product3.product_code}: {dp3.order_quantity}個")

        dp4, created = DeliveryProgress.objects.get_or_create(
            product=product4,
            order_date=target_date,
            defaults={'order_quantity': 10, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product4.product_code}: {dp4.order_quantity}個")

        dp5, created = DeliveryProgress.objects.get_or_create(
            product=product5,
            order_date=target_date,
            defaults={'order_quantity': 16, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product5.product_code}: {dp5.order_quantity}個")

        # 3便目用データ
        dp6, created = DeliveryProgress.objects.get_or_create(
            product=product6,
            order_date=target_date,
            defaults={'order_quantity': 30, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product6.product_code}: {dp6.order_quantity}個")

        dp7, created = DeliveryProgress.objects.get_or_create(
            product=product7,
            order_date=target_date,
            defaults={'order_quantity': 24, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product7.product_code}: {dp7.order_quantity}個")

        # SUB_BLADE
        dp8, created = DeliveryProgress.objects.get_or_create(
            product=product8,
            order_date=target_date,
            defaults={'order_quantity': 5, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product8.product_code}: {dp8.order_quantity}個")

        # 注意製品
        dp9, created = DeliveryProgress.objects.get_or_create(
            product=product9,
            order_date=target_date,
            defaults={'order_quantity': 3, 'shipped_quantity': 0}
        )
        if created:
            print(f"    - {product9.product_code}: {dp9.order_quantity}個")

    print("\nテストデータの作成が完了しました！")
    print(f"\n今日の日付: {today}")
    print(f"明日の日付: {tomorrow}")
    print("\nブラウザで出荷指示書画面にアクセスして、日付を選択してください。")


if __name__ == '__main__':
    create_test_data()
