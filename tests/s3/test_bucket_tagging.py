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

"""This file contains test related to Bucket Tagging."""

import os
import time
import logging
import pytest


from commons.constants import S3_ENGINE_RGW
from commons import error_messages as errmsg
from commons.params import TEST_DATA_FOLDER
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.s3_utils import assert_s3_err_msg
from config.s3 import S3_CFG
from config import CMN_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib


# pylint: disable-msg=too-many-public-methods
class TestBucketTagging:
    """Bucket tagging test suite."""

    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite and cleanup test.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: setup test suite operations.")
        self.s3_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_file = "obj_tag{}.txt"
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestBucketTagging")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("Test data directory path: %s", self.test_dir_path)
        self.test_file_path = os.path.join(
            self.test_dir_path, self.test_file.format(time.perf_counter_ns()))
        self.bucket_name = "tagbucket-{}".format(time.perf_counter_ns())
        self.log.info("ENDED: Test setup operations.")
        yield
        self.log.info("STARTED: Test teardown operations.")
        resp = self.s3_obj.bucket_list()[1]
        if self.bucket_name in resp:
            resp = self.s3_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp)
        self.log.info("ENDED: Test teardown operations.")

    @pytest.fixture(scope="function", autouse=False)
    def create_bucket(self):
        """Create bucket for test-cases"""
        self.log.info("Creating a bucket: %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Created a bucket: %s ", self.bucket_name)

    @pytest.mark.sanity
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5514")
    @CTFailOn(error_handler)
    def test_2432(self):
        """Verify PUT Bucket tagging."""
        self.log.info("STARTED: Verify PUT Bucket tagging")
        self.log.info("Step 1: Setting tag for bucket")
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testval")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for bucket")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][0]["Key"], f"testkey{0}", f"testkey{0}")
        assert_utils.assert_equal(resp[1][0]["Value"], f"testval{0}", f"testval{0}")
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: Verify PUT Bucket tagging")

    @pytest.mark.sanity
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5517")
    @CTFailOn(error_handler)
    def test_2433(self):
        """Verify GET Bucket tagging."""
        self.log.info("STARTED: Verify GET Bucket tagging")
        self.log.info("Step 1: Setting tag for a bucket")
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testval")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][0]["Key"], f"testkey{0}", f"testkey{0}")
        assert_utils.assert_equal(resp[1][0]["Value"], f"testval{0}", f"testval{0}")
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: Verify GET Bucket tagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5519")
    @CTFailOn(error_handler)
    def test_2434(self):
        """Verify DELETE Bucket tagging."""
        self.log.info("STARTED: Verify DELETE Bucket tagging")
        self.log.info("Step 1: Setting tag for a bucket")
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testval")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket")
        self.log.info("Step 3: Deleting tag of a bucket")
        resp = self.tag_obj.delete_bucket_tagging(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Deleted tag of a bucket")
        self.log.info("Step 4: Retrieving tag of same bucket")
        try:
            resp = self.tag_obj.get_bucket_tags(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_utils.assert_in(errmsg.S3_BKT_SET_TAG_ERR, str(error.message), error.message)
        self.log.info("Step 4: Retrieving bucket tag failed with NoSuchTagSetError")
        self.log.info("ENDED: Verify DELETE Bucket tagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5533")
    @CTFailOn(error_handler)
    def test_2435(self):
        """Create a tag whose key is up to 128 Unicode characters in length."""
        self.log.info(
            "STARTED: Create a tag whose key is up to 128 Unicode "
            "characters in length")
        self.log.info("Step 1: Setting tag for a bucket")
        resp = self.tag_obj.set_bucket_tag(
            self.bucket_name,
            "organizationCreateatagwhosekeyisupto128UnicodecharactersinlengtCreateatagwhosekey"
            "isupto128Unicodecharacterslengthshouldbe128cha",
            "testvalue")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket")
        self.log.info("Step 2: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        tag_key = f"organizationCreateatagwhosekeyisupto128UnicodecharactersinlengtCreateatag" \
            f"whosekeyisupto128Unicodecharacterslengthshouldbe128cha{0}"
        assert_utils.assert_equal(resp[1][0]["Key"], tag_key, tag_key)
        assert_utils.assert_equal(resp[1][0]["Value"], f"testvalue{0}", f"testvalue{0}")
        self.log.info("Step 2: Retrieved tag of a bucket")
        self.log.info("ENDED: Create a tag whose key is up to 128 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5534")
    @CTFailOn(error_handler)
    def test_2436(self):
        """
        Create a tag whose key is more than 128 Unicode characters in length.

        This is negative testing
        """
        self.log.info(
            "STARTED: Create a tag whose key is more than 128 Unicode characters in length")
        self.log.info("Step 1: Setting tag for a bucket")
        try:
            resp = self.tag_obj.set_bucket_tag(
                self.bucket_name,
                "organizationCreateatagwhosekeyisupto128UnicodecharactersinlengtCreateatagwhose"
                "keyisupto128Unicodecharacterslengthshouldbe128char",
                "testvalue")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_s3_err_msg(errmsg.S3_RGW_BKT_INVALID_TAG_ERR,
                              errmsg.S3_CORTX_BKT_INVALID_TAG_ERR,
                              CMN_CFG["s3_engine"], error)
        self.log.info("Step 2: Setting tag for a bucket failed with InvalidTag Error")
        self.log.info(
            "ENDED: Create a tag whose key is more than 128 Unicode "
            "characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5535")
    @CTFailOn(error_handler)
    def test_2437(self):
        """Create a tag having values up to 256 Unicode characters in length."""
        self.log.info(
            "STARTED: Create a tag having values up to 256 Unicode "
            "characters in length")
        self.log.info("Step 1: Setting tag for a bucket")
        resp = self.tag_obj.set_bucket_tag(
            self.bucket_name,
            "testkey",
            "organizationCreateatagwhosekeyisupto128UnicodecharactersinlengtCreateatagwhosekey"
            "isupto128Unicodecharacterslengthshouldbe128charorganizationCreateatagwhosekey"
            "isupto128UnicodecharactersinlengtCreateatagwhosekeyisupto128Unicodecharacters"
            "lengthshouldbe128cha")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        tag_value = f"organizationCreateatagwhosekeyisupto128UnicodecharactersinlengtCreateatag" \
            f"whosekeyisupto128Unicodecharacterslengthshouldbe128charorganizationCreateatagwhose" \
            f"keyisupto128UnicodecharactersinlengtCreateatagwhosekeyisupto128Unicodecharacters" \
            f"lengthshouldbe128cha{0}"
        assert_utils.assert_equal(resp[1][0]["Key"], f"testkey{0}", f"testkey{0}")
        assert_utils.assert_equal(resp[1][0]["Value"], tag_value, tag_value)
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: Create a tag having values up to 256 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5536")
    @CTFailOn(error_handler)
    def test_2438(self):
        """
        Create a tag having values more than 512 Unicode characters in length.

        info - This is negative testing
        """
        self.log.info(
            "STARTED: Create a tag having values more than 512 Unicode characters in length")
        self.log.info("Step 1: Setting tag for a bucket")
        try:
            resp = self.tag_obj.set_bucket_tag(
                self.bucket_name,
                "testkey",
                "caationCreateatagwhosekeyisupto128UnicodecharactersinlengtCreateatagwhosekeyis"
                "upto128Unicodecharacterslengthshouldbe128charorganaationCreateatagwhosekeyis"
                "upto128UnicodecharactersinlengtCreateatagwhosekeyisupto128Unicodecharacterslength"
                "shouldbe128charorganaationCreateatagwhosekeyisupto128Unicodecharactersinlengt"
                "Createatagwhosekeyisupto128Unicodecharacterslengthshouldbe128charorgaaation"
                "Createatagwhosekeyisupto128UnicodecharactersinlengtCreateatagwhosekeyisupto128"
                "Unicodecharacterslengthshouldbe128charorgaaaaaa")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_s3_err_msg(errmsg.S3_RGW_BKT_INVALID_TAG_ERR,
                              errmsg.S3_CORTX_BKT_INVALID_TAG_ERR,
                              CMN_CFG["s3_engine"], error)
            self.log.info(
                "Step 2: Setting tag for a bucket failed with %s", error.message)
        self.log.info(
            "ENDED: Create a tag having values more than 512 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.regression
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5528")
    @CTFailOn(error_handler)
    def test_2439(self):
        """Create Bucket tags, up to 50."""
        self.log.info("STARTED: Create Bucket tags, up to 50")
        self.log.info("Step 1: Setting %s tags for a bucket", self.bucket_name)
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testval", 50)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: %d tags are set for a bucket", 50)
        self.log.info("Step 3: Retrieving tags of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        sorted_tags = sorted(resp[1], key=lambda x: int(x["Key"][len("testkey"):]))
        self.log.info(sorted_tags)
        assert_utils.assert_true(resp[0], resp[1])
        for num in range(50):
            assert_utils.assert_equal(
                sorted_tags[num]["Key"], f"testkey{num}", f"testkey{num}")
            assert_utils.assert_equal(
                sorted_tags[num]["Value"], f"testval{num}", f"testval{num}")
        self.log.info("Step 3: Retrieved tags of a bucket")
        self.log.info("ENDED: Create Bucket tags, up to 50")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5529")
    @CTFailOn(error_handler)
    def test_2440(self):
        """Create Bucket tags, more than 50."""
        self.log.info("STARTED: Create Bucket tags, more than 50")
        self.log.info("Step 1: Setting %d tags for a bucket", 51)
        try:
            resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testval", 51)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_s3_err_msg(errmsg.S3_RGW_BKT_INVALID_TAG_ERR,
                              errmsg.S3_CORTX_BKT_INVALID_TAG_ERR,
                              CMN_CFG["s3_engine"], error)
            self.log.info(
                "Setting %d tags for a bucket failed with %s", 51, error.message)
        self.log.info("ENDED: Create Bucket tags, more than 50")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5521")
    @CTFailOn(error_handler)
    def test_2441(self):
        """Verify bucket Tag Keys with case sensitive labels."""
        self.log.info("STARTED: Verify bucket Tag Keys with case sensitive labels")
        self.log.info("Step 1: Setting tag for a bucket with case sensitive tag keys")
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "TESTKEY", "testval")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket with case sensitive tag keys")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][0]["Key"], f"TESTKEY{0}", f"TESTKEY{0}")
        assert_utils.assert_equal(resp[1][0]["Value"], f"testval{0}", f"testval{0}")
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: Verify bucket Tag Keys with case sensitive labels")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5520")
    @CTFailOn(error_handler)
    def test_2442(self):
        """Verify bucket tag Values with case sensitive labels."""
        self.log.info("STARTED: Verify bucket tag Values with case sensitive labels")
        self.log.info("Step 1: Setting tag for a bucket with case sensitive tag values")
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "TESTVALUE")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket with case sensitive tag values")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][0]["Key"], f"testkey{0}", f"testkey{0}")
        assert_utils.assert_equal(resp[1][0]["Value"], f"TESTVALUE{0}", f"TESTVALUE{0}")
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: Verify bucket tag Values with case sensitive labels")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5526")
    @CTFailOn(error_handler)
    def test_2443(self):
        """Create multiple tags with tag keys having special characters."""
        self.log.info("STARTED: Create multiple tags with tag keys having special characters")
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            lst_special_chars = [
                                "~", "`", "!", "@", "#", "$",
                                "%", "^", "&", "*", "(", ")",
                                "-", "_", "+", "=", ";", ":",
                                "|", "\\", ":", ";", "\"", "\'",
                                "<", ",", ">", ".", "?", "\/"
                                ]
        else:
            lst_special_chars = ["+", "-", "=", ".", "_", ":"]
        self.log.info("Step 1: Setting multiple tags with tag keys having special characters")
        for char in lst_special_chars:
            tag_key = f"{char}key{char}"
            resp = self.tag_obj.set_bucket_tag(self.bucket_name, tag_key, "testval")
            time.sleep(S3_CFG["sync_delay"])
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.tag_obj.get_bucket_tags(self.bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            for tags in resp[1]:
                if tag_key in tags["Key"]:
                    resp[1][0] = tags
            assert_utils.assert_equal(resp[1][0]["Key"], f"{tag_key}{0}", f"{tag_key}{0}")
            assert_utils.assert_equal(resp[1][0]["Value"], f"testval{0}", f"testval{0}")
        self.log.info("Step 2: Set multiple tags with tag keys having special characters")
        self.log.info("ENDED: Create multiple tags with tag keys having special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5527")
    @CTFailOn(error_handler)
    def test_2444(self):
        """Create multiple tags with tag keys having invalid special characters."""
        self.log.info(
            "STARTED: Create multiple tags with tag keys having invalid special characters")
        self.log.info(
            "Step 1: Setting tags for a bucket with tag keys having invalid special characters")
        for char in ["?", "*", "!", "@", "#"]:
            key = f"{char}key{char}"
            try:
                resp = self.tag_obj.set_bucket_tag(self.bucket_name, key, "testval")
                assert_utils.assert_false(resp[0], resp[1])
            except CTException as error:
                self.log.info(error)
                assert_s3_err_msg(errmsg.S3_RGW_BKT_INVALID_TAG_ERR,
                                  errmsg.S3_CORTX_BKT_INVALID_TAG_ERR,
                                  CMN_CFG["s3_engine"], error)
        self.log.info("Step 2: Could not set tags for a bucket with tag keys "
                      "having invalid special characters")
        self.log.info("ENDED: Create multiple tags with tag keys having"
                      " invalid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5524")
    @CTFailOn(error_handler)
    def test_2445(self):
        """Create multiple tags with tag values having invalid special character."""
        self.log.info("STARTED: Create multiple tags with tag values having "
                      "invalid special character")
        self.log.info("Step 1: Setting multiple tags with tag values having "
                      "invalid special character")
        for char in ["?", "*", "!", "@", "#"]:
            value = f"{char}val{char}"
            try:
                resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", value)
                assert_utils.assert_false(resp[0], resp[1])
            except CTException as error:
                self.log.info(error)
                assert_utils.assert_in(errmsg.S3_BKT_INVALID_TAG_ERR, str(error.message),
                                       error.message)
        self.log.info("Step 2: Could not set multiple tags with tag values"
                      " having invalid special character")
        self.log.info("ENDED: Create multiple tags with tag values having "
                      "invalid special character")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5531")
    @CTFailOn(error_handler)
    def test_2446(self):
        """Create bucket tags with duplicate keys."""
        self.log.info("STARTED: Create bucket tags with duplicate keys")
        self.log.info("Step 1: Setting bucket tags with duplicate keys")
        try:
            resp = self.tag_obj.set_bucket_tag_duplicate_keys(
                self.bucket_name, "testkey", "testval")
            if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
                assert_utils.assert_true(resp[0], resp[1])
            else:
                assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
                self.log.error(
                    "Step 2: Setting bucket tags with duplicate keys failed with %s",
                    error.message)
            else:
                assert_utils.assert_in(errmsg.MALFORMED_XML_ERR, str(error.message), error.message)
                self.log.info(
                    "Step 2: Setting bucket tags with duplicate keys failed with %s",
                    "   MalformedXML")
        self.log.info("ENDED: Create bucket tags with duplicate keys")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5512")
    @CTFailOn(error_handler)
    def test_2447(self):
        """verify values in a tag set should be unique."""
        self.log.info("STARTED: verify values in a tag set should be unique")
        self.log.info("Step 1: Setting bucket tags with unique tag values")
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testvalue", 2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testvalue", 2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Set bucket tags with unique tag values")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for num in range(2):
            assert_utils.assert_equal(
                resp[1][num]["Key"], f"testkey{num}", f"testkey{num}")
            assert_utils.assert_equal(
                resp[1][num]["Value"], f"testvalue{num}", f"testvalue{num}")
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: verify values in a tag set should be unique")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-5530")
    @CTFailOn(error_handler)
    def test_2448(self):
        """Create bucket tags with invalid special characters."""
        self.log.info("STARTED: Create bucket tags with invalid "
                      "(characters outside the allowed set) special characters")
        self.log.info(
            "Step 1: Setting a bucket tag with invalid special characters")
        resp = self.tag_obj.set_bucket_tag_invalid_char(self.bucket_name, "testkey", "testvalue")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Set a bucket tag with invalid special characters")
        self.log.info("Step 3: Retrieving tag of a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Retrieved tag of a bucket")
        self.log.info("ENDED: Create bucket tags with invalid "
                      "(characters outside the allowed set) special characters")

    # pylint: disable-msg=too-many-statements
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.tags("TEST-5523")
    @CTFailOn(error_handler)
    def test_2449(self):
        """Delete Bucket having tags associated with Bucket and its Objects."""
        self.log.info(
            "STARTED: Delete Bucket having tags associated with Bucket and its Objects")
        obj_name = "{}{}".format("tagobj2449", time.perf_counter_ns())
        self.log.info(
            "Step 1: Creating a bucket %s and uploading an object %s",
            self.bucket_name, obj_name)
        resp = self.s3_obj.create_bucket_put_object(
            self.bucket_name, obj_name, self.test_file_path, 1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1:  Created a bucket %s and uploaded an object %s",
            self.bucket_name, obj_name)
        self.log.info("Step 2: Setting tag for a bucket %s", self.bucket_name)
        resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testval")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Tag is set for a bucket %s", self.bucket_name)
        self.log.info("Step 3: Setting tag for an object %s", obj_name)
        resp = self.tag_obj.set_object_tag(
            self.bucket_name, obj_name, "testobjkey", "testobjvalue", tag_count=2)
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(S3_CFG["sync_delay"])
        self.log.info("Step 3: Set tag for an object %s", obj_name)
        self.log.info("Step 4: Verifying tag is set for a bucket")
        resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][0]["Key"], f"testkey{1 - 1}", f"testkey{1 - 1}")
        assert_utils.assert_equal(resp[1][0]["Value"], f"testval{1 - 1}", f"testval{1 - 1}")
        self.log.info("Step 4: Verified that tag is set for a bucket successfully")
        self.log.info("Step 5: Verifying tag is set for an object")
        resp = self.tag_obj.get_object_tags(self.bucket_name, obj_name)
        assert_utils.assert_true(resp[0], resp[1])
        for num in range(2):
            assert_utils.assert_equal(resp[1][num]["Key"], f"testobjkey{num}", f"testobjkey{num}")
            assert_utils.assert_equal(
                resp[1][num]["Value"], f"testobjvalue{num}", f"testobjvalue{num}")
        self.log.info("Step 5: Verified tag is set for an object")
        self.log.info("Step 6: Deleting a bucket")
        resp = self.s3_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Retrieving tag of a bucket")
        try:
            resp = self.tag_obj.get_bucket_tags(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 7: Retrieving tag of a bucket failed with NoSuchBucket")
        self.log.info("Step 8: Retrieving tag of an object")
        try:
            resp = self.tag_obj.get_object_tags(self.bucket_name, obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 8: Retrieving tag of an object failed with NoSuchBucket")
        self.log.info("ENDED: Delete Bucket having tags associated with Bucket and its Objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.tags("TEST-5522")
    @CTFailOn(error_handler)
    def test_2450(self):
        """Verify user can create max no of buckets with max no of tags per bucket."""
        self.log.info("STARTED: Verification of max. no. of Buckets user"
                      " can create with max no. of tags per Bucket")
        buckets = []
        for i in range(100):
            bucket_name = "{}-{}".format(self.bucket_name, str(i))
            resp = self.s3_obj.create_bucket(bucket_name)
            assert_utils.assert_is_not_none(resp[0], resp[1])
            assert_utils.assert_equal(bucket_name, resp[1], resp[1])
            buckets.append(bucket_name)
        for bucket in buckets:
            resp = self.tag_obj.set_bucket_tag(
                bucket, "testkey", "testval", 50)
            assert_utils.assert_is_not_none(resp[0], resp[1])
            resp = self.tag_obj.get_bucket_tags(bucket)
            assert_utils.assert_is_not_none(resp[0], resp[1])
        self.log.debug(buckets)
        self.log.debug("Total buckets : %d", len(buckets))
        status, resp = self.s3_obj.delete_multiple_buckets(buckets)
        assert_utils.assert_true(status, resp)
        self.log.info("ENDED: Verification of max. no. of Buckets user can "
                      "create with max no. of tags per Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.tags("TEST-5513")
    @CTFailOn(error_handler)
    def test_2451(self):
        """Verify PUT bucket tagging to non-existing bucket."""
        self.log.info("STARTED: Verify PUT bucket tagging to non-existing bucket")
        self.log.info("Step 1: Setting a tag for non existing bucket: %s", self.bucket_name)
        try:
            resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testvalue")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.exception(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 1: Setting a tag for non existing bucket failed with: NoSuchBucket")
        self.log.info("Step 2: Retrieving tag of non existing bucket")
        try:
            resp = self.tag_obj.get_bucket_tags(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.exception(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 2: Retrieved tag of non existing bucket failed with NoSuchBucket")
        self.log.info(
            "Step 2: Verified PUT and GET tag of non existing bucket failed with NoSuchBucket")
        self.log.info("ENDED: Verify PUT bucket tagging to non-existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.tags("TEST-5516")
    @CTFailOn(error_handler)
    def test_2452(self):
        """verify GET bucket tagging to non-existing bucket."""
        self.log.info(
            "STARTED: Verify GET bucket tagging to non-existing bucket")
        self.log.info("Step 1: Retrieving tag of non existing bucket")
        try:
            resp = self.tag_obj.get_bucket_tags(self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.exception(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 1: Retrieved tag of non existing bucket failed with NoSuchBucket")
        self.log.info("ENDED: Verify GET bucket tagging to non-existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.tags("TEST-5518")
    @CTFailOn(error_handler)
    def test_2453(self):
        """verify DELETE bucket tagging to non-existing bucket."""
        self.log.info("STARTED: Verify DELETE bucket tagging to non-existing bucket")
        self.log.info("Step 1: Setting tag for non existing bucket")
        try:
            resp = self.tag_obj.set_bucket_tag(self.bucket_name, "testkey", "testvalue")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 1: Setting tag for non existing bucket failed")
        self.log.info("Step 2: Deleting tag of a non existing bucket")
        try:
            resp = self.tag_obj.delete_bucket_tagging(
                self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_utils.assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(error.message), error.message)
        self.log.info("Step 2: Deleting tag of a non existing bucket failed with NoSuchBucket")
        self.log.info("ENDED: Verify DELETE bucket tagging to non-existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-43486")
    def test_43486(self):
        """Create bucket tags with encoded k:v pair with base64 encoding."""
        self.log.info("STARTED: Create bucket tags with encoded k:v with base64 encoding")
        self.log.info("Step 1: Setting a bucket tag with encoded key-value pair")
        set_resp = self.tag_obj.set_encoded_tag_values(self.bucket_name, encoding_type = "base64")
        assert_utils.assert_true(set_resp[0], set_resp[1])
        self.log.info("Step 2: Set a bucket tag with encoded special characters")
        self.log.info("Step 3: Retrieving tag of a bucket")
        put_resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        assert_utils.assert_equal(set_resp[2][0]["Key"], put_resp[1][0]["Key"],
                                  put_resp[1][0]["Key"])
        assert_utils.assert_equal(set_resp[2][0]["Value"], put_resp[1][0]["Value"],
                                  put_resp[1][0]["Value"])
        self.log.info("Step 3: Retrieved tag set of a bucket is valid")
        self.log.info("ENDED: Create bucket tags with encoded k:v with base64 encoding")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_tags
    @pytest.mark.usefixtures("create_bucket")
    @pytest.mark.tags("TEST-43488")
    def test_43488(self):
        """Create bucket tags with encoded k:v pair with utf-8 encoding."""
        self.log.info("STARTED: Create bucket tags with encoded k:v with utf-8 encoding")
        self.log.info("Step 1: Setting a bucket tag with encoded key-value pair")
        set_resp = self.tag_obj.set_encoded_tag_values(self.bucket_name, encoding_type = "utf-8")
        assert_utils.assert_true(set_resp[0], set_resp[1])
        self.log.info("Step 2: Set a bucket tag with encoded special characters")
        self.log.info("Step 3: Retrieving tag of a bucket")
        put_resp = self.tag_obj.get_bucket_tags(self.bucket_name)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        assert_utils.assert_equal(set_resp[2][0]["Key"], put_resp[1][0]["Key"],
                                  put_resp[1][0]["Key"])
        assert_utils.assert_equal(set_resp[2][0]["Value"], put_resp[1][0]["Value"],
                                  put_resp[1][0]["Value"])
        self.log.info("Step 3: Retrieved tag set of a bucket is valid")
        self.log.info("ENDED: Create bucket tags with encoded k:v with utf-8 encoding")
