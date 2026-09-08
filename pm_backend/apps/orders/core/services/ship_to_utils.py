from shipping.models import ShipToLeadTime


def normalize_kubota_ship_to_code(value):
    """クボタの数値納入先コードを5桁にそろえる。英数字コードは維持する。"""
    code = (value or '').strip()
    numeric_code = code.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    if numeric_code and numeric_code.isascii() and numeric_code.isdecimal():
        return numeric_code.zfill(5)
    return code


def ensure_ship_to_records(raw_records, customer):
    """受注取り込み時に新しい納入地をShipToLeadTimeに自動登録する。
    既存レコードのship_to_nameが空で、今回のデータに名前がある場合は更新する。
    """
    ship_to_map = {}
    for raw in raw_records:
        payload = raw.raw_payload or {}
        code = (payload.get('ship_to') or payload.get('ship_to_code') or '').strip()
        if not code:
            continue
        name = (payload.get('ship_to_name') or '').strip()
        if code not in ship_to_map or (name and not ship_to_map[code]):
            ship_to_map[code] = name

    if not ship_to_map:
        return

    existing = {
        stlt.ship_to_code: stlt
        for stlt in ShipToLeadTime.objects.filter(
            customer=customer, ship_to_code__in=ship_to_map.keys()
        )
    }

    new_records = []
    for code, name in ship_to_map.items():
        if code in existing:
            stlt = existing[code]
            if name and not stlt.ship_to_name:
                stlt.ship_to_name = name
                stlt.save(update_fields=['ship_to_name'])
        else:
            new_records.append(ShipToLeadTime(
                customer=customer,
                ship_to_code=code,
                ship_to_name=name,
                additional_days=0,
                is_active=True,
            ))

    if new_records:
        ShipToLeadTime.objects.bulk_create(new_records, ignore_conflicts=True)
