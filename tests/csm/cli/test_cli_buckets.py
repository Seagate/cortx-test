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
from commons import commands
from commons import constants
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from config import CSM_CFG
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cli_csm_user import CortxCliCsmUser


class TestCliS3BKT:
    """CORTX CLI Test suite for S3 bucket operations"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        cls.LOGGER = logging.getLogger(__name__)
        cls.LOGGER.info("STARTED : Setup operations at test suit level")
        cls.S3BKT_OBJ = CortxCliS3BucketOperations()
        cls.S3BKT_OBJ.open_connection()
        cls.S3ACC_OBJ = CortxCliS3AccountOperations(session_obj=cls.S3BKT_OBJ.session_obj)
        cls.CSM_USER_OBJ = CortxCliCsmUser(session_obj=cls.S3BKT_OBJ.session_obj)
        cls.bucket_prefix = "clis3bkt"
        cls.s3acc_prefix = "clis3bkt_acc"
        cls.s3acc_name = "{}_{}".format(cls.s3acc_prefix, int(time.time()))
        cls.s3acc_email = "{}@seagate.com".format(cls.s3acc_name)
        cls.s3acc_password = CSM_CFG["CliConfig"]["acc_password"]
        cls.bucket_name = None
        login = cls.S3ACC_OBJ.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        response = cls.S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, response[0], response[1])
        cls.S3ACC_OBJ.logout_cortx_cli()
        cls.LOGGER.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        self.LOGGER.info("STARTED : Setup operations at test function level")
        self.bucket_name = "{}-{}".format(self.bucket_prefix, int(time.time()))
        login = self.S3BKT_OBJ.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.LOGGER.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        """
        self.LOGGER.info("STARTED : Teardown operations at test function level")
        self.S3BKT_OBJ.logout_cortx_cli()
        self.LOGGER.info("ENDED : Teardown operations at test function level")

    @classmethod
    def teardown_class(cls):
        """
        Teardown any state that was previously setup with a setup_class
        """
        cls.LOGGER.info("STARTED : Teardown operations at test suit level")
        login = cls.S3ACC_OBJ.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        accounts = cls.S3ACC_OBJ.show_s3account_cortx_cli(output_format="json")[1]
        accounts = cls.S3ACC_OBJ.format_str_to_dict(
            input_str=accounts)["s3_accounts"]
        accounts = [acc["account_name"]
                    for acc in accounts if cls.s3acc_prefix in acc["account_name"]]
        cls.S3ACC_OBJ.logout_cortx_cli()
        for acc in accounts:
            login = cls.S3ACC_OBJ.login_cortx_cli(
                username=acc, password=cls.s3acc_password)
            assert_utils.assert_equals(True, login[0], login[1])
            buckets = cls.S3BKT_OBJ.list_buckets_cortx_cli(op_format="json")[1]
            buckets = cls.S3BKT_OBJ.format_str_to_dict(
                input_str=buckets)["buckets"]
            buckets = [bkt["name"] for bkt in buckets if cls.bucket_prefix in bkt["name"]]
            for bkt in buckets:
                resp = cls.S3BKT_OBJ.delete_bucket_cortx_cli(bkt)
                assert_utils.assert_equals(True, resp[0], resp[1])
            response = cls.S3ACC_OBJ.delete_s3account_cortx_cli(account_name=acc)
            assert_utils.assert_equals(True, response[0], response[1])
            cls.S3ACC_OBJ.logout_cortx_cli()
            cls.S3BKT_OBJ.close_connection()
        cls.LOGGER.info("ENDED : Teardown operations at test suit level")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10805")
    @CTFailOn(error_handler)
    def test_971_verify_delete_bucket(self):
        """
        Test that S3 account user able to delete the bucket using CORTX CLI
        """
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.self.LOGGER.info("Created bucket %s", self.bucket_name)
        resp = self.S3BKT_OBJ.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.self.LOGGER.info("Deleted bucket %s", self.bucket_name)

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10804")
    @CTFailOn(error_handler)
    def test_965_verify_create_bucket(self):
        """
        Initiating the test case to verify create bucket
        """
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created bucket %s", self.bucket_name)

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10806")
    @CTFailOn(error_handler)
    def test_969_create_bucket_by_admin_csm_user(self):
        """
        Initiating the test case to verify error occurs when admin/CSM user
        executes bucket related commands
        """
        logout = self.S3BKT_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.S3BKT_OBJ.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info("Failed to create bucket using admin user %s", resp[1])

        csm_user_name = "{0}{1}".format("auto_csm_user", str(int(time.time())))
        csm_user_email = "{0}{1}".format(csm_user_name, "@seagate.com")
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user_pwd"]
        self.LOGGER.info("Creating csm user with name %s", csm_user_name)
        resp = self.CSM_USER_OBJ.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="manage",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_equals(
            True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.LOGGER.info("Created csm user with name %s", csm_user_name)
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info("Failed to create bucket using csm user %s", resp[1])

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10807")
    @CTFailOn(error_handler)
    def test_968_create_duplicate_bucket(self):
        """
        Initiating the test case to verify error msg while creating duplicate bucket
        """
        error_msg = "The bucket you tried to create already exists, and you own it"
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created bucket %s", self.bucket_name)
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.LOGGER.info("Failed to create duplicate bucket %s", resp[1])

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10808")
    @CTFailOn(error_handler)
    def test_967_create_invalid_bucket(self):
        """
        Initiating the test case to verify create bucket with invalid bucket name
        """
        bucket_name = "_".join([self.bucket_name, "@#$"])
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        self.LOGGER.info("Failed to create bucket with invalid name: %s", resp[1])

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10809")
    @CTFailOn(error_handler)
    def test_972_delete_non_existing_bucket(self):
        """
        Initiating the test case to verify delete bucket which doesn't exist
        """
        error_msg = "The specified bucket does not exist"
        resp = self.S3BKT_OBJ.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.LOGGER.info("Delete bucket failed with error: %s", resp[1])

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10810")
    @CTFailOn(error_handler)
    def test_964_s3bucket_help(self):
        """
        Initiating the test case to verify help response for s3 bucket
        """
        resp = self.S3BKT_OBJ.execute_cli_commands(cmd=commands.CMD_S3BKT_HELP)
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.LOGGER.info("Successfully verified help response for s3 bucket")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10811")
    @CTFailOn(error_handler)
    def test_9431_create_s3bucket_help(self):
        """
        Initiating the test case to verify help response for create s3 bucket
        """
        create_bucket_help = " ".join([commands.CMD_CREATE_BUCKET.format(
            self.bucket_name), commands.CMD_HELP_OPTION])
        resp = self.S3BKT_OBJ.execute_cli_commands(cmd=create_bucket_help)
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_CREATE_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.LOGGER.info("Successfully verified help response for create s3 bucket")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10812")
    @CTFailOn(error_handler)
    def test_9434_delete_s3bucket_help(self):
        """
        Initiating the test case to verify help response for delete s3 bucket
        """
        delete_bucket_help = " ".join([commands.CMD_DELETE_BUCKET.format(
            self.bucket_name), commands.CMD_HELP_OPTION])
        resp = self.S3BKT_OBJ.execute_cli_commands(cmd=delete_bucket_help)
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_DELETE_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.LOGGER.info("Successfully verified help response for delete s3 bucket")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10813")
    @CTFailOn(error_handler)
    def test_9432_list_s3bucket_help(self):
        """
        Initiating the test case to verify help response for list s3 bucket
        """
        show_bucket_help = " ".join(
            [commands.CMD_SHOW_BUCKETS, commands.CMD_HELP_OPTION])
        resp = self.S3BKT_OBJ.execute_cli_commands(cmd=show_bucket_help)
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_SHOW_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.LOGGER.info("Successfully verified help response for list s3 bucket")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10814")
    @CTFailOn(error_handler)
    def test_970_list_bucket_invalid_format(self):
        """
        Initiating the test case to verify error for invalid format for list s3 bucket
        """
        dummy_format = "text"
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created bucket %s", self.bucket_name)
        resp = self.S3BKT_OBJ.list_buckets_cortx_cli(op_format=dummy_format)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.LOGGER.info("List buckets failed with error: %s", resp[1])

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10815")
    @CTFailOn(error_handler)
    def test_934_list_bucket(self):
        """
        Initiating the test case to verify response for list s3 bucket
        """
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created bucket %s", self.bucket_name)
        resp = self.S3BKT_OBJ.list_buckets_cortx_cli()
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.LOGGER.info("Successfully verified list bucket response")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16210")
    @CTFailOn(error_handler)
    def test_974_delete_bucket_different_account(self):
        """
        Test that S3 account user can only delete buckets from his account using csm cli
        """
        s3acc_name = "{}_{}".format(self.s3acc_prefix, int(time.time()))
        s3acc_email = "{}@seagate.com".format(s3acc_name)
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created bucket %s", self.bucket_name)
        logout = self.S3BKT_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.S3ACC_OBJ.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=s3acc_name,
            account_email=s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created s3 account %s", s3acc_name)
        logout = self.S3ACC_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.S3ACC_OBJ.login_cortx_cli(
            username=s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.S3BKT_OBJ.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_exact_string(resp[1], "Access Denied")
        self.LOGGER.info("Delete bucket failed with error: %s", resp[1])
        resp = self.S3ACC_OBJ.delete_s3account_cortx_cli(account_name=s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-17175")
    @CTFailOn(error_handler)
    def test_959_list_buckets_with_format(self):
        """
        Test that S3 account user is able to view the bucket names using csmcli in different
        format with -f parameter.
        """
        resp = self.S3BKT_OBJ.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Created bucket %s", self.bucket_name)
        resp = self.S3BKT_OBJ.list_buckets_cortx_cli(op_format="json")
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.LOGGER.info("Successfully listed buckets in json format")
        resp = self.S3BKT_OBJ.list_buckets_cortx_cli(op_format="xml")
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.LOGGER.info("Successfully listed buckets in xml format")
