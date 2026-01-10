from django.db import migrations, models


def classify_line_types(apps, schema_editor):
    Line = apps.get_model('masters', 'Line')
    for line in Line.objects.all():
        line_code = (line.line_code or '').upper()
        line_name = line.line_name or ''
        if line_code.startswith('SUP') or line_code.startswith('PURCHASE') or '仕入' in line_name or '購買' in line_name:
            line_type = 'PURCHASE'
        elif line_code.startswith('GAISAKU') or '外作' in line_name or '外注' in line_name:
            line_type = 'OUTSOURCE'
        else:
            line_type = 'PROD'
        line.line_type = line_type
        line.save(update_fields=['line_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0022_alter_routingstep_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='line',
            name='line_type',
            field=models.CharField(
                choices=[('PROD', '生産'), ('PURCHASE', '購買'), ('OUTSOURCE', '外作'), ('OTHER', 'その他')],
                default='PROD',
                max_length=20,
                verbose_name='ライン種別',
            ),
        ),
        migrations.RunPython(classify_line_types, migrations.RunPython.noop),
    ]
