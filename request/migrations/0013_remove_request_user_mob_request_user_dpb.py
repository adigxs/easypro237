# Generated by Django 5.0.1 on 2024-01-25 17:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0012_alter_request_user_last_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='request',
            name='user_mob',
        ),
        migrations.AddField(
            model_name='request',
            name='user_dpb',
            field=models.ForeignKey(blank=True, help_text='Department of birth', max_length=150, null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.department'),
        ),
    ]
