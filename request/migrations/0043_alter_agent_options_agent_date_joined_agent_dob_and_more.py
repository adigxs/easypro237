# Generated by Django 5.0.1 on 2024-03-28 10:51

import django.contrib.auth.validators
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('request', '0042_payment_message_alter_payment_created_on_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agent',
            options={'permissions': [('view_user_birthday_certificate', 'Can view and download birthday certificate'), ('view_user_passport', 'Can view and download birthday certificate'), ('view_proof_of_stay', 'Can view and download birthday certificate'), ('view_id_card', 'Can view and download birthday certificate'), ('view_wedding_certificate', 'Can view and download birthday certificate'), ('view_destination_address', 'Can view and download birthday certificate'), ('view_destination_location', 'Can view attachment details'), ('change_request_status', 'Can change status of a request')]},
        ),
        migrations.AddField(
            model_name='agent',
            name='date_joined',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined'),
        ),
        migrations.AddField(
            model_name='agent',
            name='dob',
            field=models.DateField(blank=True, db_index=True, help_text='Date of birth', null=True),
        ),
        migrations.AddField(
            model_name='agent',
            name='gender',
            field=models.CharField(choices=[('M', 'M'), ('F', 'F')], default='M', max_length=1),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='agent',
            name='groups',
            field=models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups'),
        ),
        migrations.AddField(
            model_name='agent',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active'),
        ),
        migrations.AddField(
            model_name='agent',
            name='is_staff',
            field=models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status'),
        ),
        migrations.AddField(
            model_name='agent',
            name='is_superuser',
            field=models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status'),
        ),
        migrations.AddField(
            model_name='agent',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True, verbose_name='last login'),
        ),
        migrations.AddField(
            model_name='agent',
            name='logo',
            field=models.FileField(blank=True, null=True, upload_to='Agents', verbose_name='Agent profile picture'),
        ),
        migrations.AddField(
            model_name='agent',
            name='password',
            field=models.CharField(default='pbkdf2_sha256$720000$XnhHjmywHyBIvIEhJhNczd$xG7Uf8+E7MsmNWyuCykalsZrIIkTlxaWiTjbb7gDRpk=', max_length=128, verbose_name='password'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='agent',
            name='phone',
            field=models.TextField(default='699999999', help_text='Phone'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='agent',
            name='user_permissions',
            field=models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions'),
        ),
        migrations.AddField(
            model_name='agent',
            name='username',
            field=models.CharField(default='easypro1', error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=False, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='agent',
            name='verify',
            field=models.BooleanField(default=False, help_text='Ensure email or phone is verified'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='email address'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='first_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='agent',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='agent',
            name='last_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='last name'),
        ),
    ]
