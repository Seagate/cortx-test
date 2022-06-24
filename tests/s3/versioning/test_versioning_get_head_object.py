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

"""GET/HEAD Object test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons import errorcodes as err
from commons import error_messages as errmsg
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import s3_utils
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import check_get_head_object_version
from libs.s3.s3_versioning_common_test_lib import download_and_check
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket


class TestVersioningGetHeadObject:
    """Test GET and HEAD Object API with Object Versioning"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """
        Function will perform setup prior to each test case.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningGetHeadObject")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        file_name1 = "{0}{1}".format("ver_get_head", time.perf_counter_ns())
        file_name2 = "{0}{1}".format("ver_get_head", time.perf_counter_ns())
        file_name3 = "{0}{1}".format("ver_get_head", time.perf_counter_ns())
        download_file = "{0}{1}".format("ver_download", time.perf_counter_ns())
        self.file_path1 = os.path.join(self.test_dir_path, file_name1)
        self.file_path2 = os.path.join(self.test_dir_path, file_name2)
        self.file_path3 = os.path.join(self.test_dir_path, file_name3)
        self.download_path = os.path.join(self.test_dir_path, download_file)
        for file_path in (self.file_path1, self.file_path2, self.file_path3):
            create_file(file_path, 1, "/dev/urandom")
            self.log.info("Created file: %s", file_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        self.object_name = "ver-obj-{}".format(time.perf_counter_ns())
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will perform cleanup after each test case.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        for file_path in (self.file_path1, self.file_path2, self.file_path3, self.download_path):
            if path_exists(file_path):
                res = remove_file(file_path)
                self.log.info("cleaned path: %s, res: %s", file_path, res)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = []
        for bucket_name in res[1]:
            if bucket_name.startswith("ver-bkt"):
                empty_versioned_bucket(self.s3_ver_test_obj, bucket_name)
                pref_list.append(bucket_name)
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32739')
    @CTFailOn(error_handler)
    def test_get_head_object_preexisting_32739(self):
        """
        Test GET/HEAD Object for pre-existing object in versioned bucket.
        """
        self.log.info("STARTED: Test GET/HEAD Object for pre-existing object in versioned bucket.")
        versions = []
        self.log.info("Step 1: Upload object before enabling versioning and check object content")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": "null", "ETag": res[1]["ETag"]})
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path)
        self.log.info("Step 2: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Upload a new version for the object")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path2)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 4: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"])
        self.log.info("Step 5: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"],
                                      version_id=versions[1]["VersionId"])
        self.log.info("Step 6: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path)
        self.log.info("Step 7: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      version_id="null", etag=versions[0]["ETag"])
        self.log.info("Step 9: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"],
                                      version_id=versions[1]["VersionId"])
        self.log.info("Step 10: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"])
        download_and_check(self.s3_test_obj,  self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path)
        self.log.info("Step 11: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 12: Upload object after re-enabling versioning")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path3)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 13: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"], version_id="null")
        self.log.info("Step 14: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"],
                                      version_id=versions[1]["VersionId"])
        self.log.info("Step 15: Check GET/HEAD Object with VersionId=version2id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[2]["ETag"],
                                      version_id=versions[2]["VersionId"])
        self.log.info("Step 16: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[2]["ETag"])
        download_and_check(self.s3_test_obj,  self.bucket_name, self.object_name,
                           file_path=self.file_path3, download_path=self.download_path)
        self.log.info("Step 17: Verify version contents")
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path,
                           version_id=versions[0]["VersionId"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path,
                           version_id=versions[1]["VersionId"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path3, download_path=self.download_path,
                           version_id=versions[2]["VersionId"])

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32731')
    @CTFailOn(error_handler)
    def test_get_head_object_versioned_bucket_32731(self):
        """
        Test GET/HEAD Object for objects uploaded to a versioned bucket.
        """
        self.log.info("STARTED: Test GET/HEAD Object for objects uploaded to a versioned bucket")
        versions = []
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Upload two new versions for the object and verify object content")
        for file_path in (self.file_path1, self.file_path2):
            res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              file_path=file_path)
            assert_utils.assert_true(res[0], res[1])
            download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                               file_path=file_path, download_path=self.download_path)
            versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 3: Check GET/HEAD Object with VersionId=null returns error")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 4: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"],
                                      version_id=versions[0]["VersionId"])
        self.log.info("Step 5: Check GET/HEAD Object with VersionId=version2id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"],
                                      version_id=versions[1]["VersionId"])
        self.log.info("Step 6: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path)
        self.log.info("Step 7: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: Check GET/HEAD Object with VersionId=null returns error")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 9: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"],
                                      version_id=versions[0]["VersionId"])
        self.log.info("Step 10: Check GET/HEAD Object with VersionId=version2id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"],
                                      version_id=versions[1]["VersionId"])
        self.log.info("Step 11: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path)
        self.log.info("Step 12: Upload object after suspending versioning")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path3)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": "null", "ETag": res[1]["ETag"]})
        self.log.info("Step 13: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[2]["ETag"])
        self.log.info("Step 14: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"],
                                      version_id=versions[0]["VersionId"],)
        self.log.info("Step 15: Check GET/HEAD Object with VersionId=version2id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"],
                                      version_id=versions[1]["VersionId"])
        self.log.info("Step 16: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[2]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path3, download_path=self.download_path)
        self.log.info("Step 17: Verify version contents")
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path,
                           version_id=versions[0]["VersionId"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path,
                           version_id=versions[1]["VersionId"])
        download_and_check(self.s3_test_obj,  self.bucket_name, self.object_name,
                           file_path=self.file_path3, download_path=self.download_path,
                           version_id=versions[2]["VersionId"])

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32729')
    @CTFailOn(error_handler)
    def test_get_head_object_versioned_bucket_32729(self):
        """
        Test GET/HEAD Object for objects uploaded to a versioning suspended bucket.
        """
        self.log.info("STARTED: Test GET/HEAD Object for objects uploaded to a versioning "
                      "suspended bucket.")
        versions = []
        self.log.info("Step 1: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Upload object and check object content")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": "null", "ETag": res[1]["ETag"]})
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path)
        self.log.info("Step 3: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"])
        self.log.info("Step 4: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path)
        self.log.info("Step 5: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"])
        self.log.info("Step 7: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path)
        self.log.info("Step 8: Upload a new version for the object and check object content")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path2)
        assert_utils.assert_true(res[0], res[1])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path)
        versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 9: Check GET/HEAD Object with VersionId=null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[0]["ETag"])
        self.log.info("Step 10: Check GET/HEAD Object with VersionId=version1id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      version_id=versions[1]["VersionId"],
                                      etag=versions[1]["ETag"])
        self.log.info("Step 11: Check GET/HEAD Object without VersionId, check object content")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      etag=versions[1]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path)
        self.log.info("Step 12: Verify version contents")
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path1, download_path=self.download_path,
                           version_id=versions[0]["VersionId"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.object_name,
                           file_path=self.file_path2, download_path=self.download_path,
                           version_id=versions[1]["VersionId"])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32727')
    @pytest.mark.parametrize("versioning_status", [None, "Enabled", "Suspended"])
    def test_get_head_versioned_object_invalid_32727(self, versioning_status):
        """
        Test invalid scenarios for GET/HEAD Object for versioned object.
        """
        non_existent_object = "ver-obj-{}".format(time.perf_counter_ns())
        non_existent_version_id = "Vr1" * 9
        self.log.info("STARTED: Test invalid scenarios for GET/HEAD Object for versioned object.")
        if versioning_status:
            self.log.info("Testing with bucket versioning configuration: %s", versioning_status)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
        else:
            self.log.info("Testing with unversioned bucket")
        self.log.info("Step 1: Upload object")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name,
                                          file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Check GET/HEAD Object of non-existing object version returns error")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="null",
                                      bucket_name=self.bucket_name,
                                      object_name=non_existent_object,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 3: Check GET/HEAD Object with non existent version id returns error")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name,
                                      object_name=self.object_name,
                                      version_id=non_existent_version_id,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 4: Check GET/HEAD Object with invalid version id returns error")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      version_id="version1",
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 5: Check GET/HEAD Object with empty version id returns error")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj, version_id="",
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
