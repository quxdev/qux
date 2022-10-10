import base64
import os
import traceback
import re

from django.utils import timezone
from django.conf import settings

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import FileContent, FileName, FileType
from sendgrid.helpers.mail import Mail, Attachment
from sendgrid.helpers.mail import To

from boto3 import client as aws_client
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import urllib

#


class Email(object):
    def __init__(self):
        self.provider = getattr(settings, "EMAIL_PROVIDER", "AWS")
        self.sender = settings.EMAIL_SENDER
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

        if self.provider not in ["aws", "sendgrid"]:
            self.provider = "sendgrid"
        if self.provider == "aws":
            response, status = self._send_using_aws()
        elif self.provider == "sendgrid":
            response, status = self._send_using_sendgrid()
        else:
            response, status = self._send_using_sendgrid()

        obj = self.log(status)
        return obj, response, status

    def log(self, status):

        from core.models import CoreCommLog

        try:
            # ALTER TABLE comm_notification CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            obj = CoreCommLog.objects.create(
                comm_type="email",
                user=self.user,
                provider=self.provider,
                sender=self.sender,
                to=",".join(self.to),
                cc=",".join(self.cc),
                bcc=",".join(self.bcc),
                subject=self.subject,
                message=self.message,
                sent_at=timezone.now(),
                status=status,
            )
            return obj
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            # if '_notification_log' not in self.subject:
            #     trace_error = traceback.format_exc()
            #     message = "_notification_log()<br><br>" \
            #               f"To = {self.to}<br><br>" \
            #               f"Subject = {self.subject}<br><br>" \
            #               f"Exception e = {e}<br><br>" \
            #               f"Stack = {trace_error}"
            #     send_async_bug_email(jsond)
            return None

    def _send_using_sendgrid(self):
        print("Email._send_using_sendgrid()")

        foo = SendGridMessage()
        foo.sender = self.sender
        foo.to = self.to
        foo.also = self.also
        foo.subject = self.subject
        foo.message = self.message
        foo.files = self.files
        message, response = foo.send()
        if response and response.status_code == 202:
            return response, True
        else:
            return response, False


class SendGridMessage(object):
    def __init__(self):
        self.sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        self.sender = "raptor@finmachines.net"
        self.also = None
        self.to = None
        self.subject = "[FM Energy] Raptor Pricing"
        self.message = None
        self.files = None

    def send(self):
        if self.sg is None:
            print("{}.sg = None".format(self.__name__))
            return None, None

        if self.message is None:
            return None, None

        if type(self.to) is str:
            to = [To(self.to)]
        elif type(self.to) is list:
            to = [To(target) for target in self.to]
        else:
            to = []

        if type(self.also) is str:
            to = to + [To(self.also)]
        elif type(self.also) is list:
            to = to + [To(target) for target in self.also]

        message = Mail(
            from_email=self.sender,
            to_emails=to,
            subject=self.subject,
            html_content=self.message,
        )
        if self.files:
            if type(self.files) is list:
                for f in self.files:
                    att = self.getattachment(f)
                    message.add_attachment(att)
            else:
                message.add_attachment(self.files)

        try:
            response = self.sg.send(message)
        except Exception as e:
            response = None

        return message, response

    @staticmethod
    def getattachment(filename):
        if filename is None:
            return None

        with open(filename, "rb") as f:
            data = f.read()
            f.close()

        encoded = base64.b64encode(data).decode()

        attachment = Attachment()
        attachment.file_content = FileContent(encoded)
        attachment.file_type = FileType(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        attachment.file_name = FileName(os.path.basename(filename))
        # attachment.disposition = Disposition('attachment')
        # attachment.content_id = ContentId('Example Content ID')

        return attachment


class AWSEmail(object):
    def __init__(self):
        self.sender = "raptor@finmachines.net"
        self.to = None
        self.cc = None
        self.bcc = None
        self.subject = None
        self.message = None
        self.files = None
        self.client = aws_client(service_name="ses", region_name="us-east-2")

    @staticmethod
    def destination_header(value):
        if type(value) is str:
            return value
        if type(value) is list:
            return ",".join(value)
        return

    @staticmethod
    def destination_aslist(*args):
        result = []
        for arg in args:
            if type(arg) is str:
                result.extend([arg])
            if type(arg) is list:
                result.extend(arg)
        return result

    @staticmethod
    def getattachment(filename):
        if not os.path.exists(filename):
            return None

        part = MIMEApplication(
            open(filename, "rb").read(), filename=os.path.basename(filename)
        )
        part.add_header(
            "Content-Disposition", "attachment", filename=os.path.basename(filename)
        )
        # part.set_type()
        return part

    def send(self):
        if self.client is None:
            return
        if self.subject is None:
            return
        if self.message is None:
            return
        if self.to is None:
            return

        # destination = {
        #     'ToAddresses': self.destination_value(self.to),
        #     'CcAddresses': self.destination_value(self.cc),
        #     'BccAddresses': self.destination_value(self.bcc)
        # }

        # message = {
        #     'Subject': {
        #         'Data': self.subject
        #     },
        #     'Body': {
        #         'Html': {
        #             'Data': self.message
        #         },
        #     }
        # }

        # response = self.client.send_email(
        #     Destination=target,
        #     Message=message,
        #     Source=self.sender
        # )
        # print("AWSEmail send response =", response)
        # return response

        message = MIMEMultipart()

        message["Subject"] = self.subject
        message["From"] = self.sender

        if self.to:
            message["To"] = self.destination_header(self.to)
        if self.cc:
            message["Cc"] = self.destination_header(self.cc)
        if self.bcc:
            message["Bcc"] = self.destination_header(self.bcc)

        part = MIMEText(self.message, "html", "utf-8")
        message.attach(part)

        if self.files:
            if type(self.files) is not list:
                self.files = [self.files]
            for file in self.files:
                attachment = self.getattachment(file)
                if attachment:
                    message.attach(attachment)
                else:
                    print(f"Cannot attach file:{file}")

        rawmessage = dict(Data=message.as_string())
        response = self.client.send_raw_email(
            Destinations=self.destination_aslist(self.to, self.cc, self.bcc),
            Source=self.sender,
            RawMessage=rawmessage,
        )
        return message, response


def test():
    foo = SendGridMessage()
    foo.send()


def test_aws():
    filename = "/Users/vishal/Downloads/Pavo 175MW - 9.13.2020 - Board Meeting - Input File.xlsx"

    foo = AWSEmail()
    foo.to = "vishal@finmachines.com"
    foo.cc = "vishal@finmachines.net"
    foo.bcc = foo.cc
    foo.files = filename
    foo.subject = "RACECAR"
    foo.message = "PALINDROME"


if __name__ == "__main__":
    test_aws()
