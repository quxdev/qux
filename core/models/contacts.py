from django.core.validators import RegexValidator
from django.db import models

from core.models import CoreModel
from core.utilities.phone import phone_number


class AbstractCompany(CoreModel):
    name = models.CharField(max_length=128, default=None, null=True, blank=True)
    shortname = models.CharField(max_length=32, default=None, null=True, blank=True)
    url = models.URLField()

    class Meta:
        abstract = True


class AbstractContact(CoreModel):
    regexp = RegexValidator(
        regex=r'^\+?[1-9]\d{4,14}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )

    first_name = models.CharField(
        max_length=128, default=None, null=True, blank=True
    )
    last_name = models.CharField(
        max_length=128, default=None, null=True, blank=True
    )
    display_name = models.CharField(
        max_length=256, default=None, null=True, blank=True
    )
    is_favorite = models.BooleanField(default=False)
    is_private = models.BooleanField(default=True)
    phone = models.CharField(
        max_length=16, validators=[regexp], default=None, null=True, blank=True
    )
    email = models.EmailField(
        max_length=256, default=None, null=True, blank=True
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.phone:
            x = phone_number(self.phone)
            self.phone = x

        super(AbstractContact, self).save(*args, **kwargs)

    def displayname(self):
        if self.display_name:
            return self.display_name
        elif self.first_name:
            if self.last_name:
                return self.first_name + ' ' + self.last_name
            else:
                return self.first_name
        else:
            return self.id

    def asdict(self):
        result = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'display': self.displayname(),
            'is_favorite': self.is_favorite,
            'is_private': self.is_private,
            'phone': self.phone,
            'phones': [x.asdict() for x in self.phones.all().order_by('-is_primary')],
            'email': self.email,
            'emails': [x.asdict() for x in self.emails.all().order_by('-is_primary')],
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


class AbstractContactPhone(CoreModel):
    regexp = RegexValidator(
        regex=r'^\+?[1-9]\d{4,14}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    contact = models.ForeignKey(
        AbstractContact, on_delete=models.CASCADE, related_name='phones'
    )
    phone = models.CharField(max_length=16, validators=[regexp], blank=False)
    label = models.CharField(max_length=100, default=None, null=True, blank=True)
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
            'id': self.id,
            'phone': self.phone,
            'label': self.label,
            'is_primary': self.is_primary
        }
        return result


class AbstractContactEmail(CoreModel):
    contact = models.ForeignKey(
        AbstractContact, on_delete=models.CASCADE, related_name='emails'
    )
    email = models.EmailField(max_length=256, blank=False)
    label = models.CharField(max_length=100, default=None, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.email

    def asdict(self):
        result = {
            'id': self.id,
            'email': self.email,
            'label': self.label,
            'is_primary': self.is_primary
        }
        return result
