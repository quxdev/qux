# Qux Web hooks - QHOOK
```
A simple webhook module to be able to register a hook and return data upon completion as required.
The webhook will be attempted multiple times in case of a failure upto a maximum provided in the settings - QHOOK_MAX_ATTEMPTS
```

## settings.py

```python
INSTALLED_APPS = [
    ...,
    'qux.qhook',
]
```

```python
QHOOK_EVENTS = ["calculation_completed"]
QHOOK_MAX_ATTEMPTS = 3

```

## apiviews.py

```
register the hook in the required api as follows: Identifier is a unique string like a slug for the given calculation
the request should have a target_url else it will not register and ignore the webhook registration.
```
```python
from qux.qhook.models import QHookTarget
QHookTarget.register(self.request, <identifier>, "calculation_completed")
```

## tasks.py
```
Define a method to call the hook with the required data as the following example:
@qhook decorator will use the data returned from the method to be sent to the calling user.
A callback is acted upon only if the event is listed in the QHOOK_EVENTS list in settings.

```
```python
@qhook
def call_hook(slug, event):
    data = {
        "identifier": slug,
        "event": event,
        "dragon_slug": slug,
    }
    return data
```

```
Calling App/Service
1. Will need a callback url to be sent as part of the service call as target_url
2. A view to handle the incoming post request on the target_url