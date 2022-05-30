#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
# -*- coding: utf-8 -*-
# !/usr/bin/python
"""
Module for generating email
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Mail:
    """
    module to send mail
    """

    def __init__(self, sender, receiver):
        """
        Init method
        # param sender: email address of sender
        # param receiver: email address of receiver
        """
        self.mail_host = os.getenv("mail_host")
        self.port = os.getenv("port")
        self.sender = sender
        self.receiver = receiver

    def send_mail(self, subject, body):
        """
        function to send mail
        #param subject: subject of email
        #param body: body of email
        """
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = self.receiver
        LOGGER.info("Sending mail with Subject %s:", subject)
        with smtplib.SMTP(self.mail_host, self.port) as server:
            server.sendmail(self.sender, self.receiver.split(','), msg.as_string())
