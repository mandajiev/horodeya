# Generated by Django 2.2.8 on 2020-06-16 13:45

from django.db import migrations, models
import rules.contrib.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0036_auto_20200616_0756'),
    ]

    operations = [
        migrations.CreateModel(
            name='BugReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(editable=False)),
                ('updated_at', models.DateTimeField(editable=False)),
                ('email', models.EmailField(max_length=254)),
                ('message', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=(rules.contrib.models.RulesModelMixin, models.Model),
        ),
        migrations.AlterField(
            model_name='project',
            name='report_period',
            field=models.CharField(choices=[('weekly', 'weekly'), ('monthly', 'montly'), ('twoweeks', 'twoweeks')], default='weekly', max_length=50, verbose_name='report_period'),
        ),
        migrations.AlterField(
            model_name='project',
            name='verified_status',
            field=models.CharField(choices=[('review', 'review'), ('accepted', 'accepted'), ('rejected', 'rejected')], default='review', max_length=20, null=True, verbose_name='verified_status'),
        ),
    ]