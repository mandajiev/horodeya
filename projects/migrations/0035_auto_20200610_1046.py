# Generated by Django 2.2.8 on 2020-06-10 07:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0034_auto_20200609_1230'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='verified',
        ),
        migrations.AddField(
            model_name='project',
            name='verified_status',
            field=models.CharField(choices=[('review', 'review'), ('accepted', 'accepted'), ('rejected', 'rejected')], default='review', max_length=20),
        ),
    ]
