# Generated by Django 2.2.6 on 2019-10-31 08:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_auto_20191028_1013'),
    ]

    operations = [
        migrations.RenameField(
            model_name='legalentity',
            old_name='edited_at',
            new_name='updated_at',
        ),
        migrations.RenameField(
            model_name='project',
            old_name='edited_at',
            new_name='updated_at',
        ),
        migrations.RenameField(
            model_name='report',
            old_name='edited_at',
            new_name='updated_at',
        ),
    ]
