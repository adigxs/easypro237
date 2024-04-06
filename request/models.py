from bson import ObjectId
import uuid
import os

from datetime import timezone

from django.db import models
from django.contrib.auth.models import AbstractUser, Permission, Group, UserManager
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from request.constants import REQUEST_STATUS, REQUEST_FORMATS, MARITAL_STATUS, TYPE_OF_DOCUMENT, GENDERS, COURT_TYPES, \
    STARTED, DELIVERY_STATUSES, CIVILITIES, PENDING


# Create your models here.


def get_object_id():
    """Generates a string version of bson ObjectId."""
    # return str(ObjectId())
    return str(uuid.uuid4())


class BaseAdapterModel(models.Model):
    """
    This abstract model uses id as a string version of
    bson ObjectId. This is done to support models coming
    from the MongoDB storage; so those models must inherit
    this class to work properly.
    """
    id = models.CharField(max_length=255, primary_key=True, default=get_object_id, editable=True)

    class Meta:
        abstract = True


class BaseModel(models.Model):
    """
    Helper base Model that defines two fields: created_on and updated_on.
    Both are DateTimeField. updated_on automatically receives the current
    datetime whenever the model is updated in the database
    """
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False, db_index=True)
    updated_on = models.DateTimeField(auto_now=True, null=True, db_index=True)

    class Meta:
        abstract = True

    # def save(self, **kwargs):
    #     for field in self._meta.fields:
    #         if type(field) == JSONField and isinstance(self.__getattribute__(field.name), models.Model):
    #             self.__setattr__(field.name, to_dict(self.__getattribute__(field.name), False))
    #     super(BaseModel, self).save(**kwargs)

    def _get_display_date(self):
        if not self.created_on:
            return ''
        now = timezone.now()
        if self.created_on.year == now.year and self.created_on.month == now.month \
                and self.created_on.day == now.day:
            return self.created_on.strftime('%H:%M')
        return self.created_on.strftime('%Y-%m-%d')
    display_date = property(_get_display_date)


class TrashQuerySet(models.QuerySet):
    """
    QuerySet whose delete() does not delete items, but instead marks the
    rows as not active, and updates the timestamps
    """
    def delete(self):
        count = self.count()
        for obj in self:
            obj.delete()
        return count


class TrashManager(models.Manager):
    def get_queryset(self):
        return TrashQuerySet(self.model, using=self._db)


class TrashMixin(models.Model):
    objects = TrashManager()

    class Meta:
        abstract = True

    def delete(self, **kwargs):
        try:
            TrashModel.objects.create(model_name=self._meta.label, data=self.to_dict())
        except:
            pass
        super(TrashMixin, self).delete(**kwargs)


def add_database_to_settings(db_url):
    """
    Adds a database connection to the global settings on the fly.
    That is equivalent to do the following in Django settings file:

    DATABASES = {
        'default': {
            'ENGINE': 'current_database_engine',
            'NAME': 'default_database',
            ...
        },
        'alias': {
            'ENGINE': 'engine_in_db_info',
            'NAME': database,
            ...
        }
    }

    That connection is named 'database'
    @param db_url: string representing database under the form engine://<username>:<password>@<host>[:<port>]/database
    """
    # Defaults
    engine = getattr(settings, 'DATABASES')['default']['ENGINE']
    host = getattr(settings, 'DATABASES')['default'].get('HOST', '127.0.0.1')
    port = getattr(settings, 'DATABASES')['default'].get('PORT')
    username = getattr(settings, 'DATABASES')['default'].get('USER')
    password = getattr(settings, 'DATABASES')['default'].get('PASSWORD')

    tokens = db_url.strip().split('://')
    if len(tokens) == 1:
        alias = tokens[0]
    else:
        engine = tokens[0]
        db_tokens = tokens[1].split('/')
        if len(db_tokens) == 1:
            alias = db_tokens[0]
        else:
            access = db_tokens[0]
            alias = db_tokens[1]
            access_tokens = access.split('@')
            credentials = access_tokens[0].split(':')
            location = access_tokens[1].split(':')
            username = credentials[0]
            password = credentials[1]
            host = location[0]
            if len(location) > 1:
                port = location[1]
    DATABASES = getattr(settings, 'DATABASES')
    if DATABASES.get(alias) is None:  # If this alias was not yet added
        name = alias
        if engine == 'sqlite':
            engine = 'django.db.backends.sqlite3'
            name = os.path.join(getattr(settings, 'BASE_DIR'), '%s.sqlite3' % alias)
        elif engine == 'mysql':
            engine = 'django.db.backends.mysql'
        elif engine == 'postgres':
            engine = 'django.db.backends.postgresql_psycopg2'
        elif engine == 'oracle':
            engine = 'django.db.backends.oracle'
        DATABASES[alias] = {
            'ENGINE': engine,
            'NAME': name,
            'HOST': host
        }
        if port:
            DATABASES[alias]['PORT'] = port
        if username:
            DATABASES[alias]['USER'] = username
            DATABASES[alias]['PASSWORD'] = password
    setattr(settings, 'DATABASES', DATABASES)
    return alias


