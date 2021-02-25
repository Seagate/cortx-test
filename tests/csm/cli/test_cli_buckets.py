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
"""Test suite for S3 bucket operations"""

import logging
import time
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from config import CSM_CFG
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations

S3BKT_OBJ = CortxCliS3BucketOperations()
S3ACC_OBJ = CortxCliS3AccountOperations(session_obj=S3BKT_OBJ.session_obj)
LOGGER = logging.getLogger(__name__)


class TestCliS3BKT:
    """CORTX CLI Test suite for S3 bucket operations"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        LOGGER.info("STARTED : Setup operations at test suit level")
        cls.bucket_name = "clis3bkt"
        cls.s3acc_name = "clis3bkt_acc_{}".format(int(time.time()))
        cls.s3acc_email = "{}@seagate.com".format(cls.s3acc_name)
        cls.s3acc_password = CSM_CFG["CliConfig"]["acc_password"]
        login = S3ACC_OBJ.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        response = S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, response[0], response[1])
        S3ACC_OBJ.logout_cortx_cli()
        login = S3BKT_OBJ.login_cortx_cli(
            username=cls.s3acc_name,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        LOGGER.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        LOGGER.info("STARTED : Setup operations at test function level")
        self.bucket_name = "{}-{}".format(self.bucket_name, int(time.time()))
        LOGGER.info("ENDED : Setup operations at test function level")

    @classmethod
    def teardown_class(cls):
        """
        Teardown any state that was previously setup with a setup_class
        """
        LOGGER.info("STARTED : Teardown operations at test suit level")
        S3BKT_OBJ.logout_cortx_cli()
        login = S3ACC_OBJ.login_cortx_cli(
            username=cls.s3acc_name,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        response = S3ACC_OBJ.delete_s3account_cortx_cli(
            account_name=cls.s3acc_name)
        assert_utils.assert_equals(True, response[0], response[1])
        LOGGER.info("ENDED : Setup operations at test suit level")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10805")
    @CTFailOn(error_handler)
    def test_971_verify_delete_bucket(self):
        """
        Test that S3 account user able to delete the bucket using CORTX CLI
        """
        resp = S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Created bucket %s", self.bucket_name)
        resp = S3BKT_OBJ.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Deleted bucket %s", self.bucket_name)
