# -*- coding: utf-8 -*-
import re

# カテゴリ変換
CATEGORY_MAP = {
    '1': 'ASSEMBLY',
    '2': 'SINGLE',
    '3': 'MATERIAL',
    '4': 'PURCHASED'
}

products = []
current_product = {}
in_set_section = False

with open('d:/pm/all_latest_master_data.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()

        if '### SET' in line:
            in_set_section = True
            if current_product and 'product_code' in current_product:
                products.append(current_product)
            current_product = {}
            continue

        if in_set_section and '###   @' in line:
            match = re.match(r'###   @(\d+)=(.+)', line)
            if match:
                col_num = match.group(1)
                value = match.group(2).strip("'")

                if col_num == '2':  # product_code
                    current_product['product_code'] = value
                elif col_num == '3':  # product_name
                    current_product['product_name'] = value
                elif col_num == '4':  # category
                    current_product['category'] = CATEGORY_MAP.get(value, 'MATERIAL')
                elif col_num == '5':  # unit
                    current_product['unit'] = value
                elif col_num == '8':  # is_final_product
                    current_product['is_final_product'] = value
                elif col_num == '10':  # is_active
                    current_product['is_active'] = value

# Add last product
if current_product and 'product_code' in current_product:
    products.append(current_product)

# Generate SQL
with open('d:/pm/recovered_products.sql', 'w', encoding='utf-8') as f:
    f.write("-- 復旧された製品マスタ（12/05 10:00時点）\n")
    f.write("SET NAMES utf8mb4;\n")
    f.write("SET CHARACTER SET utf8mb4;\n")
    f.write("SET time_zone = '+09:00';\n\n")
    f.write("USE pm_db;\n\n")

    for p in products:
        if 'product_code' in p:
            sql = f"INSERT INTO m_product (product_code, product_name, category, unit, is_final_product, is_active) VALUES\n"
            sql += f"('{p.get('product_code', '')}', '{p.get('product_name', '')}', '{p.get('category', 'MATERIAL')}', '{p.get('unit', '個')}', {p.get('is_final_product', '0')}, {p.get('is_active', '1')})\n"
            sql += f"ON DUPLICATE KEY UPDATE product_name=VALUES(product_name), category=VALUES(category);\n\n"
            f.write(sql)

    f.write(f"-- 合計 {len(products)} 製品を復旧\n")
    f.write("SELECT COUNT(*) as recovered_products FROM m_product;\n")

print(f"抽出完了: {len(products)}製品")
