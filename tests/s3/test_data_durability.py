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

"""Data Durability test module."""

import os
import time
import logging
import pytest

from commons import commands as cmd
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.host import Host
from libs.s3 import S3H_OBJ, CMN_CFG
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.iam_test_lib import IamTestLib

S3T_OBJ = S3TestLib()
IAMT_OBJ = IamTestLib()


class TestDataDurability:
    """Data Durability Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.timestamp = time.time()
        cls.bucket_name = "data-durability-bkt{0}".format(cls.timestamp)
        cls.test_file = "data_durability.txt"
        cls.file_size = 5
        cls.object_name = "obj_data_durability"
        cls.sleep_time = 4
        cls.host_ip = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.test_dir_path = os.path.join(
            os.getcwd(), "testdata", "TestDataDurability")
        cls.file_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.hobj = Host(
            hostname=cls.host_ip,
            username=cls.uname,
            password=cls.passwd)
        cls.hobj.connect()
        cls.log.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if system_utils.path_exists(cls.test_dir_path):
            system_utils.remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.hobj.disconnect()
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log.info("STARTED: Setup operations")
        self.log.info("Test file path: %s", self.file_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform all cleanup operations.
        This function will delete buckets and accounts created for tests.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info(
            "Deleting all buckets/objects created during TC execution")
        resp = S3T_OBJ.bucket_list()
        if resp:
            pref_list = [each_bucket for each_bucket in resp[1]
                         if each_bucket.startswith("data-durability-bkt")]
            if pref_list:
                S3T_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("Deleting the IAM accounts and users")
        all_accounts = IAMT_OBJ.list_accounts_s3iamcli(
            self.ldap_user,
            self.ldap_pwd)[1]
        iam_accounts = [acc["AccountName"]
                        for acc in all_accounts if
                        "data_durability" in acc["AccountName"]]
        self.log.info(iam_accounts)
        if iam_accounts:
            for acc in iam_accounts:
                resp = IAMT_OBJ.reset_access_key_and_delete_account_s3iamcli(
                    acc)
        self.log.info("Deleted the IAM accounts and users")
        self.log.info("Deleting the file created locally for object")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        self.log.info("Local file was deleted")
        self.log.info("ENDED: Teardown operations")

    def create_bkt_put_obj(self):
        """
        Function will create a bucket and uploads an object to it.

        also it will calculate checksum of file content
        :return str: Checksum of file content
        """
        self.log.info(
            "Step 1: Creating a file with name %s", (
                self.test_file))
        system_utils.create_file(self.file_path, self.file_size)
        self.log.info(
            "Step 1: Created a file with name %s", (
                self.test_file))
        self.log.info(
            "Step 2: Retrieving checksum of file %s", (
                self.test_file))
        resp1 = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp1[0], resp1[1])
        chksm_before_put_obj = resp1[1]
        self.log.info(
            "Step 2: Retrieved checksum of file %s", (
                self.test_file))
        self.log.info(
            "Step 3: Uploading a object to a bucket %s", (
                self.bucket_name))
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Uploaded an object to a bucket %s", (
                self.bucket_name))
        return chksm_before_put_obj

    def pcs_start_stop_cluster(self, start_stop_cmd, status_cmd):
        """
        Function starts and stops the cluster using the pcs command.

        :param string start_stop_cmd : start and stop command option
        :param string status_cmd: status command option
        :return: (Boolean and response)
        """
        self.hobj.execute_cmd(cmd=start_stop_cmd, read_lines=True)
        time.sleep(self.sleep_time)
        result = self.hobj.execute_cmd(cmd=status_cmd, read_lines=True)
        for value in result:
            if "cluster is not currently running on this node" in value:
                return False, result

        return True, result

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8005')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_s3authserver_restart_4232(self):
        """Test NO data loss in case of service restart- s3authserver."""
        self.log.info(
            "STARTED: Test NO data loss in case of service restart- s3authserver")
        restart_cmd = cmd.SYSTEM_CTL_RESTART_CMD.format("s3authserver")
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info(
            "Step 4: Restarting %s service",
            "s3authserver")
        system_utils.run_remote_cmd(
            restart_cmd,
            self.host_ip,
            self.uname,
            self.passwd)
        time.sleep(self.sleep_time)
        resp = S3H_OBJ.get_s3server_service_status(
            "s3authserver")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Restarted %s service",
            "s3authserver")
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be same")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss in case of service restart- s3authserver")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8006')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_haproxy_restart_4233(self):
        """Test NO data loss in case of service restart - haproxy."""
        self.log.info(
            "STARTED: Test NO data loss in case of service restart - haproxy")
        restart_cmd = cmd.SYSTEM_CTL_RESTART_CMD.format("haproxy")
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info(
            "Step 4: Restarting %s service",
            "haproxy")
        system_utils.run_remote_cmd(
            restart_cmd,
            self.host_ip,
            self.uname,
            self.passwd)
        time.sleep(self.sleep_time)
        resp = S3H_OBJ.get_s3server_service_status(
            "haproxy")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Restarted %s service", "haproxy")
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be file")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss in case of service restart - haproxy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8009')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_account_cred_change_4238(self):
        """Test NO data loss in case of account credentials change."""
        self.log.info(
            "STARTED: Test NO data loss in case of account credentials change")
        self.log.info(
            "Step 1: Creating a file with name %s", (
                self.test_file))
        system_utils.create_file(self.file_path, self.file_size)
        self.log.info(
            "Step 1: Created a file with name %s", (
                self.test_file))
        self.log.info(
            "Step 2: Retrieving checksum of file %s", (
                self.test_file))
        resp1 = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp1[0], resp1[1])
        chksm_before_put_obj = resp1[1]
        self.log.info(
            "Step 2: Retrieved checksum of file %s", (
                self.test_file))
        account_name = "{0}{1}".format(
            "data_durability_acc", str(
                time.time()))
        email_id = "{0}{1}".format(account_name, "@seagate.com")
        self.log.info(
            "Step 3: Uploading a object to a bucket %s", (
                self.bucket_name))
        resp = IAMT_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Uploaded an object to a bucket %s", (
                self.bucket_name))
        self.log.info(
            "Step 4: Changing credentials of an account %s", account_name)
        resp = IAMT_OBJ.reset_account_access_key_s3iamcli(
            account_name, self.ldap_user,
            self.ldap_pwd)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["AccessKeyId"]
        secret_key = resp[1]["SecretKey"]
        s3_temp_obj = S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 4: Changed credentials of an account %s", account_name)
        self.log.info(
            "Step 5: Verifying that data is accessible with new set of credentials")
        resp = s3_temp_obj.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 5: Verified that data is accessible with new set of credentials")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = s3_temp_obj.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be same")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(chksm_before_put_obj, chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        # Cleanup activity
        resp = s3_temp_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test NO data loss in case of account credentials change")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8004')
    @CTFailOn(error_handler)
    def test_no_data_loss_corruption_in_case_s3server_restart_4231(self):
        """Test NO data loss or corruption in case of service restart - s3server."""
        self.log.info(
            "STARTED: Test NO data loss or corruption in case of service restart - s3server")
        cluster_start = cmd.PCS_CLUSTER_START.format("--all")
        cluster_status = cmd.PCS_CLUSTER_STATUS
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info("Step 4: Restarting s3service service")
        resp = self.pcs_start_stop_cluster(cluster_start, cluster_status)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Restarted s3service service")
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be file")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss or corruption in case of service restart - s3server")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8007')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_motr_restart_4234(self):
        """Test NO data loss in case of service restart - motr."""
        self.log.info(
            "STARTED: Test NO data loss in case of service restart - motr")
        cluster_start = cmd.PCS_CLUSTER_START.format("--all")
        cluster_status = cmd.PCS_CLUSTER_STATUS
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info("Step 4: Restarting motr service")
        resp = self.pcs_start_stop_cluster(cluster_start, cluster_status)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Restarted motr service")
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be file")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss in case of service restart - motr")
