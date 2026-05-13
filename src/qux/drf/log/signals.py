from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save

from .models import APILoggingRule
from .rules import invalidate_rules_cache


class Signals:
    """Signal hookups for API logging."""

    @staticmethod
    def connect():

        post_save.connect(lambda *args, **kwargs: invalidate_rules_cache(), sender=APILoggingRule)
        post_delete.connect(lambda *args, **kwargs: invalidate_rules_cache(), sender=APILoggingRule)

        # Ensure default API logging rule for new users (enabled=True)
        UserModel = get_user_model()

        def ensure_default_rule(sender, instance, created, **kwargs):
            if not created:
                return
            APILoggingRule.objects.get_or_create(
                user=instance, defaults={"enabled": True, "active": True}
            )
            invalidate_rules_cache()

        post_save.connect(ensure_default_rule, sender=UserModel)
