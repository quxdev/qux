"""qux.auth has no ORM models of its own.

Earlier versions hosted ``Service`` and ``Preference`` models here. Both were
project-specific (general key/value-by-name storage; only one downstream
consumer in production). They were removed in May 2026 — qux.auth is now
authentication views, forms, and tokens only.

Downstream apps that need a key/value preference store should define their
own ``Preference`` model in their own app rather than reaching into a
shared library namespace. The original migration history (``0002_preference_service``,
etc.) and the ``qux_preference`` / ``qux_service`` tables remain in place so
existing data is queryable; only the ORM model classes are gone.
"""
