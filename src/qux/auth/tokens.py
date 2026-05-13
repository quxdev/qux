from django.contrib.auth.tokens import PasswordResetTokenGenerator


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.is_active) + str(user.password)


account_activation_token = TokenGenerator()


class MagicLinkTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Do NOT include last_login to avoid scanners consuming links.
        # Include password so tokens invalidate if password changes.
        return str(user.pk) + str(timestamp) + str(user.is_active) + str(user.password)


magic_link_token = MagicLinkTokenGenerator()
