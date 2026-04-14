from django.db import migrations


INITIAL_TRUCKS = [
    {
        'name': 'NO_2_10T',
        'width': 2400,
        'depth': 9740,
        'height': 2400,
        'max_weight': 10000,
        'departure_time': '11:00:00',
        'arrival_time': '15:15:00',
        'arrival_day_offset': 0,
        'default_use': True,
        'display_order': 1,
    },
    {
        'name': 'NO_3_10T',
        'width': 2400,
        'depth': 9500,
        'height': 2400,
        'max_weight': 10000,
        'departure_time': '18:00:00',
        'arrival_time': '10:00:00',
        'arrival_day_offset': 1,
        'default_use': True,
        'display_order': 2,
    },
    {
        'name': 'NO_4_10T',
        'width': 2400,
        'depth': 9000,
        'height': 2400,
        'max_weight': 10000,
        'departure_time': '10:00:00',
        'arrival_time': '12:00:00',
        'arrival_day_offset': 0,
        'default_use': True,
        'display_order': 3,
    },
    {
        'name': 'NO_5_10T',
        'width': 2400,
        'depth': 6100,
        'height': 2400,
        'max_weight': 4000,
        'departure_time': '18:00:00',
        'arrival_time': '10:00:00',
        'arrival_day_offset': 1,
        'default_use': False,
        'display_order': 4,
    },
]


def seed_initial_trucks(apps, schema_editor):
    KubotaSakaiTruck = apps.get_model('masters', 'KubotaSakaiTruck')
    for item in INITIAL_TRUCKS:
        KubotaSakaiTruck.objects.get_or_create(
            name=item['name'],
            defaults=item,
        )


def delete_initial_trucks(apps, schema_editor):
    KubotaSakaiTruck = apps.get_model('masters', 'KubotaSakaiTruck')
    KubotaSakaiTruck.objects.filter(
        name__in=[t['name'] for t in INITIAL_TRUCKS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0044_add_kubota_sakai_truck'),
    ]

    operations = [
        migrations.RunPython(seed_initial_trucks, delete_initial_trucks),
    ]
