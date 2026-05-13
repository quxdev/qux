# Qux Auth

## settings.py

```python
INSTALLED_APPS = [
    ...,
    'qux',
    'qux.auth',
]
```

```python
LOGIN_URL = '/login/'
LOGOUT_URL = '/logout/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
```

## urls.py

```
urlpatterns += [
    path('', include('qux.auth.urls')),
    path('', TemplateView.as_view(template_name='qux_default_home.html'),
name='home'),
]
```

## ENVIRONMENT variables

Configuring Mail

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_SUBJECT_PREFIX`
- `EMAIL_USE_LOCALTIME`

Sending email

- `DEFAULT_FROM_EMAIL`

Sending error messages to `ADMINS` and `MANAGERS`

- `SERVER_EMAIL`

References

- [Django Settings](https://docs.djangoproject.com/en/4.2/ref/settings/)
- [Sending email with Django](https://docs.djangoproject.com/en/4.2/topics/email/)

## Templates

TBD
