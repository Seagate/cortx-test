#!/usr/bin/python
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
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("STARTED : Setup operations at test suit level")
        cls.s3bkt_obj = CortxCliS3BucketOperations()
        cls.s3bkt_obj.open_connection()
        cls.s3acc_obj = CortxCliS3AccountOperations(session_obj=cls.s3bkt_obj.session_obj)
        cls.csm_user_obj = CortxCliCsmUser(session_obj=cls.s3bkt_obj.session_obj)
        cls.bucket_prefix = "clis3bkt"
        cls.s3acc_prefix = "clis3bkt_acc"
        cls.s3acc_name = f"{cls.s3acc_prefix}_{int(time.time())}"
        cls.s3acc_email = f"{cls.s3acc_name}@seagate.com"
        cls.s3acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.bucket_name = None
        login = cls.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        response = cls.s3acc_obj.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, response[0], response[1])
        cls.s3acc_obj.logout_cortx_cli()
        cls.logger.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        self.logger.info("STARTED : Setup operations at test function level")
        self.bucket_name = f"{self.bucket_prefix}-{int(time.time())}"
        login = self.s3bkt_obj.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        self.logger.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        """
        self.logger.info("STARTED : Teardown operations at test function level")
        self.s3bkt_obj.logout_cortx_cli()
        self.logger.info("ENDED : Teardown operations at test function level")

    @classmethod
    def teardown_class(cls):
        """
        Teardown any state that was previously setup with a setup_class
        """
        cls.logger.info("STARTED : Teardown operations at test suit level")
        login = cls.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        accounts = cls.s3acc_obj.show_s3account_cortx_cli(output_format="json")[1]
        accounts = cls.s3acc_obj.format_str_to_dict(
            input_str=accounts)["s3_accounts"]
        accounts = [acc["account_name"]
                    for acc in accounts if cls.s3acc_prefix in acc["account_name"]]
        cls.s3acc_obj.logout_cortx_cli()
        for acc in accounts:
            login = cls.s3acc_obj.login_cortx_cli(
                username=acc, password=cls.s3acc_password)
            assert_utils.assert_equals(True, login[0], login[1])
            buckets = cls.s3bkt_obj.list_buckets_cortx_cli(op_format="json")[1]
            buckets = cls.s3bkt_obj.format_str_to_dict(
                input_str=buckets)["buckets"]
            buckets = [bkt["name"] for bkt in buckets if cls.bucket_prefix in bkt["name"]]
            for bkt in buckets:
                resp = cls.s3bkt_obj.delete_bucket_cortx_cli(bkt)
                assert_utils.assert_equals(True, resp[0], resp[1])
            response = cls.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            assert_utils.assert_equals(True, response[0], response[1])
            cls.s3acc_obj.logout_cortx_cli()
        cls.s3bkt_obj.close_connection()
        cls.logger.info("ENDED : Teardown operations at test suit level")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10805")
    @CTFailOn(error_handler)
    def test_971_verify_delete_bucket(self):
        """
        Test that S3 account user able to delete the bucket using CORTX CLI
        """
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Deleted bucket %s", self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10804")
    @CTFailOn(error_handler)
    def test_965_verify_create_bucket(self):
        """
        Initiating the test case to verify create bucket
        """
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10806")
    @CTFailOn(error_handler)
    def test_969_create_bucket_by_admin_csm_user(self):
        """
        Initiating the test case to verify error occurs when admin/CSM user
        executes bucket related commands
        """
        logout = self.s3bkt_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3bkt_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info("Failed to create bucket using admin user %s", resp[1])

        csm_user_name = f"auto_csm_user{str(int(time.time()))}"
        csm_user_email = f"{csm_user_name}@seagate.com"
        csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.logger.info("Creating csm user with name %s", csm_user_name)
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=csm_user_name,
            email_id=csm_user_email,
            role="manage",
            password=csm_user_pwd,
            confirm_password=csm_user_pwd)
        assert_utils.assert_equals(
            True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "User created")
        self.logger.info("Created csm user with name %s", csm_user_name)
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info("Failed to create bucket using csm user %s", resp[1])
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(csm_user_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10807")
    @CTFailOn(error_handler)
    def test_968_create_duplicate_bucket(self):
        """
        Initiating the test case to verify error msg while creating duplicate bucket
        """
        error_msg = "The bucket you tried to create already exists, and you own it"
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Failed to create duplicate bucket %s", resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10808")
    @CTFailOn(error_handler)
    def test_967_create_invalid_bucket(self):
        """
        Initiating the test case to verify create bucket with invalid bucket name
        """
        bucket_name = "_".join([self.bucket_name, "@#$"])
        resp = self.s3bkt_obj.create_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        self.logger.info("Failed to create bucket with invalid name: %s", resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10809")
    @CTFailOn(error_handler)
    def test_972_delete_non_existing_bucket(self):
        """
        Initiating the test case to verify delete bucket which doesn't exist
        """
        error_msg = "The specified bucket does not exist"
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.logger.info("Delete bucket failed with error: %s", resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10810")
    @CTFailOn(error_handler)
    def test_964_s3bucket_help(self):
        """
        Initiating the test case to verify help response for s3 bucket
        """
        resp = self.s3bkt_obj.execute_cli_commands(cmd=commands.CMD_S3BKT_HELP, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.logger.info("Successfully verified help response for s3 bucket")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10811")
    @CTFailOn(error_handler)
    def test_9431_create_s3bucket_help(self):
        """
        Initiating the test case to verify help response for create s3 bucket
        """
        create_bucket_help = " ".join([commands.CMD_CREATE_BUCKET.format(
            self.bucket_name), commands.CMD_HELP_OPTION])
        resp = self.s3bkt_obj.execute_cli_commands(cmd=create_bucket_help, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_CREATE_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.logger.info("Successfully verified help response for create s3 bucket")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10812")
    @CTFailOn(error_handler)
    def test_9434_delete_s3bucket_help(self):
        """
        Initiating the test case to verify help response for delete s3 bucket
        """
        delete_bucket_help = " ".join([commands.CMD_DELETE_BUCKET.format(
            self.bucket_name), commands.CMD_HELP_OPTION])
        resp = self.s3bkt_obj.execute_cli_commands(cmd=delete_bucket_help, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_DELETE_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.logger.info("Successfully verified help response for delete s3 bucket")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10813")
    @CTFailOn(error_handler)
    def test_9432_list_s3bucket_help(self):
        """
        Initiating the test case to verify help response for list s3 bucket
        """
        show_bucket_help = " ".join(
            [commands.CMD_SHOW_BUCKETS, commands.CMD_HELP_OPTION])
        resp = self.s3bkt_obj.execute_cli_commands(cmd=show_bucket_help, patterns=["usage:"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        for msg in constants.S3BUCKET_SHOW_HELP:
            assert_utils.assert_exact_string(resp[1], msg)
        self.logger.info("Successfully verified help response for list s3 bucket")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10814")
    @CTFailOn(error_handler)
    def test_970_list_bucket_invalid_format(self):
        """
        Initiating the test case to verify error for invalid format for list s3 bucket
        """
        dummy_format = "text"
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        resp = self.s3bkt_obj.list_buckets_cortx_cli(op_format=dummy_format)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "invalid choice")
        self.logger.info("List buckets failed with error: %s", resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10815")
    @CTFailOn(error_handler)
    def test_934_list_bucket(self):
        """
        Initiating the test case to verify response for list s3 bucket
        """
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        resp = self.s3bkt_obj.list_buckets_cortx_cli()
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.logger.info("Successfully verified list bucket response")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16210")
    @CTFailOn(error_handler)
    def test_974_delete_bucket_different_account(self):
        """
        Test that S3 account user can only delete buckets from his account using csm cli
        """
        s3acc_name = f"{self.s3acc_prefix}_{int(time.time())}"
        s3acc_email = f"{s3acc_name}@seagate.com"
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        logout = self.s3bkt_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=s3acc_name,
            account_email=s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created s3 account %s", s3acc_name)
        logout = self.s3acc_obj.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = self.s3acc_obj.login_cortx_cli(
            username=s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = self.s3bkt_obj.delete_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_exact_string(resp[1], "Access Denied")
        self.logger.info("Delete bucket failed with error: %s", resp[1])
        resp = self.s3acc_obj.delete_s3account_cortx_cli(account_name=s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-17175")
    @CTFailOn(error_handler)
    def test_959_list_buckets_with_format(self):
        """
        Test that S3 account user is able to view the bucket names using csmcli in different
        format with -f parameter.
        """
        resp = self.s3bkt_obj.create_bucket_cortx_cli(self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.logger.info("Created bucket %s", self.bucket_name)
        resp = self.s3bkt_obj.list_buckets_cortx_cli(op_format="json")
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.logger.info("Successfully listed buckets in json format")
        resp = self.s3bkt_obj.list_buckets_cortx_cli(op_format="xml")
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.logger.info("Successfully listed buckets in xml format")
