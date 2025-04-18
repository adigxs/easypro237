# Generated by Django 5.0.4 on 2025-03-18 10:08

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
import request.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of the company ...', max_length=255)),
                ('percentage', models.PositiveIntegerField(default=0, help_text='Percentage the company earns for disbursement on each transaction. Eg: 5, 3, 25 etc...')),
            ],
            options={
                'verbose_name_plural': 'Companies',
            },
        ),
        migrations.CreateModel(
            name='Court',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=150, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('type', models.CharField(choices=[('CFI', 'CFI'), ('CFHI', 'CFHI')], db_index=True, max_length=150)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='TrashModel',
            fields=[
                ('id', models.CharField(default=request.models.get_object_id, max_length=255, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('model_name', models.CharField(db_index=True, max_length=100)),
                ('data', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('iso2', models.CharField(db_index=True, max_length=2)),
                ('iso3', models.CharField(db_index=True, max_length=3)),
                ('lang', models.CharField(db_index=True, max_length=2)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('slug', models.SlugField(blank=True, editable=False, max_length=150, null=True)),
            ],
            options={
                'verbose_name_plural': 'Countries',
                'unique_together': {('iso2', 'iso3'), ('iso3', 'lang'), ('name', 'iso2')},
            },
        ),
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('gender', models.CharField(choices=[('M', 'M'), ('F', 'F')], max_length=1)),
                ('verify', models.BooleanField(default=False, help_text='Ensure email or phone is verified')),
                ('phone', models.TextField(help_text='Phone')),
                ('dob', models.DateField(blank=True, db_index=True, help_text='Date of birth', null=True)),
                ('logo', models.FileField(blank=True, null=True, upload_to='Agents', verbose_name='Agent profile picture')),
                ('region_code', models.CharField(blank=True, db_index=True, max_length=2, null=True)),
                ('is_csa', models.BooleanField(default=False)),
                ('pending_task_count', models.IntegerField(default=0)),
                ('lang', models.CharField(blank=True, db_index=True, default='en', help_text='Agent language', max_length=2, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
                ('court', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='request.court')),
            ],
            options={
                'ordering': ['first_name', 'last_name'],
                'permissions': [('view_user_birthday_certificate', 'Can view and download birthday certificate'), ('view_user_passport', 'Can view user passport'), ('view_proof_of_stay', 'Can view proof of stay'), ('view_id_card', 'Can view ID card'), ('view_wedding_certificate', 'Can view wedding certificate'), ('view_destination_address', 'Can view destination address'), ('view_destination_location', 'Can view destination location'), ('change_request_status', 'Can change status of a request')],
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('region_code', models.CharField(blank=True, db_index=True, help_text='Region code', max_length=2, null=True)),
                ('name', models.CharField(max_length=150)),
                ('slug', models.SlugField(max_length=150, unique=True)),
            ],
            options={
                'unique_together': {('region_code', 'name')},
            },
        ),
        migrations.AddField(
            model_name='court',
            name='department',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.department'),
        ),
        migrations.CreateModel(
            name='Municipality',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=150)),
                ('slug', models.SlugField(max_length=150, unique=True)),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='request.department')),
            ],
            options={
                'verbose_name_plural': 'Municipalities',
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('request_code', models.CharField(db_index=True, max_length=24, null=True)),
                ('label', models.CharField(db_index=True, default='', max_length=150, null=True)),
                ('amount', models.FloatField(db_index=True)),
                ('pay_token', models.CharField(db_index=True, max_length=36, null=True)),
                ('mean', models.CharField(db_index=True, max_length=15, null=True, verbose_name='Payment Methods')),
                ('user_lang', models.CharField(db_index=True, default='en-us', max_length=2, null=True, verbose_name='User Language')),
                ('operator_tx_id', models.CharField(db_index=True, max_length=50, null=True)),
                ('operator_user_id', models.CharField(db_index=True, max_length=50, null=True)),
                ('status', models.CharField(db_index=True, default='PENDING', max_length=36)),
                ('currency_code', models.CharField(default='XAF', help_text='Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ...', max_length=5)),
                ('message', models.CharField(default='', help_text='Message rendered by the gateway for initiated payment transaction ...', max_length=255)),
            ],
            options={
                'unique_together': {('request_code', 'status')},
            },
        ),
        migrations.CreateModel(
            name='Income',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True, db_index=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now=True, db_index=True, null=True)),
                ('amount', models.FloatField(default=0)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='request.company')),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='request.payment')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True)),
                ('slug', models.SlugField(blank=True, editable=False, max_length=150, null=True)),
                ('code', models.CharField(db_index=True, max_length=2, unique=True)),
                ('lang', models.CharField(db_index=True, max_length=2)),
            ],
            options={
                'unique_together': {('code', 'lang')},
            },
        ),
        migrations.CreateModel(
            name='Request',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=20, unique=True)),
                ('created_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('status', models.CharField(choices=[('STARTED', 'STARTED'), ('PENDING', 'PENDING'), ('COMMITTED', 'COMMITTED'), ('REJECTED', 'REJECTED'), ('INCORRECT', 'INCORRECT'), ('COMPLETED', 'COMPLETED')], db_index=True, default='STARTED', max_length=15)),
                ('user_full_name', models.CharField(db_index=True, help_text='Full name of the client requesting the service', max_length=150)),
                ('user_first_name', models.CharField(db_index=True, help_text='First name of the client requesting the service', max_length=150)),
                ('user_last_name', models.CharField(blank=True, db_index=True, help_text='Last name of the client requesting the service', max_length=150, null=True)),
                ('user_middle_name', models.CharField(blank=True, db_index=True, help_text='Middle name of client requesting the service', max_length=150, null=True)),
                ('user_gender', models.CharField(choices=[('M', 'M'), ('F', 'F')], db_index=True, help_text='Gender of client requesting the service', max_length=6)),
                ('user_civility', models.CharField(choices=[('Sir', 'Sir'), ('Mrs', 'Mrs'), ('Ms', 'Ms')], db_index=True, default='', help_text='Civility of the client requesting the service', max_length=15, verbose_name='Civility')),
                ('user_id_scan_1', models.FileField(blank=True, db_index=True, help_text='ID card scan of client requesting the service', null=True, upload_to='SCANS')),
                ('user_id_scan_2', models.FileField(blank=True, db_index=True, help_text='ID card scan of client requesting the service', null=True, upload_to='SCANS')),
                ('user_passport_1', models.FileField(blank=True, db_index=True, help_text='Passport of client requesting the service', null=True, upload_to='SCANS')),
                ('user_passport_2', models.FileField(blank=True, db_index=True, help_text='Passport of client requesting the service', null=True, upload_to='SCANS')),
                ('proof_of_stay', models.FileField(blank=True, db_index=True, help_text='Proof of stay in Cameroon', null=True, upload_to='SCANS')),
                ('user_birthday_certificate', models.FileField(blank=True, db_index=True, help_text='Birthday certificate of client requesting the service', null=True, upload_to='SCANS')),
                ('user_phone_number_1', models.CharField(db_index=True, help_text='1st phone number of the client requesting the service', max_length=15)),
                ('user_phone_number_2', models.CharField(blank=True, db_index=True, help_text='2nd phone number of the client  of client requesting the service', max_length=15, null=True)),
                ('user_close_friend_number', models.CharField(blank=True, db_index=True, help_text="Close friend phone's number", max_length=15, null=True)),
                ('user_whatsapp_number', models.CharField(db_index=True, help_text='Whatsapp phone number of client requesting the service', max_length=15)),
                ('user_email', models.EmailField(blank=True, db_index=True, help_text='Email of client requesting the service', max_length=150, null=True)),
                ('user_dob', models.DateField(blank=True, db_index=True, null=True, verbose_name='Date of birth')),
                ('user_cob_code', models.CharField(blank=True, db_index=True, default=None, help_text='Country of birth', max_length=2, null=True)),
                ('user_lang', models.CharField(blank=True, db_index=True, default='en', help_text='User language', max_length=2, null=True)),
                ('user_residency_hood', models.CharField(blank=True, db_index=True, max_length=150, null=True, verbose_name="Residency's hood")),
                ('user_residency_country_code', models.CharField(blank=True, db_index=True, help_text='Country of residency', max_length=2, null=True)),
                ('user_nationality_code', models.CharField(blank=True, db_index=True, help_text='Nationality of client requesting the service', max_length=2, null=True)),
                ('user_occupation', models.CharField(blank=True, db_index=True, max_length=150, null=True, verbose_name='Occupation of the client requesting the service')),
                ('user_marital_status', models.CharField(blank=True, choices=[('MARRIED', 'MARRIED'), ('SINGLE', 'SINGLE'), ('DIVORCED', 'DIVORCED'), ('WIDOW', 'WIDOW'), ('WIDOWER', 'WIDOWER')], db_index=True, max_length=150, null=True, verbose_name='Marital status of the client requesting the service')),
                ('user_address', models.CharField(blank=True, help_text='Address line where the user stays', max_length=255, null=True)),
                ('user_postal_code', models.CharField(blank=True, help_text="Postal address of the client, it's going to be use to ship request", max_length=150, null=True, verbose_name='Postal code')),
                ('user_birthday_certificate_url', models.URLField(blank=True, max_length=250, null=True)),
                ('user_passport_1_url', models.URLField(blank=True, max_length=250, null=True)),
                ('user_passport_2_url', models.URLField(blank=True, max_length=250, null=True)),
                ('user_proof_of_stay_url', models.URLField(blank=True, max_length=250, null=True)),
                ('user_id_card_1_url', models.URLField(blank=True, max_length=250, null=True)),
                ('user_id_card_2_url', models.URLField(blank=True, max_length=250, null=True)),
                ('user_wedding_certificate_url', models.URLField(blank=True, max_length=250, null=True)),
                ('destination_address', models.CharField(blank=True, db_index=True, max_length=150)),
                ('destination_location', models.CharField(blank=True, db_index=True, max_length=150)),
                ('has_stayed_in_cameroon', models.BooleanField(default=True)),
                ('copy_count', models.PositiveIntegerField(default=1)),
                ('purpose', models.TextField(blank=True, db_index=True, null=True, verbose_name='Describe the purpose of your request')),
                ('amount', models.IntegerField(blank=True, db_index=True, null=True, verbose_name='Amount of the request')),
                ('agent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('court', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='request.court')),
                ('user_dpb', models.ForeignKey(blank=True, help_text='Department of birth', null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.department')),
                ('user_residency_municipality', models.ForeignKey(blank=True, help_text='Municipality of residency', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='user_residency_municipality', to='request.municipality')),
            ],
        ),
        migrations.CreateModel(
            name='ExpenseReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stamp_fee', models.FloatField(db_index=True)),
                ('stamp_quantity', models.IntegerField(db_index=True)),
                ('honorary_fee', models.FloatField(db_index=True)),
                ('honorary_quantity', models.IntegerField(db_index=True)),
                ('disbursement_fee', models.FloatField(db_index=True)),
                ('disbursement_quantity', models.CharField(default='Forfait', max_length=150)),
                ('request', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='request.request')),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_of_document', models.CharField(choices=[('CRIMINAL RECORD', 'EXTRAIT DE CASIER JUDICIAIRE'), ('CERTIFICATE OF NON CONVICTION', 'CERTIFICATE OF NON CONVICTION')], max_length=150)),
                ('format', models.CharField(choices=[('PHYSICAL COPY', 'PHYSICAL COPY'), ('SCANNED COPY', 'SCANNED COPY'), ('DUAL COPY', 'DUAL COPY')], max_length=150)),
                ('rob_code', models.CharField(blank=True, help_text='Region of birth', max_length=2, null=True)),
                ('ror_code', models.CharField(blank=True, help_text='Region of residency', max_length=2, null=True)),
                ('cor_code', models.CharField(blank=True, help_text='Country of residency', max_length=2, null=True)),
                ('cost', models.PositiveIntegerField(default=0)),
                ('disbursement', models.FloatField(default=0, verbose_name='Disbursement fee of the service')),
                ('stamp_fee', models.FloatField(default=0, verbose_name='Recognized stamp fee of the service')),
                ('honorary_fee', models.FloatField(default=0, verbose_name='Honorary fee of the service')),
                ('excavation_fee', models.FloatField(default=500, verbose_name='Excavation fee of the service')),
                ('additional_cr_fee', models.FloatField(default=0, verbose_name='Default additional criminal record fee of the service')),
                ('currency_code', models.CharField(default='XAF', help_text='Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ...', max_length=5)),
            ],
            options={
                'unique_together': {('format', 'rob_code', 'cor_code'), ('format', 'ror_code', 'rob_code')},
            },
        ),
        migrations.AddField(
            model_name='request',
            name='service',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.service'),
        ),
        migrations.CreateModel(
            name='Town',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('slug', models.SlugField(editable=False, max_length=150, unique=True)),
                ('municipality', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='request.municipality')),
            ],
        ),
        migrations.CreateModel(
            name='Shipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_on', models.DateTimeField(auto_now_add=True, null=True)),
                ('destination_hood', models.CharField(blank=True, db_index=True, help_text='Hood where a requested document will be shipped', max_length=250, null=True)),
                ('destination_country_code', models.CharField(db_index=True, max_length=3)),
                ('destination_address', models.CharField(blank=True, db_index=True, max_length=150)),
                ('destination_location', models.CharField(blank=True, db_index=True, max_length=150)),
                ('transport_company', models.CharField(blank=True, db_index=True, max_length=150)),
                ('status', models.CharField(choices=[('STARTED', 'STARTED'), ('SHIPPED', 'SHIPPED'), ('RECEIVED', 'RECEIVED'), ('DELIVERED', 'DELIVERED')], db_index=True, default='STARTED', max_length=150)),
                ('agent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('destination_municipality', models.ForeignKey(blank=True, help_text='Municipality where a requested document will be shipped', null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.municipality')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='request.request')),
                ('destination_town', models.ForeignKey(blank=True, help_text='Town where a requested document will be shipped', null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.town')),
            ],
        ),
        migrations.AddField(
            model_name='request',
            name='user_residency_town',
            field=models.ForeignKey(blank=True, help_text='Town of residency', null=True, on_delete=django.db.models.deletion.SET_NULL, to='request.town'),
        ),
    ]
