from django.db import models

from .base import CoreModel, CoreManager


class CoreManagerPlus(CoreManager):
    def get(self, *args, **kwargs):
        return self.get_queryset().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()


class CoreModelPlus(CoreModel):
    objects = CoreManagerPlus()
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()
