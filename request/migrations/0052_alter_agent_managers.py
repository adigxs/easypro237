# Generated by Django 5.0.1 on 2024-03-31 17:29

import django.contrib.auth.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0051_agent_region'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='agent',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
