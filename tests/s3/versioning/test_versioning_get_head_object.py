#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

"""GET/HEAD Object test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons.ct_fail_on import CTFailOn
from commons import errorcodes as err
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import s3_utils
from commons.utils import assert_utils
from config.s3 import S3_CFG
from config.s3 import S3_VER_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib


class TestVersioningGetHeadObject:
    """Test GET and HEAD Object API with Object Versioning"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
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
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
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
        pref_list = [
            each_bucket for each_bucket in res[1] if each_bucket.startswith("ver-bkt")]
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    def check_get_head_object_version(self,
                                      version_id: str = None,
                                      **kwargs) -> None:
        """
        Verify GET/HEAD Object response for specified version/object

        :param version_id: Optional version ID for GET/HEAD Object call.
            In case it is not specified, object is retrieved instead of a specific version.
        :param **kwargs: Optional keyword arguments
            "bucket_name": Bucket name to specify in the request
            "object_name": Object/Key name to specify in the request
            "etag": Expected ETag of the version/object
            "error_msg": Error message to verify, in case GET/HEAD is expected to fail
        """
        bucket_name = kwargs.get("bucket_name", self.bucket_name)
        object_name = kwargs.get("object_name", self.object_name)
        etag = kwargs.get("etag", None)
        error_msg = kwargs.get("error_msg", None)
        self.log.info("Verifying GET Object with VersionId response")
        try:
            if version_id:
                get_response = self.s3_ver_test_obj.get_object_version(
                    bucket_name, object_name, version_id=version_id)
            else:
                get_response = self.s3_ver_test_obj.get_object(
                    bucket=bucket_name, key=object_name)
            assert_utils.assert_true(get_response[0], get_response[1])
            if version_id:
                assert_utils.assert_equal(
                    get_response[1]["ResponseMetadata"]["VersionId"], version_id)
            if etag:
                assert_utils.assert_equal(get_response[1]["ResponseMetadata"]["ETag"], etag)
            self.log.info("Successfully performed GET Object: %s", get_response)
        except CTException as error:
            self.log.error(error.message)
            if not error_msg:
                raise CTException(err.CLI_ERROR, error.args[0]) from error
            assert_utils.assert_in(error_msg["get_obj_error"], error.message, error.message)
        self.log.info("Verifying HEAD Object with VersionId response")
        try:
            if version_id:
                head_response = self.s3_ver_test_obj.head_object_version(
                    bucket=bucket_name, key=object_name, version_id=version_id)
            else:
                head_response = self.s3_ver_test_obj.object_info(
                    bucket_name=bucket_name, key=object_name)
            assert_utils.assert_true(head_response[0], head_response[1])
            if version_id:
                assert_utils.assert_equal(
                    head_response[1]["ResponseMetadata"]["VersionId"], version_id)
            if etag:
                assert_utils.assert_equal(head_response[1]["ResponseMetadata"]["ETag"], etag)
            self.log.info("Successfully performed HEAD Object: %s", head_response)
        except CTException as error:
            self.log.error(error.message)
            if not error_msg:
                raise CTException(err.CLI_ERROR, error.args[0]) from error
            assert_utils.assert_in(error_msg["head_obj_error"], error.message, error.message)

    def download_and_check(self,
                           version_id: str = None,
                           file_path: str = None) -> None:
        """
        Download an object/version and verify checksum of it's contents

        :param version_id: Target version ID for GET/HEAD Object call.
            In case it is not specified/None, object is retrieved instead of a specific version.
        :param file_path: File path of the uploaded file
        """
        expected_checksum = s3_utils.calc_checksum(file_path)
        if version_id:
            resp = self.s3_test_obj.object_download(
                self.bucket_name, self.object_name, self.download_path,
                ExtraArgs={'VersionId': version_id})
        else:
            resp = self.s3_test_obj.object_download(
                self.bucket_name, self.object_name, self.download_path)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = s3_utils.calc_checksum(self.download_path)
        assert_utils.assert_equal(
            expected_checksum, download_checksum, "Mismatch in object/version contents")

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
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": "null", "ETag": res[1]["ETag"]})
        self.download_and_check(self.file_path1)
        self.log.info("Step 2: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Upload a new version for the object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path2)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 4: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[0]["ETag"]))
        self.log.info("Step 5: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 6: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[1]["ETag"]))
        self.download_and_check(self.file_path2)
        self.log.info("Step 7: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[0]["ETag"]))
        self.log.info("Step 9: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 10: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[1]["ETag"]))
        self.download_and_check(self.file_path2)
        self.log.info("Step 11: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 12: Upload object after re-enabling versioning")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path3)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 13: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[0]["ETag"]))
        self.log.info("Step 14: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 15: Check GET/HEAD Object with VersionId=version2id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[2]["VersionId"], etag=versions[2]["ETag"]))
        self.log.info("Step 16: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[2]["ETag"]))
        self.download_and_check(self.file_path3)
        self.log.info("Step 17: Verify version contents")
        self.download_and_check(version_id=versions[0]["VersionId"], file_path=self.file_path1)
        self.download_and_check(version_id=versions[1]["VersionId"], file_path=self.file_path2)
        self.download_and_check(version_id=versions[2]["VersionId"], file_path=self.file_path3)

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
            res = self.s3_test_obj.put_object(
                bucket_name=self.bucket_name, object_name=self.object_name, file_path=file_path)
            assert_utils.assert_true(res[0], res[1])
            self.download_and_check(file_path)
            versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 3: Check GET/HEAD Object with VersionId=null returns error")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", error_msg=S3_VER_CFG["error_messages"]["version_not_found_error"]))
        self.log.info("Step 4: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[0]["VersionId"], etag=versions[0]["ETag"]))
        self.log.info("Step 5: Check GET/HEAD Object with VersionId=version2id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 6: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[1]["ETag"]))
        self.download_and_check(self.file_path2)
        self.log.info("Step 7: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: Check GET/HEAD Object with VersionId=null returns error")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", error_msg=S3_VER_CFG["error_messages"]["version_not_found_error"]))
        self.log.info("Step 9: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[0]["VersionId"], etag=versions[0]["ETag"]))
        self.log.info("Step 10: Check GET/HEAD Object with VersionId=version2id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 11: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[1]["ETag"]))
        self.download_and_check(self.file_path2)
        self.log.info("Step 12: Upload object after suspending versioning")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path3)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": "null", "ETag": res[1]["ETag"]})
        self.log.info("Step 13: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[2]["ETag"]))
        self.log.info("Step 14: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[0]["VersionId"], etag=versions[0]["ETag"]))
        self.log.info("Step 15: Check GET/HEAD Object with VersionId=version2id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 16: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[2]["ETag"]))
        self.download_and_check(self.file_path3)
        self.log.info("Step 17: Verify version contents")
        self.download_and_check(version_id=versions[0]["VersionId"], file_path=self.file_path1)
        self.download_and_check(version_id=versions[1]["VersionId"], file_path=self.file_path2)
        self.download_and_check(version_id=versions[2]["VersionId"], file_path=self.file_path3)

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32729')
    @CTFailOn(error_handler)
    def test_get_head_object_versioned_bucket_32729(self):
        """
        Test GET/HEAD Object for objects uploaded to a versioning suspended bucket.
        """
        self.log.info(
            "STARTED: Test GET/HEAD Object for objects uploaded to a versioning suspended bucket.")
        versions = []
        self.log.info("Step 1: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Upload object and check object content")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        versions.append({"VersionId": "null", "ETag": res[1]["ETag"]})
        self.download_and_check(self.file_path1)
        self.log.info("Step 3: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[0]["ETag"]))
        self.log.info("Step 4: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[0]["ETag"]))
        self.download_and_check(self.file_path1)
        self.log.info("Step 5: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[0]["ETag"]))
        self.log.info("Step 7: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[0]["ETag"]))
        self.download_and_check(self.file_path1)
        self.log.info("Step 8: Upload a new version for the object and check object content")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path2)
        assert_utils.assert_true(res[0], res[1])
        self.download_and_check(self.file_path2)
        versions.append({"VersionId": res[1]["VersionId"], "ETag": res[1]["ETag"]})
        self.log.info("Step 9: Check GET/HEAD Object with VersionId=null")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id="null", etag=versions[0]["ETag"]))
        self.log.info("Step 10: Check GET/HEAD Object with VersionId=version1id")
        assert_utils.assert_true(self.check_get_head_object_version(
            version_id=versions[1]["VersionId"], etag=versions[1]["ETag"]))
        self.log.info("Step 11: Check GET/HEAD Object without VersionId, check object content")
        assert_utils.assert_true(self.check_get_head_object_version(etag=versions[1]["ETag"]))
        self.download_and_check(self.file_path2)
        self.log.info("Step 12: Verify version contents")
        self.download_and_check(version_id=versions[0]["VersionId"], file_path=self.file_path1)
        self.download_and_check(version_id=versions[1]["VersionId"], file_path=self.file_path2)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32727')
    @CTFailOn(error_handler)
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
            res = self.s3_ver_test_obj.put_bucket_versioning(
                bucket_name=self.bucket_name, status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
        else:
            self.log.info("Testing with unversioned bucket")
        self.log.info("Step 1: Upload object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Check GET/HEAD Object of non-existing object version returns error")
        assert_utils.assert_true(self.check_get_head_object_version(
            bucket_name=self.bucket_name, object_name=non_existent_object, version_id="null",
            error_msg=S3_VER_CFG["error_messages"]["version_not_found_error"]))
        self.log.info("Step 3: Check GET/HEAD Object with non existent version id returns error")
        assert_utils.assert_true(self.check_get_head_object_version(
            bucket_name=self.bucket_name, object_name=self.object_name,
            version_id=non_existent_version_id,
            error_msg=S3_VER_CFG["error_messages"]["version_not_found_error"]))
        self.log.info("Step 4: Check GET/HEAD Object with invalid version id returns error")
        assert_utils.assert_true(self.check_get_head_object_version(
            bucket_name=self.bucket_name, object_name=self.object_name, version_id="version1",
            error_msg=S3_VER_CFG["error_messages"]["invalid_version_id_error"]))
        self.log.info("Step 5: Check GET/HEAD Object with empty version id returns error")
        assert_utils.assert_true(self.check_get_head_object_version(
            bucket_name=self.bucket_name, object_name=self.object_name,
            version_id="", error_msg=S3_VER_CFG["empty_version_id_error"]))
