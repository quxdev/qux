from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from qux.models import CoreModel, default_null_blank


class Company(CoreModel):
    SLUG_PREFIX = "company"

    slug = models.CharField(max_length=14, unique=True)
    name = models.CharField(max_length=128)
    address = models.TextField(**default_null_blank)
    domain = models.CharField(max_length=255)
    url = models.URLField(max_length=1024, **default_null_blank)

    class Meta:
        db_table = "qux_auth_company"
        verbose_name = "Company"
        verbose_name_plural = "Companies"


class CompanyUser(CoreModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    class Meta:
        db_table = "qux_auth_company_users"
        verbose_name = "User at Company"
        verbose_name_plural = "Users at Companies"


class Profile(CoreModel):
    SLUG_PREFIX = "user"

    # https://en.wikipedia.org/wiki/E.164
    regexp = RegexValidator(
        regex=r"^\+?[1-9]\d{4,14}$",
        message="Phone number must be entered in the format: '+999999999'. "
        "Up to 15 digits allowed.",
    )

    slug = models.CharField(max_length=11, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=16, validators=[regexp])
    company = models.ForeignKey(
        Company, on_delete=models.DO_NOTHING, **default_null_blank
    )
    title = models.CharField(max_length=255, **default_null_blank)

    class Meta:
        db_table = "qux_auth_profile"
        verbose_name = "User Profile"

    @classmethod
    def get_user(cls, slug):
        return cls.objects.get(slug=slug).user

    def get_initials(self):
        user = self.user
        if user.first_name and user.last_name:
            initials = user.first_name[0] + " " + user.last_name[0]
        elif user.first_name:
            initials = user.first_name[0]
        elif user.last_name:
            initials = user.last_name[0]
        else:
            initials = None

        return initials

    def get_fullname(self):
        user = self.user
        if user.first_name and user.last_name:
            fullname = user.first_name + " " + user.last_name
        elif user.first_name:
            fullname = user.first_name
        elif user.last_name:
            fullname = user.last_name
        else:
            fullname = user.email

        return fullname


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, "Profile"):
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    p, created = Profile.objects.get_or_create(user=instance)
    p.save()
