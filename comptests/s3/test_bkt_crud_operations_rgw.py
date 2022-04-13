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

"""Test Bucket CRUD Operations."""

import logging
import time
import pytest

from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from config import S3_CFG
from libs.s3 import s3_test_lib

class TestRgwBucketCrudOperations:

    """Bucket CRUD Operations Test suite."""

    @classmethod
    def setup_class(cls):
        """Function to perform the setup ops for each test."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup testsuite operations.")
        cls.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.log.info("ENDED: Setup testsuite operations")

    @classmethod
    def teardown_class(cls):
        """Function will be invoked after completion of all test case.
           It will clean up resources which are getting created during test suite setup."""
        cls.log.info("STARTED: Teardown test suite operations.")
        del cls.s3_test_obj
        cls.log.info("ENDED: Teardown test suite operations.")

    def setup_method(self):
        """Function will be invoked prior to each test case.
           It will perform all prerequisite test steps if any."""
        self.log.info("STARTED: Setup operations")
        self.bucket_name = "bktwrkflow1-{}".format(time.perf_counter_ns())
        self.bucket_list = []
        self.log.info("ENDED: Setup operations")
        
    def teardown_method(self):
        """Function to perform the clean up for each test."""
        self.log.info("STARTED: Cleanup test operations.")
        bucket_list = self.s3_test_obj.bucket_list()[1]
        for bucket_name in self.bucket_list:
            if bucket_name in bucket_list:
                resp = self.s3_test_obj.delete_bucket(bucket_name, force=True)
                assert_utils.assert_true(resp[0], resp[1])
        del self.bucket_list
        self.log.info("ENDED: Cleanup test operations.")


    @pytest.mark.comp_s3
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36100")
    @CTFailOn(error_handler)
    def test_create_list_delete_1000_buckets(self):

        """Verification of max. no. of buckets(1000) user can create and then list and delete them
           TODO: User creation to be done using rgw rest api."""

        self.log.info(
            "STARTED: Verification of max. no. of buckets(1000) user can create and then list and delete them")
        self.log.info("Creating 1000 max buckets")
        resp1 = self.s3_test_obj.bucket_count()
        self.log.info(resp1)
        bkt_list = []
        for each in range(1000):
            bucket_name = "{0}{1}".format("bkttest-36100-", each)
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            bkt_list.append(bucket_name)
        self.log.info("Created 1000 buckets")
        self.log.info("Verifying that bucket is created")
        resp = self.s3_test_obj.bucket_count()
        self.log.info(resp)
        assert resp[0], resp[1]
        assert_utils.assert_equal(
            len(bkt_list), 1000, "failed to create 1000 buckets")
        self.log.info("Listing 1000 buckets")
        resp = self.s3_test_obj.bucket_list()
        self.log.info(resp)
        assert resp[0], resp[1]
        resp = self.s3_test_obj.delete_multiple_buckets(bkt_list)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp1[1])
        self.log.info("Verified that 1000 buckets are created")
        self.log.info("ENDED: Verification of max. no. of buckets(1000) user can create and then list and delete them")

    @pytest.mark.comp_s3
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36157")
    @CTFailOn(error_handler)
    def test_listbkt_bktname_3to63_chars_long(self):
        """List bucket with bucket name within range 3to63 chars long and  with less than 3 characters and more than 63 characters
           TODO: User creation to be done using rgw rest api."""

        self.log.info(
            "STARTED: List bucket with bucket name within range 3to63 chars long and with less than 3 characters and more than 63 characters")
        self.log.info(
            "Creating buckets")
        bkt_names = [
            "bkt",
            "a2",
            "bktworkflow-seagateeosbucket-36157-bktworkflow-seagateeosbucket",
            "bktworkflow-seagateeosbucket-36157-bktworkflow-seagateeosbucketsbktworkflow"
            "-seagateeosbucket"]
        for each_bucket in bkt_names:
            if len(each_bucket) > 2 and len(each_bucket) < 64:
                self.log.info("Creating bucket with name %s", each_bucket)
                resp = self.s3_test_obj.create_bucket(each_bucket)
                assert resp[0], resp[1]
                assert resp[1] == each_bucket, resp[1]
                self.log.info("Bucket is created with name %s", each_bucket)
                self.bucket_list.append(each_bucket)
            else:
                try:
                    self.log.info("Creating bucket with name %s", each_bucket)
                    resp = self.s3_test_obj.create_bucket(each_bucket)
                    #self.log.info("Bucket is created with name %s", each_bucket)
                    #self.bucket_list.append(each_bucket)
                    assert_utils.assert_false(resp[0], resp[1])
                except CTException as error:
                    self.log.info(error.message)
                    assert "InvalidBucketName" in error.message, error.message
                    self.log.info("Creation of bucket %s is failed", each_bucket)
        self.log.info("Listing buckets")
        resp = self.s3_test_obj.bucket_list()
        self.log.info(resp)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_list, resp[1]
        self.log.info(
            "ENDED: List bucket with bucket name within range 3to63 chars long and with less than 3 characters and more than 63 characters")

