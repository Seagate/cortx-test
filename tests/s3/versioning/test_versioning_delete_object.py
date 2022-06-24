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

"""DELETE Object test module for Object Versioning."""

import logging
import os
import time
import pytest

from commons import error_messages as errmsg
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import check_get_head_object_version
from libs.s3.s3_versioning_common_test_lib import check_list_object_versions
from libs.s3.s3_versioning_common_test_lib import check_list_objects
from libs.s3.s3_versioning_common_test_lib import delete_version
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket
from libs.s3.s3_versioning_common_test_lib import upload_version
from libs.s3.s3_versioning_common_test_lib import upload_versions


class TestVersioningDeleteObject:
    """Test DELETE Object API with Object Versioning"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """
        Function will be perform prerequisite test steps prior to each test case.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningDeleteObject")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        file_name1 = "{0}{1}".format("ver_del_obj", time.perf_counter_ns())
        file_name2 = "{0}{1}".format("ver_del_obj", time.perf_counter_ns())
        file_name3 = "{0}{1}".format("ver_del_obj", time.perf_counter_ns())
        download_file = "{0}{1}".format("ver_download", time.perf_counter_ns())
        self.file_path1 = os.path.join(self.test_dir_path, file_name1)
        self.file_path2 = os.path.join(self.test_dir_path, file_name2)
        self.file_path3 = os.path.join(self.test_dir_path, file_name3)
        self.download_path = os.path.join(self.test_dir_path, download_file)
        self.upload_file_paths = [self.file_path1, self.file_path2, self.file_path3]
        for file_path in self.upload_file_paths:
            create_file(file_path, 1, "/dev/urandom")
            self.log.info("Created file: %s", file_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        self.object_name1 = "key-obj-1-{}".format(time.perf_counter_ns())
        self.object_name2 = "key-obj-2-{}".format(time.perf_counter_ns())
        self.object_name3 = "key-obj-3-{}".format(time.perf_counter_ns())
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be invoked after each test case to clean up any test artifacts.
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

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32722")
    @CTFailOn(error_handler)
    def test_delete_object_unversioned_32722(self):
        """
        Test DELETE Object in an unversioned bucket.
        """
        self.log.info("STARTED: Test DELETE Object in an unversioned bucket")
        self.log.info("Step 1: Upload object to the unversioned bucket")
        res = self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                          object_name=self.object_name1,
                                          file_path=self.file_path1)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Delete the uploaded object")
        res = self.s3_test_obj.delete_object(bucket_name=self.bucket_name,
                                             obj_name=self.object_name1)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_in("VersionId", res[1])
        assert_utils.assert_not_in("DeleteMarker", res[1])
        self.log.info("ENDED: Test DELETE Object in an unversioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32726")
    @CTFailOn(error_handler)
    def test_delete_object_preexisting_32726(self):
        """
        Test DELETE Object with pre-existing objects in a versioned bucket.
        """
        self.log.info("STARTED: Test DELETE Object with pre-existing objects in a versioned bucket")
        self.log.info("Step 1: Setup objects/versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   pre_obj_list=[self.object_name1, self.object_name2],
                                   file_paths=self.upload_file_paths)
        self.log.info("Step 2: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Delete pre-existing object1 in versioning enabled bucket")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       check_deletemarker=True, versions_dict=versions)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Verify List Objects does not include deleted object")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[self.object_name2])
        self.log.info("Step 6: Verify GET/HEAD response for deleted object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 7: Verify GET/HEAD response for object with delete marker version id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      version_id=versions[self.object_name1]["is_latest"],
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 8: Verify GET/HEAD response for object with null version id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      etag=versions[self.object_name1]["versions"]["null"],
                                      version_id="null")
        self.log.info("Step 9: Delete pre-existing object2 in a versioned bucket by version id")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name2,
                       versions_dict=versions, version_id="null")
        self.log.info("Step 10: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 11: Verify List Objects does not include deleted object")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[])
        self.log.info("Step 12: Verify GET/HEAD response for deleted object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name2,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 13: Verify GET/HEAD response for object with null version id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name2,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test DELETE Object with pre-existing objects in a versioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32717")
    @CTFailOn(error_handler)
    def test_delete_object_versioning_enabled_32717(self):
        """
        Test DELETE Object in a versioning enabled bucket.
        """
        self.log.info("STARTED: Test DELETE Object in a versioning enabled bucket")
        self.log.info("Step 1: Setup objects/versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 5)])
        self.log.info("Step 2: Delete 2 versions of the object")
        version_id1 = list(versions[self.object_name1]["versions"].keys())[2]
        version_id2 = list(versions[self.object_name1]["versions"].keys())[4]
        for v_id in [version_id1, version_id2]:
            delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                           bucket_name=self.bucket_name, object_name=self.object_name1,
                           versions_dict=versions, version_id=v_id)
        self.log.info("Step 3: Verify remaining versions of object are present")
        for v_id in versions[self.object_name1]["versions"].keys():
            etag = versions[self.object_name1]["versions"][v_id]
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name,
                                          object_name=self.object_name1, version_id=v_id,
                                          etag=etag)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Perform DELETE Object without version id")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       versions_dict=versions)
        self.log.info("Step 6: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 7: Verify GET/HEAD response for deleted object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 8: Verify GET/HEAD response for delete marker version id")
        dm_id = versions[self.object_name1]["delete_markers"][-1]
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      version_id=dm_id,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 9: Delete remaining versions")
        version_list = list(versions[self.object_name1]["versions"].keys())
        for v_id in version_list:
            delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                           bucket_name=self.bucket_name, object_name=self.object_name1,
                           versions_dict=versions, version_id=v_id)
        self.log.info("Step 10: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("ENDED: Test DELETE Object in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32744")
    @CTFailOn(error_handler)
    def test_delete_object_versioning_suspended_32744(self):
        """
        Test DELETE Object in a versioning suspended bucket.
        """
        self.log.info("STARTED: Test DELETE Object in a versioning suspended bucket")
        self.log.info("Step 1: Setup objects/versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   pre_obj_list=[self.object_name1, self.object_name2],
                                   obj_list=[("Enabled", self.object_name2, 1),
                                             ("Enabled", self.object_name3, 2)])
        self.log.info("Step 2: Set bucket versioning to Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Delete object1")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       versions_dict=versions)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Verify GET/HEAD response for object1")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 6: Verify GET/HEAD response for object1 with null version id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      version_id="null",
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 7: Delete object2")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name2,
                       versions_dict=versions)
        self.log.info("Step 8: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 9: Verify GET/HEAD response for object2")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name2,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 10: Verify GET/HEAD response for object2 with null version id")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name2,
                                      version_id="null",
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 11: Verify GET/HEAD response for object2 with version id "
                      "present before delete marker")
        v_id = versions[self.object_name2]["version_history"][-2]
        etag = versions[self.object_name2]["versions"][v_id]
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name2,
                                      version_id=v_id, etag=etag)
        self.log.info("Step 12: Delete object3")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name3,
                       versions_dict=versions)
        self.log.info("Step 13: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 14: Verify GET/HEAD response for object3")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name3,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 15: Verify GET/HEAD response for object3 undeleted versions")
        for v_id in versions[self.object_name3]["version_history"][:2]:
            etag = versions[self.object_name3]["versions"][v_id]
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, etag=etag,
                                          object_name=self.object_name3, version_id=v_id)
        self.log.info("ENDED: Test DELETE Object in a versioning suspended bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32723")
    @CTFailOn(error_handler)
    def test_delete_object_deletemarker_id_32723(self):
        """
        Test DELETE Object with the version id of a delete marker.
        """
        self.log.info("STARTED: Test DELETE Object with the version id of a delete marker")
        self.log.info("Step 1: Setup objects/versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   pre_obj_list=[self.object_name1],
                                   obj_list=[("Enabled", self.object_name2, 1),
                                             ("Suspended", self.object_name3, 1)])
        self.log.info("Step 2: Set bucket versioning to Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Enabled")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Create delete markers for object1 and object2")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       versions_dict=versions)
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name2,
                       versions_dict=versions)
        self.log.info("Step 4: Set bucket versioning to Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Create delete marker for object3")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name3,
                       versions_dict=versions)
        self.log.info("Step 6: Delete the delete markers for all 3 objects")
        for obj_name in [self.object_name1, self.object_name2, self.object_name3]:
            dm_id = versions[obj_name]["delete_markers"][0]
            delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                           bucket_name=self.bucket_name, object_name=obj_name,
                           versions_dict=versions, version_id=dm_id)
        self.log.info("Step 7: Verify GET/HEAD Object response for all 3 objects")
        for obj_name in [self.object_name1, self.object_name2]:
            v_id = versions[obj_name]["version_history"][0]
            etag = versions[obj_name]["versions"][v_id]
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          etag=etag)
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name3,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 8: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("ENDED: Test DELETE Object with the version id of a delete marker")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32751")
    @CTFailOn(error_handler)
    def test_delete_object_with_deletemarker_32751(self):
        """
        Test DELETE Object on an object already having a delete marker.
        """
        self.log.info("STARTED: Test DELETE Object on an object already having a delete marker")
        self.log.info("Step 1: Setup objects/versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 1)])
        self.log.info("Step 2: Delete object object1 to create a delete marker")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       versions_dict=versions)
        self.log.info("Step 3: Delete object object1 with delete marker already present")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       versions_dict=versions)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("ENDED: Test DELETE Object on an object already having a delete marker")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32748")
    @CTFailOn(error_handler)
    def test_delete_object_all_versions_32748(self):
        """
        Test DELETE Object on all versions of an object by version id.
        """
        self.log.info("STARTED: Test DELETE Object on all versions of an object by version id")
        self.log.info("Step 1: Setup objects in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 5)])
        self.log.info("Step 2: Delete all versions of object1")
        version_ids = list(versions[self.object_name1]["versions"].keys())
        for v_id in version_ids:
            delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                           bucket_name=self.bucket_name, object_name=self.object_name1,
                           versions_dict=versions, version_id=v_id)
        self.log.info("Step 3: Verify GET/HEAD response for deleted object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Verify List Objects does not include deleted object")
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[])
        self.log.info("ENDED: Test DELETE Object on all versions of an object by version id")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32746")
    @CTFailOn(error_handler)
    def test_delete_reupload_versioning_enabled_32746(self):
        """
        Test DELETE Object followed by PUT Object in a versioning enabled bucket.
        """
        self.log.info("STARTED: Test DELETE Object followed by PUT Object in a versioning enabled "
                      "bucket")
        self.log.info("Step 1: Setup objects in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   pre_obj_list=[self.object_name1, self.object_name2],
                                   obj_list=[("Enabled", self.object_name2, 1),
                                             ("Enabled", self.object_name3, 2)])
        self.log.info("Step 2: Delete all 3 objects to create delete markers")
        for obj_name in [self.object_name1, self.object_name2, self.object_name3]:
            delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                           bucket_name=self.bucket_name, object_name=obj_name,
                           versions_dict=versions)
        self.log.info("Step 3: Upload new versions to all 3 objects")
        for obj_name in [self.object_name1, self.object_name2, self.object_name3]:
            upload_version(self.s3_test_obj, bucket_name=self.bucket_name, object_name=obj_name,
                           file_path=self.file_path1, versions_dict=versions)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Verify GET/HEAD response for all 3 objects")
        for obj_name in [self.object_name1, self.object_name2, self.object_name3]:
            v_id = versions[obj_name]["version_history"][-1]
            etag = versions[obj_name]["versions"][v_id]
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          etag=etag)
        self.log.info("ENDED: Test DELETE Object followed by PUT Object in a versioning enabled "
                      "bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-32736")
    @CTFailOn(error_handler)
    def test_delete_reupload_versioning_suspended_32736(self):
        """
        Test DELETE Object followed by PUT Object in a versioning suspended bucket.
        """
        self.log.info("STARTED: Test DELETE Object followed by PUT Object in a versioning "
                      "suspended bucket")
        self.log.info("Step 1: Setup objects in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Suspended", self.object_name1, 1)])
        self.log.info("Step 2: Delete object1")
        delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_test_obj,
                       bucket_name=self.bucket_name, object_name=self.object_name1,
                       versions_dict=versions)
        self.log.info("Step 3: Upload new version for object1")
        upload_version(self.s3_test_obj, bucket_name=self.bucket_name, versions_dict=versions,
                       object_name=self.object_name1, file_path=self.file_path1,
                       chk_null_version=True)
        self.log.info("Step 4: Verify List Object Versions response")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions=versions)
        self.log.info("Step 5: Verify GET/HEAD response for all 3 objects")
        v_id = versions[self.object_name1]["version_history"][-1]
        etag = versions[self.object_name1]["versions"][v_id]
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name1,
                                      etag=etag)
        self.log.info("ENDED: Test DELETE Object followed by PUT Object in a versioning "
                      "suspended bucket")
