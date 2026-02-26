import base64
import mimetypes
import os

from sendgrid.helpers.mail import FileContent, FileName, FileType, Mail, Attachment, To

from sendgrid.sendgrid import SendGridAPIClient


class QuxSendGrid:
    def __init__(self):
        self.sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        self.sender = None
        self.also = None
        self.to = None
        self.subject = None
        self.message = None
        self.files = None

    def send(self):
        if self.sg is None:
            return None, None

        if self.message is None:
            return None, None

        if isinstance(self.to, str):
            to = [To(self.to)]
        elif isinstance(self.to, list):
            to = [To(target) for target in self.to]
        else:
            to = []

        if isinstance(self.also, str):
            to = to + [To(self.also)]
        elif isinstance(self.also, list):
            to = to + [To(target) for target in self.also]

        message = Mail(
            from_email=self.sender,
            to_emails=to,
            subject=self.subject,
            html_content=self.message,
        )
        if self.files:
            if isinstance(self.files, list):
                for f in self.files:
                    att = self.getattachment(f)
                    message.add_attachment(att)
            else:
                message.add_attachment(self.files)

        try:
            response = self.sg.send(message)
        except Exception:  # pylint: disable=broad-exception-caught
            response = None

        return message, response

    @staticmethod
    def getattachment(filename):
        if filename is None:
            return None

        with open(filename, "rb") as f:
            data = f.read()

        encoded = base64.b64encode(data).decode()

        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        attachment = Attachment()
        attachment.file_content = FileContent(encoded)
        attachment.file_type = FileType(mime_type)
        attachment.file_name = FileName(os.path.basename(filename))

        return attachment
