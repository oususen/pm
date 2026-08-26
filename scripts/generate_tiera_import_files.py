import csv
import sys
from pathlib import Path

from openpyxl import Workbook


PRODUCT_HEADERS = [
    "構成品番",
    "品名規格",
    "品番区分名",
    "ライン情報",
    "ライン名",
    "工程情報",
    "工程名",
    "後工程",
    "後工程名",
    "管理区分",
    "最終品",
    "ライン最終品",
    "単位",
    "単価",
    "標準LT(日)",
    "自工程LT(日)",
    "機種名",
    "製品グループ",
    "グループ名",
    "移動先",
    "比重(g/cm³)",
    "縦(mm)",
    "横(mm)",
    "厚さ(mm)",
    "発注倍数",
    "最小発注数",
    "使用容器",
    "容器入り数",
    "置き場1",
    "置き場2",
    "置き場3",
    "置き場4",
]


BOM_HEADERS = [
    "完成品",
    "親品番",
    "子品番",
    "数量",
    "工程コード",
    "工程名",
    "ラインコード",
    "ライン名",
    "調達区分",
    "仕入先コード",
    "仕入先名",
    "ＬＴ(日)",
    "所要時間(分)",
    "時間単位",
]


SUPPLIER_CODE_MAP = {
    "株式会社三原金属工業": "000387",
    "抱月工業株式会社": "000259",
    "株式会社大豊製作所": "000132",
    "株式会社日立建機ティエラ": "G00001",
}


PROCESS_LINE_MAP = {
    "レーザー加工１": ("0801", "L0801"),
    "ＹＢ－００３　ブレーキ１２５ｔ": ("4010", "L0010"),
    "ＷＭ－０２８　製缶セルライン": ("4023", "L3104"),
}


def read_rows(src: Path):
    with src.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def leading_spaces(value: str) -> int:
    count = 0
    for ch in value:
        if ch == "■":
            count += 1
        else:
            break
    return count


def normalize_code(raw_code: str, is_outsourced: bool) -> str:
    code = (raw_code or "").lstrip("■").strip()
    if is_outsourced and code and not code.endswith("G"):
        return f"{code}G"
    return code


def classify_sourcing(row):
    process_type = (row.get("加工区分名") or "").strip()
    category = (row.get("品番区分名") or "").strip()
    if process_type == "外作":
        return "外注", True
    if category == "購入品":
        return "購買", False
    return "自社製造", False


