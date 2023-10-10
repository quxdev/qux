from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

from qux.utils.phone import phone_number
from ..models import (
    CoreModel,
    AbstractCompany,
    default_null_blank,
    regexp_phone,
)


class Company(AbstractCompany):
    class Meta:
        db_table = "qux_contacts_company"


class Contact(CoreModel):
    first_name = models.CharField(max_length=128, **default_null_blank)
    last_name = models.CharField(max_length=128, **default_null_blank)
    display_name = models.CharField(max_length=256, **default_null_blank)
    is_favorite = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.DO_NOTHING,
        related_name="contacts",
    )
    phone = models.CharField(
        max_length=16,
        validators=[regexp_phone],
        **default_null_blank,
    )
    email = models.EmailField(
        max_length=256,
        **default_null_blank,
    )

    class Meta:
        db_table = "qux_contacts_contact"

    def displayname(self):
        if self.display_name:
            return self.display_name
        elif self.first_name:
            if self.last_name:
                return self.first_name + " " + self.last_name
            else:
                return self.first_name
        else:
            return self.id

    def asdict(self):
        result = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display": self.displayname(),
            "is_favorite": self.is_favorite,
            "is_private": self.is_private,
            "phone": self.phone,
            "phones": [x.asdict() for x in self.phones.all().order_by("-is_primary")],
            "email": self.email,
            "emails": [x.asdict() for x in self.emails.all().order_by("-is_primary")],
        }
        return result

    def primaryphone(self):
        phone = self.phones.filter(is_primary=True)
        if phone.exists():
            return phone.first()
        else:
            return self.phones.first()

    def primaryemail(self):
        email = self.emails.filter(is_primary=True)
        if email.exists():
            return email.first()
        else:
            return self.emails.first()

    def hasphone(self, phone):
        p = phone_number(phone)
        if p is None:
            return False

        result = any([x for x in self.phones.all() if x.phone == p])
        return result


@receiver(pre_save, sender=Contact)
def contact_pre_save(sender, instance, **kwargs):
    if instance.phone:
        x = phone_number(instance.phone)
        instance.phone = x


class AbstractContactPhone(CoreModel):
    # TODO: set to actual child of AbstractContact
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="phones"
    )
    phone = models.CharField(
        max_length=16,
        validators=[regexp_phone],
        blank=False,
    )
    label = models.CharField(max_length=100, **default_null_blank)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.phone

    def save(self, *args, **kwargs):
        x = phone_number(self.phone)
        if x:
            self.phone = x
            super(AbstractContactPhone, self).save(*args, **kwargs)
        else:
            return

    def asdict(self):
        result = {
            "id": self.id,
            "phone": self.phone,
            "label": self.label,
            "is_primary": self.is_primary,
        }
        return result


class AbstractContactEmail(CoreModel):
    # TODO: Set to actual child of AbstractContact
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="emails",
    )
    email = models.EmailField(max_length=256, blank=False)
    label = models.CharField(max_length=100, **default_null_blank)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.email

    def asdict(self):
        result = {
            "id": self.id,
            "email": self.email,
            "label": self.label,
            "is_primary": self.is_primary,
        }
        return result
