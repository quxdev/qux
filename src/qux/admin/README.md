# `qux.admin` — admin base classes

Shared `ModelAdmin` base classes for the `CoreModel` hierarchy. Each base wires up the `dtm_created`/`dtm_updated` columns, sensible `list_display` defaults, and respects soft-delete semantics where applicable.

## Bases

- **`base.py` — `CoreAdmin`** — base for `CoreModel`-derived models. Adds timestamps to `list_display` and `readonly_fields`.
- **`plus.py` — `CoreAdminPlus`** — `CoreAdmin` extension for `CoreModelPlus`. Filters `is_deleted` rows from the changelist by default; adds an "include deleted" toggle.
- **`audit.py` — `CoreAdminAudit`** — admin for the audit-summary / audit-detail tables. Read-only by default.

## Use

```python
from django.contrib import admin
from qux.admin import CoreAdmin
from .models import MyModel

@admin.register(MyModel)
class MyModelAdmin(CoreAdmin):
    list_display = ("name",) + CoreAdmin.list_display
```

## Note

`qux.admin` is not a Django app — it's a plain Python package of admin helpers. No `apps.py`, no migrations.
