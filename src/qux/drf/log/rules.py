from __future__ import annotations

from django.core.cache import cache

from .models import APILoggingRule

ALLOW_CACHE_KEY = "drf_log:allow_users"
DENY_CACHE_KEY = "drf_log:deny_users"
CACHE_TIMEOUT = 60  # seconds


def _load_sets() -> tuple[set[int], set[int]]:
    allow: set[int] | None = cache.get(ALLOW_CACHE_KEY)
    deny: set[int] | None = cache.get(DENY_CACHE_KEY)
    if allow is None or deny is None:
        allow = set(
            APILoggingRule.objects.filter(active=True, enabled=True).values_list(
                "user_id", flat=True
            )
        )
        deny = set(
            APILoggingRule.objects.filter(active=True, enabled=False).values_list(
                "user_id", flat=True
            )
        )
        cache.set(ALLOW_CACHE_KEY, allow, CACHE_TIMEOUT)
        cache.set(DENY_CACHE_KEY, deny, CACHE_TIMEOUT)
    return allow or set(), deny or set()


def invalidate_rules_cache() -> None:
    cache.delete_many([ALLOW_CACHE_KEY, DENY_CACHE_KEY])


def should_log(user_identifier: str | None) -> bool:
    """
    Decide whether to log this request.
    user_identifier is expected to be a string like "userid_123" or a slug; we only honor
    numeric IDs if present, otherwise fall back to deny/allow-empty policy.
    Precedence: deny > allow > default allow.
    """

    allow_set, deny_set = _load_sets()

    # Try to parse numeric id from common patterns; ignore non-numeric slugs
    user_id: int | None = None
    if user_identifier and isinstance(user_identifier, str):
        try:
            if user_identifier.startswith("userid_"):
                user_id = int(user_identifier.split("_", 1)[1])
            else:
                # If the whole identifier is numeric, honor it
                user_id = int(user_identifier)
        except (ValueError, IndexError):
            user_id = None

    if user_id is not None:
        if user_id in deny_set:
            return False
        if user_id in allow_set:
            return True

    # Default: allow logging when no explicit deny.
    return True
