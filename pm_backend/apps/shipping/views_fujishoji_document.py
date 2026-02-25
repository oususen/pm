# -*- coding: utf-8 -*-
"""
富士商事向け出荷指示書API
ティエラ顧客のフロア製品群を対象に、指定日の出荷数量を返す
"""

import math
import os
import tempfile
from datetime import datetime
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum

# フロア製品の固定マッピング（製品コード → 番号・俗称・色）
FLOOR_PRODUCT_MAPPING = [
    {"product_code": "YD40006245", "number": "1", "label": "U-5 CAB",      "color": "#FFB6C1"},
    {"product_code": "YD40006630", "number": "2", "label": "U-5 CANOPY",   "color": "#87CEEB"},
    {"product_code": "YD40006237", "number": "3", "label": "55UR CAB",     "color": "#90EE90"},
    {"product_code": "YD40006618", "number": "4", "label": "55UR CANOPY",  "color": "#FFD700"},
    {"product_code": "YD40002946", "number": "5", "label": "30/40UR",      "color": "#FFA500"},
    {"product_code": "YD40006842", "number": "A", "label": "5t-EN CAB",    "color": "#CD853F"},
    {"product_code": "YD40007003", "number": "B", "label": "3t-EN CAB",    "color": "#D3D3D3"},
    {"product_code": "YD40007243", "number": "C", "label": "U-5NA CAB",    "color": "#4682B4"},
    {"product_code": "YD40007372", "number": "D", "label": "U-5NA CANOPY", "color": "#2F4F4F"},
    {"product_code": "YD40007722", "number": "E", "label": "U-6EN 5tKTEG","color": "#FF6347"},
    {"product_code": "YD40007688", "number": "F", "label": "55US-6 KTEG",  "color": "#9370DB"},
]

FLOOR_PRODUCT_CODES = [p["product_code"] for p in FLOOR_PRODUCT_MAPPING]

# 台車・便の設定
ITEMS_PER_CART = 2      # 台車1台に積める個数
CARTS_PER_TRIP = 14     # 1便あたりの台車数


def _resolve_creator_name(request) -> str:
    """ログインユーザーからPDF作成者名（姓のみ）を解決する。"""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return "システム"

    last_name = (user.last_name or "").strip()
    if last_name:
        return last_name

    username = (user.get_username() or "").strip()
    if username:
        return username

    email = (getattr(user, "email", "") or "").strip()
    return email or "システム"


def _get_floor_qty_map(tiera, target_date):
    """
    指定日・ティエラ顧客のフロア製品数量を集計して {product_code: qty} を返す。
    shipping_order_service と同じく OPEN + FIRM 受注のみ対象。
    """
    from orders.core.models import OrderLine

    firm_filter = Q(order_type='FIRM') | Q(order_type__isnull=True, order__order_type='FIRM')
    qs = (
        OrderLine.objects.filter(
            order__customer=tiera,
            order__status='OPEN',
            due_date=target_date,
            product_code__in=FLOOR_PRODUCT_CODES,
            quantity__gt=0,
        )
        .filter(firm_filter)
        .values("product_code")
        .annotate(total_qty=Sum("quantity"))
    )
    return {row["product_code"]: int(row["total_qty"] or 0) for row in qs}


def _build_cart_layout(products_with_qty):
    """
    製品リスト（番号順）から①便・②便の台車レイアウトを生成する。
    各製品の台車数 = ceil(qty / ITEMS_PER_CART)
    ①便14台車を超えたら②便へ溢れる。
    1製品をできるだけ連続して積む（製品間をまたいで余白を作らない）。
    台車ごとに { product_code, number, label, color, qty_in_cart } を返す。
    """
    trips = [[], []]  # [①便, ②便]
    current_trip = 0

    for p in products_with_qty:
        qty = p["qty"]
        if qty <= 0:
            continue
        remaining = qty
        while remaining > 0:
            cart_qty = min(remaining, ITEMS_PER_CART)
            if current_trip < 2 and len(trips[current_trip]) >= CARTS_PER_TRIP:
                current_trip += 1
            if current_trip >= 2:
                # 2便以上は切り捨て（想定外）
                break
            trips[current_trip].append({
                "product_code": p["product_code"],
                "number": p["number"],
                "label": p["label"],
                "color": p["color"],
                "qty_in_cart": cart_qty,
            })
            remaining -= cart_qty

    return trips


