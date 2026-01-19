from django.db import migrations, models


def migrate_targets(apps, schema_editor):
    Notification = apps.get_model('notifications', 'Notification')
    for notification in Notification.objects.all():
        if getattr(notification, 'target_department_id', None):
            notification.target_departments.add(notification.target_department_id)
        position = getattr(notification, 'target_position', '') or ''
        if position:
            notification.target_positions = [position]
            notification.save(update_fields=['target_positions'])


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0002_notification_targets'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='target_departments',
            field=models.ManyToManyField(
                blank=True,
                related_name='notifications',
                to='accounts.department',
                verbose_name='対象部署',
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='target_positions',
            field=models.JSONField(blank=True, default=list, verbose_name='対象役職'),
        ),
        migrations.RunPython(migrate_targets, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='notification',
            name='target_department',
        ),
        migrations.RemoveField(
            model_name='notification',
            name='target_position',
        ),
    ]
