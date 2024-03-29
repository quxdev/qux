import os
from binascii import hexlify

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework.authentication import TokenAuthentication

from qux.models import QuxModel


class CustomToken(QuxModel):
    key = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=128)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Custom Token"
        verbose_name_plural = "Custom Tokens"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    @classmethod
    def generate_key(cls):
        return hexlify(os.urandom(20)).decode()


class CustomTokenAuthentication(TokenAuthentication):
    model = CustomToken
