# Generated by Django 5.0.1 on 2024-02-10 13:29

import request.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0029_country_slug_alter_request_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('created_on', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('request_code', models.CharField(db_index=True, max_length=24, null=True)),
                ('label', models.CharField(db_index=True, default='', max_length=150, null=True)),
                ('amount', models.FloatField(db_index=True)),
                ('pay_token', models.CharField(db_index=True, max_length=36, null=True)),
                ('operator_tx_id', models.CharField(db_index=True, max_length=50, null=True)),
                ('operator_user_id', models.CharField(db_index=True, max_length=50, null=True)),
                ('status', models.CharField(db_index=True, default='PENDING', max_length=36)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TrashModel',
            fields=[
                ('id', models.CharField(default=request.models.get_object_id, max_length=36, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('model_name', models.CharField(db_index=True, max_length=100)),
                ('data', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]