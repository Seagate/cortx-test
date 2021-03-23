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
"""Tests Audit logs using REST API
"""
import time
import logging
import pytest
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_audit_logs import RestAuditLogs
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_s3user import RestS3user
from commons import configmanager
from commons.constants import Rest as const
from commons.utils import assert_utils
from commons import cortxlogging

class TestAuditLogs():
    """Audit logs Testsuite"""

    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setup...")
        cls.audit_logs = RestAuditLogs(component_csm="csm",
                                        component_s3="s3")
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
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_audit_logs.yaml")
        cls.log.info("Test setup initialized...")

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10733')
    def test_4918(self):
        """Test that s3 account and iam user don't have access to audit logs
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(
            params=params,
            expected_status_code=403,
            login_as="s3account_user",
            validate_expected_response=False,
            )
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10735')
    def test_4926(self):
        """Verify that API to download audit logs returns 404 error code on invalid component name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              expected_status_code=404,
                                                              validate_expected_response=False,
                                                              invalid_component=True)
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10736')
    def test_4925(self):
        """Verify that API to show audit logs returns 404 error code on invalid component name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          expected_status_code=404,
                                                          validate_expected_response=False,
                                                          invalid_component=True)
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10737')
    def test_4913(self):
        """Test that GET API returns audit logs in binary format for both csm and s3 components
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_s3_download(params=params,
                                                             validate_expected_response=True,
                                                             response_type=str
                                                             )
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              validate_expected_response=True,
                                                              response_type=str
                                                              )
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10738')
    def test_4914(self):
        """Test that API response of audit logs API for CSM component
        contain info reagrding specified parameters and in specified format.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          validate_expected_response=True
                                                          )
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10739')
    def test_4917(self):
        """Test that admin can download and see audit logs
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        params = {"start_date": self.start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          validate_expected_response=True
                                                          )
        assert self.audit_logs.verify_audit_logs_csm_download(params=params,
                                                              validate_expected_response=True,
                                                              response_type=str
                                                              )
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10741')
    def test_4919(self):
        """Test that audit log is returned for different time intervals
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
        start_time = self.end_time - ((4 * 24) * 60 * 60)
        params = {"start_date": start_time, "end_date": self.end_time}
        assert self.audit_logs.verify_audit_logs_csm_show(params=params,
                                                          validate_expected_response=True
                                                          )
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-10743')
    def test_4916(self):
        """Test that csm user(having manage or monitor rights) can download and see audit logs
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)
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
        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-12841')
    def test_4920(self):
        """Test that Verify that content of both 'show' and 'dowload' api is exactly same
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)

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

        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-15865')
    def test_4922(self):
        """
        Test that GET api returns audit logs for date range specified and total
        count should not exceed more than 10000
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)

        data = self.csm_conf["test_4922"]
        start_time = self.end_time - \
            ((data["end_date"] * data["hrs"]) * data["min"] * data["sec"])

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
        self.log.info("Count of records in audit logs is:%s",
            len(response.json()))

        self.log.info("Generating autdit logs for test purpose")
        if len(response.json()) < data["record_count"]:
            for i in range(len(response.json()), data["max_record_count"]):
                resp = self.csm_user.list_csm_single_user(
                    request_type="get",
                    expect_status_code=const.SUCCESS_STATUS,
                    user=self.audit_logs.config["csm_admin_user"]["username"],
                    return_actual_response=True)
                assert resp

        response = self.audit_logs.audit_logs_csm_show(params)
        self.log.info("Count of records in audit logs is:%s",
            len(response.json()))
        assert_utils.assert_equals(len(response.json()), data["record_count"])

        self.log.info(
            "Step 2: Verified that GET api returns records not more than 10000")

        self.log.info("##### Test ended -  %s #####",test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-16553')
    def test_4915(self):
        """
        Test that API response of audit logs for s3 component
        contain info regarding specified parameters and in specified format
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####",test_case_name)

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

        self.log.info("##### Test ended -  %s #####",test_case_name)
