# Generated by Django 5.0.1 on 2024-03-31 14:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0048_alter_agent_managers'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='court',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='courts', to='request.court'),
        ),
    ]