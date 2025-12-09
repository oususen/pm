from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0007_routingstep_output_product'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoutingStepMaterial',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('quantity', models.DecimalField(decimal_places=3, max_digits=12, verbose_name='数量')),
                ('consume_timing', models.CharField(choices=[('START', '工程開始'), ('END', '工程完了')], default='START', max_length=10, verbose_name='消費タイミング')),
                ('remark', models.CharField(blank=True, max_length=200, null=True, verbose_name='備考')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新日時')),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routing_step_materials', to='masters.product', verbose_name='部品')),
                ('routing_step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='masters.routingstep', verbose_name='工程')),
            ],
            options={
                'verbose_name': '工程別部品消費',
                'verbose_name_plural': '工程別部品消費',
                'db_table': 'm_routing_step_material',
                'unique_together': {('routing_step', 'component')},
            },
        ),
    ]
