from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from rangefilter.filters import DateRangeFilter

default_null_blank = dict(default=None, null=True, blank=True)


class CoreManager(models.Manager):
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except ObjectDoesNotExist:
            return None


class CoreModel(models.Model):
    objects = CoreManager()
    all_objects = models.Manager()

    dtm_created = models.DateTimeField(
        verbose_name='DTM Created',
        auto_now_add=True
    )
    dtm_updated = models.DateTimeField(
        verbose_name='DTM Updated',
        auto_now=True
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.dtm_created:
            self.dtm_created = timezone.now()
        self.dtm_updated = timezone.now()
        return super(CoreModel, self).save(*args, **kwargs)

    @classmethod
    def initdata(cls):
        print('{}.initdata()'.format(cls.__name__))

    def to_dict(self):
        return model_to_dict(self, exclude=['id', 'dtm_created', 'dtm_updated'])

    @classmethod
    def get_dict(cls, pk):
        result = cls.objects.get(id=pk)
        return result.to_dict()


class CoreModelAdmin(admin.ModelAdmin):
    list_display = ('dtm_created', 'dtm_updated',)
    list_filter = (
        ('dtm_created', DateRangeFilter),
        ('dtm_updated', DateRangeFilter)
    )
    readonly_fields = ('dtm_created', 'dtm_updated',)

    list_per_page = 50
    show_full_result_count = False

    # noinspection PyProtectedMember
    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """

        # Default: qs = self.model._default_manager.get_query_set()
        qs = self.model._default_manager.get_queryset()

        # TODO: this should be handled by some parameter to the ChangeList.
        # () because *None is bad
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


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

    def delete(self, **kwargs):
        self.is_deleted = True
        self.save()

    def restore(self):
        self.is_deleted = False
        self.save()


class CoreModelPlusAdmin(admin.ModelAdmin):
    list_display = ('is_deleted', 'dtm_created', 'dtm_updated',)
    list_filter = (
        'is_deleted',
        ('dtm_created', DateRangeFilter),
        ('dtm_updated', DateRangeFilter)
    )
    readonly_fields = ('dtm_created', 'dtm_updated',)

    list_per_page = 50
    show_full_result_count = False

    # noinspection PyProtectedMember
    def get_queryset(self, request):
        """
        Returns a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """

        # Default: qs = self.model._default_manager.get_query_set()
        qs = self.model._default_manager.all_with_deleted()

        # TODO: this should be handled by some parameter to the ChangeList.
        # () because *None is bad
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs
