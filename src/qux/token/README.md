# `qux.token` — DRF token CRUD with per-user UI

Django REST Framework token authentication with a Django-side UI for users to create / list / view / delete their own API keys. Wraps `rest_framework.authentication.TokenAuthentication`.

## Models

- **`CustomToken`** — token row, `OneToMany(User)` (a user can have multiple named tokens, unlike DRF's default 1:1).
- **`CustomTokenAuthentication`** — DRF authentication class; resolves a request's `Authorization: Token <key>` header to a User.

## Wiring

```python
# settings.py
INSTALLED_APPS = [..., "qux.token"]
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "qux.token.models.CustomTokenAuthentication",
        # plus session/basic if needed
    ],
}

# urls.py
urlpatterns += [path("token/", include("qux.token.urls", namespace="qux_token"))]
```

## URLs (namespace `qux_token`)

- `""` (list view, name=`home`)
- `<key>/` (detail view, name=`key`)
- `new/` (create view, name=`new`)
- `<key>/update/` (rename, name=`update`)
- `<key>/delete/` (delete, name=`delete`)

Templates select between bs4 and bs5 variants based on `settings.BOOTSTRAP`.

## Mixins

`mixins.py` provides DRF view mixins for endpoints that want token auth with extra rate-limit / scoping behaviour. Apply alongside `CustomTokenAuthentication`.

## Naming note

The package is named `qux.token` — not to be confused with Python's stdlib `token` module. The two coexist because qux is always imported as a fully-qualified `qux.token`. Don't run scripts with cwd inside the qux source tree as a top-level entry; if you must, see `runtests.py` for the sys.path strip pattern.
