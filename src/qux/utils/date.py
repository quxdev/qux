"""Date / datetime helpers — month boundaries, range iteration, fuzzy parse."""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from typing import Any

# Format strings tried in order by ``todate`` when coercing strings to date.
# Add new formats at the end; earlier formats win on ambiguous input.
FMT_DTSTR = [
    "%Y-%m-%d",
    "%b %Y",
    "%b_%Y",
    "%Y-%m-%d %H:%M",
    "%Y%m%d",
    "%Y%m%d %H:%M",
    "%d%b%Y",
    "%m/%d/%y",
    "%d%b%Y %H:%M",
    "%b-%d-%y",
    "%b-%d-%y %H:%M",
    "%d-%b-%Y",
    "%d-%b-%Y %H:%M",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%d-%m-%Y",
    "%d-%m-%Y %H:%M",
    "%b-%y",
    "%H:%M",
]


def eomonth(dt: datetime.date, nummonths: int) -> datetime.date:
    """Return the date reflecting the end-of-month for ``dt`` shifted by ``nummonths``."""
    eomyr = dt.year + ((dt.month + nummonths) // 12)
    eommo = (dt.month + nummonths) % 12
    return datetime.date(eomyr, eommo + 1, 1) + datetime.timedelta(days=-1)


def fomonth(dt: datetime.date, nummonths: int) -> datetime.date:
    """Return the first-of-month for ``dt`` shifted by ``nummonths``."""
    return eomonth(dt, nummonths - 1) + datetime.timedelta(days=1)


def daterange(start: datetime.date, end: datetime.date) -> Iterator[datetime.date]:
    """Yield each date from min(start,end) through max(start,end), inclusive."""
    numberofdays = abs((end - start).days)
    d = min(start, end)
    for n in range(numberofdays + 1):
        yield d + datetime.timedelta(days=n)


def todate(x: Any, default: Any = None, timestamp: bool = False) -> Any:
    """Coerce ``x`` to a ``date`` (or ``datetime`` if ``timestamp=True``).

    Returns ``default`` when ``x`` cannot be parsed. String inputs are tried
    against every format in :data:`FMT_DTSTR`; the first match wins.
    """
    if isinstance(x, datetime.datetime):
        return x if timestamp else x.date()
    if isinstance(x, datetime.date):
        return x
    if isinstance(x, str):
        for fmt in FMT_DTSTR:
            try:
                result = datetime.datetime.strptime(x, fmt)
            except ValueError:
                continue
            return result if timestamp else result.date()
    return default
