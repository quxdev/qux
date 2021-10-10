from django.contrib.auth.models import User
from django.db import models
from django.db import transaction

from .models import CoreModel
from .models import qux_model_to_dict
from qux.utils import stacktrace


class QuxPermission(CoreModel):
    slug = models.SlugField(max_length=32, unique=True)
    app_name = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    description = models.CharField(max_length=128, null=True)

    class Meta:
        db_table = 'qux_permissions'
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
    authorized = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='can_access')
    perm = models.ForeignKey(QuxPermission, on_delete=models.DO_NOTHING)

    class Meta:
        db_table = 'qux_entity_permission'

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


class QuxEntity(CoreModel):
    """
    Abstract class to be inherited by shareable entities
    """
    owner = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    deleted = models.IntegerField(default=0)
    is_shared = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def __str__(self):
        return '<{}:{:d}'.format(self.__class__.__name__, self.id)

    @property
    def all_current_grants(self):
        app_name = 'app_' + self.__class__._meta.app_label
        entity_name = self.__class__.__name__
        entity_id = self.id
        current_grants = QuxPermission.objects.filter(app_name=app_name, entity_name=entity_name, entity_id=entity_id)
        return current_grants

    @property
    def sharedwithinfo(self):
        result = []
        for cg in self.all_current_grants:
            g = {'actor': cg.actor,
                 'authorized': cg.authorized,
                 'perm': cg.perm,
                 }
            result.append(g)
        return result

    @classmethod
    def contents(cls):
        items = cls.objects.filter(deleted=0).order_by('id')
        return [item for item in items]

    @classmethod
    def ownedbyuser(cls, user):
        print(type(user))

        if user is None:
            return

        try:
            items = cls.objects.filter(owner=user, deleted=0).order_by('id')
            result = [item for item in items]
        except TypeError:
            # TypeError: 'AnonymousUser' object is not iterable
            result = None

        return result

    @classmethod
    def getbyid(cls, objid):
        try:
            obj = cls.objects.get(id=objid, deleted=0)
        except cls.DoesNotExist:
            obj = None
        return obj

    @classmethod
    def getbyid_and_owner(cls, objid, user):
        try:
            obj = cls.objects.get(id=objid, owner=user, deleted=0)
        except cls.DoesNotExist:
            obj = None
        return obj

    @classmethod
    def get_sharedwithuser(cls, user):
        """
        List of objects shared with this user by other users
        """
        if user is None:
            return []
        result = []
        notowned = cls.objects.exclude(owner=user).filter(deleted=0)
        result.extend([o for o in notowned if o.has_ro_grantforuser(user)])
        return result

    def custom_to_dict(self, user):
        result = qux_model_to_dict(self)
        result['name'] = self.name
        result['owner_initials'] = self.owner.profile.initials

        sharedwith = []
        for grant in self.all_current_grants:
            sw = {
                'userid': grant.authorized.id,
                'user_initials': grant.authorized.profile.initials,
                'perm': grant.perm.name
            }
            sharedwith.append(sw)

        result['sharedwith'] = sharedwith
        result['myperm'] = [sw['perm'] for sw in sharedwith if sw['userid'] == user.id]
        result['myperm'] = result['myperm'][0] if result['myperm'] else None

        return result

    def get_current_grantforuser(self, user):
        current_usergrants = [g for g in self.all_current_grants if g.authorized == user]
        current_grantforuser = current_usergrants[0] if current_usergrants else None
        return current_grantforuser

    def has_ro_grantforuser(self, user):
        if self.owner == user:
            return True
        grant = self.get_current_grantforuser(user)
        if grant and grant.perm.name in ('ro', 'rw', 'rw-admin'):
            return True
        else:
            return False

    def has_rw_grantforuser(self, user):
        if self.owner == user:
            return True
        grant = self.get_current_grantforuser(user)
        if grant and grant.perm.name in ('rw', 'rw-admin'):
            return True
        else:
            return False

    def has_admin_grantforuser(self, user):
        if self.owner == user:
            return True
        grant = self.get_current_grantforuser(user)
        if grant and grant.perm.name == 'rw-admin':
            return True
        else:
            return False

    def has_execute_grantforuser(self, user):
        if self.owner == user:
            return True
        grant = self.get_current_grantforuser(user)
        if grant and grant.perm.name in ('ro', 'rw', 'rw-admin'):
            return True
        else:
            return False

    def delete(self, **kwargs):
        try:
            self.deleted = self.id
            self.save()
            result = True
        except:
            stacktrace()
            result = False

        return {'deleted': result}

    def rename(self, newname):
        dtmupdated = None
        try:
            self.name = newname
            self.save()
            dtmupdated = self.dtm_updated.strftime("%b %d, %Y %H:%M")
            result = True
        except:
            stacktrace()
            result = False
        return {'updated': result, 'dtmupdated': dtmupdated}

    @transaction.atomic
    def sharewith(self, userid, actor, app_name, permname='ro'):
        """
        Share this object with other user. Default perm is 'ro'
        """
        entity_name = self.__class__.__name__
        entity_id = self.id
        user = User.objects.filter(id=userid).first()
        if user is None or user == self.owner:
            return False, 'Sharing with the specified user is not possible.'
        perm = QuxPermission.objects.filter(app_name=app_name, name=permname).first()
        if perm is None:
            return False, 'Sharing with the specified permission is not possible.'

        try:
            current_grant = self.get_current_grantforuser(user)
            if current_grant:
                if current_grant.perm == perm:
                    return True, ''
                else:
                    current_grant.revoke(actor=actor)
            QuxEntityPermission.get_or_create(app_name, entity_name, entity_id, actor, user, perm,)
            self.is_shared = True
            self.save()
            result = True, ''
        except:
            stacktrace()
            result = False, 'Error while sharing.'
        return result

    @transaction.atomic
    def revokefrom(self, userid, actor):
        """
        Revoke access to this object from other user
        """
        user = User.objects.filter(id=userid).first()
        if user is None or user == self.owner:
            return False, 'Revoking from specified user is not possible.'

        try:
            current_grant = self.get_current_grantforuser(user)
            if current_grant:
                current_grant.revoke(actor=actor)
                if self.all_current_grants.count() == 0:
                    self.is_shared = False
                    self.save()
                result = True, ''
            else:
                result = False, 'No current grant present for the specified user. Can not be revoked.'
        except:
            stacktrace()
            result = False, 'Error while revoking.'
        return result


class QuxEntityPermissionLog(CoreModel):
    app_name = models.CharField(max_length=128)
    entity_name = models.CharField(max_length=128)
    entity_id = models.IntegerField()
    actor = models.ForeignKey(User, on_delete=models.CASCADE)
    authorized = models.ForeignKey(User, on_delete=models.CASCADE, related_name='has_access_to')
    perm = models.ForeignKey(QuxPermission, on_delete=models.CASCADE)
    action = models.CharField(max_length=128)

    class Meta:
        db_table = 'qux_entity_permission_log'
