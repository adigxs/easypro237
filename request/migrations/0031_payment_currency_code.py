# Generated by Django 5.0.1 on 2024-02-10 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0030_payment_trashmodel'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='currency_code',
            field=models.CharField(default='XAF', help_text='Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ...', max_length=5),
        ),
    ]