# Generated by Django 5.0.1 on 2024-02-03 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('request', '0020_request_proof_of_stay'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='user_close_friend_number',
            field=models.CharField(blank=True, db_index=True, help_text="Close friend phone's number", max_length=15, null=True),
        ),
    ]