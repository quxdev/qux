from qux.models import CoreModel, default_null_blank

from django.db import models
from django.contrib.auth.models import User
from utils.slop import get_random_string


class Webhook(CoreModel):
    slug = models.CharField(max_length=8, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    app = models.CharField(max_length=32)
    action = models.CharField(max_length=64, **default_null_blank)
    url = models.URLField()
    secret = models.CharField(max_length=32, **default_null_blank)
    is_validated = models.DateTimeField(**default_null_blank)

    class Meta:
        unique_together = (('user', 'app', 'action'),)
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.secret = get_random_string(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def validate(self):
        try:
            response = requests.get(self.url, verify=False)
        except requests.exceptions.SSLError as e:
            print("Website does not support https.\n")
            print(str(e))
            return False, "ERR_SSL_PROTOCOL_ERROR"
        except Exception as e:
            trace_error = traceback.format_exc()
            message = "validate()<br><br>" \
                      f"IVRWebhook ID = {self.id}<br><br>" \
                      f"URL = {self.url}<br><br>" \
                      f"Exception e = {e}<br><br>" \
                      f"trace_error = {trace_error}"
            jsond = {
                'subject': f'IVR({self.ivr.id}) | IVRWebhook({self.id}).validate(): Exception',
                'message': message,
            }
            create_async_task('core.comm.tasks.send_async_bug_email', jsond)
            return False, None

        response_text = response.text.strip('\"')
        print("IVRWebhook get response =", response)
        print("IVRWebhook get response_text =", str(response_text))
        print("IVRWebhook get self.secret =", str(self.secret))

        if str(response_text) == str(self.secret):
            self.is_validated = timezone.now()
            self.save()
            return True, None
        return False, None

    def test_webhook(self, app, action):
        url = self.url
        secret = self.secret
        data = {
            'app': app,
            'action': action,
            'secret': secret,
        }
        response = requests.post(url, data=data)
        print("IVRWebhook test_webhook response =", response)
        print("IVRWebhook test_webhook response.text =", response.text)
        return response.text
