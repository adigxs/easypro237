# Generated by Django 5.0.1 on 2024-02-26 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0039_alter_payment_unique_together_alter_payment_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(db_index=True, default='PENDING', max_length=36),
        ),
        migrations.AlterUniqueTogether(
            name='payment',
            unique_together={('request_code', 'status')},
        ),
    ]