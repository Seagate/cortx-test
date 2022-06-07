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

"""Test module for DELETE Object Tagging"""

import logging
import os
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from config.s3 import S3_CFG
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_common_test_lib import put_object_tagging
from libs.s3.s3_versioning_common_test_lib import upload_version
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestTaggingDeleteObject:
    """Test Delete Object Tagging"""

    def setup_method(self):
        """
        Function will be invoked perform setup prior to each test case.
        """
        LOGGER.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestTaggingDeleteObject")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", self.test_dir_path)
        self.file_path = os.path.join(self.test_dir_path, f"del_obj_tag_{time.perf_counter_ns()}")
        create_file(fpath=self.file_path, count=1)
        LOGGER.info("Created file: %s", self.file_path)
        self.bucket_name = f"tag-bkt-{time.perf_counter_ns()}"
        self.object_name = f"tag-obj-{time.perf_counter_ns()}"
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        LOGGER.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be perform cleanup after each test case.
        """
        LOGGER.info("STARTED: Teardown operations")
        LOGGER.info("Clean : %s", self.test_dir_path)
        if path_exists(self.file_path):
            res = remove_file(self.file_path)
            LOGGER.info("cleaned path: %s, res: %s", self.file_path, res)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        LOGGER.info("Cleanup test directory: %s", self.test_dir_path)
        # DELETE Object with VersionId is WIP, uncomment once feature is available
        # res = self.s3_test_obj.bucket_list()
        # pref_list = []
        # for bucket_name in res[1]:
        #     if bucket_name.startswith("tag-bkt"):
        #         empty_versioned_bucket(self.s3_ver_obj, bucket_name)
        #         pref_list.append(bucket_name)
        # if pref_list:
        #     res = self.s3_test_obj.delete_multiple_buckets(pref_list)
        #     assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41277")
    @CTFailOn(error_handler)
    def test_tag_key_limit_41277(self):
        """
        Test maximum key length of a tag for a versioned object - 128 Unicode characters
        """


