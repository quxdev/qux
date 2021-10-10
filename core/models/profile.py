from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CoreModel, default_null_blank


class Company(CoreModel):
    name = models.CharField(max_length=128)
    address = models.TextField(**default_null_blank)
    domain = models.CharField(max_length=255)
    url = models.URLField(max_length=1024, **default_null_blank)

    class Meta:
        db_table = 'qux_company'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'


class CompanyUser(CoreModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    class Meta:
        db_table = 'qux_company_users'
        verbose_name = 'Company:User'
        verbose_name_plural = 'Company:User'


class Profile(CoreModel):
    # https://en.wikipedia.org/wiki/E.164
    regexp = RegexValidator(
        regex=r'^\+?[1-9]\d{4,14}$',
        message="Phone number must be entered in the format: '+999999999'. "
                "Up to 15 digits allowed."
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=16, validators=[regexp])
    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING, **default_null_blank)
    title = models.CharField(max_length=255, **default_null_blank)

    class Meta:
        db_table = 'qux_user_profile'
        verbose_name = 'User Profile'


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'Profile'):
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    try:
        p = instance.profile
        p.save()
    except ObjectDoesNotExist:
        Profile.objects.create(user=instance)
