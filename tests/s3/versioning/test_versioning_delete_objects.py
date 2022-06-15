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

"""DELETE Objects test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons import error_messages as errmsg
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_versioning_common_test_lib import check_get_head_object_version
from libs.s3.s3_versioning_common_test_lib import check_list_object_versions
from libs.s3.s3_versioning_common_test_lib import check_list_objects
from libs.s3.s3_versioning_common_test_lib import delete_objects
from libs.s3.s3_versioning_common_test_lib import upload_version
from libs.s3.s3_versioning_common_test_lib import upload_versions


class TestVersioningDeleteObjects:
    """Test DELETE Objects API with Object Versioning"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """Function will be perform prerequisite test steps prior to each test case."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3mp_test_obj = S3MultipartTestLib()
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningDeleteObject")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        file_name1 = "{0}{1}".format("ver_del_obj", time.perf_counter_ns())
        file_name2 = "{0}{1}".format("ver_del_obj", time.perf_counter_ns())
        file_name3 = "{0}{1}".format("ver_del_obj", time.perf_counter_ns())
        mp_file_name = "{0}{1}".format("ver_del_obj_mpu", time.perf_counter_ns())
        download_file = "{0}{1}".format("ver_download", time.perf_counter_ns())
        self.file_path1 = os.path.join(self.test_dir_path, file_name1)
        self.file_path2 = os.path.join(self.test_dir_path, file_name2)
        self.file_path3 = os.path.join(self.test_dir_path, file_name3)
        self.mp_file_path = os.path.join(self.test_dir_path, mp_file_name)
        self.download_path = os.path.join(self.test_dir_path, download_file)
        self.upload_file_paths = [self.file_path1, self.file_path2, self.file_path3]
        for file_path in self.upload_file_paths:
            create_file(file_path, 1, "/dev/urandom")
            self.log.info("Created file: %s", file_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        self.object_name1 = "obj-1-{}".format(time.perf_counter_ns())
        self.object_name2 = "obj-2-{}".format(time.perf_counter_ns())
        self.object_name3 = "obj-3-{}".format(time.perf_counter_ns())
        self.object_name4 = "obj-4-{}".format(time.perf_counter_ns())
        self.object_name5 = "obj-5-{}".format(time.perf_counter_ns())
        self.object_name6 = "obj-6-{}".format(time.perf_counter_ns())
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """Function will be invoked after each test case to clean up any test artifacts."""
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        # DELETE Object with VersionId is WIP, uncomment once feature is available
        # res = self.s3_test_obj.bucket_list()
        # pref_list = []
        # for bucket_name in res[1]:
        #     if bucket_name.startswith("ver-bkt"):
        #         empty_versioned_bucket(self.s3_ver_test_obj, bucket_name)
        #         pref_list.append(bucket_name)
        # if pref_list:
        #     res = self.s3_test_obj.delete_multiple_buckets(pref_list)
        #     assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43187")
    def test_delete_objects_preexisting_43187(self):
        """
        Test DELETE Objects for pre-existing objects in a versioned bucket.
        """
        self.log.info("STARTED: Test DELETE Objects for pre-existing objects in a versioned bucket")
        self.log.info("Setup objects/versions")
        obj_names = [self.object_name1, self.object_name2, self.object_name3, self.object_name4]
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   pre_obj_list=obj_names)
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: DeleteObjects with Key=object1")
        obj_list = [(self.object_name1, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: DeleteObjects with Key=object2 and VersionId=null")
        obj_list = [(self.object_name2, "null")]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: DeleteObjects with Key=object2 and VersionId=null")
        obj_list = [(self.object_name2, "null")]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 4: Set bucket versioning to Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: DeleteObjects with Key=object3")
        obj_list = [(self.object_name3, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 6: DeleteObjects with Key=object4 and VersionId=null")
        obj_list = [(self.object_name4, "null")]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 7: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 8: Verify List Objects does not include deleted object")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[])
        self.log.info("Step 9: Perform GET/HEAD Object for object1 - object4")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test DELETE Objects for pre-existing objects in a versioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43188")
    def test_delete_objects_versioned_43188(self):
        """
        Test DELETE Objects for objects in a versioned bucket.
        """
        self.log.info("STARTED: Test DELETE Objects for objects in a versioned bucket")
        self.log.info("Setup objects/versions")
        obj_names = [self.object_name1, self.object_name2, self.object_name3, self.object_name4]
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 1),
                                             ("Enabled", self.object_name2, 1),
                                             ("Enabled", self.object_name3, 1),
                                             ("Enabled", self.object_name4, 2)])
        self.log.info("Step 1: DeleteObjects with Key=object1")
        obj_list = [(self.object_name1, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 2: DeleteObjects with Key=object2 and VersionId")
        version_id = versions[self.object_name2]["version_history"][-1]
        obj_list = [(self.object_name2, version_id)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: DeleteObjects with two entries for Key=object3")
        obj_list = [(self.object_name3, None), (self.object_name3, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 4: DeleteObjects with two entries for Key=object4, "
                      "with and without version id")
        version_id = versions[self.object_name4]["version_history"][0]
        obj_list = [(self.object_name4, None), (self.object_name3, version_id)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 5: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 6: Verify List Objects does not include deleted object")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[])
        self.log.info("Step 7: Perform GET/HEAD Object for object1 - object4")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test DELETE Objects for objects in a versioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43189")
    def test_delete_objects_suspended_43189(self):
        """
        Test DELETE Objects for objects in a versioning suspended bucket.
        """
        self.log.info("STARTED: Test DELETE Objects for objects in a versioning suspended bucket")
        self.log.info("Setup objects/versions")
        obj_names = [self.object_name1, self.object_name2, self.object_name3, self.object_name4]
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 1),
                                             ("Enabled", self.object_name2, 1),
                                             ("Suspended", self.object_name3, 1),
                                             ("Suspended", self.object_name4, 1)])
        self.log.info("Step 1: DeleteObjects with Key=object1")
        obj_list = [(self.object_name1, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 2: DeleteObjects with Key=object2 and VersionId")
        version_id = versions[self.object_name2]["version_history"][-1]
        obj_list = [(self.object_name2, version_id)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: DeleteObjects with Key=object3")
        obj_list = [(self.object_name3, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 4: DeleteObjects with Key=object4 and VersionId=null")
        obj_list = [(self.object_name4, "null")]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 5: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 6: Verify List Objects does not include deleted object")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[])
        self.log.info("Step 7: Perform GET/HEAD Object for object1 - object4")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test DELETE Objects for objects in a versioning suspended bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43190")
    def test_delete_objects_1000_limit_43190(self):
        """
        Test Delete Objects limit of 1000 entries.
        """
        self.log.info("STARTED: Test Delete Objects limit of 1000 entries")
        self.log.info("Setup objects/versions")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 1001)])
        self.log.info("Step 1: DeleteObjects with 1001 versions specified")
        obj_list = [(self.object_name1, v_id)
                    for v_id in versions[self.object_name1]["version_history"]]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list,
                       expected_error=errmsg.BAD_REQUEST_ERR)
        self.log.info("Step 2: DeleteObjects with 1000 versions specified")
        del obj_list[-1]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 4: Verify List Objects contains object1")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[self.object_name1])
        self.log.info("Step 5: Perform GET/HEAD Object for object1 - object4")
        version_id = versions[self.object_name1]["is_latest"]
        etag = versions[self.object_name1]["versions"][version_id]
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name,
                                      object_name=self.object_name1, etag=etag)
        self.log.info("ENDED: Test Delete Objects limit of 1000 entries")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43191")
    def test_delete_objects_quiet_mode_43191(self):
        """
        Test Delete Objects in Quiet mode.
        """
        self.log.info("STARTED: Test Delete Objects in Quiet mode")
        self.log.info("Setup objects/versions")
        obj_names = [self.object_name1, self.object_name2, self.object_name3, self.object_name4,
                     self.object_name5, self.object_name6]
        obj_list = [("Enabled", obj, 1) for obj in obj_names]
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=obj_list)
        self.log.info("Step 1: DeleteObjects with Quiet=False")
        version_id = versions[self.object_name2]["is_latest"]
        obj_list = [(self.object_name1, None), (self.object_name2, version_id),
                    (self.object_name3, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list, quiet=False)
        self.log.info("Step 2: DeleteObjects with Quiet=True")
        version_id = versions[self.object_name5]["is_latest"]
        obj_list = [(self.object_name4, None), (self.object_name5, version_id),
                    (self.object_name6, None)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 4: Verify List Objects does not contain deleted objects")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[])
        self.log.info("Step 5: Perform GET/HEAD Object for object1 - object4")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test Delete Objects in Quiet mode")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43192")
    def test_delete_objects_invalid_43192(self):
        """
        Test invalid scenarios for Delete Objects.
        """
        self.log.info("STARTED: Test invalid scenarios for Delete Objects")
        self.log.info("Setup objects/versions")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=("Enabled", self.object_name1, 1))
        self.log.info("Step 1: DeleteObjects with no keys/versions specified")
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=[])
        self.log.info("Step 2: DeleteObjects with incorrect key name")
        version_id = versions[self.object_name1]["is_latest"]
        obj_list = [(self.object_name2, version_id)]
        self.log.info("Step 3: DeleteObjects with incorrect version id")
        incorrect_vid = version_id[1:] + version_id[0]
        obj_list = [(self.object_name1, incorrect_vid)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Verify List Objects contains object1")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[self.object_name1])
        self.log.info("Step 6: Perform GET/HEAD Object for object1")
        etag = versions[self.object_name1]["versions"][version_id]
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name,
                                      object_name=self.object_name1, etag=etag)
        self.log.info("ENDED: Test invalid scenarios for Delete Objects")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43183")
    def test_delete_objects_preexisting_multipart_43183(self):
        """
        Test Delete Objects for pre-existing multipart uploads.
        """
        self.log.info("STARTED: Test Delete Objects for pre-existing multipart uploads")
        versions = {}
        obj_names = [self.object_name1, self.object_name2]
        self.log.info("Step 1: Upload multipart objects")
        for obj_name in obj_names:
            upload_version(self.s3mp_test_obj, self.bucket_name, obj_name,
                           self.mp_file_path, versions_dict=versions,
                           is_multipart=True, total_parts=2, file_size=20)
        self.log.info("Step 2: Perform DeleteObjects")
        version_id = versions[self.object_name2]["is_latest"]
        obj_list = [(self.object_name1, None), (self.object_name2, version_id)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 4: Verify List Objects does not contain multipart uploads")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name, expected_objects=[])
        self.log.info("Step 5: Perform GET/HEAD Object for object1")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test Delete Objects for pre-existing multipart uploads")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43184")
    def test_delete_objects_multipart_versioned_43184(self):
        """
        Test Delete Objects for multipart uploads in a versioning enabled bucket.
        """
        self.log.info("STARTED: Test Delete Objects for multipart uploads in a versioning enabled "
                      "bucket")
        versions = {}
        obj_names = [self.object_name1, self.object_name2]
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 1: Upload multipart objects")
        for obj_name in obj_names:
            upload_version(self.s3mp_test_obj, self.bucket_name, obj_name,
                           self.mp_file_path, versions_dict=versions,
                           is_multipart=True, total_parts=2, file_size=20)
        self.log.info("Step 2: Perform DeleteObjects")
        version_id = versions[self.object_name2]["is_latest"]
        obj_list = [(self.object_name1, None), (self.object_name2, version_id)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 4: Verify List Objects does not contain multipart uploads")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name, expected_objects=[])
        self.log.info("Step 5: Perform GET/HEAD Object for object1")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test Delete Objects for multipart uploads in a versioning enabled "
                      "bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-43185")
    def test_delete_objects_multipart_versioned_43185(self):
        """
        Test Delete Objects for multipart uploads in a versioning suspended bucket.
        """
        self.log.info("STARTED: Test Delete Objects for multipart uploads in a versioning "
                      "suspended bucket")
        versions = {}
        obj_names = [self.object_name1, self.object_name2]
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 1: Upload multipart object object1")
        upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name1, self.mp_file_path,
                       versions_dict=versions, is_multipart=True, total_parts=2, file_size=20)
        self.log.info("Step 2: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 1: Upload multipart object object2")
        upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name2, self.mp_file_path,
                       versions_dict=versions, is_multipart=True, total_parts=2, file_size=20)
        self.log.info("Step 2: Perform DeleteObjects")
        version_id = versions[self.object_name2]["is_latest"]
        obj_list = [(self.object_name1, None), (self.object_name2, version_id)]
        delete_objects(s3_test_obj=self.s3_test_obj, bucket_name=self.bucket_name,
                       versions_dict=versions, obj_ver_list=obj_list)
        self.log.info("Step 3: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 4: Verify List Objects does not contain multipart uploads")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name, expected_objects=[])
        self.log.info("Step 5: Perform GET/HEAD Object for object1")
        for obj in obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test Delete Objects for multipart uploads in a versioning "
                      "suspended bucket")
