#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
Prov test file for all the Prov tests scenarios for single node VM.
"""

import logging
import pytest
import os
from config import CMN_CFG
from commons.utils import assert_utils
from libs.csm.cli.cortxcli_support_user import CortxCLISupportUser

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestSupportUser:
    """
    Test suite for prov tests scenarios for support user verification
    """
    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.support_uname = "support"
        cls.cortx_support = CortxCLISupportUser(host=cls.host, username=cls.uname, password=cls.passwd)
        cls.cortx_support.open_connection()
        local_file_path = "var/data/support.yaml"
        if os.path.exists(local_file_path):
            cmd = "opt/seagate/cortx/provisioner/srv/components/provisioner/scripts/support --get-credentials /var/data/support.yaml"
            resp = cls.cortx_support.execute_cli_commands(cmd=cmd, patterns=["support.yaml"], timeout=300)
            LOGGER.info("Response is %s", resp[1])
            output = resp[1].split("yaml")
            LOGGER.info("new pasword %s", output[1])
            cls.support_passwd = output[1]
        else:
            cls.support_passwd = "Seagate123!"
        cls.cortx_support.close_connection()
        cls.cortx_support_new = CortxCLISupportUser(host=cls.host, username=cls.support_uname,
                                                    password=cls.support_passwd)
        cls.cortx_support_new.open_connection()

    def teardown_method(self):
        """
        Teardown operations after each test.
        """
        self.cortx_support_new.close_connection()
        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-25269")
    def test_support_user(self):
        result = self.cortx_support_new.show_cluster(password=self.support_passwd, timeout=150)
        assert_utils.assert_true(result[0],result[1])
        LOGGER.info("successfully verified support user %s", result[1])
