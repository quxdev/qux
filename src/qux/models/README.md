# `qux.models` — abstract model bases

Abstract `models.Model` subclasses that downstream concrete models inherit from. Nothing concrete is defined here.

## Bases (in `models/base.py`)

- **`CoreModel`** — adds `dtm_created` (auto_now_add) and `dtm_updated` (auto_now), plus `to_dict(self)`, `get_dict(cls, pk)`, and an opt-in auto-slug pattern (set `SLUG_PREFIX` and `SLUG_ALLOWED_CHARS` on the subclass to enable). Also provides `randomize()` for test-data generation.
- **`QuxModel`** — `CoreModel` extended with utilities consumed by `qux.seo` and `qux.token`. Use this for app models that want extra niceties.
- **`AbstractLead`** — base for lead-capture forms (name, email, phone, source, status).

## Soft delete (in `models/plus.py`)

- **`CoreModelPlus`** — `CoreModel` + `is_deleted` boolean. `delete()` sets the flag; `CoreManagerPlus.get_queryset()` hides them.

  Caveat: the manager filter does **not** propagate through reverse FK relations (`parent.children.all()` returns soft-deleted rows). Plan a fix or use `CoreModelPlus.objects.filter(...)` directly.

## Audit (in `models/audit.py`)

- **`CoreModelAuditSummary`** — base for per-model audit summary rows.
- **`CoreModelAuditDetails`** — base for per-field change detail rows.

## Contacts (in `models/contacts.py`)

- **`AbstractCompany`** — abstract `Company` with `slug`, `name`, `domain` (unique).
- **`AbstractProfile`** — abstract `OneToOneField(User, related_name="%(class)s")` profile.

For concrete contacts/company/phone/email tables, see `qux.contacts`.

## When to use which base

| Need | Use |
|---|---|
| Plain timestamps + slug + dict helpers | `CoreModel` |
| Same, plus soft-delete | `CoreModelPlus` |
| Concrete `qux.seo` / `qux.token`-style model | `QuxModel` |
| Lead capture | `AbstractLead` |
| Audit trail | `CoreModelAuditSummary` + `CoreModelAuditDetails` |
| Company + profile | `AbstractCompany` + `AbstractProfile` |
