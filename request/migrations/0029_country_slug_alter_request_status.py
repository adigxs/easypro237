# Generated by Django 5.0.1 on 2024-02-10 08:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0028_request_court'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='slug',
            field=models.SlugField(blank=True, editable=False, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='request',
            name='status',
            field=models.CharField(choices=[('STARTED', 'STARTED'), ('PENDING', 'PENDING'), ('COMMITTED', 'COMMITTED'), ('COMPLETED', 'COMPLETED')], db_index=True, default='STARTED', max_length=15),
        ),
    ]