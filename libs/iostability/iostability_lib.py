#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
Utility Method for IO stability testing
"""
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.utils import make_msgid, formatdate, COMMASPACE

from commons import commands
from commons.mail_script_utils import Mail
from commons.utils import system_utils
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


class IOStabilityLib:
    """
    This class contains common utility methods for IO stability.
    """

    def __init__(self, max_retries, timeout, access_key=ACCESS_KEY,
                 secret_key=SECRET_KEY):
        self.log = logging.getLogger(__name__)
        self.s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)
        self.max_retries = max_retries
        self.http_client_timeout = timeout

    def execute_workload_distribution(self, distribution, clients, total_obj,
                                      duration_in_days, log_file_prefix, buckets_created=None):
        """Execution given workload distribution.
        :param distribution: Distribution of object size
        :param clients: No of clients
        :param total_obj: total number of objects per iteration
        :param duration_in_days: Duration expected of the test run
        :param log_file_prefix: Log file prefix for s3bench
        :param buckets_created: Buckets already created to be used for IO operations.
        """
        workloads = [(size, int(total_obj * percent / 100)) for size, percent in
                     distribution.items()]
        end_time = datetime.now() + timedelta(days=duration_in_days)
        loop = 0
        while datetime.now() < end_time:
            for size, samples in workloads:
                bucket_name = f"{log_file_prefix}-bucket-{loop}-{str(int(time.time()))}".lower()
                skip_cleanup = False
                if buckets_created is not None:
                    bucket_name = buckets_created[loop % len(buckets_created)]
                    skip_cleanup = True
                if samples == 0:
                    continue
                cur_clients = clients
                if cur_clients > samples:
                    cur_clients = samples
                resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name,
                                       num_clients=cur_clients, num_sample=samples,
                                       obj_name_pref="object-", obj_size=size,
                                       skip_cleanup=skip_cleanup, duration=None,
                                       log_file_prefix=str(log_file_prefix).upper(),
                                       end_point=S3_CFG["s3_url"],
                                       validate_certs=S3_CFG["validate_certs"],
                                       max_retries=self.max_retries,
                                       httpclientimeout=self.http_client_timeout)
                self.log.info("Loop: %s Workload: %s objects of %s with %s parallel clients.",
                              loop, samples, size, clients)
                self.log.info("Log Path %s", resp[1])
                assert not s3bench.check_log_file_error(resp[1]), \
                    f"S3bench workload failed in loop {loop}. Please read log file {resp[1]}"
                # delete file if operation successful.
                system_utils.remove_file(resp[1])
                if skip_cleanup:
                    # delete only objects, to be used for degraded mode.
                    self.log.info("Delete Created Objects")
                    resp = self.s3t_obj.object_list(bucket_name=bucket_name)
                    obj_list = resp[1]
                    while len(obj_list):
                        if len(obj_list) > 1000:
                            self.s3t_obj.delete_multiple_objects(bucket_name,
                                                                 obj_list=obj_list[0:1000])
                            obj_list = obj_list[1000:]
                        else:
                            self.s3t_obj.delete_multiple_objects(bucket_name=bucket_name,
                                                                 obj_list=obj_list)
                            obj_list = []
                    self.log.info("Objects deletion completed")
            loop += 1


class MailNotification(threading.Thread):
    """
    This class contains common utility methods for Mail Notification.
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, sender, receiver, test_id, health_obj, build_url):
        """
        Init method:
        :param sender: sender of mail
        :param receiver: receiver of mail
        :param test_id : Test ID to be sent in subject.
        :param health_obj: Health object to monitor health.
        """
        threading.Thread.__init__(self)
        self.event_pass = threading.Event()
        self.event_fail = threading.Event()
        self.mail_obj = Mail(sender=sender, receiver=receiver)
        self.sender = sender
        self.receiver = receiver
        self.test_id = test_id
        self.health_obj = health_obj
        self.interval = 4  # Mail to be sent periodically after 4 hours.
        self.message_id = None
        self.build_url = build_url
        self.start_time = datetime.now()

    def prepare_email(self, execution_status) -> MIMEMultipart:
        """
        Prepare email message with format and attachment
        :param execution_status: Execution status. In Progress/Fail
        :return: Formatted MIME message
        """
        hctl_status = json.dumps(self.health_obj.get_hctl_status()[1], indent=4)
        result, pod_status = self.health_obj.execute_command(commands.CMD_POD_STATUS)
        status = f"IOStability Test {self.test_id} {execution_status} on {self.health_obj.hostname}"
        subject = status
        body = f"<h3>{status}.</h2>\n" \
               f"<h3>PFA hctl cluster status, pod status & execution status.</h3>\n"
        body += f"Hours of execution: {datetime.now() - self.start_time}"
        if self.build_url:
            body += f"""Visit Jenkins Job: <a href="{self.build_url}">{self.build_url}</a>"""
        message = MIMEMultipart()
        message['From'] = self.sender
        message['To'] = COMMASPACE.join(self.receiver.split(','))
        message['Date'] = formatdate(localtime=True)
        message['Subject'] = subject
        if not self.message_id:
            self.message_id = make_msgid()
            message["Message-ID"] = self.message_id
        else:
            message["In-Reply-To"] = self.message_id
            message["References"] = self.message_id
        attachment = MIMEApplication(hctl_status, Name="hctl_status.txt")
        attachment['Content-Disposition'] = 'attachment; filename=hctl_status.txt'
        message.attach(attachment)
        if result:
            attachment = MIMEApplication(pod_status, Name="pod_status.txt")
            attachment['Content-Disposition'] = 'attachment; filename=pod_status.txt'
            message.attach(attachment)
        else:
            body += """<h3>Could not collect pod status</h3>"""
        return message

    def run(self):
        """
        Send Mail notification periodically.
        """
        while not self.event_pass.is_set() and not self.event_fail.is_set():
            message = self.prepare_email(execution_status="in progress")
            self.mail_obj.send_mail(message)
            current_time = time.time()
            while time.time() < current_time + self.interval * 60 * 60:
                if self.event_pass.is_set() or self.event_fail.is_set():
                    break
                time.sleep(60)
        test_status = "Failed"
        if self.event_pass.is_set():
            test_status = "Passed"
        message = self.prepare_email(execution_status=test_status)
        self.mail_obj.send_mail(message)


def send_mail_notification(sender_mail_id, receiver_mail_id, test_id, health_obj, build_url):
    """
    Send mail notification
    :param sender_mail_id: Sender Mail ID
    :param receiver_mail_id: Receiver Mail ID
    :param test_id: Test ID
    :param health_obj: Health object.
    :param build_url: Jenkins build URL
    :return MailNotification Object.
    """
    mail_notify = MailNotification(sender=sender_mail_id,
                                   receiver=receiver_mail_id,
                                   test_id=test_id,
                                   health_obj=health_obj,
                                   build_url=build_url)
    mail_notify.start()
    return mail_notify
