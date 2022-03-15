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

"""List-Object-V2 test module."""

import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_awscli import AWScliS3api


class TestListObjectV2:
    """List-Object-V2 TestSuite."""

    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Setup method.

        Description: This function will be invoked prior to each test case. It will perform all
        prerequisite test steps if any and cleanup.
        """
        self.log = logging.getLogger(__name__)
        self.awscli_s3api_obj = AWScliS3api()
        self.s3_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.log.info("STARTED: setup test operations.")
        resp = system_utils.path_exists(S3_CFG["aws_config_path"])
        assert_utils.assert_true(
            resp, "config path not exists: {}".format(S3_CFG["aws_config_path"]))
        self.bucket_name = f"s3bkt-listobjectv2-{time.perf_counter_ns()}"
        self.object_prefix = "s3obj-listobjectv2"
        self.folder_path = os.path.join(
            TEST_DATA_FOLDER, f"TestObjectV2List{time.perf_counter_ns()}")
        if not system_utils.path_exists(self.folder_path):
            system_utils.make_dirs(self.folder_path)
        self.log.info("Test data path: %s", self.folder_path)
        self.log.info("ENDED: setup test operations.")
        yield
        self.log.info("STARTED: setup teardown operations.")
        if system_utils.path_exists(self.folder_path):
            system_utils.remove_dirs(self.folder_path)
        bktlist = self.s3_obj.bucket_list()[1]
        if self.bucket_name in bktlist:
            resp = self.s3_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: setup teardown operations.")

    def create_bucket_upload_folder(self, bucket_name) -> list:
        """
        Create a bucket using aws s3 mb upload folder in it.

        :param bucket_name: Name of the bucket.
        :return: Upload file response.
        """
        self.log.info("Create a bucket '%s' using aws s3 mb.", bucket_name)
        resp = self.awscli_s3api_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Upload few object in hierarchical and non-hierarchical list.")
        fpath_list = system_utils.create_dir_hierarchy_and_objects(
            self.folder_path, self.object_prefix, depth=3, obj_count=5)
        self.log.info("File list: %s", fpath_list)
        assert_utils.assert_equal(20, len(fpath_list), "Failed to create hierarchy.")
        resp = self.awscli_s3api_obj.upload_directory(bucket_name, self.folder_path)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(len(fpath_list), len(resp[1]), "Failed to upload hierarchy.")

        return resp[1]

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-15187")
    @CTFailOn(error_handler)
    def test_15187(self):
        """Test to list the objects in the specified bucket using list-objects-v2."""
        self.log.info("START: Lists the objects in the specified bucket using list-objects-v2.")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info("Run list-objects-v2 to lists the objects in the specified bucket.")
        resp = self.awscli_s3api_obj.list_objects_v2(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("END: Lists the objects in the specified bucket using list-objects-v2.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-15188")
    @CTFailOn(error_handler)
    def test_15188(self):
        """Test list-objects-v2--delimiter options using aws s3api."""
        self.log.info("START: Test list-objects-v2--delimiter options using aws s3api.")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info("Run list-objects-v2 --delimiter to group keys.")
        resp = self.awscli_s3api_obj.list_objects_v2(self.bucket_name, delimiter="//")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("END: Test list-objects-v2--delimiter options using aws s3api.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-15189")
    @CTFailOn(error_handler)
    def test_15189(self):
        """Test list-objects-v2 --prefix options using aws s3api."""
        self.log.info("START: Test list-objects-v2 --prefix options using aws s3api.")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info("Run list-objects-v2 --prefix to Limits the response to keys that begin "
                      "with the specified prefix.")
        resp = self.awscli_s3api_obj.list_objects_v2(self.bucket_name, prefix=self.object_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        for rdict in resp[1]["Contents"]:
            assert_utils.assert_in(self.object_prefix, rdict["Key"])
        self.log.info("END: Test list-objects-v2 --prefix options using aws s3api.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-15190")
    @CTFailOn(error_handler)
    def test_15190(self):
        """Test list-objects-v2 --delimiter and --prefix options using aws s3api."""
        self.log.info("START: list-objects-v2 --delimiter and --prefix options using aws s3api.")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info("Run list-objects-v2  --delimiter and --prefix to Limits the response to keys"
                      " that begin with the specified prefix and group similar key with delimiter")
        resp = self.awscli_s3api_obj.list_objects_v2(
            self.bucket_name, prefix=self.object_prefix, delimiter='//')
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("END: Test list-objects-v2 --delimiter and --prefix options using aws s3api.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-15191")
    @CTFailOn(error_handler)
    def test_15191(self):
        """Test list-objects-v2 --max-items and --starting-token option using aws s3api."""
        self.log.info("START: Test list-objects-v2 with --max-items and --starting-token options.")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 --max-items and --starting-token option for total number"
            " of items to return in the command's output and then token to specify where"
            " to start paginating. This is the NextToken from a previously truncated response.")
        resp = self.awscli_s3api_obj.list_objects_v2(
            self.bucket_name, prefix=self.object_prefix, max_items=2)
        assert_utils.assert_true(resp[0], resp[1])
        next_token = resp[1]["NextToken"]
        resp = self.awscli_s3api_obj.list_objects_v2(
            self.bucket_name, prefix=self.object_prefix, starting_token=next_token)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("END: Test list-objects-v2 with --max-items and --starting-token options.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-15194")
    @CTFailOn(error_handler)
    def test_15194(self):
        """Test list-objects-v2 --fetch-owner and --no-fetch-owner using aws s3api."""
        self.log.info("START: Test list-objects-v2 with --fetch-owner and --no-fetch-owner options")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 to test --fetch-owner and --no-fetch-owner using existing bucket.")
        resp = self.awscli_s3api_obj.list_objects_v2(self.bucket_name, fetch_owner=None)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.awscli_s3api_obj.list_objects_v2(
            self.bucket_name, no_fetch_owner=None)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("END: Test list-objects-v2 with --fetch-owner and --no-fetch-owner options")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-15192")
    @CTFailOn(error_handler)
    def test_15192(self):
        """Test list-objects-v2 --start-after option using aws s3api."""
        self.log.info("START: Test list-objects-v2 --start-after option using aws s3api.")
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info("Run list-objects-v2 --start-after to list all keys after the key specified.")
        resp = self.awscli_s3api_obj.list_objects_v2(
            self.bucket_name, start_after=self.object_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("END: Test list-objects-v2 --start-after option using aws s3api.")
