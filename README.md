# Qux: A Django Template

## Installation

### _blank.html

Create your own _blank.html file and add your own CSS and JS files

```html
{% block stylesheets %}
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"
      integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3"
      crossorigin="anonymous">
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css">
{{ block.super }}
<link rel="stylesheet" href="/static/css/site.css">
{% endblock %}
```

```html
{% block javascript %}
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"
        integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p"
        crossorigin="anonymous"></script>
{{ block.super }}
```
## Introduction

Qux is a django template with augmented models,
extra template tags, and useful utilities.

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
- CoreModelPlus - where all deleted rows are soft-deleted only


- `AbstractCompany`
- `AbstractContact`
- `AbstractContactPhone`
- `AbstractContactEmail`


- `Company`
- `Profile` - `OneToOne(User)`


- `DownloadLog`
- `UploadLog`
- `CoreURLLog`
- `CommLog`

## Auth [_qux_auth_]

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
