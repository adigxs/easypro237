# Generated by Django 5.0.1 on 2024-01-24 12:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0005_agent_email'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='court',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='municipality',
            name='court',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.court'),
        ),
        migrations.RemoveField(
            model_name='court',
            name='municipality',
        ),
    ]
