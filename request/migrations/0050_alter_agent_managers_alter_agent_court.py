# Generated by Django 5.0.1 on 2024-03-31 15:50

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0049_alter_agent_court'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='agent',
            managers=[
            ],
        ),
        migrations.AlterField(
            model_name='agent',
            name='court',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='request.court'),
        ),
    ]