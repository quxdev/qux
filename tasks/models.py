from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from qux.models import CoreModel
from qux.models import default_null_blank


class TaskStatus(CoreModel):
    SLUG_PREFIX = "taskstatus"
    slug = models.CharField(max_length=17, unique=True)
    order = models.IntegerField(default=-1)
    name = models.CharField(max_length=16, unique=True)
    description = models.CharField(max_length=64)

    class Meta:
        db_table = "task_status"
        verbose_name = "Task Status"
        verbose_name_plural = "Task Statuses"
        ordering = ("order",)


class QueuedTask(CoreModel):
    SLUG_PREFIX = "task"

    slug = models.CharField(max_length=11, unique=True)
    status = models.ForeignKey(TaskStatus, on_delete=models.DO_NOTHING)
    user = models.CharField(max_length=11)
    task = models.CharField(max_length=255)
    data = models.JSONField(**default_null_blank)
    # ContentTypes
    content_type = models.ForeignKey(
        ContentType, **default_null_blank, on_delete=models.CASCADE
    )
    object_id = models.PositiveIntegerField(**default_null_blank)
    content_object = GenericForeignKey()

    class Meta:
        db_table = "qux_task_queue"

    @classmethod
    def get_queryset(cls, user, task):
        if user is None:
            return

        queryset = cls.objects.filter(task=task)
        if not user.is_superuser:
            queryset = cls.objects.filter(user=user)

        return queryset
