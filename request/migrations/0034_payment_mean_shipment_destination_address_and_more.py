# Generated by Django 5.0.1 on 2024-02-16 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0033_alter_payment_request_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='mean',
            field=models.CharField(db_index=True, max_length=15, null=True, verbose_name='Payment Methods'),
        ),
        migrations.AddField(
            model_name='shipment',
            name='destination_address',
            field=models.CharField(blank=True, db_index=True, max_length=150),
        ),
        migrations.AddField(
            model_name='shipment',
            name='destination_location',
            field=models.CharField(blank=True, db_index=True, max_length=150),
        ),
    ]