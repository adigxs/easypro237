# Generated by Django 5.0.1 on 2024-03-03 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0040_alter_payment_status_alter_payment_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='dispursement',
            field=models.PositiveIntegerField(default=0, verbose_name='Dispursement fee of the service'),
        ),
    ]
