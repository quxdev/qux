# Qux: A Django Template

## Installation

### _blank.html

Create your own _blank.html file and add your own CSS and JS files

```html
{% extends '_seo.html' %}

...

{% block stylesheets %}
{{ block.super }}
{# Bootstrap is included with _seo.html #}
{# Overload after block.super if you don't want the Qux version #}
<link rel="stylesheet" href="{% static 'css/site.css' %}">
{% endblock %}

{% block javascript %}
{{ block.super }}
{# Bootstrap is included with _seo.html #}
{# Overload after block.super if you don't want the Qux version #}
{# Site Javascript #}
<script src="{% static 'js/site.js' %}"></script>
{% endblock}}
```

## Introduction

Qux is a django template with augmented models,
extra template tags, and useful utilities.

It is similar in intent to django_extensions, a massively useful tool.

- [Core](auth/README.md)
- Auth
- SEO
- Templates
- TemplateTags
- Utils
  - `mysql`
  - `date`
  - `phone`

## Core [_qux_core_]

### Models

- `CoreModel`
  - `dtm_created`
  - `dtm_updated`
  - `to_dict(self)`
  - `get_dict(cls, pk)`
  - `slug` - CharField() that also indicates if the model requires auto-slugs
  - `AUDIT_SUMMARY` - AuditSummary model
  - `AUDIT_DETAIL` - AuditDetail model
- `CoreModelPlus` - where all deleted rows are soft-deleted only
- `AbstractLead`
- `CoreModelAuditSummary`
- `CoreModelAuditDetail`

#### qux_auth

- `Company`
- `Profile` - `OneToOne(User)`

#### qux_core

Abstractions

- `AbstractCompany`
- `AbstractContactPhone`
- `AbstractContactEmail`
- `AbstractContact`

Logging

- `DownloadLog`
- `UploadLog`
- `CoreURLLog`
- `CommLog`

## Auth [_qux_auth_]

### urls.py

```python
urlpatterns += [
    ...,
    path("", include("qux.auth.urls.appurls", namespace="qux_auth")),
    ...,
]
```

### URLS

- _login/_
- _logout/_
- _change-password/_
- _password-reset/_

## SEO [_qux_seo_]

### Models

- `SEOSite` - `OneToOne(Site)`
- `SEOPage`

### Mixin

- SEOMixin

## Templates

- `_blank.html`

## Template Tags

### Library: qux

- `multiply`
- `divide`
- `atleast`
- `qux_min`
- `qux_max`
- `date_before`
- `addstr`
- `url_replace`
- `{% lineless %}{% endlineless %}`

### Library: quxform

- `is_checkbox` &rightarrow; `Boolean`

Add these configuration in `project/project/settings.py` file after adding `qux` app in your project
```sh
LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
SHOW_USERNAME_SIGNUP = False

ROOT_TEMPLATE = "_app.html"
```
