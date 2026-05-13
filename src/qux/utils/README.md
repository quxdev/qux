# `qux.utils` — pure utility leaves

A flat set of single-purpose helper modules. Each leaf is independent (no cross-utility imports, no `qux.*` app imports) and consumable in isolation. The package itself (`qux/utils/__init__.py`) is empty — import from the leaf you want, never from the package.

## Leaves

| Module | What it provides |
|---|---|
| `qux.utils.coerce` | `cast(valtype, value, default=None)`, `toint`, `tofloat`, `tobool`, `tostring`, `tonumericlist` — string → typed-value with safe fallback. |
| `qux.utils.date` | `daterange`, `eomonth`, `fomonth`, `todate`, `FMT_DTSTR` — date arithmetic + parse helpers. |
| `qux.utils.decorators` | `qux_debug` — log-on-entry decorator gated on `settings.DEBUG`. |
| `qux.utils.devtools` | `stacktrace(depth=6)` — emit current traceback on the `qux` logger. |
| `qux.utils.file` | `filedate`, `filehash`, `uploadfile` — filesystem + upload helpers. |
| `qux.utils.forms` | `QuxForm`, `QuxModelForm` — Bootstrap-classed Django form bases. |
| `qux.utils.json` | `QuxComplexEncoder` — JSON encoder for datetime / Decimal / UUID / numpy scalars. |
| `qux.utils.modelfields` | `FloatListField`, `validate_comma_separated_float_list` — list-as-CSV ORM field. |
| `qux.utils.mysql` | `resetsequence` — reset auto-increment after manual data load. |
| `qux.utils.phone` | `phone_number(s, country=...)`, `format_phone_number` — E.164 parse/format via `phonenumbers`. |
| `qux.utils.random` | `random_string`, `random_number` — short identifier generators. |
| `qux.utils.urls` | `fetchurl`, `MetaURL` — HTTP fetch + OG/canonical meta extraction. Not Django URLconf. |
| `qux.utils.validators` | `ValidateListOfN` — comma-separated-list validator. |

## Import shape

Always import from the leaf:

```python
from qux.utils.coerce import cast
from qux.utils.date import daterange
import json
from qux.utils.json import QuxComplexEncoder
```

`from qux.utils import cast` will raise `ImportError`. The package does not re-export; explicit leaf imports keep call sites unambiguous and prevent stdlib-name shadowing (`qux.utils.json` and `qux.utils.random` coexist with stdlib `json` / `random` without surprise).

## Architectural contract

`pyproject.toml [tool.importlinter]` declares "Utilities don't depend on apps": no leaf under `qux.utils` may import from `qux.auth`, `qux.token`, `qux.seo`, `qux.qhook`, `qux.contacts`, `qux.telemetry`, `qux.drf`, `qux.pagespeed`, or `qux.sitespeed`. Verified by `lint-imports`.

If you find yourself wanting to add an app import to a util, the util is misplaced — promote it into the consuming app or split the concern.
