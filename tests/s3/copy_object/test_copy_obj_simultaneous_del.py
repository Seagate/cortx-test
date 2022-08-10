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

"""S3 copy object for simultaneous delete test module."""

import logging
import multiprocessing
import os

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
class TestCopyObjectSimultaneousDelete:
    """S3 copy object for simultaneous delete class."""

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
        self.buckets = ["src-buck", "dest-buck"]
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
    def delete_object_wrapper(bucket, obj):
        """ Delete object wrapper for multiprocessing"""
        s3_obj = s3_test_lib.S3TestLib()
        return s3_obj.delete_object(bucket, obj)

    def create_put_parallel_copy_and_delete_object(self, copy_args, delete_args, is_mpu=False):
        """Create and uplaod object to bucket and then Parallel copy object and put object with
        given arguments"""
        for obj_size in [1024, 5*1024]:
            if obj_size == 1024:
                LOGGER.info("Upload a large object (~1GB) srcobj to srcbuck")
            else:
                LOGGER.info("Upload a large object (~5GB) srcobj to srcbuck")
            if is_mpu:
                resp = system_utils.create_file(fpath=copy_args[6], count=obj_size, b_size="1M")
                assert_utils.assert_true(resp[0], resp[1])
                resp = self.s3mp_obj.simple_multipart_upload(copy_args[0], copy_args[1], obj_size,
                                                             copy_args[6], copy_args[5])
            else:
                self.create_put_object(copy_args[0], copy_args[1], obj_size)
            LOGGER.info("Parallely, \n1. From %s copy %s to %s as %s\n2. Delete %s from %s",
                        copy_args[0], copy_args[1], copy_args[2], copy_args[3], delete_args[1],
                        delete_args[1])
            with multiprocessing.Pool(processes=2) as pool:
                process1 = pool.apply_async(self.copy_object_wrapper, args=copy_args[:5])
                process2 = pool.apply_async(self.delete_object_wrapper, args=delete_args)
                assert_utils.assert_true(process1.get()[0], process1.get()[1])
                assert_utils.assert_true(process2.get()[0], process2.get()[1])

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-45516")
    @CTFailOn(error_handler)
    def test_45516(self):
        """Test Parallel copy and put operation from same source bucket"""
        LOGGER.info("STARTED: Test Delete source object when copy simple object is in progress")
        self.create_put_parallel_copy_and_delete_object(("src-buck", "src-obj", "dest-buck",
                                                        "dest-obj", "NoSuchKey"),
                                                        ("src-buck", "src-obj"))
        LOGGER.info("ENDED: Test Delete source object when copy simple object is in progress")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-45518")
    @CTFailOn(error_handler)
    def test_45518(self):
        """Test Delete destination object when copy simple object is in progress"""
        LOGGER.info("STARTED: Test Delete destination object when copy simple object is in "
                    "progress")
        self.create_put_parallel_copy_and_delete_object(("src-buck", "src-obj", "dest-buck",
                                                         "dest-obj", None),
                                                        ("dest-buck", "dest-obj"))
        LOGGER.info("ENDED: Test Delete destination object when copy simple object is in progress")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-45519")
    @CTFailOn(error_handler)
    def test_45519(self):
        """Test Delete source object when copy simple object is in progress"""
        LOGGER.info("STARTED: Test Delete source object when copy simple object is in progress in "
                    "the same bucket")
        self.create_put_parallel_copy_and_delete_object(("src-buck", "src-obj", "src-buck",
                                                         "dest-obj", "NoSuchKey"),
                                                        ("src-buck", "src-obj"))
        LOGGER.info("ENDED: Test Delete source object when copy simple object is in progress in "
                    "the same bucket")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-45523")
    @CTFailOn(error_handler)
    def test_45523(self):
        """Test Delete source object when copy multipart object is in progress"""
        LOGGER.info("STARTED: Test Delete source object when copy multipart object is in progress")
        LOGGER.info("Upload a large object (~1GB) srcobj to srcbuck")
        self.create_put_parallel_copy_and_delete_object(("src-buck", "src-obj", "dest-buck",
                                                         "dest-obj", "NoSuchKey", 4,
                                                         self.file_path), ("src-buck", "src-obj"),
                                                        is_mpu = True)
        LOGGER.info("ENDED: Test Delete source object when copy multipart object is in progress")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-45524")
    @CTFailOn(error_handler)
    def test_45524(self):
        """Test Delete destination object when copy multipart object is in progress"""
        LOGGER.info("STARTED: Test Delete destination object when copy multipart object is in "
                    "progress")
        self.create_put_parallel_copy_and_delete_object(("src-buck", "src-obj", "src-buck",
                                                         "dest-obj", None, 5,
                                                         self.file_path), ("dest-buck", "dest-obj"),
                                                        is_mpu=True)
        LOGGER.info("ENDED: Test Delete destination object when copy multipart object is in "
                    "progress")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-45525")
    @CTFailOn(error_handler)
    def test_45525(self):
        """Test Delete source object when copy multipart object is in progress in same bucket"""
        LOGGER.info("STARTED: Test Delete source object when copy multipart object is in "
                    "progress in same bucket")
        self.create_put_parallel_copy_and_delete_object(("src-buck", "src-obj", "src-buck",
                                                         "dest-obj", "NoSuchKey", 5,
                                                         self.file_path), ("src-buck", "src-obj"),
                                                        is_mpu=True)
        LOGGER.info("ENDED: Test Delete source object when copy multipart object is in "
                    "progress in same bucket")
