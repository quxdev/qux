from django.contrib.auth.models import User
from django.db import models
from django.db import transaction

from .models import CoreModel


class QuxPermission(CoreModel):
    slug = models.SlugField(max_length=32, unique=True)
    app_name = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=128, null=True)

    class Meta:
        app_label = 'qux'
        unique_together = ('app_name', 'name')

    def __str__(self):
        return "{:s}".format(self.name)

    @classmethod
    def get_or_create(cls, app_name, name, description):
        created = False
        result = cls.objects.filter(app_name=app_name, name=name)
        if not result:
            result = cls.objects.create(
                app_name=app_name,
                name=name,
                description=description,
            )
            created = True

        return created, result


class QuxEntityPermission(CoreModel):
    app_name = models.CharField(max_length=128)
    entity_name = models.CharField(max_length=128)
    entity_id = models.IntegerField()
    actor = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    authorized = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='can_access')
    perm = models.ForeignKey(QuxPermission, on_delete=models.DO_NOTHING)

    @classmethod
    @transaction.atomic
    def get_or_create(cls, app_name, entity_name, entity_id, actor, authorized, perm,):
        permdata = dict(
            app_name=app_name,
            entity_name=entity_name,
            entity_id=entity_id,
            authorized=authorized
        )

        result = cls.objects.filter(**permdata)
        if not result:
            permdata['actor'] = actor
            permdata['perm'] = perm
            result = cls.objects.create(**permdata)
            QuxEntityPermissionLog.objects.create(**perm, action='granted')

        return result

    @transaction.atomic
    def revoke(self, actor):
        permlog = dict(
            app_name=self.app_name,
            entity_name=self.entity_name,
            entity_id=self.entity_id,
            actor=actor,
            authorized=self.authorized,
            perm=self.perm,
            action='revoked'
        )
        QuxEntityPermissionLog.objects.create(**permlog)
        self.delete()


class QuxEntityPermissionLog(CoreModel):
    app_name = models.CharField(max_length=128)
    entity_name = models.CharField(max_length=128)
    entity_id = models.IntegerField()
    actor = models.ForeignKey(User, on_delete=models.CASCADE)
    authorized = models.ForeignKey(User, on_delete=models.CASCADE, related_name='has_access_to')
    perm = models.ForeignKey(QuxPermission, on_delete=models.CASCADE)
    action = models.CharField(max_length=128)
