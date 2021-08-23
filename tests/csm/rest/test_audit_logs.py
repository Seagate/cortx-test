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
#
"""Tests Audit logs using REST API."""

import os
import time
import logging
from time import perf_counter_ns

import pytest
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_audit_logs import RestAuditLogs
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_s3user import RestS3user
from config import S3_CFG
from commons import configmanager
from commons.constants import Rest as const
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons import cortxlogging
from commons.exceptions import CTException
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_common_test_lib import create_s3_acc


class TestAuditLogs:
    """Audit logs Testsuite"""

    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setup...")
        cls.audit_logs = RestAuditLogs(component_csm="csm", component_s3="s3")
        cls.end_time = int(time.time())
        cls.start_time = cls.end_time - ((7 * 24) * 60 * 60)
        cls.csm_user = RestCsmUser()
        cls.config = CSMConfigsCheck()
        cls.log.info("Verifying if pre-defined CSM users are present...")
        user_already_present = cls.config.check_predefined_csm_user_present()
        cls.log.info("Creating pre-defined CSM users if not present...")
        if not user_already_present:
            cls.config.setup_csm_users()

        cls.log.info("Verifying if pre-defined S3 account is present...")
        setup_ready = cls.config.check_predefined_s3account_present()
        cls.log.info("Creating pre-defined S3 account if not present...")
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3()
        assert setup_ready
        cls.s3_buckets = RestS3Bucket()
        cls.s3_account = RestS3user()
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_audit_logs.yaml")
        cls.folder_path = os.path.join(TEST_DATA_FOLDER, "TestAuditLogs")
        if not system_utils.path_exists(cls.folder_path):
            system_utils.make_dirs(cls.folder_path)
        cls.log.info("Test setup initialized...")

    @pytest.fixture(autouse=True)
    def setup(self):
        """Test setup and teardown."""
        self.epoc_time_diff = 6400 # 86400
        self.s3_account_prefix = "s3audit-user{}"
        self.s3_email_prefix = "{}@seagate.com"
        self.s3_bucket_prefix = "s3audi-bkt{}"
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.s3_accounts = list()
        self.s3_objs = list()
        self.rest_obj = S3AccountOperations()
        self.upload_path = os.path.join(self.folder_path, "s3audit-upobj{}.txt")
        self.download_path = os.path.join(self.folder_path, "s3audit-dnobj{}.txt")
        yield
        if system_utils.path_exists(self.download_path):
            system_utils.remove_dirs(self.download_path)
        for s3obj in self.s3_objs:
            buckets = s3obj.bucket_list()[1]
            resp = s3obj.delete_multiple_buckets(buckets)
        for acc in self.s3_accounts:
            self.log.debug("Deleting %s account", acc)
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Deleted %s account successfully", acc)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10733')
    def test_4918(self):
        """Test that s3 account and iam user don't have access to audit logs
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(
            params=params,
            expected_status_code=403,
            login_as="s3account_user",
            validate_expected_response=False,
        )
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10735')
    def test_4926(self):
        """Verify that API to download audit logs returns 404 error code on invalid component name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              expected_status_code=404,
                                                              validate_expected_response=False,
                                                              invalid_component=True)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10736')
    def test_4925(self):
        """Verify that API to show audit logs returns 404 error code on invalid component name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          expected_status_code=404,
                                                          validate_expected_response=False,
                                                          invalid_component=True)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10737')
    def test_4913(self):
        """Test that GET API returns audit logs in binary format for both csm and s3 components
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_s3_download(params=params,
                                                             validate_expected_response=True,
                                                             response_type=str
                                                             )
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              validate_expected_response=True,
                                                              response_type=str
                                                              )
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10738')
    def test_4914(self):
        """Test that API response of audit logs API for CSM component
        contain info reagrding specified parameters and in specified format.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          validate_expected_response=True
                                                          )
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10739')
    def test_4917(self):
        """Test that admin can download and see audit logs
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          validate_expected_response=True
                                                          )
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              validate_expected_response=True,
                                                              response_type=str
                                                              )
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10741')
    def test_4919(self):
        """Test that audit log is returned for different time intervals
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        start_time = self.end_time - ((4 * 24) * 60 * 60)
        params = {"start_date": start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          validate_expected_response=True
                                                          )
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10743')
    def test_4916(self):
        """Test that csm user(having manage or monitor rights) can download and see audit logs
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          login_as="csm_user_manage",
                                                          validate_expected_response=True
                                                          )
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              login_as="csm_user_monitor",
                                                              validate_expected_response=True,
                                                              response_type=str
                                                              )
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12841')
    def test_4920(self):
        """Test that Verify that content of both 'show' and 'dowload' api is exactly same
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Creating the payload for the audit log show api and audit log download api")
        data = self.csm_conf["test_4920"]["duration"]
        end_time = int(time.time())
        start_time = end_time - data
        params = {"start_date": start_time, "end_date": end_time}

        self.log.info("Step 1: Sending audit log show request for start time: %s and end time: %s",
                      start_time, end_time)
        audit_log_show_response = self.audit_logs.audit_logs_csm_show(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_show_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Step 1: Verified that audit log show request returned status: %s",
                      audit_log_show_response.status_code)

        self.log.info("Step 2: Sending audit log download request for start "
                      "time: %s and end time: %s",
                      start_time, end_time)
        audit_log_download_response = self.audit_logs.audit_logs_csm_download(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_download_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Step 2: Verified that audit log show request returned status: %s",
                      audit_log_download_response.status_code)

        self.log.info(
            "Step 3:Comparing and verifying if the audit log show api content "
            "and the downloaded file content with audit log download api match")
        assert self.audit_logs.verify_audit_logs_show_download(
            audit_log_show_response, audit_log_download_response)
        self.log.info(
            "Step 3:Verified the audit log show api content and the downloaded "
            "file content with audit log download api match ")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15865')
    def test_4922(self):
        """
        Test that GET api returns audit logs for date range specified and total
        count should not exceed more than 10000
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_4922"]
        self.end_time = int(time.time())
        start_time = self.end_time - ((data["end_date"] * data["hrs"]) * data["min"] * data["sec"])

        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": self.end_time}

        self.log.info(
            "Step 1: Verifying that GET api returns audit logs for date range specified")
        for i in range(0, len(data["user_list"])):
            self.log.info("Fetchin audit log GET API by logging in as %s user",
                          data["user_list"][i])
            response = self.audit_logs.audit_logs_csm_show(
                params, login_as=data["user_list"][i])
            assert_utils.assert_equals(response.status_code,
                                       const.SUCCESS_STATUS)
        self.log.info(
            "Step 1: Verified that GET api returns audit logs for date range specified")

        self.log.info(
            "Step 2: Verifying that GET api returns records not more than 10000")
        response = self.audit_logs.audit_logs_csm_show(params)
        self.log.info("Count of records in audit logs is:%s", response.json()['total_records'])

        self.log.info("Generating autdit logs for test purpose")
        if response.json()['total_records'] < data["record_count"]:
            for i in range(response.json()['total_records'], data["max_record_count"]):
                resp = self.csm_user.list_csm_single_user(
                    request_type="get",
                    expect_status_code=const.SUCCESS_STATUS,
                    user=self.audit_logs.config["csm_admin_user"]["username"],
                    return_actual_response=True)
                assert resp
        self.end_time = int(time.time())
        start_time = self.end_time - ((data["end_date"] * data["hrs"]) * data["min"] * data["sec"])
        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": self.end_time}
        response = self.audit_logs.audit_logs_csm_show(params)
        self.log.info("Count of records in audit logs is:%s", response.json()['total_records'])
        assert_utils.assert_equals(response.json()['total_records'], data["record_count"])

        self.log.info(
            "Step 2: Verified that GET api returns records not more than 10000")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16553')
    def test_4915(self):
        """
        Test that API response of audit logs for s3 component
        contain info regarding specified parameters and in specified format
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        epoc_time_diff = self.csm_conf["test_4915"]["epoc_time_diff"]

        self.log.info("Creating S3 bucket")
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")

        self.log.info("Verifying S3 bucket was created")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Verified s3 bucket: %s was created",
                      response.json()["bucket_name"])
        bucket = response.json()["bucket_name"]

        self.log.info(
            "Waiting for sometime for the log of the newly created s3 bucket to be available...")
        time.sleep(3)
        end_time = int(time.time())
        start_time = int(time.time() - epoc_time_diff)

        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": end_time}

        self.log.info(
            "Verifying audit logs for s3 component contain info regarding "
            "specified parameters and in specified format ")
        assert self.audit_logs.verify_audit_logs_s3_show(params=params,
                                                         validate_expected_response=True,
                                                         bucket=bucket
                                                         )
        self.log.info(
            "Verified audit logs for s3 component contain info regarding "
            "specified parameters and in specified format ")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22361')
    def test_22361(self):
        """Test single sort by user parameters on view , download operation on S3 audit log."""
        self.log.info("STARTED: Test single sort by user parameters on view , download operation"
                      " on S3 audit log.")
        self.log.info("Step 1: Create 10 S3 users.")
        for i in range(10):
            self.s3_user = self.s3_account_prefix.format(perf_counter_ns())
            resp = create_s3_acc(self.s3_user, self.s3_email_prefix.format(self.s3_user),
                                 self.s3acc_passwd)
            assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
            s3_obj = resp[0]
            self.s3_accounts.append(self.s3_user)
            self.s3_objs.append(s3_obj)
        self.log.info("Step 2: Login from each S3 user and create buckets on it.")
        s3obj_dict = {}
        for s3ob in self.s3_objs:
            self.s3_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
            resp = s3ob.create_bucket(self.s3_valid_bkt)
            assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
            assert_utils.assert_equal(resp[1], self.s3_valid_bkt,
                                      f"Failed to create s3 bucket, resp: {resp}")
            s3obj_dict[s3ob] = self.s3_bkt
        self.log.info("Step 3: Perform Read and write operations on the above buckets.")
        # TODO 
        self.log.info("Step 4: Delete the bucket and associated S3 account.")
        for s3ob in s3obj_dict:
            resp = s3ob.delete_bucket(s3obj_dict[s3ob])
            assert_utils.assert_true(resp[0], resp[1])
        for s3acc in self.s3_accounts:
            resp = self.rest_obj.delete_s3_account(s3acc)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: GET S3 audit log sorted by User.")
        time.sleep(10)
        start_time = int(time.time()) - self.epoc_time_diff
        end_time = int(time.time()) + self.epoc_time_diff
        self.log.info("Parameters for the audit logs GET api")
        for user in self.s3_accounts:
            params = {"start_date": start_time, "end_date": end_time, "sortby": user}
            resp = self.audit_logs.verify_audit_logs_s3_show(
                params=params, validate_expected_response=True, bucket=self.s3_valid_bkt)
            assert_utils.assert_true(resp,
                                     f"Failed to find bucket {self.s3_valid_bkt} in s3 audit log")
        self.log.info("Step 6: View, Download CSM audit log is sorted by User.")
        for user in self.s3_accounts:
            params = {"start_date": start_time, "end_date": end_time, "sortby": user}
            assert self.audit_logs.verify_audit_logs_s3_download(
                params=params, validate_expected_response=True)
        self.log.info("Step 7: Repeat the above steps for specified number of iterations.")
        self.log.info("ENDED: Test single sort by user parameters on view , download operation"
                      " on S3 audit log.")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22360')
    def test_22360(self):
        """Test single sort by timestamp parameters on view , download operation on S3 audit log."""
        self.log.info("STARTED: Test single sort by timestamp parameters on view , download "
                      "operation on S3 audit log.")
        self.s3_user = self.s3_account_prefix.format(perf_counter_ns())
        self.log.info("Step 1: Pre-requisite, Create admin, S3, IAM users if not created.")
        resp = create_s3_acc(self.s3_user, self.s3_email_prefix.format(self.s3_user),
                             self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.s3_accounts.append(self.s3_user)
        self.s3_objs.append(s3_obj)
        for _ in range(5):
            start_time = int(time.time()) - self.epoc_time_diff
            self.s3_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
            self.log.info("Step 2: Login using S3 user and create bucket.")
            resp = s3_obj.create_bucket(self.s3_bkt)
            assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
            assert_utils.assert_equal(resp[1], self.s3_bkt,
                                      f"Failed to create s3 bucket, resp: {resp}")
            bkt_create_time = int(time.time())
            self.log.info("Step 3: Perform create a bucket after every 60 seconds for the specified"
                          " number of mins. Make a note of the time stamp when the bucket was created.")
            end_time = int(time.time()) + self.epoc_time_diff
            self.log.info("Parameters for the audit logs GET api")
            params = {"start_date": start_time, "end_date": end_time, 'sortby': "timestamp"}
            self.log.info("Step 4: View S3 audit log sorted by timestamp.")
            resp = self.audit_logs.verify_audit_logs_s3_show(
                params=params, validate_expected_response=True, bucket=self.s3_bkt)
            assert_utils.assert_true(resp,
                                     f"Failed to find bucket {self.s3_valid_bkt} in s3 audit log")
            self.log.info("Step 5: Download CSM audit log is sorted by User.")
            assert self.audit_logs.verify_audit_logs_s3_download(
                params=params, validate_expected_response=True)
            time.sleep(60)
        self.log.info("ENDED: Test single sort by timestamp parameters on view , download "
                      "operation on S3 audit log.")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22359')
    def test_22359(self):
        """
        Sort, view and download s3 audit logs.

        Test single sort by response code parameters on view, download operation on S3 audit log.
        """
        self.log.info("STARTED: Test single sort by response code parameters on view, download"
                      " operation on S3 audit log")
        self.s3_user = self.s3_account_prefix.format(perf_counter_ns())
        self.s3_valid_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
        self.s3_invalid_bkt = (self.s3_bucket_prefix.format(perf_counter_ns())).upper()
        start_time = int(time.time()) - self.epoc_time_diff
        self.log.info("Step 1: Pre-requisite, Create new S3 account")
        resp = create_s3_acc(self.s3_user, self.s3_email_prefix.format(self.s3_user),
                             self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.s3_accounts.append(self.s3_user)
        self.s3_objs.append(s3_obj)
        self.log.info("Step 2: Login using S3 user and perform, Valid Create bucket operation, "
                      "Invalid Create bucket operation")
        resp = s3_obj.create_bucket(self.s3_valid_bkt)
        assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
        assert_utils.assert_equal(resp[1], self.s3_valid_bkt,
                                  f"Failed to create s3 bucket, resp: {resp}")
        try:
            resp = s3_obj.create_bucket(self.s3_invalid_bkt)
            assert_utils.assert_false(resp[0], f"Created s3 bucket, resp: {resp}")
            assert_utils.assert_not_equal(resp[1], self.s3_invalid_bkt,
                                          f"Created s3 bucket, resp: {resp}")
        except CTException as error:
            self.log.error(error.message)
        self.log.info("Step 3: Login using admin user and view S3 audit log")
        self.log.info(
            "Waiting for sometime for the log of the newly created s3 bucket to be available...")
        time.sleep(3)
        end_time = int(time.time()) + self.epoc_time_diff
        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": end_time}
        self.log.info(
            "Verifying audit logs for s3 component contain info regarding "
            "specified parameters and in specified format ")
        resp = self.audit_logs.verify_audit_logs_s3_show(
            params=params, validate_expected_response=True, bucket=self.s3_valid_bkt)
        #assert_utils.assert_true(resp, f"Failed to find bucket {self.s3_valid_bkt} in s3 audit log")
        resp = self.audit_logs.verify_audit_logs_s3_show(
            params=params, validate_expected_response=True, expected_status_code=400,
            bucket=self.s3_invalid_bkt)
        assert_utils.assert_true(resp,
                                  f"Failed to find invalid bucket {self.s3_invalid_bkt} in audit log")
        self.log.info("Step 4: Login using admin user and download S3 audit log")
        # assert self.audit_logs.verify_audit_logs_s3_download(
        #     params=params, validate_expected_response=True)
        self.log.info("ENDED: Test single sort by response code parameters on view , download "
                      "operation on S3 audit log")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22358')
    def test_22358(self):
        """Test filtering by user parameters on view , download operation on S3 audit log."""
        self.log.info("STARTED: Test filtering by user parameters on view , download operation on"
                      " S3 audit log")
        self.s3_user = self.s3_account_prefix.format(perf_counter_ns())
        self.s3_valid_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
        self.log.info("Step 1: Create an S3 user which is the same as the specified number of"
                      " iteration.")
        resp = create_s3_acc(self.s3_user, self.s3_email_prefix.format(self.s3_user),
                             self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.s3_accounts.append(self.s3_user)
        self.s3_objs.append(s3_obj)
        self.log.info("Step 2: Login using above S3 account.")
        self.log.info("Step 3: Perform the following operations using S3 login.")
        self.log.info("Step 3.1 Create bucket")
        resp = s3_obj.put_object(self.s3_valid_bkt)
        assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
        assert_utils.assert_equal(resp[1], self.s3_valid_bkt,
                                  f"Failed to create s3 bucket, resp: {resp}")
        self.log.info("Step 3.2 Perform IO on the created bucket")
        # TODO
        self.log.info("Step 3.3 Delete the created bucket.")
        resp = s3_obj.delete_bucket(self.s3_valid_bkt, force=True)
        assert_utils.assert_true(resp[0], f"Failed to delete s3 bucket, resp: {resp}")
        assert_utils.assert_equal(resp[1], self.s3_valid_bkt,
                                  f"Failed to delete s3 bucket, resp: {resp}")
        self.log.info("Step 4: Delete the S3 account.")
        resp = self.rest_obj.delete_s3_account(self.s3_user)
        assert_utils.assert_true(resp[0], f"Failed to delete s3 user: {resp[1]}")
        self.log.info("Step 5: View S3 audit log sorted by User, Endpoint: /auditlogs/show/S3,"
                      " parameter: filter by above S3 user.")
        self.log.info("Parameters for the audit logs GET api")
        time.sleep(3)
        start_time = int(time.time()) - self.epoc_time_diff
        end_time = int(time.time())
        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": end_time, 'sortby': self.s3_user}
        resp = self.audit_logs.verify_audit_logs_s3_show(
            params=params, validate_expected_response=True, bucket=self.s3_valid_bkt)
        assert_utils.assert_true(resp, f"Failed to find bucket {self.s3_valid_bkt} in s3 audit log")
        self.log.info("Step 6: Download CSM audit log is sorted by User")
        assert self.audit_logs.verify_audit_logs_s3_download(
            params=params, validate_expected_response=True)
        self.log.info("Step 7: Repeat the above operations for different s3 user.")
        self.log.info("ENDED: Test filtering by user parameters on view , download operation on"
                      " S3 audit log")
