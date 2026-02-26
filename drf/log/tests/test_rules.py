from django.contrib.auth import get_user_model
from django.test import TestCase

from qux.drf.log.models import APILoggingRule
from qux.drf.log.rules import invalidate_rules_cache, should_log


class TestLoggingRules(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="u1", email="u1@example.com"
        )
        self.user.set_unusable_password()
        self.user.save()
        invalidate_rules_cache()

    def test_allow_rule_enables_logging(self):
        # Signal auto-creates an enabled rule; verify it works
        rule = APILoggingRule.objects.get(user=self.user)
        self.assertTrue(rule.enabled)
        self.assertTrue(should_log(f"userid_{self.user.id}"))

    def test_deny_overrides_allow(self):
        # Switch the auto-created rule to disabled
        APILoggingRule.objects.filter(user=self.user).update(enabled=False)
        invalidate_rules_cache()
        self.assertFalse(should_log(f"userid_{self.user.id}"))

    def test_unknown_user_defaults_allow(self):
        self.assertTrue(should_log("userid_99999"))
