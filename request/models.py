from django.db import models
from django.utils.translation import gettext_lazy as _

from request.constants import REQUEST_STATUS, REQUEST_FORMATS, MARITAL_STATUS, TYPE_OF_DOCUMENT, GENDERS, COURT_TYPES, \
    STARTED, SHIPMENT_STATUS, CIVILITIES


# Create your models here.


class Country(models.Model):
    name = models.CharField(max_length=150)
    iso2 = models.CharField(max_length=2, db_index=True)
    iso3 = models.CharField(max_length=3, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

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
        return f'{self.type} {self.name}'

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
    currency_code = models.CharField(max_length=5, default='XAF',
                                     help_text=_("Code of your currency. Eg: <strong>USD, GBP, EUR, XAF,</strong> ..."))

    def __str__(self):
        return self.type_of_document

    class Meta:
        unique_together = (
            ('ror', 'rob', 'cost'),
            ('format', 'ror', 'rob')
        )
    # @property
    # def cost(self):
    #     return self.


class Agent(models.Model):
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)

    first_name = models.CharField(max_length=150, db_index=True)
    last_name = models.CharField(max_length=150, db_index=True)
    email = models.EmailField(db_index=True, unique=True)
    court = models.OneToOneField(Court, db_index=True, on_delete=models.PROTECT)
    pending_task_count = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.first_name}, {self.last_name}'

    @property
    def full_name(self):
        return self.__str__()


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
                                      db_index=True)
    user_middle_name = models.CharField(max_length=150, help_text=_("Middle name of client requesting the service"),
                                        db_index=True, null=True, blank=True)
    user_gender = models.CharField(max_length=6, choices=GENDERS, help_text=_("Gender of client requesting "
                                                                              "the service"), db_index=True)
    civility = models.CharField(max_length=15, choices=CIVILITIES, help_text=_("Civility of the client requesting"
                                                                               " the service"), db_index=True, default='')
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
                                 default=Country.objects.get(name__iexact='cameroun').id)
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

    # This parameter mostly relevant for non-Cameroonian but who has stayed in Cameroon during a period
    has_stayed_in_cameroon = models.BooleanField(default=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    copy_count = models.PositiveIntegerField(default=1)
    purpose = models.TextField(_("Describe the purpose of your request"),  blank=True, null=True, db_index=True)
    amount = models.IntegerField(_("Amount of the request"),  blank=True, null=True, db_index=True)
    user_address = models.CharField(max_length=255, null=True, blank=True,
                                    help_text=_("Address line where the user stays"))

    __court = Court()
    __agent = Agent()

    def __str__(self):
        return f"{self.code}"

    # @property
    # def user_full_name(self):
    #     return f'{self.user_first_name}, {self.user_last_name}'

    # def __setattr__(self, court, val):
    #     super(Request, self).__setattr__(court, val)
    #     self._court = val
    #
    # def __getattr__(self, ):
    #     return super(Request, self).__getattr__(attrname)

    @property
    def court(self):
        return self.__court

    @court.setter
    def court(self, value):
        self.setter(Court.__name__, court=value)

    @property
    def agent(self):
        return self._agent

    @agent.setter
    def agent(self, value):
        self.setter(Court.__name__, agent=value)


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
    request = models.ForeignKey(Request, db_index=True, on_delete=models.PROTECT)
    transport_company = models.CharField(max_length=150, db_index=True, blank=True)
    status = models.CharField(max_length=150, choices=SHIPMENT_STATUS, db_index=True, default=STARTED)




