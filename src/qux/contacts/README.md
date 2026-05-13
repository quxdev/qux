# `qux.contacts` — concrete contact + company tables

Concrete companion to the abstract bases in `qux.models.contacts`. Provides ready-to-use `Company`, `Contact`, and per-contact phone/email subrecords.

## Models (in `models.py`)

- **`Company`** — concrete `AbstractCompany` (slug, name, domain).
- **`Contact`** — `first_name`, `last_name`, `email`, `phone`, `company` FK (SET_NULL).
- **`AbstractContactPhone`** — abstract base for per-contact phone rows. FK to `Contact` (CASCADE), normalized via `phonenumbers` on `pre_save`.
- **`AbstractContactEmail`** — abstract base for per-contact email rows. FK to `Contact` (CASCADE).

## Why both abstract phone/email and concrete Contact

`Contact` carries a single primary `email` and `phone`. Downstream apps that need _multiple_ phones or emails per contact concretize `AbstractContactPhone` / `AbstractContactEmail` in their own app. This keeps the common case simple and the multi-value case explicit.

## Wiring

```python
INSTALLED_APPS = [..., "qux.contacts"]
```

No URLs; pure data layer.

## Caveat

There's overlap between `qux.contacts` (concrete) and `qux.models.contacts` (abstract — `AbstractCompany`, `AbstractProfile`). Don't try to use both simultaneously for the same concept; pick one ownership model per project. Migration ownership cleanup is tracked in the project consolidation backlog.
