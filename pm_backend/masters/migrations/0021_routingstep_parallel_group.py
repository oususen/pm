from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0020_routingstep_parallel_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='routingstep',
            name='parallel_group',
            field=models.IntegerField(default=1, verbose_name='並列グループ'),
        ),
        migrations.AlterUniqueTogether(
            name='routingstep',
            unique_together={('routing', 'step_no', 'parallel_group')},
        ),
    ]
