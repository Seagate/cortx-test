"""
Module to get a mail from test execution.
"""

import smtplib
from email.mime.text import MIMEText
import logging
from config import MAIL_SCRIPT_CFG

# Global Constants
LOGGER = logging.getLogger(__name__)

class Mail:
    def __init__(self, mail_host=MAIL_SCRIPT_CFG['mail_server'], port=MAIL_SCRIPT_CFG['port']):
        self.mail_host = mail_host
        self.port = port
        

    def send_mail(self, sender, receiver, subject, body):
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = receiver
        with smtplib.SMTP(self.mail_host, self.port) as server:
            server.sendmail(sender, receiver, msg.as_string())
