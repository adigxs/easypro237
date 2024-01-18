from django.db import models
from django.utils.translation import gettext_lazy as _

from request.constants import REQUEST_STATUS, REQUEST_FORMATS, MARITAL_STATUS, TYPE_OF_DOCUMENT, GENDERS
# Create your models here.


class Region(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, db_index=True)


class Department(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, db_index=True)


class District(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)


class Town(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, db_index=True)


class Service(models.Model):
    type_of_document = models.CharField(max_length=150, choices=TYPE_OF_DOCUMENT)
    format = models.CharField(max_length=150, choices=REQUEST_FORMATS)
    town = models.ForeignKey(Town, on_delete=models.SET_NULL, blank=True, null=True)
    district = models.ForeignKey(Town, on_delete=models.SET_NULL, blank=True, null=True)
    # department = models.ForeignKey(Department, on_delete=models.SET_NULL)
    # region = models.ForeignKey(Region, on_delete=models.SET_NULL)
    cost = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.type_of_document

    def _get_region(self):
        return self.town.district.department.region

    def _get_department(self):
        return self.town.district.department

    def _get_district(self):
        return self.town.district

    region = property(_get_region)
    department = property(_get_department)
    district = property(_get_district)


class Request(models.Model):
    code = models.CharField(max_length=12, db_index=True)
    created_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    updated_on = models.DateTimeField(auto_now_add=True, null=True, editable=False)
    status = models.CharField(max_length=15, choices=REQUEST_STATUS, default=REQUEST_STATUS[0], db_index=True)
    user_first_name = models.CharField(max_length=150, help_text=_("First name of the client requesting the service"),
                                       db_index=True)
    user_last_name = models.CharField(max_length=150, help_text=_("Last name of the client requesting the service"),
                                      db_index=True)
    user_middle_name = models.CharField(max_length=150, help_text=_("Middle name of client requesting the service"),
                                        db_index=True)
    user_gender = models.CharField(max_length=6, choices=GENDERS, help_text=_("Middle name of client requesting "
                                                                              "the service"), db_index=True)
    user_id_scan = models.FileField(upload_to="SCANS", help_text=_("Middle name of client requesting the service"),
                                    db_index=True)
    user_phone_number_1 = models.CharField(max_length=15, help_text=_("1st phone number of the client requesting "
                                                                      "the service"), db_index=True)
    user_phone_number_2 = models.CharField(max_length=15, help_text=_("2nd phone number of the client  of client "
                                                                      "requesting the service"), db_index=True)
    user_whatsapp_number = models.CharField(max_length=15, help_text=_("Middle name of client requesting the service"),
                                            db_index=True)
    user_email = models.FileField(max_length=150, help_text=_("Middle name of client requesting the service"),
                                  db_index=True)
    user_dob = models.DateField(_("Date of birth"), blank=True, null=True, db_index=True)
    user_pob = models.CharField(_("Place of birth"), max_length=150, blank=True, null=True, db_index=True)
    user_cob = models.CharField(_("Country of birth"), max_length=150, blank=True, null=True, db_index=True)
    user_residency_country = models.CharField(_("Country of residency"), max_length=150, blank=True,
                                              null=True, db_index=True)
    user_nationality = models.CharField(_("Nationality of client requesting the service"), max_length=150,
                                        blank=True, null=True, db_index=True)
    user_occupation = models.CharField(_("Occupation of the client requesting the service"), max_length=150,
                                       blank=True, null=True, db_index=True)
    user_marital_status = models.CharField(_("Marital status of the client requesting the service"), max_length=150, blank=True,
                                           null=True, db_index=True, choices=MARITAL_STATUS)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    copy_count = models.PositiveIntegerField(default=1)


class OfficeDistrict(models.Model):
    name = models.CharField(max_length=150, db_index=True)
    type = models.CharField(max_length=150, db_index=True)
    town = models.ForeignKey(Town, db_index=True, on_delete=models.SET_NULL, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def _get_region(self):
        return f"{self.town.district.department.region}"

    def _get_department(self):
        return f"{self.town.district.department}"

    def _get_district(self):
        return self.town.district

    region = property(_get_region)
    department = property(_get_department)
    district = property(_get_district)


class Agent(models.Model):
    first_name = models.CharField(max_length=150, db_index=True)
    last_name = models.CharField(max_length=150, db_index=True)
    district = models.CharField(max_length=150, db_index=True)

    def __str__(self):
        return f'{self.first_name}, {self.last_name}'

    def _get_region(self):
        return self.district.department.region

    def _get_department(self):
        return self.district.department

    region = property(_get_region)
    department = property(_get_department)


class Shipment(models.Model):
    agent = models.ForeignKey(Agent, db_index=True, on_delete=models.SET_NULL, blank=True, null=True)
    destination = models.ForeignKey(Town, db_index=True, help_text=_("Destination where a requested document will be "
                                                                     "shipped"), on_delete=models.SET_NULL, blank=True, null=True)
    request = models.ForeignKey(Request, db_index=True, on_delete=models.SET_NULL, blank=True, null=True)
    transport_company = models.CharField(max_length=150, db_index=True)




