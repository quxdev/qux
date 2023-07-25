import re

from django.conf import settings
from django.utils import timezone

from .sendgrid import QuxSendGrid


class Email(object):
    def __init__(self):
        self.provider = getattr(settings, "EMAIL_PROVIDER", "AWS")
        self.sender = settings.EMAIL_SENDER
        self.mailer = QuxSendGrid()
        self.to = None
        self.also = None
        self.cc = None
        self.bcc = None
        self.subject = None
        self.message = None
        self.files = None
        self.user = None

    @staticmethod
    def validate_email(email):
        regex = r"^[\w\d._%+\-]+@(?![.])[\w\d.\-]+\.[\w\d]{2,}$"
        email_regex = re.compile(regex)

        if type(email) is str:
            if email_regex.match(email):
                return True
        elif type(email) is tuple:
            if email_regex.match(email[1]):
                return True
        return False

    def validate_target(self, single_target):
        to = []
        if type(single_target) is str:
            if self.validate_email(single_target):
                to = [single_target]
        elif type(single_target) is list:
            to = [target for target in single_target if self.validate_email(target)]

        return to

    def validate_all_targets(self):
        self.to = self.validate_target(self.to)
        self.cc = self.validate_target(self.cc)
        self.bcc = self.validate_target(self.bcc)

    def send(self):
        """

        :return: comm_object, response, status
        """
        result = (None, None, False)
        self.validate_all_targets()
        if len(self.to) == 0:
            return result
        if self.subject is None:
            return result
        if self.message is None:
            return result

        self.mailer.sender = self.sender
        self.mailer.to = self.to
        self.mailer.also = self.also
        self.mailer.subject = self.subject
        self.mailer.message = self.message
        self.mailer.files = self.files
        message, response = self.mailer.send()
        status = response and response.status_code == 202

        obj = self.log(status)
        return obj, response, status

    def log(self, status):
        obj = {
            "comm_type": "email",
            "user": self.user,
            "provider": self.provider,
            "sender": self.sender,
            "to": ",".join(self.to),
            "cc": ",".join(self.cc),
            "bcc": ",".join(self.bcc),
            "subject": self.subject,
            "message": self.message,
            "sent_at": timezone.now(),
            "status": status,
        }
        return obj

