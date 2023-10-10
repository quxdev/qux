import hashlib
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from qux.models import CoreModel
from qux.models import default_null_blank


# from django_mysql.models import EnumField


class DownloadLog(CoreModel):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, **default_null_blank)
    url = models.URLField(max_length=2048, verbose_name="URL")
    original = models.CharField(
        max_length=128, **default_null_blank, verbose_name="Original File Name"
    )
    filename = models.CharField(
        max_length=128, **default_null_blank, verbose_name="Download File Name"
    )

    class Meta:
        db_table = "qux_log_download"
        verbose_name = "Download Log"


class UploadLog(CoreModel):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, **default_null_blank)
    filename = models.CharField(max_length=128)
    filepath = models.CharField(max_length=256)
    filehash = models.CharField(max_length=16, editable=False)
    filedate = models.DateTimeField()

    class Meta:
        db_table = "qux_log_upload"
        verbose_name = "Upload Log"

    def save(self, *args, **kwargs):
        # https://stackoverflow.com/a/3431838/
        fullpath = os.path.join(settings.BASE_DIR, self.filepath, self.filename)
        filehash = hashlib.md5()
        with open(fullpath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                filehash.update(chunk)
        self.filehash = filehash.hexdigest()

        # https://stackoverflow.com/a/25527773/
        super().save(*args, **kwargs)


class CoreURLLog(CoreModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name="authlog_user"
    )
    username = models.CharField(max_length=100, null=True, blank=True)
    accesstoken = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    request = models.CharField(max_length=255, null=True, blank=True)
    urlpath = models.CharField(max_length=500)
    params = models.TextField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=False)
    csrf = models.CharField(max_length=255, null=True, blank=True)
    responsetype = models.CharField(
        max_length=128, default="application/json", null=True, blank=True
    )
    response = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "qux_log_url"
        verbose_name = "URL Log"
        verbose_name_plural = "URL Log"

    def __str__(self):
        return "{:d}".format(self.id if self.id else id(self))


class CoreCommLog(CoreModel):
    NOTIFICATION_TYPE = (
        ("sms", "sms"),
        ("email", "email"),
        ("whatsapp", "whatsapp"),
    )

    comm_type = models.CharField(
        max_length=16,
        choices=NOTIFICATION_TYPE,
        default="email",
        verbose_name="Comm Type",
    )
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, **default_null_blank)
    provider = models.CharField(
        max_length=32, **default_null_blank, verbose_name="Service Provider"
    )
    sent_at = models.DateTimeField(
        editable=False, **default_null_blank, verbose_name="Sent At"
    )
    sender = models.CharField(max_length=128)
    to = models.CharField(max_length=512, **default_null_blank)
    cc = models.CharField(max_length=512, **default_null_blank)
    bcc = models.CharField(max_length=512, **default_null_blank)
    subject = models.CharField(max_length=256, **default_null_blank)
    message = models.TextField(**default_null_blank)
    attrs = models.JSONField(**default_null_blank, verbose_name="Attributes")
    status = models.BooleanField(default=False)
    response = models.TextField(**default_null_blank)

    class Meta:
        db_table = "qux_log_comm"
        verbose_name = "Communication Log"
        verbose_name_plural = "Communication Log"
