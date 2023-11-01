import datetime
import random
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import FieldError
from django.core.exceptions import ObjectDoesNotExist, FieldDoesNotExist
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields import DateField, DateTimeField
from django.db.models.fields.files import FileField
from django.db.models.fields.related import ManyToManyField
from django.db.models.signals import pre_save, post_init, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.crypto import get_random_string
from itertools import chain
from qux.lorem import Lorem

from .base import CoreModel, CoreManager


class CoreManagerPlus(CoreManager):
    def get(self, *args, **kwargs):
        # print("get is_deleted=False")
        return self.get_queryset().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        # print("filter is_deleted=False")
        return self.get_queryset().filter(*args, **kwargs)

    def get_queryset(self):
        # print("get_queryset is_deleted=False")
        return super(CoreManagerPlus, self).get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        # print("all_with_deleted is_deleted=False")
        return super(CoreManagerPlus, self).get_queryset()


class CoreModelPlus(CoreModel):
    objects = CoreManagerPlus()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.dtm_created:
            self.dtm_created = timezone.now()
        self.dtm_updated = timezone.now()
        return super(CoreModelPlus, self).save(*args, **kwargs)

    def delete(self):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()
