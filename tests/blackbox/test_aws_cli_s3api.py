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
"""Test suite for awscli s3api operations"""


import logging
import time
import pytest
from commons import commands
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from commons.utils.system_utils import run_local_cmd, create_file


LOGGER = logging.getLogger(__name__)


class AwsCliS3Api:
    """Blackbox AWS CLI S3API Testsuite"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        LOGGER.info("STARTED : Setup operations at test suit level")
        cls.bucket_name = "blackboxs3bkt"
        LOGGER.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        LOGGER.info("STARTED : Setup operations at test function level")
        self.bucket_name = "-".join([self.bucket_name, int(time.time())])
        LOGGER.info("ENDED : Setup operations at test function level")

    @staticmethod
    def create_bucket_awscli(bucket_name: str):
        """
        Method to create a bucket using awscli
        :param bucket_name: Name of the bucket
        :return: True/False and output of command execution
        """
        LOGGER.info("Creating a bucket with name: %s", bucket_name)
        success_msg = "make_bucket: {}".format(bucket_name)
        response = run_local_cmd(
            cmd=commands.AWSCLI_CREATE_BUCKET.format(bucket_name))[1]
        LOGGER.info("Response returned: %s", response)
        if success_msg in response:
            return True, response

        return False, response

    @staticmethod
    def delete_bucket_awscli(bucket_name: str, force: bool = False):
        """
        Method to delete a bucket using awscli
        :param bucket_name: Name of the bucket
        :param force: True for forcefully deleting bucket containing objects
        :return: True/False and output of command execution
        """
        LOGGER.info("Deleting bucket: %s", bucket_name)
        success_msg = "remove_bucket: {}".format(bucket_name)
        delete_bkt_cmd = commands.AWSCLI_DELETE_BUCKET
        if force:
            delete_bkt_cmd = " ".join([delete_bkt_cmd, "--force"])
        response = run_local_cmd(cmd=delete_bkt_cmd.format(bucket_name))[1]
        LOGGER.info("Response returned: %s", response)
        if success_msg in response:
            return True, response

        return False, response

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        It is performing below operations as pre-requisites
            - Deletes bucket created during test execution
        """
        LOGGER.info("STARTED : Teardown operations at test function level")
        self.delete_bucket_awscli(self.bucket_name, force=True)
        LOGGER.info("ENDED : Teardown operations at test function level")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7113")
    @CTFailOn(error_handler)
    def test_2328(self):
        """
        create single bucket using aws cli
        """
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Successfully create single bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7114")
    @CTFailOn(error_handler)
    def test_2329(self):
        """
        Create multiple buckets using aws cli
        """
        buckets = []
        for i in range(2):
            buckets.append("-".join([self.bucket_name, i]))
        resp = self.create_bucket_awscli(bucket_name=" ".join(buckets))
        assert_utils.assert_equals(False, resp[0], resp[1])
        LOGGER.info("Failed to create multiple buckets at a time using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7115")
    @CTFailOn(error_handler)
    def test_2330(self):
        """
        list buckets using aws cli
        """
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(cmd=commands.AWSCLI_LIST_BUCKETS)
        assert_utils.assert_equals(True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        LOGGER.info("Successfully listed buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7116")
    @CTFailOn(error_handler)
    def test_2331(self):
        """
        max no of buckets supported using aws cli
        """
        max_buckets = 1000
        for i in range(max_buckets):
            bucket_name = f"{self.bucket_name}{i}"
            resp = self.create_bucket_awscli(bucket_name=bucket_name)
            assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Successfully created max no. of buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7117")
    @CTFailOn(error_handler)
    def test_2332(self):
        """
        delete empty bucket using aws cli
        """
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = self.delete_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Successfully deleted empty bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7118")
    @CTFailOn(error_handler)
    def test_2333(self):
        """
        delete bucket which has objects using aws cli
        """
        object_name = "blackboxs3obj"
        error_msg = "BucketNotEmpty"
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = create_file(fpath=object_name, count=1)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                object_name,
                self.bucket_name,
                object_name))
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = self.delete_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        LOGGER.info("Failed to delete bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7119")
    @CTFailOn(error_handler)
    def test_2334(self):
        """
        Verify HEAD bucket using aws client
        """
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_HEAD_BUCKET.format(
                self.bucket_name))
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Successfully verified head bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7120")
    @CTFailOn(error_handler)
    def test_2335(self):
        """
        Verification of bucket location using aws
        """
        location = '"LocationConstraint": "US"'
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_GET_BUCKET_LOCATION.format(
                self.bucket_name))
        assert_utils.assert_equals(True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], location)
        LOGGER.info("Successfully verified bucket location using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7121")
    @CTFailOn(error_handler)
    def test_2336(self):
        """
        create bucket using existing bucket name using aws cli
        """
        error_msg = "BucketAlreadyOwnedByYou"
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        LOGGER.info("Failed to create bucket using existing bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7122")
    @CTFailOn(error_handler)
    def test_2337(self):
        """
        Delete bucket forcefully which has objects using aws cli
        """
        object_name = "blackboxs3obj"
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = create_file(fpath=object_name, count=1)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                object_name,
                self.bucket_name,
                object_name))
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = self.delete_bucket_awscli(
            bucket_name=self.bucket_name, force=True)
        assert_utils.assert_equals(False, resp[0], resp[1])
        LOGGER.info("Successfully deleted bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7123")
    @CTFailOn(error_handler)
    def test_2338(self):
        """
        list objects in bucket using AWS
        """
        object_name = "blackboxs3obj"
        resp = self.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = create_file(fpath=object_name, count=1)
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                object_name,
                self.bucket_name,
                object_name))
        assert_utils.assert_equals(True, resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_equals(True, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], object_name)
        LOGGER.info("Successfully listed objects from bucket using awscli")
