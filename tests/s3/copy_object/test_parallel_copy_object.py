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

"""S3 copy object test module."""

import logging
import multiprocessing
import os
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from libs.s3 import s3_test_lib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class TestCopyObjects:
    """S3 copy object class."""

    @classmethod
    def setup_class(cls):
        """Common Setup"""
        LOGGER.info("STARTED: Class setup.")
        cls.s3_obj = s3_test_lib.S3TestLib()
        cls.s3mp_obj = S3MultipartTestLib()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "test_copy_object")
        cls.file_path = os.path.join(cls.test_dir_path, "hello.txt")
        cls.buckets = []
        LOGGER.info("ENDED: Class setup.")

    def setup_method(self):
        """Setup for tests"""
        LOGGER.info("STARTED: Test setup.")
        if not os.path.exists(self.test_dir_path):
            os.makedirs(self.test_dir_path, exist_ok=True)
        self.buckets = ["src-bucket", "dest-bucket", "src-bucket1", "src-bucket2", "dest-bucket1",
                        "dest-bucket2"]
        for bucket in self.buckets:
            resp = self.s3_obj.create_bucket(bucket)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Created %s bucket", bucket)
        LOGGER.info("ENDED: Test setup.")

    def teardown_method(self):
        """Teardown for tests"""
        LOGGER.info("STARTED: Test teardown.")
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        LOGGER.info("Delete the objects and buckets created")
        self.s3_obj.delete_multiple_buckets(self.buckets)
        LOGGER.info("ENDED: Test teardown.")

    @staticmethod
    def copy_object_wrapper(src_bucket, src_obj, dest_bucket, dest_obj, exception=None):
        """Copy object wrapper for multiprocessing"""
        s3_obj = s3_test_lib.S3TestLib()
        try:
            return s3_obj.copy_object(src_bucket, src_obj, dest_bucket, dest_obj)
        except CTException as err:
            LOGGER.info("Exception in copy object %s", err)
            if exception:
                return exception in err.message, f"Expected {exception} Received {err}"
            return False, f"Unexpected exception {err}"

    def create_put_object(self, bucket, obj, size, base='1M'):
        """Create and Put object of (size*1M) size and assert"""
        resp = system_utils.create_file(fpath=self.file_path, count=size, b_size=base)
        assert_utils.assert_true(resp[0], resp[1])
        return self.s3_obj.put_object(bucket, obj, self.file_path)

    @staticmethod
    def put_object_wrapper(bucket, obj, file_path):
        """Put object wrapper for multiprocessing"""
        s3_obj = s3_test_lib.S3TestLib()
        return s3_obj.put_object(bucket, obj, file_path)

    def objects_in_buckets(self, bucket, objects):
        """Assert if any of the given object not listed in given bucket"""
        listed_objects = self.s3_obj.object_list(bucket)[1]
        for obj in objects:
            assert_utils.assert_true(obj in listed_objects, f"{obj} not present in {bucket}")

    def parallel_copy_and_put_object(self, copy_args, put_args):
        """Parallel copy object and put object with given arguments"""
        LOGGER.info("Parallely, \n1. From %s copy %s to %s as %s\n2. Put %s to %s as %s",
                    copy_args[0], copy_args[1], copy_args[2], copy_args[3],
                    put_args[2], put_args[0], put_args[1])
        with multiprocessing.Pool(processes=2) as pool:
            process1 = pool.apply_async(self.copy_object_wrapper, args=copy_args)
            process2 = pool.apply_async(self.put_object_wrapper, args=put_args)
            assert_utils.assert_true(process1.get()[0], process1.get()[1])
            assert_utils.assert_true(process2.get()[0], process2.get()[1])

    @pytest.mark.tags("TEST-44786")
    @CTFailOn(error_handler)
    def test_44786(self):
        """Test Parallel copy and put operation from same source bucket"""
        LOGGER.info("STARTED: Test Parallel copy and put operation from same source bucket "
                    "(for simple and multipart source objects)")
        LOGGER.info("Upload object1 to source bucket1")
        self.create_put_object("src-bucket", "obj1", 100)
        self.parallel_copy_and_put_object(("src-bucket", "obj1", "dest-bucket", "obj2"),
                                          ("src-bucket", "obj3", self.file_path))
        LOGGER.info("Upload multipart object mp-obj1 to src-bucket")
        self.s3mp_obj.simple_multipart_upload("src-bucket", "mp-obj1", 1024, self.file_path, 4)

        self.parallel_copy_and_put_object(("src-bucket", "mp-obj1", "dest-bucket", "obj4"),
                                          ("src-bucket", "obj5", self.file_path))
        LOGGER.info("All objects should be listed in relevant buckets")
        self.objects_in_buckets(bucket="src-bucket", objects=["obj1", "obj3", "mp-obj1", "obj5"])
        self.objects_in_buckets(bucket="dest-bucket", objects=["obj2", "obj4"])
        LOGGER.info("ENDED: Test Parallel copy and put operation from same source bucket "
                    "(for simple and multipart source objects)")

    @pytest.mark.tags("TEST-44810")
    @CTFailOn(error_handler)
    def test_44810(self):
        """Test Parallel copy and overwrite of same object"""
        LOGGER.info("STARTED: Test Parallel copy and overwrite of same object "
                    "(for simple and multipart source objects)")
        LOGGER.info("Upload object1 to source bucket1")
        self.create_put_object("src-bucket", "obj1", 100)
        resp = system_utils.create_file(fpath=self.file_path, count=1000, b_size="1M")
        assert_utils.assert_true(resp[0], resp[1])
        self.parallel_copy_and_put_object(("src-bucket", "obj1", "dest-bucket", "obj2"),
                                          ("src-bucket", "obj1", self.file_path))
        LOGGER.info("Upload multipart object mp-obj1 to src-bucket")
        self.s3mp_obj.simple_multipart_upload("src-bucket", "mp-obj1", 1024, self.file_path, 4)
        self.parallel_copy_and_put_object(("src-bucket", "mp-obj1", "dest-bucket", "obj4"),
                                          ("src-bucket", "mp-obj1", self.file_path))
        LOGGER.info("All objects should be listed in relevant buckets")
        self.objects_in_buckets(bucket="src-bucket", objects=["obj1", "mp-obj1"])
        self.objects_in_buckets(bucket="dest-bucket", objects=["obj2", "obj4"])
        LOGGER.info("ENDED: Test Parallel copy and overwrite of same object "
                    "(for simple and multipart source objects)")

    @pytest.mark.tags("TEST-44791")
    @CTFailOn(error_handler)
    def test_44791(self):
        """Test Parallel self-copy and overwrite on same source bucket"""
        LOGGER.info("STARTED: Test Parallel self-copy and overwrite on same source bucket "
                    "(simple and multipart source objects)")
        LOGGER.info("Upload object1 to source bucket1")
        self.create_put_object("src-bucket", "obj1", 100)
        self.parallel_copy_and_put_object(
            ("src-bucket", "obj1", "src-bucket", "obj1", "InvalidRequest"),
            ("src-bucket", "obj1", self.file_path))
        LOGGER.info("Upload multipart object mp-obj1 to src-bucket")
        self.s3mp_obj.simple_multipart_upload("src-bucket", "mp-obj1", 1024, self.file_path, 4)
        self.parallel_copy_and_put_object(
            ("src-bucket", "mp-obj1", "src-bucket", "mp-obj1", "InvalidRequest"),
            ("src-bucket", "mp-obj1", self.file_path))
        LOGGER.info("All objects should be listed in relevant buckets")
        self.objects_in_buckets(bucket="src-bucket", objects=["obj1", "mp-obj1"])
        LOGGER.info("ENDED: Test Parallel self-copy and overwrite on same source bucket "
                    "(simple and multipart source objects)")

    @pytest.mark.tags("TEST-44809")
    @CTFailOn(error_handler)
    def test_44809(self):
        """Test Parallel put and copy on destination object"""
        LOGGER.info("STARTED: Test Parallel put and copy on destination object "
                    "(simple and multipart source objects)")
        LOGGER.info("Upload object1 to source bucket1")
        self.create_put_object("src-bucket", "obj1", 1024)
        self.parallel_copy_and_put_object(("src-bucket", "obj1", "src-bucket", "obj2"),
                                          ("src-bucket", "obj2", self.file_path))
        LOGGER.info("Upload multipart object obj3 to src-bucket")
        self.s3mp_obj.simple_multipart_upload("src-bucket", "mp-obj1", 1024, self.file_path, 4)
        self.parallel_copy_and_put_object(("src-bucket", "mp-obj1", "src-bucket", "obj4"),
                                          ("src-bucket", "obj4", self.file_path))
        LOGGER.info("All objects should be listed in relevant buckets")
        self.objects_in_buckets(bucket="src-bucket", objects=["obj1", "obj2", "mp-obj1", "obj4"])
        LOGGER.info("ENDED: Test Parallel put and copy on destination object "
                    "(simple and multipart source objects)")

    @pytest.mark.tags("TEST-44807")
    @CTFailOn(error_handler)
    def test_44807(self):
        """Test Parallel copy and overwrite of same source object"""
        LOGGER.info("STARTED: Test Parallel copy and overwrite of same source object "
                    "(simple and multipart source object)")
        LOGGER.info("Upload object1 to source bucket1")
        self.create_put_object("src-bucket", "obj1", 2048)
        self.parallel_copy_and_put_object(("src-bucket", "obj1", "src-bucket", "obj2"),
                                          ("src-bucket", "obj1", self.file_path))
        LOGGER.info("Upload multipart object obj3 to src-bucket")
        self.s3mp_obj.simple_multipart_upload("src-bucket", "obj3", 1024, self.file_path, 4)
        self.parallel_copy_and_put_object(("src-bucket", "obj3", "src-bucket", "obj4"),
                                          ("src-bucket", "obj3", self.file_path))
        LOGGER.info("All objects should be listed in relevant buckets")
        self.objects_in_buckets(bucket="src-bucket", objects=["obj1", "obj2", "obj3", "obj4"])
        LOGGER.info("ENDED: Test Parallel copy and overwrite of same source object "
                    "(simple and multipart source objects)")

    @pytest.mark.tags("TEST-44792")
    @CTFailOn(error_handler)
    def test_44792(self):
        """Test Parallel Self copy and put object in same bucket"""
        LOGGER.info("STARTED: Test Parallel Self copy and put object in same bucket "
                    "(simple and multipart source object)")
        LOGGER.info("Upload object1 to source bucket1")
        self.create_put_object("src-bucket", "obj1", 5 * 1024)
        self.parallel_copy_and_put_object(
            ("src-bucket", "obj1", "src-bucket", "obj1", "InvalidRequest"),
            ("src-bucket", "obj2", self.file_path))
        LOGGER.info("Upload multipart object obj3 to src-bucket")
        self.s3mp_obj.simple_multipart_upload("src-bucket", "mp-obj1", 3 * 1024, self.file_path, 4)
        self.parallel_copy_and_put_object(
            ("src-bucket", "mp-obj1", "src-bucket", "mp-obj1", "InvalidRequest"),
            ("src-bucket", "obj4", self.file_path))
        LOGGER.info("All objects should be listed in relevant buckets")
        self.objects_in_buckets(bucket="src-bucket", objects=["obj1", "obj2", "mp-obj1", "obj4"])
        LOGGER.info("ENDED: Test Parallel copy and overwrite of same source object "
                    "(simple and multipart source objects)")

    def parallel_copy_object(self, args1, args2):
        """Parallel copy object with given arguments"""
        LOGGER.info("Parallely, \n1. From %s copy %s to %s as %s\n2. From %s copy %s to %s as %s",
                    args1[0], args1[1], args1[2], args1[3], args2[0], args2[1], args2[2], args2[3])
        with multiprocessing.Pool(processes=2) as pool:
            process1 = pool.apply_async(self.copy_object_wrapper, args=args1)
            process2 = pool.apply_async(self.copy_object_wrapper, args=args2)
            assert_utils.assert_true(process1.get()[0], process1.get()[1])
            assert_utils.assert_true(process2.get()[0], process2.get()[1])

    @pytest.mark.tags("TEST-44806")
    @CTFailOn(error_handler)
    def test_44806(self):
        """Test Parallel copy from multiple source buckets to one or multiple destination buckets"""
        LOGGER.info("STARTED: Test Parallel copy from multiple source buckets to one or multiple "
                    "destination buckets (simple and multipart source objects)")
        for obj_type in ["simple", "multipart"]:
            if obj_type == "simple":
                resp1 = self.create_put_object("src-bucket1", f"{obj_type}-obj1", 10)
                resp2 = self.create_put_object("src-bucket1", f"{obj_type}-obj3", 100)
                resp3 = self.create_put_object("src-bucket2", f"{obj_type}-obj3", 1000)
            else:
                resp1 = self.s3mp_obj.simple_multipart_upload("src-bucket1", f"{obj_type}-obj1",
                                                              512, self.file_path, 4)
                resp2 = self.s3mp_obj.simple_multipart_upload("src-bucket1", f"{obj_type}-obj3",
                                                              1024, self.file_path, 4)
                resp3 = self.s3mp_obj.simple_multipart_upload("src-bucket2", f"{obj_type}-obj3",
                                                              2048, self.file_path, 4)
            LOGGER.info("Uploaded %s-obj1 to src-bucket1", obj_type)
            LOGGER.info("Uploaded %s-obj3 to src-bucket1", obj_type)
            LOGGER.info("Uploaded %s-obj3 to src-bucket2", obj_type)
            self.parallel_copy_object(("src-bucket1", f"{obj_type}-obj1", "dest-bucket1",
                                       f"{obj_type}-dest-obj2"),
                                      ("src-bucket1", f"{obj_type}-obj3", "dest-bucket1",
                                       f"{obj_type}-dest-obj2"))
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj2")
            assert_utils.assert_equal(resp2[1]["ETag"], resp[1]["ETag"])
            self.parallel_copy_object(("src-bucket1", f"{obj_type}-obj1", "dest-bucket1",
                                       f"{obj_type}-dest-obj2"),
                                      ("src-bucket2", f"{obj_type}-obj3", "dest-bucket2",
                                       f"{obj_type}-dest-obj4"))
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj2")
            assert_utils.assert_equal(resp1[1]["ETag"], resp[1]["ETag"])
            resp = self.s3_obj.object_info("dest-bucket2", f"{obj_type}-dest-obj4")
            assert_utils.assert_equal(resp3[1]["ETag"], resp[1]["ETag"])
            self.parallel_copy_object(("src-bucket1", f"{obj_type}-obj1", "dest-bucket1",
                                       f"{obj_type}-dest-obj6"),
                                      ("src-bucket2", f"{obj_type}-obj3", "dest-bucket1",
                                       f"{obj_type}-dest-obj6"))
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj6")
            assert_utils.assert_equal(resp3[1]["ETag"], resp[1]["ETag"])
            self.parallel_copy_object(("src-bucket1", f"{obj_type}-obj1", "dest-bucket1",
                                       f"{obj_type}-dest-obj8"),
                                      ("src-bucket1", f"{obj_type}-obj3", "dest-bucket1",
                                       f"{obj_type}-dest-obj9"))
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj8")
            assert_utils.assert_equal(resp1[1]["ETag"], resp[1]["ETag"])
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj9")
            assert_utils.assert_equal(resp2[1]["ETag"], resp[1]["ETag"])
            self.parallel_copy_object(("src-bucket1", f"{obj_type}-obj1", "dest-bucket1",
                                       f"{obj_type}-dest-obj3"),
                                      ("src-bucket2", f"{obj_type}-obj3", "dest-bucket1",
                                       f"{obj_type}-dest-obj4"))
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj3")
            assert_utils.assert_equal(resp1[1]["ETag"], resp[1]["ETag"])
            resp = self.s3_obj.object_info("dest-bucket1", f"{obj_type}-dest-obj4")
            assert_utils.assert_equal(resp3[1]["ETag"], resp[1]["ETag"])

        LOGGER.info("ENDED: Test Parallel copy from multiple source buckets to one or multiple "
                    "destination buckets (simple and multipart source objects)")

    @pytest.mark.tags("TEST-44793")
    @CTFailOn(error_handler)
    def test_44793(self):
        """Test 10 times chain Copy operation (simple and multipart object)"""
        LOGGER.info("STARTED: Test 10 times chain Copy operation (simple and multipart object)")

        LOGGER.info("Upload obj1 to src-bucket1")
        LOGGER.info("Create 10 destination buckets - dest-bucket2, ….dest-bucket11")
        bucket_prefix = "test-44793-dest-bucket"
        buckets = ["src-bucket1"]
        no_of_destinations = 10
        for num in range(no_of_destinations):
            bucket = f"{time.time()}-{bucket_prefix}-{num}"
            resp = self.s3_obj.create_bucket(bucket)
            assert_utils.assert_true(resp[0], resp[1])
            buckets.append(bucket)
        for obj_type in ["simple", "multipart"]:
            if obj_type == "simple":
                obj = "obj1"
                resp = self.create_put_object("src-bucket1", obj, 10)
                etag = resp[1]["ETag"]
            else:
                obj = "mp-obj1"
                resp = self.s3mp_obj.simple_multipart_upload("src-bucket1", obj, 1024,
                                                             self.file_path, 4)
                etag = resp[1]["ETag"]
            LOGGER.info("Copy %s object from src-bucket1 to dest-bucket2.", obj_type)
            for i in range(no_of_destinations):
                source = buckets[i]
                destination = buckets[i + 1]
                LOGGER.info("Copy object from %s to %s.", source, destination)
                self.s3_obj.copy_object(source, obj, destination, obj)
            LOGGER.info("Head %s objects in all buckets and match Etags", obj_type)
            for bucket in buckets:
                resp = self.s3_obj.object_list(bucket)
                assert_utils.assert_true(obj in resp[1])
                resp = self.s3_obj.object_info(bucket, obj)
                assert_utils.assert_equal(resp[1]["ETag"], etag)
        buckets.remove("src-bucket1")
        self.s3_obj.delete_multiple_buckets(buckets)
        LOGGER.info("ENDED: Test 10 times chain Copy operation (simple and multipart object)")
