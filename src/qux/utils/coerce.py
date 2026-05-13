"""Best-effort type coercion helpers.

Each function takes an arbitrary input plus a default, returns the coerced
value or the default if coercion fails. No exceptions raised by these
functions — they're for input-cleaning at boundaries (form data, CSV cells,
API request bodies) where a partial-data result is preferred over a hard fail.
"""

from __future__ import annotations

from typing import Any


def tofloat(numstr: Any, defaultvalue: float | None = None) -> float | None:
    """Coerce to ``float``. Strips ', ' separators. Returns ``defaultvalue`` on failure."""
    if isinstance(numstr, (int, float)):
        return float(numstr)

    if isinstance(numstr, str) and numstr == "":
        return float(0)

    try:
        return float(numstr.replace(", ", ""))
    except (ValueError, AttributeError):
        return defaultvalue


def toint(numstr: Any, default: int | None = None) -> int | None:
    """Coerce to ``int``. Strips ', ' separators. Returns ``default`` on failure."""
    if isinstance(numstr, (int, float)):
        return int(numstr)
    if isinstance(numstr, str):
        if numstr == "":
            return default
        try:
            return int(numstr.replace(", ", ""))
        except (ValueError, AttributeError):
            return default
    return default


def tostring(somevalue: Any) -> Any:
    """Format numeric values with thousands separators; pass other types through unchanged."""
    numdecimalplaces = 2
    if isinstance(somevalue, float):
        return f"{somevalue:,.{numdecimalplaces}f}"
    if isinstance(somevalue, int):
        return f"{somevalue:,d}"
    return somevalue


def tonumericlist(target: Any) -> list[float | int] | None:
    """If ``target`` is a list, return all-numeric copy (non-numeric items become 0).

    Returns None if input isn't a list. If every element is already numeric,
    returns the input list unchanged (no copy).
    """
    if not isinstance(target, list):
        return None

    if all(isinstance(x, (int, float)) for x in target):
        return target

    return [x if isinstance(x, (int, float)) else 0 for x in target]


def tobool(x: Any) -> bool:
    """Truthy strings: 'yes', 'y', 'true', '1' (case-insensitive). Everything else: False."""
    return str(x).lower() in ("yes", "y", "true", "1")


def cast(valtype: str, value: Any, default: Any = None) -> Any:
    """String-typed coercion: dispatch on a type name (``"int"``, ``"float"``, ``"bool"``).

    Older API that takes the target type as a string. Useful when the target
    type isn't known at code-write time (e.g. CSV/DB rows that carry both a
    value and its intended type as separate columns). New code that knows the
    target type should prefer the typed helpers (``toint``, ``tofloat``,
    ``tobool``) — cleaner signatures, no string dispatch.

    Doesn't handle datetime types.
    """
    valtype = valtype.lower()

    if hasattr(value, "lower") and value.lower() in ("none", "null"):
        return None

    if valtype == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    if valtype == "float":
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    if valtype == "bool" and hasattr(value, "lower"):
        if value.lower() in ("true", "1"):
            return True
        if value.lower() in ("false", "0"):
            return False
        return default

    return value