def write_csv(path: Path, headers, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def write_xlsx(path: Path, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "入力用"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)


def build_product_row(code, name, category, unit_price, cumulative_lt, is_final, is_outsourced, process_code="", line_code=""):
    category_name = "外作品" if is_outsourced else category
    return [
        code,
        name,
        category_name,
        line_code,
        "",
        process_code,
        "",
        "",
        "",
        "",
        "はい" if is_final else "",
        "はい" if is_final else "",
        "",
        unit_price,
        str(cumulative_lt),
        "",
        "",
        "",
        "",
        "社内ライン" if is_outsourced else "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]


def build_bom_row(final_code, parent_code, child_code, quantity, sourcing_type, supplier_code, supplier_name, item_lt, process_code="", line_code=""):
    lead_time_days = str(item_lt)
    duration_min = ""
    time_unit = "日"
    normalized_process_code = process_code
    normalized_line_code = line_code

    if sourcing_type == "自社製造":
        if item_lt <= 0:
            lead_time_days = "0"
            duration_min = "1"
            time_unit = "分"
    elif sourcing_type == "外注":
        normalized_process_code = "G"
        normalized_line_code = ""
    elif sourcing_type == "購買":
        normalized_process_code = "PURCHASE"
        normalized_line_code = ""

    return [
        final_code,
        parent_code,
        child_code,
        quantity,
        normalized_process_code,
        "",
        normalized_line_code,
        "",
        sourcing_type,
        supplier_code,
        supplier_name,
        lead_time_days,
        duration_min,
        time_unit,
    ]


def generate_hierarchical(rows):
    parsed = []
    for row in rows:
        raw_code = row.get("構成品番") or ""
        sourcing_type, is_outsourced = classify_sourcing(row)
        code = normalize_code(raw_code, is_outsourced)
        if not code:
            continue
        supplier_name = (row.get("加工先名") or "").strip()
        process_code, line_code = PROCESS_LINE_MAP.get(supplier_name, ("", ""))
        parsed.append({
            "indent": leading_spaces(raw_code),
            "code": code,
            "name": (row.get("品名規格") or "").strip(),
            "category": (row.get("品番区分名") or "").strip(),
            "cumulative_lt": int(str(row.get("積算LT") or "0").strip() or "0"),
            "quantity": (row.get("積算自数") or "").strip(),
            "supplier_name": supplier_name,
            "supplier_code": SUPPLIER_CODE_MAP.get(supplier_name, ""),
            "process_code": process_code,
            "line_code": line_code,
            "sourcing_type": sourcing_type,
            "is_outsourced": is_outsourced,
            "unit_price": (row.get("合計単価") or "").strip(),
            "final_code": (row.get("品番") or "").strip(),
        })

    product_rows = []
    bom_rows = []
    seen = set()
    final_code = parsed[0]["final_code"] if parsed else ""

    for item in parsed:
        code = item["code"]
        if code in seen:
            continue
        seen.add(code)
        product_rows.append(build_product_row(
            code=code,
            name=item["name"],
            category=item["category"],
            unit_price=item["unit_price"],
            cumulative_lt=item["cumulative_lt"],
            is_final=(code == final_code),
            is_outsourced=item["is_outsourced"],
            process_code=item["process_code"],
            line_code=item["line_code"],
        ))

    stack = []
    for index, item in enumerate(parsed):
        if index == 0:
            stack = [(item["indent"], item["code"], item["cumulative_lt"])]
            continue

        while stack and stack[-1][0] >= item["indent"]:
            stack.pop()

        if stack:
            parent_code = stack[-1][1]
            parent_cumulative_lt = stack[-1][2]
        else:
            parent_code = final_code
            parent_cumulative_lt = parsed[0]["cumulative_lt"]

        item_lt = item["cumulative_lt"] - parent_cumulative_lt
        if item_lt < 0:
            item_lt = 0

        bom_rows.append(build_bom_row(
            final_code=final_code,
            parent_code=parent_code,
            child_code=item["code"],
            quantity=item["quantity"],
            sourcing_type=item["sourcing_type"],
            supplier_code=item["supplier_code"],
            supplier_name=item["supplier_name"],
            item_lt=item_lt,
            process_code=item["process_code"],
            line_code=item["line_code"],
        ))
        stack.append((item["indent"], item["code"], item["cumulative_lt"]))

    return product_rows, bom_rows


def generate_for_part(part_code: str):
    src = Path(rf"D:\pm\{part_code}.csv")
    rows = read_rows(src)
    product_rows, bom_rows = generate_hierarchical(rows)

    product_csv = Path(rf"D:\pm\{part_code}_product_update_import.csv")
    product_xlsx = Path(rf"D:\pm\{part_code}_product_update_import.xlsx")
    bom_csv = Path(rf"D:\pm\{part_code}_bom_import.csv")
    bom_xlsx = Path(rf"D:\pm\{part_code}_bom_import.xlsx")

    write_csv(product_csv, PRODUCT_HEADERS, product_rows)
    write_csv(bom_csv, BOM_HEADERS, bom_rows)
    write_xlsx(product_xlsx, PRODUCT_HEADERS, product_rows)
    write_xlsx(bom_xlsx, BOM_HEADERS, bom_rows)

    print(product_csv)
    print(product_xlsx)
    print(bom_csv)
    print(bom_xlsx)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/generate_tiera_import_files.py <part_code> [<part_code> ...]")
    for part_code in sys.argv[1:]:
        generate_for_part(part_code)


if __name__ == "__main__":
    main()
