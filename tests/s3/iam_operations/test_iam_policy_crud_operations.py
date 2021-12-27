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

"""iam user policy crud operations."""

import os
import logging
import json
from time import perf_counter_ns

import pytest
from config import CSM_CFG
from config.s3 import IAM_POLICY_CFG
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from libs.s3.iam_test_lib import IamTestLib
from libs.s3.iam_policy_test_lib import IamPolicyTestLib


class TestIamPolicy:
    """iam policy Test Suite."""

    # pylint:disable=attribute-defined-outside-init
    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """Setup method is called before/after each test in this test suite."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.iam_user = "iam-policy-usr{}".format(perf_counter_ns())
        self.iam_password = CSM_CFG["CliConfig"]["iam_user"]["password"]
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestIamPolicyOperations")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.iam_tobj = IamTestLib()
        response = self.iam_tobj.create_iam_user(self.iam_user, self.iam_password)
        assert_utils.assert_true(response[0], response[1])
        iam_access_key = response[1]['AccessKey']['AccessKeyId']
        iam_secret_key = response[1]['AccessKey']['SecretAccessKey']
        self.iam_policy_obj = IamPolicyTestLib(access_key=iam_access_key, secret_key=iam_secret_key)
        self.policy_arn = None
        self.log.info("ENDED: Setup operations")
        yield
        self.log.info("STARTED: Teardown operations")
        if self.policy_arn:
            response = self.iam_policy_obj.delete_policy(self.policy_arn)
            assert_utils.assert_true(response[0], response[1])
        response = self.iam_tobj.delete_iam_user(self.iam_user)
        assert_utils.assert_true(response[0], response[1])
        if system_utils.path_exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32763')
    @CTFailOn(error_handler)
    def test_32763(self):
        """Create, List & Get IAM Policy."""
        self.log.info("STARTED: Create, List & Get IAM Policy.")
        self.log.info("Steps 1: Create policy by giving only required parameters."
                      " e.g., Description, PolicyName, PolicyDocument, Path, Tags.")
        test_32763_cfg = IAM_POLICY_CFG["test_32763"]
        self.log.info(test_32763_cfg)
        response = self.iam_policy_obj.create_policy(
            policy_name=test_32763_cfg["policy_name"],
            policy_document=json.dumps(test_32763_cfg["policy_document"]),
            Path=test_32763_cfg["path"],
            Description=test_32763_cfg["description"],
            Tags=test_32763_cfg["tags"])
        assert_utils.assert_true(response[0], response[1])
        self.policy_arn = response[1]['Policy']['Arn']
        self.log.info("Steps 2: List policy and make sure it is getting listed.")
        response = self.iam_policy_obj.list_policies()
        assert_utils.assert_true(response[0], response[1])
        self.log.info("Steps 3: Get policy using ARN in step 1.")
        response = self.iam_policy_obj.get_policy(self.policy_arn)
        assert_utils.assert_true(response[0], response[1])
        self.log.info("ENDED: Create, List & Get IAM Policy.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32764')
    @CTFailOn(error_handler)
    def test_32764(self):
        """Create Policy using parameter value within limit."""
        self.log.info("STARTED: Create Policy using parameter value within limit.")
        self.log.info("Steps 1: The policy description maximum length constraints of 1000.")
        self.log.info("Steps 2: The policy Path maximum length constraints of 512")
        self.log.info("Steps 3: The PolicyDocument length constrains 6144.")
        self.log.info("Steps 4: The PolicyName length constrains 128")
        self.log.info("ENDED: Create Policy using parameter value within limit.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32765')
    @CTFailOn(error_handler)
    def test_32765(self):
        """Create Policy using parameter value beyond limit."""
        self.log.info("STARTED: Create Policy using parameter value beyond limit.")
        self.log.info("Steps 1: The policy description maximum length constraints of 1001.")
        self.log.info("Steps 2: The policy Path maximum length constraints of 513.")
        self.log.info("Steps 3: Create a IAM policy using invalid json policy document.")
        self.log.info("Steps 4: The PolicyDocument length constrains 6145.")
        self.log.info("Steps 5: The PolicyName length constrains 129.")
        self.log.info("ENDED: Create Policy using parameter value beyond limit.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32766')
    @CTFailOn(error_handler)
    def test_32766(self):
        """Create IAM Policy using invalid value for required parameters."""
        self.log.info("STARTED: Create IAM Policy using invalid value for required parameters.")
        self.log.info("Step 1: Create policy by giving no parameters.")
        test_32766_cfg = IAM_POLICY_CFG["test_32772"]
        try:
            response = self.iam_policy_obj.create_policy()
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            self.log.error(error.message)
        self.log.info("Step 2: Create policy by giving only PolicyName.")
        try:
            response = self.iam_policy_obj.create_policy(test_32766_cfg["policy_name"])
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            self.log.error(error.message)
        self.log.info("Step 3: Create policy by giving only PolicyDocument.")
        try:
            response = self.iam_policy_obj.create_policy(
                policy_document=json.dumps(test_32766_cfg["policy_document"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            self.log.error(error.message)
        self.log.info("ENDED: Create IAM Policy using invalid value for required parameters.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32767')
    @CTFailOn(error_handler)
    def test_32767(self):
        """Create a policy that already exists."""
        self.log.info("STARTED: Create a policy that already exists.")
        self.log.info("Step 1: Create valid policy using PolicyName & PolicyDocument.")
        test_32767_cfg = IAM_POLICY_CFG["test_32772"]
        response = self.iam_policy_obj.create_policy(
            test_32767_cfg["policy_name"], json.dumps(test_32767_cfg["policy_document"]))
        assert_utils.assert_true(response[0], response)
        self.policy_arn = response[1]['Policy']['Arn']
        self.log.info("Step 2: List policy and make sure it is getting listed.")
        response = self.iam_policy_obj.list_policies()
        assert_utils.assert_true(response[0], response)
        self.log.info("Step 3: Get policy using ARN in step 1.")
        response = self.iam_policy_obj.get_policy(self.policy_arn)
        assert_utils.assert_true(response[0], response)
        self.log.info("Step 4: Create again a new policy using same PolicyName & PolicyDocument.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32767_cfg["policy_name"], json.dumps(test_32767_cfg["policy_document"]))
            assert_utils.assert_false(response[0], response)
        except CTException as error:
            assert_utils.assert_in("An error", error.message)
        self.log.info("ENDED: Create a policy that already exists.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32768')
    @CTFailOn(error_handler)
    def test_32768(self):
        """Create IAM Policy beyond limits."""
        self.log.info("STARTED: Create IAM Policy beyond limits.")
        self.log.info("Step 1: Create valid IAM policies beyond Limits."
                      " (ToDo: Limit configuration action available to user)")
        self.log.info("ENDED: Create IAM Policy beyond limits.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32769')
    @CTFailOn(error_handler)
    def test_32769(self):
        """Create Policy using invalid policy document elements."""
        self.log.info("STARTED: Create Policy using invalid policy document elements.")
        self.log.info(
            "For all below steps, single value will be invalid, other will be valid values.")
        test_32769_cfg = IAM_POLICY_CFG["test_32769"]
        self.log.info("Step 1: Create policy using Version other than '2012 - 10 - 17'.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32769_cfg["policy_name"],
                json.dumps(test_32769_cfg["policy_document_invalid_version"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 2: Create policy using no Statement.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32769_cfg["policy_name"],
                json.dumps(test_32769_cfg["policy_document_no_statement"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 3: Create policy using same Sid for 2 statements.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32769_cfg["policy_name"],
                json.dumps(test_32769_cfg["policy_document_same_sid"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 4: Create policy using Effect other than Allow and Deny.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32769_cfg["policy_name"],
                json.dumps(test_32769_cfg["policy_document_invalid_effect"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 5: Create policy using Action other than implemented actions.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32769_cfg["policy_name"],
                json.dumps(test_32769_cfg["policy_document_invalid_action"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 6: Create policy using Resource which is not present.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32769_cfg["policy_name"],
                json.dumps(test_32769_cfg["policy_document_invalid_resource"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("ENDED: Create Policy using invalid policy document elements.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32770')
    @CTFailOn(error_handler)
    def test_32770(self):
        """Create Policy using minimum policy elements."""
        self.log.info("STARTED: Create Policy using minimum policy elements.")
        test_32770_cfg = IAM_POLICY_CFG["test_32770"]
        self.log.info("Step 1: Create policy using Effect, Statement, Action & Resource.")
        response = self.iam_policy_obj.create_policy(
            test_32770_cfg["policy_name"], json.dumps(test_32770_cfg["policy_document"]))
        assert_utils.assert_true(response[0], response)
        self.policy_arn = response[1]['Policy']['Arn']
        self.log.info("Step 2: List policy and make sure it is getting listed.")
        response = self.iam_policy_obj.list_policies()
        assert_utils.assert_true(response[0], response)
        self.log.info("Step 3: Get policy using ARN in step 1.")
        response = self.iam_policy_obj.get_policy(self.policy_arn)
        assert_utils.assert_true(response[0], response)
        self.log.info("ENDED: Create Policy using minimum policy elements.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32771')
    @CTFailOn(error_handler)
    def test_32771(self):
        """Create Policy using required policy document elements missing."""
        self.log.info("STARTED: Create Policy using required policy document elements missing.")
        test_32771_cfg = IAM_POLICY_CFG["test_32771"]
        self.log.info("Step 1: Create policy using only Version.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32771_cfg["policy_name"],
                json.dumps(test_32771_cfg["policy_document_version"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 2: Create policy using only Sid.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32771_cfg["policy_name"], json.dumps(test_32771_cfg["policy_document_sid"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 3: Create policy using only Effect.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32771_cfg["policy_name"], json.dumps(test_32771_cfg["policy_document_effect"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 4: Create policy using only Action.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32771_cfg["policy_name"], json.dumps(test_32771_cfg["policy_document_action"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("Step 5: Create policy using only Resource.")
        try:
            response = self.iam_policy_obj.create_policy(
                test_32771_cfg["policy_name"],
                json.dumps(test_32771_cfg["policy_document_resource"]))
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("ENDED: Create Policy using required policy document elements missing.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32772')
    @CTFailOn(error_handler)
    def test_32772(self):
        """Create Policy using tags values."""
        self.log.info("STARTED: Create Policy using tags values.")
        test_32772_cfg = IAM_POLICY_CFG["test_32772"]
        self.log.info("Step 1: Create valid policy using Name, Tags, Policy Document with elements"
                      " Version, Effect, Action, Resource.")
        response = self.iam_policy_obj.create_policy(
            test_32772_cfg["policy_name"], json.dumps(test_32772_cfg["policy_document"]))
        assert_utils.assert_true(response[0], response)
        self.policy_arn = response[1]['Policy']['Arn']
        self.log.info("Step 2: List policy.")
        response = self.iam_policy_obj.list_policies()
        assert_utils.assert_true(response[0], response)
        self.log.info("Step 3: Get policy using ARN in step 1.")
        response = self.iam_policy_obj.get_policy(self.policy_arn)
        assert_utils.assert_true(response[0], response)
        self.log.info("ENDED: Create Policy using tags values.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32773')
    @CTFailOn(error_handler)
    def test_32773(self):
        """Get policy using invalid ARN."""
        self.log.info("STARTED: Get policy using invalid ARN.")
        self.log.info("Get IAM policy with invalid ARN.")
        try:
            response = self.iam_policy_obj.get_policy(IAM_POLICY_CFG["invalid_arn"]["arn"])
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("ENDED: Delete policy using invalid ARN.")
        self.log.info("ENDED: Get policy using invalid ARN.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32774')
    @CTFailOn(error_handler)
    def test_32774(self):
        """Delete policy using invalid ARN."""
        self.log.info("STARTED: Delete policy using invalid ARN.")
        self.log.info("Delete IAM policy with invalid ARN.")
        try:
            response = self.iam_policy_obj.delete_policy(IAM_POLICY_CFG["invalid_arn"]["arn"])
            assert_utils.assert_false(response[0], response[1])
        except CTException as error:
            assert_utils.assert_in("InvalidPolicy", error.message)
        self.log.info("ENDED: Delete policy using invalid ARN.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_policy
    @pytest.mark.tags('TEST-32775')
    @CTFailOn(error_handler)
    def test_32775(self):
        """List IAM Policies"""
        self.log.info("STARTED: List IAM Policies.")
        self.log.info("Step 1: Create 10 IAM policies.")
        self.log.info("Step 2: List policy with MaxItems option set to 5.")
        self.log.info("ENDED: List IAM Policies.")
