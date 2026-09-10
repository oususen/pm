from django.db import migrations


def move_forecast_notes(apps, schema_editor):
    """既存の内示連絡を共通連絡へ移す。確定明細の連絡は変更しない。"""
    adjustment = apps.get_model('orders', 'KubotaSakaiDueAdjustment')
    shared = apps.get_model('orders', 'KubotaSakaiDueSharedNote')
    alias = schema_editor.connection.alias
    rows = adjustment.objects.using(alias).filter(order_type='FORECAST').exclude(coordination_note='').order_by('id')
    grouped = {}
    for row in rows:
        key = (row.product_code, row.ship_to_code or '', row.due_date)
        grouped.setdefault(key, [])
        if row.coordination_note not in grouped[key]:
            grouped[key].append(row.coordination_note)
    for (product, ship_to, due_date), notes in grouped.items():
        key = dict(product_code=product, ship_to_code=ship_to, due_date=due_date)
        existing = shared.objects.using(alias).filter(**key).first()
        if existing and existing.coordination_note and existing.coordination_note not in notes:
            notes.insert(0, existing.coordination_note)
        text = '\n'.join(notes)
        if len(text) > 200:
            raise ValueError(f'共通連絡が200文字を超えるため移行を中止します: {product} / {ship_to} / {due_date}')
        shared.objects.using(alias).update_or_create(**key, defaults={'coordination_note': text})
    rows.update(coordination_note='')


class Migration(migrations.Migration):
    atomic = True
    dependencies = [('orders', '0068_kubota_sakai_due_shared_note')]
    operations = [migrations.RunPython(move_forecast_notes, atomic=True)]