class Model(BaseAdapterModel, BaseModel):
    """
    Helper base Model that creates a model suitable for save in MongoDB
    with fields created_on and updated_on.
    """

    def get_from(self, db):
        add_database_to_settings(db)
        return type(self).objects.using(db).get(pk=self.id)

    class Meta:
        abstract = True


class TrashModel(Model):
    model_name = models.CharField(max_length=100, db_index=True)
    data = models.JSONField()


class BaseUUIDModel(BaseModel, TrashMixin):
    """Base model using UUID4 as primary key"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)

    class Meta:
        abstract = True


class Country(models.Model):
    name = models.CharField(max_length=150)
    iso2 = models.CharField(max_length=2, db_index=True)
    iso3 = models.CharField(max_length=3, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    slug = models.SlugField(null=True, blank=True, max_length=150, db_index=True, editable=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Countries"
        unique_together = (
            ('name', 'iso2'),
            ('iso2', 'iso3'),
        )


class Region(models.Model):
    name = models.CharField(unique=True, max_length=150)
    slug = models.SlugField(null=True, blank=True, max_length=150, db_index=True, editable=False)
    code = models.CharField(unique=True, max_length=2, db_index=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=150, db_index=True)

    def __str__(self):
        return self.name


class Court(models.Model):
    name = models.CharField(max_length=150, db_index=True, unique=True)
    slug = models.SlugField(unique=True, db_index=True)
    type = models.CharField(max_length=150, db_index=True, choices=COURT_TYPES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, db_index=True, null=True, blank=True, default=None)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.name}'

    @property
    def region(self):
        return self.department.region if self.department else ''


class Municipality(models.Model):
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, db_index=True)
    slug = models.SlugField(unique=True, max_length=150)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Municipalities"

    @property
    def region(self):
        return self.department.region


class Town(models.Model):
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, max_length=150, db_index=True, editable=False)


class Service(models.Model):
    type_of_document = models.CharField(max_length=150, choices=TYPE_OF_DOCUMENT)
    format = models.CharField(max_length=150, choices=REQUEST_FORMATS)
    rob = models.ForeignKey(Region, help_text=_("Region of birth"), on_delete=models.SET_NULL, blank=True, null=True, related_name='rob')
    ror = models.ForeignKey(Region, help_text=_("Region of residency"), on_delete=models.SET_NULL, blank=True, null=True, related_name='ror')
    cor = models.ForeignKey(Country, help_text=_("Country of residency"), on_delete=models.SET_NULL, blank=True, null=True, related_name='cor')
    cost = models.PositiveIntegerField(default=0)
    disbursement = models.FloatField(_("Disbursement fee of the service"), default=0)
    stamp_fee = models.FloatField(_("Recognized stamp fee of the service"), default=0)
    honorary_fee = models.FloatField(_("Honorary fee of the service"), default=0)
    currency_code = models.CharField(max_length=5, default='XAF',
                                     help_text=_("Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ..."))

    def __str__(self):
        return self.type_of_document

    class Meta:
        unique_together = (
            ('format', 'ror', 'rob'),
            ('format', 'rob', 'cor'),
        )


class Agent(BaseUUIDModel, AbstractUser):
    """
    Agent will play the role of User model.
    """
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    gender = models.CharField(max_length=1, choices=GENDERS)
    verify = models.BooleanField(default=False, help_text=_("Ensure email or phone is verified"))
    phone = models.TextField(help_text=_("Phone"), editable=True)
    dob = models.DateField(blank=True, null=True, db_index=True, help_text=_("Date of birth"), editable=True)
    logo = models.FileField(_("Agent profile picture"), blank=True, null=True, upload_to="Agents")
    court = models.OneToOneField(Court, db_index=True, on_delete=models.PROTECT, null=True, blank=True)
    region = models.OneToOneField(Region, db_index=True, on_delete=models.PROTECT, null=True, blank=True)
    pending_task_count = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.first_name}, {self.last_name}'

    @property
    def full_name(self):
        return self.__str__()

    # objects = UserManager()

    class Meta:
        permissions = [
            ("view_user_birthday_certificate", "Can view and download birthday certificate"),
            ("view_user_passport", "Can view and download birthday certificate"),
            ("view_proof_of_stay", "Can view and download birthday certificate"),
            ("view_id_card", "Can view and download birthday certificate"),
            ("view_wedding_certificate", "Can view and download birthday certificate"),
            ("view_destination_address", "Can view and download birthday certificate"),
            ("view_destination_location", "Can view attachment details"),
            ("change_request_status", "Can change status of a request"),
        ]
        ordering = ['first_name', 'last_name']


class Request(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    status = models.CharField(max_length=15, choices=REQUEST_STATUS, default=STARTED, db_index=True)

    user_full_name = models.CharField(max_length=150, help_text=_("Full name of the client requesting the service"),
                                      db_index=True)
    user_first_name = models.CharField(max_length=150, help_text=_("First name of the client requesting the service"),
                                       db_index=True)

    user_last_name = models.CharField(max_length=150, help_text=_("Last name of the client requesting the service"),
                                      db_index=True, null=True, blank=True)
    user_middle_name = models.CharField(max_length=150, help_text=_("Middle name of client requesting the service"),
                                        db_index=True, null=True, blank=True)
    user_gender = models.CharField(max_length=6, choices=GENDERS, help_text=_("Gender of client requesting "
                                                                              "the service"), db_index=True)
    user_civility = models.CharField(_("Civility"), max_length=15, choices=CIVILITIES,
                                     help_text=_("Civility of the client requesting the service"), db_index=True,
                                     default='')
    user_id_scan_1 = models.FileField(upload_to="SCANS", help_text=_("ID card scan of client requesting the service"),
                                    db_index=True, null=True, blank=True)
    user_id_scan_2 = models.FileField(upload_to="SCANS", help_text=_("ID card scan of client requesting the service"),
                                    db_index=True, null=True, blank=True)
    user_passport_1 = models.FileField(upload_to="SCANS", help_text=_("Passport of client requesting the service"),
                                     db_index=True, null=True, blank=True)
    user_passport_2 = models.FileField(upload_to="SCANS", help_text=_("Passport of client requesting the service"),
                                       db_index=True, null=True, blank=True)
    proof_of_stay = models.FileField(upload_to="SCANS", help_text=_("Proof of stay in Cameroon"),
                                     db_index=True, null=True, blank=True)
    user_birthday_certificate = models.FileField(upload_to="SCANS", help_text=_("Birthday certificate of client "
                                                                                "requesting the service"),
                                                 db_index=True, null=True, blank=True)
    user_phone_number_1 = models.CharField(max_length=15, help_text=_("1st phone number of the client requesting "
                                                                      "the service"), db_index=True)
    user_phone_number_2 = models.CharField(max_length=15, help_text=_("2nd phone number of the client  of client "
                                                                      "requesting the service"), db_index=True, null=True, blank=True)
    user_close_friend_number = models.CharField(max_length=15, help_text=_("Close friend phone's number"), db_index=True,
                                           null=True, blank=True)

    user_whatsapp_number = models.CharField(max_length=15, help_text=_("Whatsapp phone number of client requesting the service"),
                                            db_index=True)
    user_email = models.EmailField(max_length=150, help_text=_("Email of client requesting the service"),
                                   db_index=True, null=True, blank=True)
    user_dob = models.DateField(_("Date of birth"), blank=True, null=True, db_index=True)
    user_dpb = models.ForeignKey(Department, help_text=_("Department of birth"), blank=True, null=True,
                                 db_index=True, on_delete=models.SET_NULL)
    user_cob = models.ForeignKey(Country, help_text=_("Country of birth"), blank=True, null=True,
                                 on_delete=models.SET_NULL, db_index=True, related_name="user_cob",
                                 default=None)
    user_residency_hood = models.CharField(_("Residency's hood"), max_length=150, blank=True, null=True, db_index=True)
    user_residency_town = models.ForeignKey(Town, help_text=_("Town of residency"), blank=True,
                                            null=True, on_delete=models.SET_NULL, db_index=True)

    user_residency_country = models.ForeignKey(Country, help_text=_("Country of residency"), on_delete=models.PROTECT,
                                               db_index=True, related_name="user_residency_country", null=True, blank=True)
    user_residency_municipality = models.ForeignKey(Municipality, help_text=_("Municipality of residency"),
                                                    on_delete=models.SET_NULL, blank=True, null=True, db_index=True,
                                                    related_name="user_residency_municipality")

    user_nationality = models.ForeignKey(Country, help_text=_("Nationality of client requesting the service"), null=True,
                                         blank=True, on_delete=models.SET_NULL, db_index=True, related_name="user_nationality")
    user_occupation = models.CharField(_("Occupation of the client requesting the service"), max_length=150,
                                       blank=True, null=True, db_index=True)
    user_marital_status = models.CharField(_("Marital status of the client requesting the service"), max_length=150, blank=True,
                                           null=True, db_index=True, choices=MARITAL_STATUS)

    user_address = models.CharField(max_length=255, null=True, blank=True,
                                    help_text=_("Address line where the user stays"))

    user_postal_code = models.CharField(_("Postal code"), max_length=150, null=True, blank=True,
                                        help_text=_("Postal address of the client, it's going to be use to ship request"))

    user_birthday_certificate_url = models.URLField(max_length=250, blank=True, null=True)
    user_passport_1_url = models.URLField(max_length=250, blank=True, null=True)
    user_passport_2_url = models.URLField(max_length=250, blank=True, null=True)
    user_proof_of_stay_url = models.URLField(max_length=250, blank=True, null=True)
    user_id_card_1_url = models.URLField(max_length=250, blank=True, null=True)
    user_id_card_2_url = models.URLField(max_length=250, blank=True, null=True)
    user_wedding_certificate_url = models.URLField(max_length=250, blank=True, null=True)
    destination_address = models.CharField(max_length=150, db_index=True, blank=True)
    destination_location = models.CharField(max_length=150, db_index=True, blank=True)

    # This parameter mostly relevant for non-Cameroonian but who has stayed in Cameroon during a period
    has_stayed_in_cameroon = models.BooleanField(default=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    copy_count = models.PositiveIntegerField(default=1)
    purpose = models.TextField(_("Describe the purpose of your request"),  blank=True, null=True, db_index=True)
    amount = models.IntegerField(_("Amount of the request"),  blank=True, null=True, db_index=True)
    court = models.ForeignKey(Court, on_delete=models.PROTECT, null=True, blank=True)
    agent = models.ForeignKey(Agent, on_delete=models.PROTECT, null=True, blank=True)


class Shipment(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    agent = models.ForeignKey(Agent, db_index=True, on_delete=models.SET_NULL, blank=True, null=True)
    destination_municipality = models.ForeignKey(Municipality, db_index=True, help_text=_("Municipality where a requested document will be "
                                                                     "shipped"), on_delete=models.SET_NULL, blank=True, null=True)
    destination_town = models.ForeignKey(Town, db_index=True,
                                                 help_text=_("Town where a requested document will be "
                                                             "shipped"), on_delete=models.SET_NULL, blank=True, null=True)
    destination_hood = models.CharField(max_length=250, db_index=True, help_text=_("Hood where a requested document will be "
                                                             "shipped"), blank=True, null=True)

    destination_country = models.ForeignKey(Country, db_index=True, on_delete=models.PROTECT)
    destination_address = models.CharField(max_length=150, db_index=True, blank=True)
    destination_location = models.CharField(max_length=150, db_index=True, blank=True)
    request = models.ForeignKey(Request, db_index=True, on_delete=models.PROTECT)
    transport_company = models.CharField(max_length=150, db_index=True, blank=True)
    status = models.CharField(max_length=150, choices=DELIVERY_STATUSES, db_index=True, default=STARTED)


class Payment(BaseUUIDModel):
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    request_code = models.CharField(max_length=24, db_index=True, null=True)
    label = models.CharField(max_length=150, db_index=True, null=True, default="")
    amount = models.FloatField(db_index=True)
    pay_token = models.CharField(max_length=36, null=True, db_index=True)
    mean = models.CharField(_('Payment Methods'), max_length=15, null=True, db_index=True)
    operator_tx_id = models.CharField(max_length=50, null=True, db_index=True)
    operator_user_id = models.CharField(max_length=50, null=True, db_index=True)

    status = models.CharField(max_length=36, default=PENDING, db_index=True)
    currency_code = models.CharField(max_length=5, default='XAF',
                                     help_text=_("Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ..."))
    message = models.CharField(max_length=255, default='',
                               help_text=_("Message rendered by the gateway for initiated payment transaction ..."))

    class Meta:
        unique_together = (
            ('request_code', 'status'),
        )


class Company(models.Model):
    name = models.CharField(max_length=255, help_text=_("Name of the company ..."))
    percentage = models.PositiveIntegerField(default=0, help_text=_("Percentage the company earns for disbursement"
                                                                    " on each transaction. Eg: 5, 3, 25 etc..."))


class Disbursement(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

    def get_total_amount(self):
        return

