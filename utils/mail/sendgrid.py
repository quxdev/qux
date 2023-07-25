import base64
import os

from sendgrid.helpers.mail import (
    FileContent, FileName, FileType,
    Mail, Attachment, To)

from sendgrid.sendgrid import SendGridAPIClient


class QuxSendGrid(object):
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
        except:
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
