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