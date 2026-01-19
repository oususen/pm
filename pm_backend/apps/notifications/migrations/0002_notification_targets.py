from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_alter_userprofile_division_group_team'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='target_department',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='notifications',
                to='accounts.department',
                verbose_name='対象部署',
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='target_position',
            field=models.CharField(blank=True, max_length=100, verbose_name='対象役職'),
        ),
    ]
