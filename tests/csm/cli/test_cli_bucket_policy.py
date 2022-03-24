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
"""Test suite for bucket policy operations"""

import time
import os
import uuid
import logging
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from commons import commands
from commons.helpers.node_helper import Node
from commons.utils import system_utils
from config import CSM_CFG
from config import CMN_CFG
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_bucket_policy import CortxCliS3BktPolicyOperations
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cli_csm_user import CortxCliCsmUser

# pylint: disable=R0904
class TestCliBucketPolicy:
    """Bucket Policy Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
            - Creating s3 account to perform bucket policy operations
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED : Setup operations for test suit")
        cls.bucket_name = "clis3bkt"
        cls.s3bkt_plc_obj = CortxCliS3BktPolicyOperations()
        cls.s3bkt_plc_obj.open_connection()
        cls.s3acc_obj = CortxCliS3AccountOperations(
            session_obj=cls.s3bkt_plc_obj.session_obj)
        cls.bkt_obj = CortxCliS3BucketOperations(
            session_obj=cls.s3bkt_plc_obj.session_obj)
        cls.csm_user_obj = CortxCliCsmUser(session_obj=cls.s3bkt_plc_obj.session_obj)
        cls.node_list = [each["hostname"] for each in CMN_CFG["nodes"] if each["hostname"]]
        cls.csm_user_pwd = CSM_CFG["CliConfig"]["csm_user"]["password"]
        cls.acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.s3acc_prefix = "cli_s3acc_policy"
        cls.user_name = None
        cls.email_id = None
        cls.policy_id = None
        cls.policy_sid = None
        cls.s3acc_name = f"cli_s3acc_policy_{int(time.time())}"
        cls.s3acc_email = f"{cls.s3acc_name}@seagate.com"
        cls.log.info("Creating s3 account with name %s", cls.s3acc_name)
        resp = cls.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = cls.s3acc_obj.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        cls.s3acc_obj.logout_cortx_cli()
        cls.log.info("Created s3 account")
        cls.bkt_policy_msg = "Bucket Policy Updated Successfully"
        cls.policy_file_path = os.path.join(
            str(os.getcwdb().decode()), "bkt_policy.json")
        cls.remote_file_path = "/tmp/bkt_policy.json"
        cls.bkt_policy = None

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as s3account user.
            - Initialize few common variables
        """
        self.log.info("STARTED : Setup operations for test function")
        self.log.info("Login to CORTX CLI using s3 account")
        login = self.s3bkt_plc_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        assert_utils.assert_equals(
            login[0], True, "Server authentication check failed")
        self.bucket_name = f"{self.bucket_name}-{int(time.time())}"
        self.user_name = f"auto_csm_user{str(int(time.time()))}"
        self.email_id = f"{self.user_name}@seagate.com"
        self.bkt_policy = [{
            "Sid": "{0}",
            "Action": [
                "s3:DeleteObject",
                "s3:AbortMultipartUpload",
                "s3:GetObject"],
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::{0}/*",
            "Principal": "*"}]
        self.policy_id = f"Policy{uuid.uuid4()}"
        self.policy_sid = f"Stmt{uuid.uuid4()}"
        self.log.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete buckets from account
            - Log out from CORTX CLI console.
            - Delete files
        """
        self.log.info("STARTED : Teardown operations for test function")
        resp = self.bkt_obj.list_buckets_cortx_cli(op_format="json")
        json_data = self.bkt_obj.format_str_to_dict(resp[1])
        if json_data["buckets"]:
            for each_bkt in json_data["buckets"]:
                self.bkt_obj.delete_bucket_cortx_cli(each_bkt["name"])
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.log.info("Removing policy files")
        remove_cmd = commands.CMD_REMOVE_DIR.format(self.remote_file_path)

        for node_id, each_node in enumerate(self.node_list):
            node_obj = Node(hostname=each_node,
                            username=CMN_CFG["nodes"][node_id]["username"],
                            password=CMN_CFG["nodes"][node_id]["password"])
            resp = node_obj.path_exists(self.remote_file_path)
            if resp:
                system_utils.run_remote_cmd(
                    cmd=remove_cmd,
                    hostname=each_node,
                    username=CMN_CFG["nodes"][0]["username"],
                    password=CMN_CFG["nodes"][0]["password"])
        self.log.info("ENDED : Teardown operations for test function")

    @classmethod
    def teardown_class(cls):
        """
        This function will be invoked after test suit.
        It is performing below operations as pre-requisites.
            - Deleting S3 account
            - Logout from cortxcli
        """
        cls.log.info("Deleting s3 account %s", cls.s3acc_name)
        login = cls.s3acc_obj.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        accounts = cls.s3acc_obj.show_s3account_cortx_cli(output_format="json")[
            1]
        accounts = cls.s3acc_obj.format_str_to_dict(
            input_str=accounts)["s3_accounts"]
        accounts = [acc["account_name"]
                    for acc in accounts if cls.s3acc_prefix in acc["account_name"]]
        cls.s3acc_obj.logout_cortx_cli()
        for acc in accounts:
            cls.s3acc_obj.login_cortx_cli(
                username=acc, password=cls.acc_password)
            cls.s3acc_obj.delete_s3account_cortx_cli(account_name=acc)
            cls.s3acc_obj.logout_cortx_cli()
        cls.log.info("Deleted s3 account %s", cls.s3acc_name)

    def create_verify_bucket(self, bucket_name: str = None):
        """
        Helper function to create bucket and verify bucket is created
        :param bucket_name: Name of the bucket.
        :return: None
        """
        resp = self.bkt_obj.create_bucket_cortx_cli(
            bucket_name=bucket_name)
        assert_utils.assert_equals(resp[0], True, resp[1])
        self.log.info("Verifying bucket is created")
        resp = self.bkt_obj.list_buckets_cortx_cli(op_format="json")
        assert_utils.assert_equals(resp[0], True, resp[1])
        json_data = self.bkt_obj.format_str_to_dict(resp[1])
        bkt_list = [each["name"] for each in json_data["buckets"]]
        assert_utils.assert_list_item(bkt_list, bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10798")
    @CTFailOn(error_handler)
    def test_6175_create_bucket_policy(self):
        """
        Initiating the test case to verify S3 account can add policy to the bucket
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10799")
    @CTFailOn(error_handler)
    def test_6174_delete_non_exist_policy(self):
        """
        Initiating the test case to verify delete
         bucket policy command when no policy exist on bucket
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Deleting policy when no policy exist on a bucket %s ",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.delete_bucket_policy(self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The specified bucket does not have a bucket policy")
        self.log.info(
            "Step 2: Deleting policy when no policy exist on a bucket "
            "%s is failed with error %s",
            self.bucket_name, resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-10800")
    @CTFailOn(error_handler)
    def test_6170_delete_bucket_policy(self):
        """
        Initiating the test case to verify delete bucket policy on bucket
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.log.debug("Bucket policy file content : %s", self.bkt_policy)
        self.log.debug("Bucket policy local file path : %s", self.policy_file_path)
        self.log.debug("Bucket policy remote file path : %s", self.remote_file_path)
        self.s3bkt_plc_obj.create_copy_json_file(self.bkt_policy,
                                                 self.policy_file_path,
                                                 self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)
        self.log.info(
            "Step 6: Deleting policy on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.delete_bucket_policy(
            bucket_name=self.bucket_name)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], "Bucket policy deleted")
        self.log.info(
            "Step 6: Deleted policy on a bucket %s",
            self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10802")
    @CTFailOn(error_handler)
    def test_6177_bkt_plc_with_invalid_path(self):
        """
        Initiating the test case to verify error occurs on
        incorrect/invalid statement file path
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 4: Uploading policy on a bucket %s with invalid file path",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            "/tmp/incorrect_file_path.json")
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(resp[1], "file operation failed")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s with "
            "invalid file path is failed with error %s",
            self.bucket_name,
            resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10801")
    @CTFailOn(error_handler)
    def test_6172_delete_plc_invalid_bkt(self):
        """
        Initiating the test case to verify error occurs if invalid bucket name
        is specified in delete bucket policy command
        """
        self.log.info(
            "Step 1: Deleting policy with invalid bucket name %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.delete_bucket_policy("invalid-bkt")
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The specified bucket does not exist")
        self.log.info(
            "Step 1: Deleting policy with invalid bucket name %s is failed with error",
            self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10803")
    @CTFailOn(error_handler)
    def test_6178_add_policy(self):
        """
        Initiating the test case to verify that s3 account can
        add policy to the bucket without mentioning version
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10982")
    @CTFailOn(error_handler)
    def test_6171_delete_plc_with_csm_user(self):
        """
        Initiating the test case to Verify that admin/csm user cannot delete bucket policy
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)
        self.log.info("Step 6: Creating csm user with name %s", self.user_name)
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.csm_user_obj.login_cortx_cli()
        resp = self.csm_user_obj.create_csm_user_cli(
            csm_user_name=self.user_name,
            email_id=self.email_id,
            role="manage",
            password=self.csm_user_pwd,
            confirm_password=self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp[1])
        self.log.info("Step 6: Created csm user with name %s", self.user_name)
        self.log.info("Step 7: Deleting bucket policy with csm user")
        self.csm_user_obj.logout_cortx_cli()
        resp = self.s3bkt_plc_obj.login_cortx_cli(
            self.user_name, self.csm_user_pwd)
        assert_utils.assert_equals(resp[0], True, resp[1])
        resp = self.s3bkt_plc_obj.delete_bucket_policy(self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "invalid choice: 's3bucketpolicy'")
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.s3bkt_plc_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        self.log.info(
            "Step 7: Deleting bucket policy with csm user is failed with error %s",
            resp[1])
        # delete created CSM user
        self.csm_user_obj.delete_csm_user(self.user_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10980")
    @CTFailOn(error_handler)
    def test_6176_create_plc_incorrect_bkt(self):
        """
        Initiating the test case to verify that error occours when incorrect/invalid bucket
        name is mentioned in create bucket policy command
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            "invalid-bucket")
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading invalid policy")
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            "invalid-bucket",
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The specified bucket does not exist")
        self.log.info(
            "Step 4: Uploaded invalid policy is failed with error %s", resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10983")
    @CTFailOn(error_handler)
    def test_6173_delete_bkt_from_another_account(self):
        """
        Initiating the test case to verify that s3 account cannot
        delete bucket policy for bucket created by some other s3 account
        """
        s3acc_name = f"cli_s3acc_policy_{int(time.time())}"
        s3acc_email = f"{s3acc_name}@seagate.com"
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)
        self.log.info(
            "Step 6: Creating s3 account user with name %s", s3acc_name)
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.s3bkt_plc_obj.login_cortx_cli()
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            s3acc_name, s3acc_email, self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp[1])
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.log.info(
            "Step 6: Created s3 account user with name %s", s3acc_name)
        self.log.info("Step 7: Deleting bucket policy with another account")
        self.s3bkt_plc_obj.login_cortx_cli(s3acc_name, self.acc_password)
        resp = self.s3bkt_plc_obj.delete_bucket_policy(self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(resp[1], "Access Denied")
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.s3bkt_plc_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        self.log.info(
            "Step 7: Deleting bucket policy with another account is failed")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-10981")
    @CTFailOn(error_handler)
    def test_6179_bkt_plc_with_missing_param(self):
        """
        Initiating the test case to verify that appropriate error message is returned
        when s3 account executes bucket policy command with some missing parameters
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s with missing parameter",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            " ",
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The following arguments are required")
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s with missing parameter is failed with error %s",
            self.bucket_name,
            resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11226")
    @CTFailOn(error_handler)
    def test_6181_update_bkt_policy(self):
        """
        Initiating the test case to verify user can Update bucket policy using create policy command
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)
        self.log.info("Step 6: Creating new bucket policy")
        new_bkt_policy = [{
            "Sid": "{0}",
            "Action": [
                "s3:DeleteObject",
                "s3:AbortMultipartUpload"],
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::{0}/*",
            "Principal": "*"}]
        new_bkt_policy[0]["Sid"] = new_bkt_policy[0]["Sid"].format(
            self.policy_id)
        new_bkt_policy[0]["Resource"] = new_bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info("Step 6: Created new bucket policy")
        self.log.info("Step 7: Creating json file for new  bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            new_bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 7: Created json file for new bucket policy")
        self.log.info(
            "Step 8: Updating new bucket policy on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 8: Updated new bucket policy on a bucket %s",
            self.bucket_name)
        self.log.info(
            "Step 9: Verifying new bucket policy is updated on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == new_bkt_policy[0]
        self.log.info(
            "Step 9: Verified new bucket policy is updated on a bucket %s",
            self.bucket_name)

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11227")
    @CTFailOn(error_handler)
    def test_6185_show_bkt_policy(self):
        """
        Initiating the test case to verify bucket
        policy should be returned in required format
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info("Step 5: Verifying policy in json format")
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info("Step 5: Verified policy in json format")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12028")
    @CTFailOn(error_handler)
    def test_6183_show_policy_from_another_account(self):
        """
        Test that s3 account cannot see bucket policy for bucket created by another s3 account
        """
        s3acc_name = f"cli_s3acc_policy_{int(time.time())}"
        s3acc_email = f"{s3acc_name}@seagate.com"
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info(
            "Step 5: Verifying policy is uploaded on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info(
            "Step 5: Verified policy is uploaded on a bucket %s",
            self.bucket_name)
        self.log.info(
            "Step 6: Creating s3 account user with name %s", s3acc_name)
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.s3bkt_plc_obj.login_cortx_cli()
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            s3acc_name, s3acc_email, self.acc_password)
        assert_utils.assert_equals(resp[0], True, resp[1])
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.log.info(
            "Step 6: Created s3 account user with name %s", s3acc_name)
        self.log.info("Step 7: Listing bucket policy with another account")
        self.s3bkt_plc_obj.login_cortx_cli(s3acc_name, self.acc_password)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(resp[1], "Access Denied")
        self.s3bkt_plc_obj.logout_cortx_cli()
        self.s3bkt_plc_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        self.log.info(
            "Step 7: Listing bucket policy with another account is failed with error %s",
            resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11228")
    @CTFailOn(error_handler)
    def test_6182_show_bkt_polc_s3_acc(self):
        """
        Initiating the test case to verify s3 account can see bucket policy with all parameters
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        self.bkt_policy[0]["Sid"] = self.bkt_policy[0]["Sid"].format(
            self.policy_id)
        self.bkt_policy[0]["Resource"] = self.bkt_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            self.bkt_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading policy on a bucket %s", self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], True, resp[1])
        assert_utils.assert_exact_string(resp[1], self.bkt_policy_msg)
        self.log.info(
            "Step 4: Uploaded policy on a bucket %s", self.bucket_name)
        self.log.info("Step 5: Verifying s3 account can see bucket policy")
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        json_data = self.s3bkt_plc_obj.format_str_to_dict(resp[1])
        assert json_data['Statement'][0] == self.bkt_policy[0]
        self.log.info("Step 5: Verified s3 account can see bucket policy")

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12033")
    @CTFailOn(error_handler)
    def test_6184_no_policy_exist(self):
        """
        Test that error is returned when no policy exist on bucket
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Retrieving bucket policy on bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.show_bucket_policy(self.bucket_name)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "The specified bucket does not have a bucket policy")
        self.log.info(
            "Step 5: Retrieving bucket policy on bucket %s is failed with error %s",
            self.bucket_name,
            resp[1])

    @pytest.mark.skip(reason="EOS-22299: CSM CLI which requires S3 Account login are unsupported")
    @pytest.mark.cluster_user_ops
    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-13137")
    @CTFailOn(error_handler)
    def test_6180_invalid_bkt_policy(self):
        """
        Test that error occours when statement file contains invalid bucket policy
        """
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        self.create_verify_bucket(self.bucket_name)
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating bucket policy on a bucket %s", self.bucket_name)
        invalid_policy = [{
            "Sid": "{0}",
            "Effect": "Allow",
            "Resource": "arn:aws:s3:::{0}/*",
            "Principal": "*"}]
        invalid_policy[0]["Sid"] = invalid_policy[0]["Sid"].format(
            self.policy_id)
        invalid_policy[0]["Resource"] = invalid_policy[0]["Resource"].format(
            self.bucket_name)
        self.log.info(
            "Step 2: Created bucket policy on a bucket %s", self.bucket_name)
        self.log.info("Step 3: Creating json file for bucket policy")
        self.s3bkt_plc_obj.create_copy_json_file(
            invalid_policy,
            self.policy_file_path,
            self.remote_file_path)
        self.log.info("Step 3: Created json file for bucket policy")
        self.log.info(
            "Step 4: Uploading invalid policy on a bucket %s",
            self.bucket_name)
        resp = self.s3bkt_plc_obj.create_bucket_policy(
            self.bucket_name,
            self.policy_id,
            self.remote_file_path)
        assert_utils.assert_equals(resp[0], False, resp[1])
        assert_utils.assert_exact_string(
            resp[1], "Missing required field Action")
        self.log.info(
            "Step 4: Uploading invalid policy on a bucket %s is failed with error %s",
            self.bucket_name,
            resp[1])
