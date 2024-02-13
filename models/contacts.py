from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from qux.models.base import (
    CoreModel,
    default_null_blank,
    regexp_phone,
)


class AbstractCompany(CoreModel):
    SLUG_PREFIX = "company"
    SLUG_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyz"

    slug = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    address = models.TextField(**default_null_blank)
    domain = models.CharField(max_length=255, unique=True)
    url = models.URLField("URL", max_length=1024, **default_null_blank)

    class Meta:
        abstract = True
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name if self.name else self.slug


class AbstractProfile(CoreModel):
    SLUG_PREFIX = "user"
    SLUG_ALLOWED_CHARS = "abcdefghijklmnopqrstuvwxyz"

    slug = models.CharField(max_length=11, unique=True)
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="%(class)s"
    )
    phone = models.CharField(
        max_length=16,
        validators=[regexp_phone],
        **default_null_blank,
    )
    title = models.CharField(max_length=255, **default_null_blank)
    is_live = models.BooleanField(default=False)

    class Meta:
        abstract = True
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


@receiver(post_save, sender=get_user_model())
def create_profile(sender, instance, created, **kwargs):
    if not created:
        return

    for subclass in AbstractProfile.__subclasses__():
        obj, created = subclass.objects.get_or_create(user=instance, id=instance.id)
        if created:
            obj.save()


@receiver(post_save, sender=get_user_model())
def save_profile(sender, instance, **kwargs):
    for subclass in AbstractProfile.__subclasses__():
        obj, created = subclass.objects.get_or_create(user=instance, id=instance.id)
        if created:
            obj.save()
