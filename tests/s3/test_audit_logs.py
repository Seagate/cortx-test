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

"""Audit logs test module."""

import logging
import os
import time

import pytest

from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.config_utils import read_yaml
from commons.utils.config_utils import update_cfg_based_on_separator
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.s3 import S3H_OBJ
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib


# pylint: disable-msg=too-many-public-methods
class TestAuditLogs:
    """Audit logs test suite."""

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log.info("STARTED: setup test suite operations.")
        cls.s3_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.mp_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.rem_path = const.S3_CONFIG
        cls.lcl_path = "/root/s3config.yaml"
        cls.common_file = "audit_test_file.txt"
        cls.test_file = "audit-obj-mp"
        cls.section = "S3_SERVER_CONFIG"
        cls.key = "S3_AUDIT_LOGGER_POLICY"
        cls.pwd_key = "password"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestAuditLogs")
        cls.common_file_path = os.path.join(cls.test_dir_path, cls.common_file)
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("Test file path: %s", cls.common_file_path)
        cls.old_value = "rsyslog-tcp"
        cls.new_val = cls.test_cfg = None
        cls.nodes = CMN_CFG["nodes"]
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
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
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log.info("STARTED: Setup operations.")
        self.log.info("Fetching s3config.yaml file from server")
        self.test_cfg = {}
        if system_utils.path_exists(self.lcl_path):
            system_utils.remove_file(self.lcl_path)
        resp = self.node_obj.copy_file_to_local(self.rem_path, self.lcl_path)
        assert_utils.assert_true(resp[0], resp[1])
        audit_config = read_yaml(self.lcl_path)[1]
        self.log.info(audit_config)
        self.old_value = audit_config[self.section][self.key]
        self.log.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform all cleanup operations.
        This function will delete buckets and accounts created for tests.
        """
        self.log.info("STARTED: Teardown operations.")
        resp = self.s3_obj.bucket_list()
        if resp:
            pref_list = [
                each_bucket for each_bucket in resp[1] if each_bucket.startswith("audit")]
            if pref_list:
                self.log.info("Deleting listed buckets: %s", pref_list)
            self.s3_obj.delete_multiple_buckets(pref_list)
        self.log.info("Reverting s3config changes to default")
        val = self.old_value
        self.old_value = self.new_val
        self.update_conf_restart_s3(val)
        self.log.info("Deleting test generated files")
        for fpath in [self.lcl_path, self.common_file_path]:
            if system_utils.path_exists(fpath):
                system_utils.remove_file(fpath)
                self.log.info("removed: %s", fpath)
        self.log.info("ENDED: Teardown operations.")

    def update_conf_restart_s3(self, new_value):
        """
        Function to update s3config.yaml file and restart each instance post
        restart also check stack status.

        :param str new_value: Value to be updated in the config file
        :return: None
        """
        self.log.info(
            "Step 1 : Update Audit info logger policy value to %s in s3config.yaml file",
            new_value)
        self.new_val = new_value
        self.log.debug("Old value : %s", self.old_value)
        self.log.debug("New value : %s", new_value)
        if self.old_value != new_value:
            for node in range(len(self.nodes)):
                host_name = CMN_CFG["nodes"][node]["host"]
                node_obj = Node(hostname=host_name,
                                username=self.uname,
                                password=self.passwd)
                resp = node_obj.copy_file_to_local(
                    self.rem_path, self.lcl_path)
                assert_utils.assert_true(resp[0], resp[1])
                resp = update_cfg_based_on_separator(
                    self.lcl_path,
                    self.key,
                    self.old_value,
                    new_value)
                assert_utils.assert_true(resp[0], resp[1])
                node_obj.copy_file_to_remote(
                    self.lcl_path,
                    self.rem_path
                )
                system_utils.remove_file(self.lcl_path)
            self.log.info(
                "Step 2 : Restarting the s3server instances for the configurations "
                "changes to take effect.")
            resp = S3H_OBJ.restart_s3server_resources(wait_time=15)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Checking hctl status post restart")
        resp = self.health_obj.is_motr_online()
        assert_utils.assert_true(resp, resp)

    def check_in_audit(self, value):
        """
        Function to check audit logs content in each s3server instance.

        :param str value: Value to be checked in log file
        :return boolean: True/False
        """
        status = False
        res = f"Searched value {value} doesn't exists"
        for node in range(len(self.nodes)):
            host_name = CMN_CFG["nodes"][node]["host"]
            username = CMN_CFG["nodes"][node]["username"]
            password = CMN_CFG["nodes"][node]["password"]
            folder = "audit"
            audit_path = "{}/{}/{}".format(
                S3_CFG["s3_logs"],
                folder,
                "audit.log")
            self.log.debug(audit_path)
            node_obj = Node(hostname=host_name, username=username, password=password)
            resp = node_obj.path_exists(audit_path)
            if resp:
                cmd = f"grep {value} {audit_path}"
                status, res = system_utils.run_remote_cmd(
                    cmd,
                    host_name,
                    username,
                    password)
                self.log.debug("status: %s, response: %s", status, res)
                if status:
                    return status, res
            else:
                self.log.warning(
                    "%s path doesn't exists on %s",
                    audit_path,
                    host_name)

        return status, res

    def check_in_messages(self, value):
        """
        Function to check messages content in each s3 server.

        :param str value: Value to be checked in file
        :return: True/False, res
        :rtype: tuple
        """
        status = False
        res = f"Searched value {value} doesn't exists"
        for node in range(len(self.nodes)):
            host_name = CMN_CFG["nodes"][node]["host"]
            username = CMN_CFG["nodes"][node]["username"]
            password = CMN_CFG["nodes"][node]["password"]
            log_msg_path = const.LOG_MSG_PATH
            self.log.debug(log_msg_path)
            node_obj = Node(hostname=host_name, username=username, password=password)
            resp = node_obj.path_exists(log_msg_path)
            if resp:
                cmd = f"grep {value} {log_msg_path}"
                status, res = system_utils.run_remote_cmd(
                    cmd, host_name, username, password)
                self.log.debug("status: %s, response: %s", status, res)
                if status:
                    return status, res
            else:
                self.log.warning(
                    "%s path doesn't exists on %s",
                    log_msg_path,
                    host_name)

        return status, res

    def audit_multipart(self, test_conf, check_audit=True):
        """
        Perform multipart operations using given test conf.

        :param test_conf: test config
        :param bool check_audit: If audit check is required after multipart operations
        """
        self.update_conf_restart_s3(test_conf["value"])
        self.log.info(
            "Step 3 : Create a 200 mb file using dd command"
            "Step 4 : Use split command to create parts"
            "Step 5 : Create multipart upload"
            "Step 6 : List multipart-upload"
            "Step 7 : Upload created parts"
            "Step 8 : List uploaded parts"
            "Step 9 : Compile list of upload parts"
            "Step 10 : Complete multipart upload")
        bucket_name = "{}{}".format(test_conf["bucket_name"],
                                    str(int(time.time())))
        self.log.info(
            "Creating a bucket with name : %s", bucket_name)
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        res = self.mp_obj.create_multipart_upload(
            bucket_name, test_conf["object_name"])
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.debug("mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        file_size = test_conf["file_size"]
        total_part = test_conf["total_parts"]
        res = self.mp_obj.upload_parts(
            mpu_id, bucket_name, test_conf["object_name"],
            file_size, total_parts=total_part,
            multipart_obj_path=self.test_file_path)
        assert_utils.assert_true(res[0], res[1])
        parts = res[1]
        self.log.info("Listing parts of multipart upload")
        res = self.mp_obj.list_parts(
            mpu_id, bucket_name, test_conf["object_name"])
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Completing multipart upload")
        res = self.mp_obj.complete_multipart_upload(
            mpu_id, parts, bucket_name, test_conf["object_name"])
        assert_utils.assert_true(res[0], res[1])
        if check_audit:
            self.log.info(
                "Step 10 : Check audit logs under every s3server instance folder."
                "Open audit.log to check if log is generated in JSON format "
                "post multipart operation")
            result = self.check_in_audit(test_conf["object_name"])
            self.log.debug(result[1])
            assert_utils.assert_true(result[0], result[1])
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)

    def audit_objects_ops(self, test_conf):
        """Perform object operations using given test conf."""
        self.update_conf_restart_s3(test_conf["value"])
        self.log.info("Step 3: Put object")
        bucket_name = "{}{}".format(test_conf["bucket_name"],
                                    str(int(time.time())))
        self.log.info(
            "Creating a bucket with name : %s", bucket_name)
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        resp = system_utils.create_file(
            self.test_file_path,
            test_conf["file_size"])
        assert_utils.assert_true(resp[0], resp[1])
        res = self.s3_obj.put_object(
            bucket_name,
            test_conf["object_name"],
            self.test_file_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 4: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "for object upload operation ")
        result = self.check_in_audit(test_conf["object_name"])
        self.log.debug(result[1])
        assert_utils.assert_true(result[0], result[1])
        self.log.info("Step 5: List Objects using list-objects command")
        res = self.s3_obj.object_list(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 6: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "for List Objects operation ")
        result = self.check_in_audit(test_conf["object_name"])
        self.log.debug(result[1])
        assert_utils.assert_true(result[0], result[1])
        self.log.info("Step 7: Delete Object within a bucket ")
        res = self.s3_obj.delete_object(bucket_name, test_conf["object_name"])
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 8: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "for Delete Object operation ")
        result = self.check_in_audit(test_conf["object_name"])
        self.log.debug(result[1])
        assert_utils.assert_true(result[0], result[1])

    def audit_bucket_ops(self, test_conf):
        """
        Perform bucket operations using given test conf.

        :param test_conf: test config
        """
        self.update_conf_restart_s3(test_conf["value"])
        self.log.info("Step 3: Create bucket")
        bucket_name = "{}{}".format(test_conf["bucket_name"],
                                    str(int(time.time())))
        self.log.info(
            "Creating a bucket with name : %s", bucket_name)
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info(
            "Step 4: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "for bucket create operation ")
        result = self.check_in_audit(bucket_name)
        self.log.debug(result[1])
        assert_utils.assert_true(result[0], result[1])
        self.log.info("Step 5: List Buckets")
        res = self.s3_obj.bucket_list()
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 6: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "for List Bucket operation ")
        result = self.check_in_audit(bucket_name)
        self.log.debug(result[1])
        assert_utils.assert_true(result[0], result[1])
        self.log.info("Step 7: Delete Bucket ")
        res = self.s3_obj.delete_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 8: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "for Delete Bucket operation ")
        result = self.check_in_audit(bucket_name)
        self.log.debug(result[1])
        assert_utils.assert_true(result[0], result[1])

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8012')
    @CTFailOn(error_handler)
    def test_5248(self):
        """
        Verify and check if audit logs are generated if we set audit logger policy to "disabled".
        """
        self.log.info("STARTED : Verify and check if audit logs are generated "
                      "if we set audit logger policy to disabled")
        self.update_conf_restart_s3("disabled")
        self.log.info("Step 3 : Create a bucket ")
        bucket_name = "{}{}".format(
            "audit-bkt5248", str(time.time()))
        resp = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4 : Check if audit folder gets "
            "created under /var/log/seagate/s3 in case already exists"
            "check bucket ops should not be logged")
        resp = self.check_in_audit(bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        resp = self.check_in_messages(bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info(
            "Step4: Verified that either file or s3 ops are not getting logged")
        self.log.info("STARTED : Verify and check if audit logs are generated "
                      "if we set audit logger policy to disabled")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8013')
    @CTFailOn(error_handler)
    def test_5236(self):
        """
        Verify and check if audit logs are generated post.

        Multipart upload with Syslog logger policy.
        """
        self.log.info(
            "STARTED : Verify and check if audit logs are generated post"
            "Multipart upload with Syslog logger policy")
        self.test_cfg["bucket_name"] = "audit-bkt5236"
        self.test_cfg["object_name"] = "audit-obj5236"
        self.test_cfg["file_size"] = 200
        self.test_cfg["value"] = "syslog"
        self.test_cfg["total_parts"] = 4
        self.audit_multipart(self.test_cfg)
        self.log.info(
            "ENDED : Verify and check if audit logs are generated post"
            "Multipart upload with Syslog logger policy")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8014')
    @CTFailOn(error_handler)
    def test_5235(self):
        """
        Verify and check if audit logs are generated post.

        S3 Object operations with "syslog" logger policy.
        """
        self.log.info(
            "STARTED : Verify and check if audit logs are generated post S3 "
            "Object operations with syslog logger policy.")
        self.test_cfg["bucket_name"] = "audit-bkt5235"
        self.test_cfg["object_name"] = "audit-obj5235"
        self.test_cfg["file_size"] = 5
        self.test_cfg["value"] = "syslog"
        self.audit_objects_ops(self.test_cfg)
        self.log.info(
            "ENDED : Verify and check if audit logs are generated post S3 "
            "Object operations with syslog logger policy.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8015')
    @CTFailOn(error_handler)
    def test_5231(self):
        """
        Verify and check if audit logs are generated post.

        S3 Bucket operations with "syslog" logger policy.
        """
        self.log.info(
            "STARTED : Verify and check if audit logs are generated post S3 "
            "Bucket operations with syslog logger policy.")
        test_cfg = {
            "bucket_name": "audit-bkt5231",
            "value": "syslog"
        }
        self.audit_bucket_ops(test_cfg)
        self.log.info(
            "ENDED : Verify and check if audit logs are generated post S3 "
            "Bucket operations with syslog logger policy.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8016')
    @CTFailOn(error_handler)
    def test_5228(self):
        """
        Verify and check if audit logs are generated post.

        S3 object operations with "log4cxx" logger policy.
        """
        self.log.info(
            "STARTED : Verify and check if audit logs are generated post S3 "
            "Object operations with log4cxx logger policy.")
        self.test_cfg["bucket_name"] = "audit-bkt5228"
        self.test_cfg["object_name"] = "audit-obj5228"
        self.test_cfg["file_size"] = 5
        self.test_cfg["value"] = "log4cxx"
        self.audit_objects_ops(self.test_cfg)
        self.log.info(
            "ENDED : Verify and check if audit logs are generated post S3 "
            "Object operations with log4cxx logger policy.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8018')
    @CTFailOn(error_handler)
    def test_5209(self):
        """
        Verify and check if audit logs are generated post.

        S3 Bucket operations with "log4cxx" logger policy.
        """
        self.log.info(
            "STARTED : Verify and check if audit logs are generated post S3 "
            "Bucket operations with log4cxx logger policy.")
        test_cfg = {
            "bucket_name": "audit-bkt5209",
            "value": "log4cxx"
        }
        self.audit_bucket_ops(test_cfg)
        self.log.info(
            "ENDED : Verify and check if audit logs are generated post S3 "
            "Bucket operations with log4cxx logger policy.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8017')
    @CTFailOn(error_handler)
    def test_5213(self):
        """
        Verify and check if audit logs are generated post.

        Multipart upload with log4cxx logger policy.
        """
        self.log.info(
            "STARTED : Verify and check if audit logs are generated post"
            "Multipart upload with log4cxx logger policy")
        self.test_cfg["bucket_name"] = "audit-bkt5213"
        self.test_cfg["object_name"] = "audit-obj5213"
        self.test_cfg["file_size"] = 200
        self.test_cfg["value"] = "log4cxx"
        self.test_cfg["total_parts"] = 4
        self.audit_multipart(self.test_cfg)
        self.log.info(
            "ENDED : Verify and check if audit logs are generated post"
            "Multipart upload with log4cxx logger policy")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8010')
    @CTFailOn(error_handler)
    def test_6253(self):
        """
        Test to Verify Password should not be logged in any.

        of the audit server logs post any bucket operation.
        """
        self.log.info(
            "STARTED: Test to Verify Password should not be logged in any of"
            " the audit server logs post any bucket operation.")
        self.log.info("Step 1,2: Updating s3 config and restating s3 instance")
        self.update_conf_restart_s3("log4cxx")
        self.log.info(
            "Step 1,2: Successfully updated config and verified hctl status")
        bucket_name = "{}{}".format("audit-bkt6253",
                                    str(int(time.time())))
        self.log.info(
            "Step 3: Creating a bucket with name : %s", bucket_name)
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_in(bucket_name, res[1], res[1])
        res = self.s3_obj.bucket_list()
        assert_utils.assert_in(bucket_name, res[1], res[1])
        self.log.info(
            "Step 3: Created a bucket with name : %s", bucket_name)
        self.log.info(
            "Step 4: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "post bucket creation")
        result = self.check_in_audit(bucket_name)
        assert_utils.assert_true(result[0], result)
        self.log.info("Step 4: Validated json generated in audit.log file"
                      " under every s3server instance folder.")
        self.log.info(
            "Step 5: Verify password should not be logged in any of the audit"
            " server logs post object upload")
        assert_utils.assert_not_in(
            self.pwd_key,
            result[1].decode(),
            result)
        self.log.info(
            "Step 5: Verified post object upload no password is logged in any"
            " of the audit server logs")
        self.log.info(
            "ENDED: Test to Verify Password should not be logged in any of"
            " the audit server logs post any bucket operation.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8011')
    @CTFailOn(error_handler)
    def test_6255(self):
        """
        Test to Verify Password should not be logged in any of the.

        audit server logs post any object operation..
        """
        self.log.info(
            "STARTED: Test to Verify Password should not be logged in any of"
            " the audit server logs post any object operation.")
        self.log.info("Step 1,2: Updating s3 config and restating s3 instance")
        self.update_conf_restart_s3("log4cxx")
        self.log.info(
            "Step 1,2: Successfully updated config and verified hctl status")
        bucket_name = "{}{}".format("audit-bkt6255",
                                    str(int(time.time())))
        obj_name = "audit-obj6255"
        self.log.info(
            "Step 3: Putting an %s object into %s bucket",
            obj_name,
            bucket_name)
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_in(bucket_name, res[1], res[1])
        res = self.s3_obj.bucket_list()
        assert_utils.assert_in(bucket_name, res[1], res[1])
        system_utils.create_file(
            self.common_file_path,
            int(2))
        res = self.s3_obj.put_object(
            bucket_name,
            obj_name,
            self.common_file_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 3: Successfully put an object into created bucket")
        self.log.info(
            "Step 4: Check audit logs under every s3server instance folder."
            "Open audit.log to check if log is generated in JSON format "
            "post object upload.")
        result = self.check_in_audit(obj_name)
        assert_utils.assert_true(result[0], result)
        self.log.info("Step 4: Validated json generated in audit.log file"
                      " under every s3server instance folder.")
        self.log.info(
            "Step 5: Verify password should not be logged in any of the audit server"
            " logs post object upload")
        assert_utils.assert_not_in(
            self.pwd_key,
            result[1].decode(),
            result)
        self.log.info(
            "Step 5: Verified post object upload no password is logged in any of the"
            " audit server logs")
        self.log.info(
            "ENDED: Test to Verify Password should not be logged in any of"
            " the audit server logs post any object operation.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8726')
    @CTFailOn(error_handler)
    def test_5238(self):
        """
        Test-Verify and check if audit logs are generated post S3 Bucket.

        operations with 'rsyslog-tcp' logger policy.
        """
        self.log.info(
            "STARTED : Test-Verify and check if audit logs are generated post S3 Bucket "
            "operations with 'rsyslog-tcp' logger policy")
        self.log.info(
            "Step 1,2: Update config and restart s3 service instances.")
        self.update_conf_restart_s3("syslog")

        bucket_name = "{}{}".format("audit-bkt5238",
                                    str(int(time.time())))
        self.log.info(
            "Step 1,2: Updated config and restarted s3 service instances.")
        self.log.info(
            "Step 3: Creating a bucket with name : %s", bucket_name)
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info(
            "Step 3: Created a bucket with name : %s", bucket_name)
        self.log.info("Step 4: List buckets")
        res = self.s3_obj.bucket_list()
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_in(bucket_name, res[1], res[1])
        self.log.info("Step 4: List bucket successful")
        self.log.info("Step 5: Delete Bucket %s", bucket_name)
        res = self.s3_obj.delete_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Bucket deleted successfully")
        self.log.info(
            "Step 7: Check Using rsyslog-tcp audit log are also directed to"
            " local log file on s3 server.")
        res = self.check_in_messages(bucket_name)
        assert_utils.assert_true(res[0], res)
        self.log.info(
            "Step 7: Check Using rsyslog-tcp audit log are also directed to"
            " local log file on s3 server.")
        self.log.info(
            "ENDED : Test- Verify and check if audit logs are generated post S3 Bucket "
            "operations with 'rsyslog-tcp' logger policy")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8727')
    @CTFailOn(error_handler)
    def test_5240(self):
        """
        Test- Verify and check if audit logs are generated post S3 Bucket.

        operations with 'rsyslog-tcp' logger policy.
        """
        self.log.info(
            "STARTED : Test- Verify and check if audit logs are generated post S3 Bucket "
            "operations with 'rsyslog-tcp' logger policy")
        self.log.info(
            "Step 1,2: Update config and restart s3 service instances.")
        self.update_conf_restart_s3("syslog")

        bucket_name = "{}{}".format("audit-bkt5240",
                                    str(int(time.time())))
        obj_name = "audit-obj5240"
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info(
            "Step 1,2: Updated config and restarted s3 service instances.")
        self.log.info(
            "Step 3: Put an object into bucket : %s", bucket_name)
        system_utils.create_file(
            self.common_file_path,
            5)
        res = self.s3_obj.put_object(
            bucket_name,
            obj_name,
            self.common_file_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Step 3: Put an object into bucket is successful")
        self.log.info("Step 4: List objects from bucket %s", bucket_name)
        res = self.s3_obj.object_list(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_in(obj_name, res[1], res[1])
        self.log.info("Step 4: Successfully listed object from bucket")
        self.log.info("Step 5: Delete object from bucket %s", bucket_name)
        res = self.s3_obj.delete_object(bucket_name, obj_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Deleted object successfully")
        self.log.info(
            "Step 7: Check Using rsyslog-tcp audit log are also directed to"
            " local log file on s3 server.")
        res = self.check_in_messages(bucket_name)
        assert_utils.assert_true(res[0], res)
        res = self.check_in_messages(obj_name)
        assert_utils.assert_true(res[0], res)
        self.log.info(
            "Step 7: Check Using rsyslog-tcp audit log are also directed to"
            " local log file on s3 server.")
        self.log.info(
            "ENDED : Test- Verify and check if audit logs are generated post S3 Bucket "
            "operations with 'rsyslog-tcp' logger policy")

    @pytest.mark.s3_ops
    @pytest.mark.s3_audit_logs
    @pytest.mark.tags('TEST-8728')
    @CTFailOn(error_handler)
    def test_5246(self):
        """
        Test-Verify and check if audit logs are generated.

        post Multipart upload with "rsyslog-tcp" logger policy..
        """
        self.log.info(
            "STARTED : Test-Verify and check if audit logs are generated "
            "post Multipart upload with 'rsyslog-tcp' logger policy.")
        self.test_cfg["bucket_name"] = "audit-bkt5246"
        self.test_cfg["object_name"] = "audit-obj5246"
        self.test_cfg["file_size"] = 200
        self.test_cfg["value"] = "syslog"
        self.test_cfg["total_parts"] = 4
        self.audit_multipart(self.test_cfg, check_audit=False)
        self.log.info(
            "Step 7: Check Using rsyslog-tcp audit log are also directed to"
            " local log file on s3 server.")
        res = self.check_in_messages(self.test_cfg["bucket_name"])
        assert_utils.assert_true(res[0], res)
        res = self.check_in_messages(self.test_cfg["object_name"])
        assert_utils.assert_true(res[0], res)
        self.log.info(
            "Step 7: Check Using rsyslog-tcp audit log are also directed to"
            " local log file on s3 server.")
        self.log.info(
            "ENDED : Test-Verify and check if audit logs are generated "
            "post Multipart upload with 'rsyslog-tcp' logger policy.")
