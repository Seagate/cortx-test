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
from time import perf_counter_ns

import pytest
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER


class TestIamPolicy:
    """iam policy Test Suite."""

    # pylint:disable=attribute-defined-outside-init
    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """Setup method is called before/after each test in this test suite."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.iam_acc_name = "iam-policy-usr{}".format(perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestIamPolicyOperations")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("ENDED: Setup operations")
        yield
        self.log.info("STARTED: Teardown operations")
        if system_utils.path_exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32763')
    @CTFailOn(error_handler)
    def test_32763(self):
        """Create, List & Get IAM Policy."""
        self.log.info("STARTED: Create, List & Get IAM Policy.")
        self.log.info("Steps 1: Create policy by giving only required parameters."
                      " e.g., Description, PolicyName, PolicyDocument, Path, Tags.")
        self.log.info("Steps 2: List policy and make sure it is getting listed.")
        self.log.info("Steps 3: Get policy using ARN in step 1.")
        self.log.info("ENDED: Create, List & Get IAM Policy.")

    @pytest.mark.s3_ops
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
    @pytest.mark.tags('TEST-32766')
    @CTFailOn(error_handler)
    def test_32766(self):
        """Create IAM Policy using invalid value for required parameters."""
        self.log.info("STARTED: Create IAM Policy using invalid value for required parameters.")
        self.log.info("Step 1: Create policy by giving no parameters.")
        self.log.info("Step 2: Create policy by giving only PolicyName.")
        self.log.info("Step 3: Create policy by giving only PolicyDocument.")
        self.log.info("ENDED: Create IAM Policy using invalid value for required parameters.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32767')
    @CTFailOn(error_handler)
    def test_32767(self):
        """Create a policy that already exists."""
        self.log.info("STARTED: Create a policy that already exists.")
        self.log.info("Step 1: Create valid policy using PolicyName & PolicyDocument.")
        self.log.info("Step 2: List policy and make sure it is getting listed.")
        self.log.info("Step 3: Get policy using ARN in step 1.")
        self.log.info("Step 4: Create again a new policy using same PolicyName & PolicyDocument.")
        self.log.info("ENDED: Create a policy that already exists.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32768')
    @CTFailOn(error_handler)
    def test_32768(self):
        """Create IAM Policy beyond limits."""
        self.log.info("STARTED: Create IAM Policy beyond limits.")
        self.log.info("Step 1: Create valid IAM policies beyond Limits."
                      " (ToDo: Limit configuration action available to user)")
        self.log.info("ENDED: Create IAM Policy beyond limits.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32769')
    @CTFailOn(error_handler)
    def test_32769(self):
        """Create Policy using invalid policy document elements."""
        self.log.info("STARTED: Create Policy using invalid policy document elements.")
        self.log.info(
            "For all below steps, single value will be invalid, other will be valid values.")
        self.log.info("Step 1: Create policy using Version other than '2012 - 10 - 17'.")
        self.log.info("Step 2: Create policy using no Statement.")
        self.log.info("Step 3: Create policy using same Sid for 2 statements.")
        self.log.info("Step 4: Create policy using Effect other than Allow and Deny.")
        self.log.info("Step 5: Create policy using Action other than implemented actions.")
        self.log.info("Step 6: Create policy using Resource which is not present.")
        self.log.info("ENDED: Create Policy using invalid policy document elements.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32770')
    @CTFailOn(error_handler)
    def test_32770(self):
        """Create Policy using minimum policy elements."""
        self.log.info("STARTED: Create Policy using minimum policy elements.")
        self.log.info("Step 1: Create policy using Effect, Statement, Action & Resource.")
        self.log.info("Step 2: List policy and make sure it is getting listed.")
        self.log.info("Step 3: Get policy using ARN in step 1.")
        self.log.info("ENDED: Create Policy using minimum policy elements.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32771')
    @CTFailOn(error_handler)
    def test_32771(self):
        """Create Policy using required policy document elements missing."""
        self.log.info("STARTED: Create Policy using required policy document elements missing.")
        self.log.info("Step 1: Create policy using only Version.")
        self.log.info("Step 2: Create policy using only Sid.")
        self.log.info("Step 3: Create policy using only Effect.")
        self.log.info("Step 4: Create policy using only Action.")
        self.log.info("Step 5: Create policy using only Resource.")
        self.log.info("ENDED: Create Policy using required policy document elements missing.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32772')
    @CTFailOn(error_handler)
    def test_32772(self):
        """Create Policy using tags values."""
        self.log.info("STARTED: Create Policy using tags values.")
        self.log.info("Step 1: Create valid policy using Name, Tags, Policy Document with elements"
                      " Version, Effect, Action, Resource.")
        self.log.info("Step 2: List policy.")
        self.log.info("Step 3: Get policy using ARN in step 1.")
        self.log.info("ENDED: Create Policy using tags values.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32773')
    @CTFailOn(error_handler)
    def test_32773(self):
        """Get policy using invalid ARN."""
        self.log.info("STARTED: Get policy using invalid ARN.")
        self.log.info("Get IAM policy with invalid ARN.")
        self.log.info("ENDED: Get policy using invalid ARN.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32774')
    @CTFailOn(error_handler)
    def test_32774(self):
        """Delete policy using invalid ARN."""
        self.log.info("STARTED: Delete policy using invalid ARN.")
        self.log.info("Delete IAM policy with invalid ARN.")
        self.log.info("ENDED: Delete policy using invalid ARN.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32775')
    @CTFailOn(error_handler)
    def test_32775(self):
        """List IAM Policies"""
        self.log.info("STARTED: List IAM Policies.")
        self.log.info("Step 1: Create 10 IAM policies.")
        self.log.info("Step 2: List policy with MaxItems option set to 5.")
        self.log.info("ENDED: List IAM Policies.")
