# Generated by Django 5.0.1 on 2024-01-28 11:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0016_service_cob'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='user_cob',
            field=models.ForeignKey(blank=True, default=39, help_text='Country of birth', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_cob', to='request.country'),
        ),
    ]