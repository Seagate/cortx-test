#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

"""S3Background or Delayed Delete test module."""

import logging
import os
import time
from multiprocessing import Pool

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_PATH
from commons.utils import assert_utils, system_utils
from commons.utils.config_utils import read_yaml
from libs.s3 import ACCESS_KEY, SECRET_KEY, s3_test_lib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from scripts.s3_bench import s3bench

DEL_CFG = read_yaml("config/s3/test_delayed_delete.yaml")[1]


class TestDelayedDelete:
    """S3Background or Delayed Delete test suit."""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.s3_obj = s3_test_lib.S3TestLib()
        cls.s3_mp_obj = S3MultipartTestLib()
        cls.test_dir_path = os.path.join(TEST_DATA_PATH, "TestDelayedDelete")
        cls.test_file = "testfile.txt"
        cls.test_file_path = None

    def setup_method(self):
        """Create test data directory"""
        self.log.info("STARTED: Test Setup")
        if not system_utils.path_exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", resp)
        self.test_file_path = os.path.join(self.test_dir_path,
                                           self.test_file.format(str(int(time.time()))))

    def teardown_method(self):
        """Delete test data file"""
        self.log.info("STARTED: Test Teardown")
        if system_utils.path_exists(self.test_file_path):
            resp = system_utils.remove_file(self.test_file_path)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("removed path: %s, resp: %s", self.test_file_path, resp)

    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28990")
    @CTFailOn(error_handler)
    def test_28990(self):
        """Verify background deletes using multiple objects delete operation"""
        self.log.info("Started: Verify background deletes using multiple objects delete operation")

        bucket_name = f"test-28990-bucket-{str(int(time.time()))}"
        clients = 5
        samples = 1000
        object_size = "2Mb"

        # Run s3bench workload of 1000 objects with cleanup option
        resp = s3bench.setup_s3bench()
        assert_utils.assert_true(resp, "Could not setup s3bench.")
        resp = s3bench.s3bench(ACCESS_KEY, SECRET_KEY, bucket=bucket_name, num_clients=clients,
                               num_sample=samples, obj_name_pref="test-object-",
                               obj_size=object_size, skip_cleanup=False, duration=None,
                               log_file_prefix="TEST-28990")
        self.log.info("Log Path %s", resp[1])
        assert_utils.assert_false(s3bench.check_log_file_error(resp[1]),
                                  f"S3bench workload for object size {object_size} failed."
                                  f"Please read log file {resp[1]}")

        # Check bucket is not accessible
        buckets = self.s3_obj.bucket_list()[1]
        assert_utils.assert_not_in(bucket_name, buckets, f"{bucket_name} bucket is present")

        self.log.info("Completed: Verify background deletes using multiple "
                      "objects delete operation")

    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28991")
    @CTFailOn(error_handler)
    def test_28991(self):
        """Verify background deletes when ran s3bench workload on multiple buckets"""
        self.log.info("Started: Verify background deletes when ran s3bench workload "
                      "on multiple buckets")

        # Run s3bench workload of 1000 objects parallel on 3 buckets with cleanup option
        resp = s3bench.setup_s3bench()
        assert_utils.assert_true(resp, "Could not setup s3bench.")
        pool = Pool(processes=3)
        buckets = [f"test-28991-bucket-{i}-{str(int(time.time()))}" for i in range(3)]
        pool.starmap(s3bench.s3bench_workload,
                     [(buckets[0], "TEST-28991", "2Mb", 3, 400, ACCESS_KEY, SECRET_KEY),
                      (buckets[1], "TEST-28991", "2Mb", 3, 400, ACCESS_KEY, SECRET_KEY),
                      (buckets[2], "TEST-28991", "2Mb", 3, 400, ACCESS_KEY, SECRET_KEY)])

        # Check if entries are getting deleted
        listed_buckets = self.s3_obj.bucket_list()[1]
        for bucket in buckets:
            assert_utils.assert_not_in(bucket, listed_buckets, f"{bucket} bucket is present")

        self.log.info("Completed: Verify background deletes when ran s3bench workload "
                      "on multiple buckets")

    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28992")
    @CTFailOn(error_handler)
    def test_28992(self):
        """Verify if deletion is successful post simple object delete"""
        self.log.info("Started: Verify if deletion is successful post simple object delete")

        # Create a bucket
        bucket_name = f"test-28992-bucket-{int(time.time())}"
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Bucket %s is created", bucket_name)

        # Create a object
        self.log.info("Create file: %s", self.test_file_path)
        system_utils.create_file(self.test_file_path, 2, "/dev/urandom", '1M')

        # Upload a object
        object_name = self.test_file
        resp = self.s3_obj.put_object(bucket_name, object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])

        # Get LastModified time using head object
        res = self.s3_obj.object_info(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        old_last_modified = res[1]["LastModified"]

        # Re-upload same object
        time.sleep(5)
        resp = self.s3_obj.put_object(bucket_name, object_name, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])

        # Get LastModified time using head object
        res = self.s3_obj.object_info(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        new_last_modified = res[1]["LastModified"]

        # Make sure the LastModified time is changed after re-uploading the object
        assert_utils.assert_true(new_last_modified > old_last_modified,
                                 f"LastModified for the old object {old_last_modified}. "
                                 f"LastModified for the new object is {new_last_modified}")

        # Deleting buckets & objects
        self.log.info("Deleting bucket %s", bucket_name)
        res = self.s3_obj.delete_bucket(bucket_name, True)
        assert_utils.assert_true(res[0], res[1])

        self.log.info("Completed: Verify if deletion is successful post simple object delete")

    @pytest.mark.s3_delete
    @pytest.mark.tags("TEST-28993")
    @CTFailOn(error_handler)
    def test_28993(self):
        """Verify if deletion is successful post Multipart object delete"""
        self.log.info("Started: Verify if deletion is successful post Multipart object delete")

        test_config = DEL_CFG["test_28993"]

        # Create bucket
        bucket_name = f"test-28993-bucket-{int(time.time())}"
        res = self.s3_obj.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)

        # Do multipart upload
        object_name = self.test_file
        self.s3_mp_obj.simple_multipart_upload(bucket_name, object_name, test_config["file_size"],
                                               self.test_file_path, test_config["total_parts"])

        # Delete object
        res = self.s3_obj.delete_object(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])

        # Verify object should not present after deletion
        try:
            response = self.s3_obj.object_info(bucket_name, object_name)
        except CTException as error:
            self.log.error("%s", error)
            assert_utils.assert_in("Not Found", error.message, error.message)
        else:
            self.log.error("Response = %s", response)
            assert_utils.assert_true(False, f"{object_name} object is still accessible "
                                            f"from bucket {bucket_name}")

        # Deleting buckets & objects
        self.log.info("Deleting bucket %s", bucket_name)
        res = self.s3_obj.delete_bucket(bucket_name, True)
        assert_utils.assert_true(res[0], res[1])

        self.log.info("Completed: Verify if deletion is successful post Multipart object delete")
