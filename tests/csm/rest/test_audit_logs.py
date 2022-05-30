# pylint: disable=too-many-lines
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
#
"""Tests Audit logs using REST API."""

from __future__ import absolute_import
from __future__ import division

import os
import time
import logging
from builtins import round
from time import perf_counter_ns

import pytest

from commons import configmanager
from commons import commands
from commons import cortxlogging
from commons.constants import Rest as const
from commons.exceptions import CTException
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.system_utils import run_remote_cmd
from config import CMN_CFG, PROV_CFG
from config.s3 import S3_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_audit_logs import RestAuditLogs
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_capacity import SystemCapacity
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3.s3_common_test_lib import create_s3_acc_get_s3testlib
from libs.s3.s3_common_test_lib import perform_s3_io
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

# pylint: disable-msg=too-many-instance-attributes
# pylint: disable-msg=too-many-public-methods
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
        cls.iam_user = RestIamUser()
        cls.system_capacity = SystemCapacity()
        cls.csm_alerts = SystemAlerts()
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
        cls.s3user = RestS3user()
        cls.rest_iam_user = RestIamUser()
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_audit_logs.yaml")
        cls.folder_path = os.path.join(TEST_DATA_FOLDER, "TestAuditLogs")
        if not system_utils.path_exists(cls.folder_path):
            system_utils.make_dirs(cls.folder_path)
        cls.log.info("Test setup initialized...")
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.health_helper = Health(CMN_CFG["nodes"][0]["hostname"],
                                   CMN_CFG["nodes"][0]["username"],
                                   CMN_CFG["nodes"][0]["password"])
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)

    @pytest.fixture(autouse=True)
    def setup(self):
        """Test setup and teardown."""
        self.epoc_time_diff = self.csm_conf["epoc_time_diff"]
        self.s3_account_prefix = "s3audit-user{}"
        self.s3_email_prefix = "{}@seagate.com"
        self.s3_bucket_prefix = "s3audi-bkt{}"
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.s3_accounts = list()
        self.s3_objs = list()
        self.rest_obj = S3AccountOperations()
        yield
        if system_utils.path_exists(self.folder_path):
            system_utils.remove_dirs(self.folder_path)
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

    @pytest.mark.skip(reason="EOS-24246 open against F-44A feature.")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22361')
    def test_22361(self):
        """
        Test single sort by user parameters on view , download operation on S3 audit log.
        TODO: Once EOS-24246 inplace we need improvement in s3/csm log validation.
        """
        self.log.info("STARTED: Test single sort by user parameters on view , download operation"
                      " on S3 audit log.")
        start_time = int(time.time()) - self.epoc_time_diff
        self.log.info("Step 1: Create 10 S3 users.")
        for _ in range(10):
            s3_user = self.s3_account_prefix.format(perf_counter_ns())
            resp = create_s3_acc_get_s3testlib(s3_user, self.s3_email_prefix.format(s3_user),
                                               self.s3acc_passwd)
            assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
            self.s3_objs.append(resp[0])
            self.s3_accounts.append(s3_user)
        self.log.info("Step 2: Login from each S3 user and create buckets on it.")
        s3obj_dict = {}
        for s3ob in self.s3_objs:
            s3_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
            resp = s3ob.create_bucket(s3_bkt)
            assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
            assert_utils.assert_equal(
                resp[1], s3_bkt, f"Failed to create s3 bucket, resp: {resp}")
            s3obj_dict[s3ob] = s3_bkt
        self.log.info("Step 3: Perform Read and write operations on the above buckets.")
        for s3obj in s3obj_dict:
            resp = perform_s3_io(s3obj, s3obj_dict[s3obj], self.folder_path)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Delete the bucket and associated S3 account.")
        for s3obj in s3obj_dict:
            resp = s3obj.delete_bucket(s3obj_dict[s3obj], force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.s3_objs = list()  # s3 object dict
        for s3acc in self.s3_accounts:
            resp = self.rest_obj.delete_s3_account(s3acc)
            assert_utils.assert_true(resp[0], resp[1])
        self.s3_accounts = list()  # Account cleanup.
        self.log.info("Step 5: GET S3 audit log sorted by User.")
        time.sleep(3)
        end_time = int(time.time()) + self.epoc_time_diff
        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": end_time, "sortby": "user"}
        resp = self.audit_logs.verify_audit_logs_s3_show(
            params=params, validate_expected_response=True)
        assert_utils.assert_true(resp, "Failed sort s3 audit log by user.")
        self.log.info("Step 6: View, Download CSM audit log is sorted by User.")
        resp = self.audit_logs.audit_logs_csm_show(params=params)
        assert_utils.assert_true(resp, "Failed view csm log by user.")
        resp = self.audit_logs.verify_audit_logs_csm_download(
            params=params, validate_expected_response=True, response_type=str)
        assert_utils.assert_true(resp, "Failed sort csm audit log by user.")
        self.log.info("Step 7: Repeat the above steps for specified number of iterations.")
        self.log.info("ENDED: Test single sort by user parameters on view , download operation"
                      " on S3 audit log.")

    @pytest.mark.skip(reason="EOS-24246 open against F-44A feature.")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22360')
    def test_22360(self):
        """
        Test single sort by timestamp parameters on view , download operation on S3 audit log.
        TODO: Once EOS-24246 inplace we need improvement in s3/csm log validation.
        """
        self.log.info("STARTED: Test single sort by timestamp parameters on view , download "
                      "operation on S3 audit log.")
        s3_user = self.s3_account_prefix.format(perf_counter_ns())
        self.log.info("Step 1: Pre-requisite, Create admin, S3, IAM users if not created.")
        resp = create_s3_acc_get_s3testlib(s3_user, self.s3_email_prefix.format(s3_user),
                                           self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.s3_accounts.append(s3_user)
        self.s3_objs.append(s3_obj)
        for _ in range(5):
            start_time = int(time.time()) - self.epoc_time_diff
            s3_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
            self.log.info("Step 2: Login using S3 user and create bucket.")
            resp = s3_obj.create_bucket(s3_bkt)
            bkt_create_time = int(time.time())
            self.log.info(bkt_create_time)
            assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
            self.log.info(
                "Step 3: Perform create a bucket after every 60 seconds for the specified"
                "number of mins. Make a note of the time stamp when the bucket was created.")
            end_time = int(time.time()) + self.epoc_time_diff
            self.log.info("Parameters for the audit logs GET api")
            params = {"start_date": start_time, "end_date": end_time, 'sortby': "timestamp"}
            self.log.info("Step 4: View S3 audit log sorted by timestamp.")
            resp = self.audit_logs.verify_audit_logs_s3_show(
                params=params, validate_expected_response=True, bucket=s3_bkt)
            assert_utils.assert_true(resp, f"Failed to find bucket {s3_bkt} in s3 audit log")
            self.log.info("Step 5: Download CSM audit log is sorted by User.")
            params = {"start_date": start_time, "end_date": end_time, 'sortby': "user"}
            assert self.audit_logs.verify_audit_logs_csm_download(
                params=params, validate_expected_response=True, response_type=str)
            time.sleep(60)
        self.log.info("ENDED: Test single sort by timestamp parameters on view , download "
                      "operation on S3 audit log.")

    @pytest.mark.skip(reason="EOS-24246 open against F-44A feature.")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22359')
    def test_22359(self):
        """
        Sort, view and download s3 audit logs.

        Test single sort by response code parameters on view, download operation on S3 audit log.
        TODO: Once EOS-24246 inplace we need improvement in s3/csm log validation.
        """
        self.log.info("STARTED: Test single sort by response code parameters on view, download"
                      " operation on S3 audit log")
        s3_user = self.s3_account_prefix.format(perf_counter_ns())
        s3_valid_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
        s3_invalid_bkt = (self.s3_bucket_prefix.format(perf_counter_ns())).upper()
        start_time = int(time.time()) - self.epoc_time_diff
        self.log.info("Step 1: Pre-requisite, Create new S3 account")
        resp = create_s3_acc_get_s3testlib(s3_user, self.s3_email_prefix.format(s3_user),
                             self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.s3_accounts.append(s3_user)
        self.s3_objs.append(s3_obj)
        self.log.info("Step 2: Login using S3 user and perform, Valid Create bucket operation, "
                      "Invalid Create bucket operation")
        resp = s3_obj.create_bucket(s3_valid_bkt)
        assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
        assert_utils.assert_equal(resp[1], s3_valid_bkt,
                                  f"Failed to create s3 bucket, resp: {resp}")
        try:
            resp = s3_obj.create_bucket(s3_invalid_bkt)
            assert_utils.assert_false(resp[0], f"Created s3 bucket, resp: {resp}")
            assert_utils.assert_not_equal(resp[1], s3_invalid_bkt,
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
            params=params, validate_expected_response=True, bucket=s3_valid_bkt)
        assert_utils.assert_true(resp, f"Failed to find bucket {s3_valid_bkt} in s3 audit log")
        resp = self.audit_logs.verify_audit_logs_s3_show(
            params=params, validate_expected_response=True, expected_status_code=400,
            bucket=s3_invalid_bkt)
        assert_utils.assert_true(
            resp, f"Failed to find invalid bucket {s3_invalid_bkt} in audit log")
        self.log.info("Step 4: Login using admin user and download S3 audit log")
        assert self.audit_logs.verify_audit_logs_s3_download(
            params=params, validate_expected_response=True, response_type=str)
        self.log.info("ENDED: Test single sort by response code parameters on view , download "
                      "operation on S3 audit log")

    @pytest.mark.skip(reason="EOS-24246 open against F-44A feature.")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22358')
    def test_22358(self):
        """
        Test filtering by user parameters on view , download operation on S3 audit log.
        TODO: Once EOS-24246 inplace we need improvement in s3/csm log validation.
        """
        self.log.info("STARTED: Test filtering by user parameters on view , download operation on"
                      " S3 audit log")
        start_time = int(time.time()) - self.epoc_time_diff
        s3_user = self.s3_account_prefix.format(perf_counter_ns())
        s3_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
        self.log.info("Step 1: Create an S3 user which is the same as the specified number of"
                      " iteration.")
        resp = create_s3_acc_get_s3testlib(s3_user, self.s3_email_prefix.format(s3_user),
                                           self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.log.info("Step 2: Login using above S3 account.")
        self.log.info("Step 3: Perform the following operations using S3 login.")
        self.log.info("Step 3.1 Create bucket")
        resp = s3_obj.create_bucket(s3_bkt)
        assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
        assert_utils.assert_equal(resp[1], s3_bkt,
                                  f"Failed to create s3 bucket, resp: {resp}")
        self.log.info("Step 3.2 Perform IO on the created bucket")
        resp = perform_s3_io(s3_obj, s3_bkt, self.folder_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3.3 Delete the created bucket.")
        resp = s3_obj.delete_bucket(s3_bkt, force=True)
        assert_utils.assert_true(resp[0], f"Failed to delete s3 bucket, resp: {resp}")
        self.log.info("Step 4: Delete the S3 account.")
        resp = self.rest_obj.delete_s3_account(s3_user)
        assert_utils.assert_true(resp[0], f"Failed to delete s3 user: {resp[1]}")
        self.log.info("Step 5: View S3 audit log sorted by User, Endpoint: /auditlogs/show/S3,"
                      " parameter: filter by above S3 user.")
        self.log.info("Parameters for the audit logs GET api")
        time.sleep(3)
        end_time = int(time.time()) + self.epoc_time_diff
        self.log.info("Parameters for the audit logs GET api")
        params = {"start_date": start_time, "end_date": end_time, 'sortby': "user"}
        resp = self.audit_logs.verify_audit_logs_s3_show(
            params=params, validate_expected_response=True)
        assert_utils.assert_true(resp, "Failed to sort s3 audit log by user.")
        self.log.info("Step 6: Download CSM audit log is sorted by User")
        assert self.audit_logs.verify_audit_logs_csm_download(
            params=params, validate_expected_response=True, response_type=str)
        self.log.info("Step 7: Repeat the above operations for different s3 user.")
        self.log.info("ENDED: Test filtering by user parameters on view , download operation on"
                      " S3 audit log")

    @pytest.mark.skip(reason="Verification of sort audit logs is blocked refer EOS-24930,EOS-24931")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22332')
    def test_22332(self):
        """Test sort by user parameters on view , download operation on CSM audit log
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Test purpose: Verifying sort operation by user parameters on view,"
            " download operation on CSM audit log")
        data = self.csm_conf["test_22332"]["duration"]
        end_time = int(time.time())
        start_time = end_time - data
        self.log.info(
            "Step 1: Login using manage user and perform GET users operation")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("Verified that status code %s was returned along "
                      "with response: %s for the get request for csm "
                      "manage user", response.status_code,
                      response.json())
        self.log.info(
            "Step 2: Login using monitor user and perform GET /users operation")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("Verified that status code %s was returned along "
                      "with response: %s for the get request for csm "
                      "monitor user", response.status_code,
                      response.json())
        self.log.info(
            "Step 3: Login using S3 account and perform GET /iamusers operation")
        self.log.info("Creating IAM user")
        status, response = self.iam_user.create_and_verify_iam_user_response_code()
        print(status)
        self.log.info("Verifying status code returned is 200 and response is not null")
        response = self.iam_user.list_iam_users(login_as="s3account_user")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("Verified that status code %s was returned along "
                      "with response: %s for the get request for csm "
                      "s3account user", response.status_code,
                      response.json())
        self.log.info("Step4: View CSM Audit logs sorted by user")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "user",
            "dir": "asc"}
        audit_log_show_response = self.audit_logs.audit_logs_csm_show(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_show_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log show request returned status: %s",
            audit_log_show_response.status_code)
        all_user = [usr['user']
                    for usr in audit_log_show_response.json()['logs']]
        self.log.info(all_user)
        assert_utils.assert_equals(
            sorted(all_user),
            all_user,
            "Failed to sort audit log by user.")
        self.log.info("Step 5: Download CSM Audit logs sorted by user")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "user",
            "dir": "asc"}
        audit_log_download_response = self.audit_logs.audit_logs_csm_download(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_download_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log show request returned status: %s",
            audit_log_download_response.status_code)
        # TODO: "Verification of sort audit logs is blocked refer EOS-24930,EOS-24931"
        self.log.info(
            "TODO: Verification of sort audit log for Download audit logs is blocked "
            "refer EOS-24930,EOS-24931")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.skip(reason="Verification of sort audit logs is blocked refer EOS-24930,EOS-24931")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22334')
    def test_22334(self):
        """Test sort by user parameters on view , download operation on CSM audit log
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test purpose: Verifying sort operation by user parameters on view,"
            " download operation on CSM audit log")
        data = self.csm_conf["test_22334"]["duration"]
        end_time = int(time.time())
        start_time = end_time - data
        self.log.info(
            "Step 1: Login using manage user and perform GET capacity / GET alerts users operation")
        self.log.info("GET capacity . . .")
        results = self.system_capacity.parse_capacity_usage()
        csm_total, csm_avail, csm_used, csm_used_percent, csm_unit = results
        ha_total, ha_avail, ha_used = self.health_helper.get_sys_capacity()
        ha_used_percent = round((ha_used / ha_total) * 100, 1)
        csm_used_percent = round(csm_used_percent, 1)
        assert_utils.assert_equals(
            csm_total, ha_total, "Total capacity check failed.")
        assert_utils.assert_equals(
            csm_avail, ha_avail, "Available capacity check failed.")
        assert_utils.assert_equals(
            csm_used, ha_used, "Used capacity check failed.")
        assert_utils.assert_equals(
            csm_used_percent,
            ha_used_percent,
            "Used capacity percentage check failed.")
        assert_utils.assert_equals(
            csm_unit, 'BYTES', "Capacity unit check failed.")
        self.log.info("Capacity reported by CSM matched HCTL response.")
        self.log.info("Login with manage user and GET Alerts . . .")
        response = self.csm_alerts.get_alerts(login_as="csm_user_manage")
        self.log.info("Verifying the status code %s and response %s returned",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Manage user and Get alerts completed")
        self.log.info("Step 2: View CSM Audit logs sorted by timestamp")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "timestamp",
            "dir": "asc"}
        audit_log_show_response = self.audit_logs.audit_logs_csm_show(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_show_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log show request returned status: %s",
            audit_log_show_response.status_code)
        all_timestamp = [temp_timestamp['timestamp']
                         for temp_timestamp in audit_log_show_response.json()['logs']]
        self.log.info(all_timestamp)
        assert_utils.assert_equals(
            sorted(all_timestamp),
            all_timestamp,
            "Failed to sort audit log by timestamp.")
        self.log.info("Step 3: Download CSM Audit logs sorted by timestamp")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "timestamp",
            "dir": "asc"}
        audit_log_download_response = self.audit_logs.audit_logs_csm_download(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_download_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log show request returned status: %s",
            audit_log_download_response.status_code)
        # TODO: "Verification of sort audit logs is blocked refer EOS-24930,EOS-24931"
        self.log.info(
            "Verification of sort audit log for "
            "Download audit logs is blocked refer EOS-24930,EOS-24931")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Verification of sort audit logs is blocked refer EOS-24930,EOS-24931")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22335')
    def test_22335(self):
        """Test single sort by response code parameters on view, download operation on CSM audit log
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Test purpose: Verifying sort operation by response code parameters on "
                      "view, download operation on CSM audit log")
        data = self.csm_conf["test_22335"]["duration"]
        end_time = int(time.time())
        start_time = end_time - data
        self.log.info("Step 1: Try to login using invalid credentials")
        username = self.csm_conf["test_22335"]["username"]
        password = self.csm_conf["test_22335"]["password"]
        status_code = self.csm_conf["test_22335"]["status_code"]
        self.log.info("Verifying with incorrect password")
        response = self.csm_user.custom_rest_login(
            username=self.csm_user.config["csm_admin_user"]["username"],
            password=password)
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Verified with incorrect password")
        self.log.info("Verifying with incorrect username")
        response = self.csm_user.custom_rest_login(
            username=username, password=self.csm_user.config[
                "csm_admin_user"]["password"])
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Verified with incorrect username")
        self.log.info("Step 2: Show audit logs returns 404 error code on invalid component name")
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          expected_status_code=404,
                                                          validate_expected_response=False,
                                                          invalid_component=True)
        self.log.info("Step 3: Send no value for sort_by param in valid request")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_by="", return_actual_response=True)
        self.log.info("Verifying response code 400 was returned")
        assert response.status_code == const.BAD_REQUEST
        self.log.info("Verified that status code %s was returned", response.status_code)
        self.log.info("Step 4: View CSM Audit logs sorted by response code")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "response_code",
            "dir": "asc"}
        audit_log_show_response = self.audit_logs.audit_logs_csm_show(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_show_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log show request returned status: %s",
            audit_log_show_response.status_code)
        all_response_code = [temp_response_code['response_code']
                             for temp_response_code in audit_log_show_response.json()['logs']]
        self.log.info(all_response_code)
        assert_utils.assert_equals(
            sorted(all_response_code),
            all_response_code,
            "Failed to sort audit log by response_code.")
        self.log.info("Step 4: Download CSM Audit logs sorted by response code")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "response_code",
            "dir": "asc"}
        audit_log_download_response = self.audit_logs.audit_logs_csm_download(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_download_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log download request returned status: %s",
            audit_log_download_response.status_code)
        # TODO: "Verification of sort download audit logs is blocked refer EOS-24930,EOS-24931"
        self.log.info(
            "Verification of sort audit log for "
            "Download audit logs is blocked refer EOS-24930,EOS-24931")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Verification of sort audit logs is blocked refer EOS-24930,EOS-24931")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22336')
    def test_22336(self):
        """Test filter by user parameter on view , download operation on CSM audit log
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Test purpose: Verifying sort operation by user parameters on view,"
            " download operation on CSM audit log")
        data = self.csm_conf["test_22336"]["duration"]
        end_time = int(time.time())
        start_time = end_time - data
        self.log.info("Step 1: Login using manage user and perform GET users operation")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("Verified that status code %s was returned"
                      "for the get request for csm manage user", response.status_code)
        self.log.info("Step 2: Login using monitor user and perform GET users operation")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("Verified that status code %s was returned"
                      "for the get request for csm monitor user", response.status_code)
        self.log.info("Step 3: Login using S3 account and perform GET operation")
        self.log.info("Creating IAM user")
        response = self.iam_user.create_and_verify_iam_user_response_code()
        print(response)
        self.log.info("Verifying status code returned is 200 and response is not null")
        response = self.iam_user.list_iam_users(login_as="s3account_user")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info("Verified that status code %s was returned"
                      "for the get request for csm s3account user", response.status_code)
        self.log.info("Step 4: View CSM Audit logs filtered by user")
        params = {
            "start_date": start_time,
            "end_date": end_time,
            "sortby": "user",
            "dir": "asc",
            "filter": "{user=csm_user_manage}"}
        audit_log_show_response = self.audit_logs.audit_logs_csm_show(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_show_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified that audit log show request returned status: %s",
            audit_log_show_response.status_code)
        all_user = [usr['user']
                    for usr in audit_log_show_response.json()['logs']]
        self.log.info(all_user)
        assert_utils.assert_equals(
            sorted(all_user),
            all_user,
            "Failed to sort audit log by user.")
        # TODO: "Verification of sort and filter audit logs is blocked refer EOS-24930,EOS-24931"
        # self.log.info("Step 5: Download CSM Audit logs filtered by user")
        # params = {
        #     "start_date": start_time,
        #     "end_date": end_time,
        #     "sortby": "user",
        #     "dir": "asc",
        #     "filter": "{user=csm_user_manage}"}
        # audit_log_download_response = self.audit_logs.audit_logs_csm_download(
        #     params=params, invalid_component=False)
        # self.log.info("Verifying if success response was returned")
        # assert_utils.assert_equals(audit_log_download_response.status_code,
        #                            const.SUCCESS_STATUS)
        # self.log.info(
        #     "Verified that audit log download request returned status: %s",
        #     audit_log_download_response.status_code)
        self.log.info(
            "TODO: Verification of filter audit log for Download audit logs is blocked "
            "refer EOS-24930,EOS-24931")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-statements
    # pylint: disable-msg=too-many-branches
    @pytest.mark.skip(reason="Verification of sort audit logs is blocked refer EOS-24930,EOS-24931")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22337')
    def test_22337(self):
        """Test view, download operation on CSM and S3 audit log when 3rd Party services are down
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Test purpose: Verifying view and download operation on CSM and S3 audit logs when "
            "3rd party services are down")
        data = self.csm_conf["test_22337"]["duration"]
        self.log.info(
            "Step 1: Bring down rsyslog and elastic search services using systemctl stop command.")
        host = CMN_CFG["nodes"][0]["hostname"]
        uname = CMN_CFG["nodes"][0]["username"]
        passwd = CMN_CFG["nodes"][0]["password"]
        status, result = run_remote_cmd(commands.SYSTEM_CTL_STOP_CMD.format(
            "rsyslog"), hostname=host, username=uname, password=passwd, read_lines=True)
        assert status, f"Command failed with error\n{result}"
        status, result = run_remote_cmd(commands.SYSTEM_CTL_STOP_CMD.format(
            "elasticsearch"), hostname=host, username=uname, password=passwd, read_lines=True)
        assert status, f"Command failed with error\n{result}"
        self.log.info("Step 2: Create IAM user, manage user and monitor user")
        self.log.info("Creating IAM user")
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        self.log.info(
            "Verifying status code returned is 200 and response is not null")
        assert status, response
        for key, value in response.items():
            self.log.info("Verifying %s is not empty", key)
            assert value
        self.log.info("Verified that S3 account %s was successfully able to create IAM user: %s",
                      self.rest_iam_user.config["s3account_user"]["username"], response)
        self.log.info("Deleting IAM user")
        user_name = response['user_name']
        self.rest_iam_user.delete_iam_user(
            login_as="s3account_user", user=user_name)
        self.log.info("Creating csm user with manage role and deleting it")
        response = self.csm_user.create_csm_user(user_type="valid", user_role="manage")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        mgusername = response.json()["username"]
        mguser_id = response.json()["id"]
        self.log.info("Verified User %s got created successfully", mgusername)
        response = self.csm_user.delete_csm_user(mguser_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info("Creating csm user with monitor role and deleting it")
        response = self.csm_user.create_csm_user(user_type="valid", user_role="monitor")
        self.log.info("Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        musername = response.json()["username"]
        muser_id = response.json()["id"]
        self.log.info("Verified User %s got created successfully", musername)
        response = self.csm_user.delete_csm_user(muser_id)
        assert response.status_code == const.SUCCESS_STATUS, "User Deleted Successfully."
        self.log.info(
            "Step 2: create s3 user and bucket, perform some IO on bucket and delete this user "
            "and bucket")
        s3_user = self.s3_account_prefix.format(perf_counter_ns())
        s3_bkt = self.s3_bucket_prefix.format(perf_counter_ns())
        self.log.info("Create an S3 user.")
        resp = create_s3_acc_get_s3testlib(s3_user, self.s3_email_prefix.format(s3_user),
                                           self.s3acc_passwd)
        assert_utils.assert_true(resp[0], f"Failed to create s3 account, resp: {resp[1]}")
        s3_obj = resp[0]
        self.log.info("Login using above S3 account.")
        self.log.info("Perform the following operations using S3 login.")
        self.log.info("Create bucket")
        resp = s3_obj.create_bucket(s3_bkt)
        assert_utils.assert_true(resp[0], f"Failed to create s3 bucket, resp: {resp}")
        assert_utils.assert_equal(resp[1], s3_bkt,
                                  f"Failed to create s3 bucket, resp: {resp}")
        self.log.info("Perform IO on the created bucket")
        resp = perform_s3_io(s3_obj, s3_bkt, self.folder_path, obj_prefix="test_22337")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Delete the created bucket.")
        resp = s3_obj.delete_bucket(s3_bkt, force=True)
        assert_utils.assert_true(resp[0], f"Failed to delete s3 bucket, resp: {resp}")
        self.log.info("Delete the S3 account.")
        resp = self.rest_obj.delete_s3_account(s3_user)
        assert_utils.assert_true(resp[0], f"Failed to delete s3 user: {resp[1]}")
        self.log.info(
            "Step 3: Bring back rsyslog and elastic search services using systemctl start command.")
        status, result = run_remote_cmd(commands.SYSTEM_CTL_START_CMD.format(
            "rsyslog"), hostname=host, username=uname, password=passwd, read_lines=True)
        assert status, f"Command failed with error\n{result}"
        time.sleep(5)
        self.log.info("Waiting for sometime for rsyslog service to start")
        status, result = run_remote_cmd(commands.SYSTEM_CTL_START_CMD.format(
            "elasticsearch"), hostname=host, username=uname, password=passwd, read_lines=True)
        assert status, f"Command failed with error\n{result}"
        time.sleep(5)
        self.log.info("Waiting for sometime for elasticsearch service to start")
        self.log.info("Step 4: Check hctl status")
        self.log.info("Check that all the services are up in hctl.")
        test_cfg = PROV_CFG["system"]
        cmd = commands.MOTR_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        self.log.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["offline"], line, "Some services look offline.")
        self.log.info("Step 5: Check pcs status")
        self.log.info("Check that all services are up in pcs.")
        cmd = commands.PCS_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        self.log.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["stopped"], line, "Some services are not up.")
        self.log.info(
            "HCTL and PCS status is clean.")
        time.sleep(self.csm_conf["test_22337"]["delay"])
        self.log.info("Step 6: View and Download CSM audit log")
        end_time = int(time.time())
        start_time = end_time - data
        params = {"start_date": start_time, "end_date": end_time, "sortby": "user", "dir": "desc"}
        self.log.info("Sending audit log show request for start time: %s and end time: %s",
                      start_time, end_time)
        audit_log_show_response = self.audit_logs.audit_logs_csm_show(
            params=params, invalid_component=False)
        self.log.info("Verifying if success response was returned")
        assert_utils.assert_equals(audit_log_show_response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Verified that audit log show request returned status: %s",
                      audit_log_show_response.status_code)
        self.log.info("Searching new created manage user %s in csm audit logs", mgusername)
        resp = audit_log_show_response.json()
        response = self.audit_logs.verify_csm_audit_logs_contents(resp, mgusername)
        if False in response:
            self.log.error("%s user is not found in audit logs", mgusername)
        self.log.info("Searching new created monitor user %s in csm audit logs", musername)
        response = self.audit_logs.verify_csm_audit_logs_contents(resp, musername)
        if False in response:
            self.log.error("%s user is not found in audit logs", musername)
        self.log.info("Searching new created s3 user %s in csm audit logs", s3_user)
        response = self.audit_logs.verify_csm_audit_logs_contents(resp, s3_user)
        if False in response:
            self.log.error("%s user is not found in audit logs", s3_user)
        # TODO: "Verification of download audit logs is blocked refer EOS-24930,EOS-24931"
        self.log.info(
            "TODO: Verification of filter/sort audit log for Download audit logs is blocked "
            "refer EOS-24930,EOS-24931")
        # self.log.info("Sending audit log download request for start "
        #               "time: %s and end time: %s",
        #               start_time, end_time)
        # audit_log_download_response = self.audit_logs.audit_logs_csm_download(
        #     params=params, invalid_component=False)
        # self.log.info("Verifying if success response was returned")
        # assert_utils.assert_equals(audit_log_download_response.status_code,
        #                            const.SUCCESS_STATUS)
        # self.log.info("Verified that audit log download request returned status: %s",
        #               audit_log_download_response.status_code)
        self.log.info("Step 7: View and Download S3 audit log")
        end_time = int(time.time())
        start_time = end_time - data
        params = {"start_date": start_time, "end_date": end_time}
        self.log.info("Sending audit log show request for start time: %s and end time: %s",
                      start_time, end_time)
        audit_log_show_response = self.audit_logs.audit_logs_s3_show(
            params=params)
        resp = audit_log_show_response.json()
        self.log.info("Searching new created bucket %s in s3 audit logs", s3_bkt)
        response = self.audit_logs.verify_s3_audit_logs_contents(resp, s3_bkt)
        if False in response:
            self.log.error("bucket is not found in audit logs")
        self.log.info("Searching new created object %s in s3 audit logs", "test_22337")
        response = self.audit_logs.verify_s3_audit_logs_contents(resp, ["test_22337"])
        if False in response:
            self.log.error("object is not found in audit logs")
        # TODO: "Verification of download audit logs is blocked refer EOS-24246"
        self.log.info(
            "TODO: Verification of filter/sort audit log for Download audit logs is blocked "
            "refer EOS-24246")
        self.log.info("##### Test ended -  %s #####", test_case_name)
