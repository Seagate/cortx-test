#!/usr/bin/python
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
#
"""Test suite for security check"""

import logging
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from commons.helpers.salt_helper import SaltHelper
from config import CMN_CFG
from config import CSM_CFG
from libs.s3 import S3H_OBJ
from commons.helpers.node_helper import Node


class TestCliSecurity:
    """CSM CLI Security TestSuite"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
        """
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("STARTED : Setup operations for test suit")
        cls.file_path = CSM_CFG["CliConfig"]["csm_conf_file"]
        cls.s3_component = "openldap"
        cls.s3_keys = ["iam_admin", "secret"]
        cls.sspl_component = "sspl"
        cls.sspl_keys = ["LOGGINGPROCESSOR", "password"]
        cls.sal_obj = SaltHelper(
            hostname=CMN_CFG["nodes"][0]["host"],
            username=CMN_CFG["nodes"][0]["username"],
            password=CMN_CFG["nodes"][0]["password"])
        cls.node_obj = Node(
            hostname=CMN_CFG["nodes"][0]["host"],
            username=CMN_CFG["nodes"][0]["username"],
            password=CMN_CFG["nodes"][0]["password"])
        cls.logger.info("ENDED : Setup operations for test suit")

    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16930")
    @CTFailOn(error_handler)
    def test_6130_check_password(self):
        """
        Test that password should be in encrypted format in csm.conf file
        """
        self.logger.info("Verifying csm conf file is exist")
        resp = self.node_obj.path_exists(path=self.file_path)
        assert_utils.assert_true(resp, f"csm conf file does not exist at {self.file_path}")
        self.logger.info("Verified csm conf file is exist")
        self.logger.info("Retrieving ldap passwords in encrypted format")
        s3_resp = self.sal_obj.get_pillar_values(
            self.s3_component, self.s3_keys)
        assert_utils.assert_equal(True, s3_resp[0], s3_resp[1])
        self.logger.info("Retrieved ldap passwords in encrypted format")
        self.logger.info(
            "Verifying ldap password is in encrypted format in csm.conf file")
        resp = self.node_obj.is_string_in_remote_file(
            string=s3_resp[1], file_path=self.file_path)
        assert_utils.assert_equal(True, resp[0], resp[1])
        self.logger.info(
            "Verified ldap password is in encrypted format in csm.conf file")
        self.logger.info("Verifying ldap password can be decrypted")
        resp = self.sal_obj.get_pillar_values(
            self.s3_component, self.s3_keys,
            decrypt=True)
        assert_utils.assert_equal(True, resp[0], resp[1])
        self.logger.debug(resp)
        self.logger.info("Verified ldap password can be decrypted")
        self.logger.info("Retrieving sspl passwords in encrypted format")
        sspl_resp = self.sal_obj.get_pillar_values(
            self.sspl_component, self.sspl_keys)
        assert_utils.assert_equal(True, sspl_resp[0], sspl_resp[1])
        self.logger.info("Retrieved sspl passwords in encrypted format")
        self.logger.info(
            "Verifying sspl password is in encrypted format in csm.conf file")
        resp = self.node_obj.is_string_in_remote_file(
            string=sspl_resp[1], file_path=self.file_path)
        assert_utils.assert_equal(True, resp[0], resp[1])
        self.logger.info(
            "Verified sspl password is in encrypted format in csm.conf file")
        self.logger.info("Verifying sspl password can be decrypted")
        resp = self.sal_obj.get_pillar_values(
            self.sspl_component, self.sspl_keys,
            decrypt=True)
        assert_utils.assert_equal(True, resp[0], resp[1])
        self.logger.debug(resp)
        self.logger.info("Verified sspl password can be decrypted")
