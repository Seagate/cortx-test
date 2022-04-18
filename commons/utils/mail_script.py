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
"""Test Suite for IO workloads."""
import time
import smtplib
from email.mime.text import MIMEText
import pytest

from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_test_lib import S3TestLib


class TestIOWorkload:
    """Test suite for IO workloads."""

    @classmethod
    def setup_class(cls):
        """Setup class."""
        cls.prov_obj = ProvDeployK8sCortxLib()
        cls.s3t_obj = S3TestLib()

    @pytest.fixture(autouse=True)
    def setup(self):
        self.test_status = False
        yield
        if self.test_status:
            self._send_mail('Test Passed', 'IO_Stability_result',
                            'rahul.telawade@seagate.com', 'rahul.telawade@seagate.com',
                            'rahul.telawade@seagate.com', 'rahul.telawade@seagate.com')
        else:
            self._send_mail('Test Failed', 'IO_Stability_result',
                            'rahul.telawade@seagate.com', 'rahul.telawade@seagate.com',
                            'rahul.telawade@seagate.com', 'rahul.telawade@seagate.com')

    def _send_mail(self, body, Subject, From, To, sender, receivers):
        sender = sender
        receivers = receivers
        port = 587
        msg = MIMEText(body)
        msg['Subject'] = Subject
        msg['From'] = From
        msg['To'] = To
        with smtplib.SMTP('mailhost.seagate.com', port) as server:
            # server.login('username', 'password')
            server.sendmail(sender, receivers, msg.as_string())
            print("Successfully sent email")

    @pytest.mark.lc
    @pytest.mark.sanity
    @pytest.mark.s3_data_path
    @pytest.mark.tags("TEST-39180")
    def test_basic_io(self):
        """Basic IO test."""
        # bucket_name = f'bucket-test-39180-{int(time.time())}'
        # self.prov_obj.basic_io_write_read_validate(bucket_name=bucket_name, s3t_obj=self.s3t_obj)
        self.test_status = True
        # assert False
        # self._send_mail()

    @pytest.mark.lc
    @pytest.mark.sanity
    @pytest.mark.s3_data_path
    @pytest.mark.tags("TEST-391802")
    def test_basic_io_1(self):
        """Basic IO test."""
        # bucket_name = f'bucket-test-39180-{int(time.time())}'
        # self.prov_obj.basic_io_write_read_validate(bucket_name=bucket_name, s3t_obj=self.s3t_obj)
        # self.test_status = True
        assert False