@require_http_methods(["GET"])
def get_fujishoji_available_dates(request):
    """
    富士商事出荷指示書の利用可能日付一覧（フロア製品の受注がある日）を返す。
    """
    try:
        from orders.core.models import OrderLine
        from masters.models import Customer

        tiera = Customer.objects.get(customer_code="000001")
        firm_filter = Q(order_type='FIRM') | Q(order_type__isnull=True, order__order_type='FIRM')
        dates = (
            OrderLine.objects.filter(
                order__customer=tiera,
                order__status='OPEN',
                product_code__in=FLOOR_PRODUCT_CODES,
                quantity__gt=0,
            )
            .filter(firm_filter)
            .values_list("due_date", flat=True)
            .distinct()
            .order_by("-due_date")
        )
        date_strings = sorted(set(d.isoformat() for d in dates if d), reverse=True)
        return JsonResponse({"dates": date_strings, "count": len(date_strings)})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_fujishoji_document_data(request, target_date_str):
    """
    指定日のフロア製品出荷数量を返す（ティエラ顧客の受注データから）

    Returns:
        JSON: {
            "date": "2026-02-25",
            "products": [
                {
                    "product_code": "YD40006245",
                    "number": "1",
                    "label": "U-5 CAB",
                    "color": "#FFB6C1",
                    "qty": 14,
                    "carts": 7
                },
                ...
            ],
            "trip1": [ { product_code, number, label, color, qty_in_cart }, ... ],
            "trip2": [ ... ],
            "carts_per_trip": 14,
            "items_per_cart": 2
        }
    """
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "日付形式が不正です（YYYY-MM-DD）"}, status=400)

    try:
        from orders.core.models import OrderLine
        from masters.models import Customer

        # ティエラ顧客を取得
        try:
            tiera = Customer.objects.get(customer_code="000001")
        except Customer.DoesNotExist:
            return JsonResponse({"error": "ティエラ顧客（000001）が見つかりません"}, status=404)

        # 指定日のフロア製品受注明細を集計（OPEN + FIRM のみ）
        qty_map = _get_floor_qty_map(tiera, target_date)

        # マッピング順に整形
        import math
        products = []
        for p in FLOOR_PRODUCT_MAPPING:
            qty = qty_map.get(p["product_code"], 0)
            carts = math.ceil(qty / ITEMS_PER_CART) if qty > 0 else 0
            products.append({
                "product_code": p["product_code"],
                "number": p["number"],
                "label": p["label"],
                "color": p["color"],
                "qty": qty,
                "carts": carts,
            })

        # 台車レイアウト生成
        trips = _build_cart_layout(products)

        return JsonResponse({
            "date": target_date_str,
            "products": products,
            "trip1": trips[0],
            "trip2": trips[1],
            "carts_per_trip": CARTS_PER_TRIP,
            "items_per_cart": ITEMS_PER_CART,
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_fujishoji_pdf_api(request):
    """
    富士商事出荷指示書 PDF を生成してダウンロードさせる。
    Body: { "target_date": "YYYY-MM-DD" }
    """
    import json
    try:
        body = json.loads(request.body)
        target_date_str = body.get("target_date", "")
    except Exception:
        return JsonResponse({"error": "リクエスト形式が不正です"}, status=400)

    if not target_date_str:
        return JsonResponse({"error": "target_date が必要です"}, status=400)

    # データ取得（get_fujishoji_document_data と同じロジック）
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "日付形式が不正です（YYYY-MM-DD）"}, status=400)

    try:
        from masters.models import Customer
        from shipping.services.fujishoji_pdf_generator import generate_fujishoji_pdf

        creator_name = _resolve_creator_name(request)
        tiera = Customer.objects.get(customer_code="000001")
        # 受注数集計（OPEN + FIRM のみ）
        qty_map = _get_floor_qty_map(tiera, target_date)

        products = []
        for p in FLOOR_PRODUCT_MAPPING:
            qty = qty_map.get(p["product_code"], 0)
            carts = math.ceil(qty / ITEMS_PER_CART) if qty > 0 else 0
            products.append({**p, "qty": qty, "carts": carts})

        trips = _build_cart_layout(products)
        doc_data = {
            "date": target_date_str,
            "products": products,
            "trip1": trips[0],
            "trip2": trips[1],
            "carts_per_trip": CARTS_PER_TRIP,
            "items_per_cart": ITEMS_PER_CART,
            "creator_name": creator_name,
        }

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        generate_fujishoji_pdf(doc_data, tmp_path, creator_name=creator_name)

        response = FileResponse(
            open(tmp_path, "rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"富士商事出荷指示書_{target_date_str}.pdf",
        )
        response["X-Temp-File"] = tmp_path  # クリーンアップ用（本番ではmiddleware等で対応）
        return response

    except Customer.DoesNotExist:
        return JsonResponse({"error": "ティエラ顧客（000001）が見つかりません"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
