from django.db import migrations, models
from collections import defaultdict


def normalize_sequence_no(apps, schema_editor):
    LineBacklog = apps.get_model('production', 'LineBacklog')

    # group rows with NULL sequence_no by unique key
    null_qs = LineBacklog.objects.filter(sequence_no__isnull=True).order_by(
        'plan_date', 'process_id', 'product_id', 'line_id', 'id'
    )
    groups = defaultdict(list)
    for row in null_qs:
        key = (row.plan_date, row.process_id, row.product_id, row.line_id)
        groups[key].append(row)

    for key, rows in groups.items():
        plan_date, process_id, product_id, line_id = key
        # collect used sequence numbers for this key
        used = set(
            LineBacklog.objects.filter(
                plan_date=plan_date,
                process_id=process_id,
                product_id=product_id,
                line_id=line_id,
                sequence_no__isnull=False,
            ).values_list('sequence_no', flat=True)
        )
        next_seq = 0
        for row in rows:
            # find the next unused sequence_no
            while next_seq in used:
                next_seq += 1
            row.sequence_no = next_seq
            row.save(update_fields=['sequence_no'])
            used.add(next_seq)
            next_seq += 1


class Migration(migrations.Migration):

    dependencies = [
        ('production', '0008_linebacklog_scrap_adjust_qty'),
    ]

    operations = [
        migrations.RunPython(normalize_sequence_no, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='linebacklog',
            name='sequence_no',
            field=models.IntegerField(default=0),
        ),
    ]
