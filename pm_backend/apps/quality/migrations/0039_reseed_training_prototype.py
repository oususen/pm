from importlib import import_module

from django.db import migrations


def reseed_training_data(apps, schema_editor):
    module = import_module("quality.migrations.0038_seed_training_prototype")
    module.seed_training_data(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("quality", "0038_seed_training_prototype"),
    ]

    operations = [
        migrations.RunPython(reseed_training_data, migrations.RunPython.noop),
    ]
