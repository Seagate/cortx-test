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
#

"""UTs for s3api."""

import os
import unittest
from time import perf_counter_ns
from config import S3_CFG
from unittests.io import logger
from commons.utils.system_utils import create_file
from libs.io.s3api.s3_bucket_ops import S3Bucket
from libs.io.s3api.s3_object_ops import S3Object
from libs.io.s3api.s3_multipart_ops import S3MultiParts


class TestS3APIOperation(unittest.TestCase):

    def setUp(self) -> None:
        """Test pre-requisite."""
        self.s3bkt_obj = S3Bucket(S3_CFG["access_key"], S3_CFG["secret_key"], S3_CFG["endpoint"])
        self.s3obj_obj = S3Object(S3_CFG["access_key"], S3_CFG["secret_key"], S3_CFG["endpoint"])
        self.s3mpart_obj = S3MultiParts(
            S3_CFG["access_key"],
            S3_CFG["secret_key"],
            S3_CFG["endpoint"])
        self.bkt_name1 = "s3bkt1-{}".format(perf_counter_ns())
        self.bkt_name2 = "s3bkt2-{}".format(perf_counter_ns())
        self.obj_name1 = "s3obj1-{}".format(perf_counter_ns())
        self.obj_name2 = "s3obj2-{}".format(perf_counter_ns())
        self.dpath = os.path.join(os.getcwd(), "TestData")
        self.fpath = os.path.join(self.dpath, self.obj_name1)
        self.down_path = os.path.join(self.dpath, self.obj_name2)

    def tearDown(self) -> None:
        """Test post-requisite."""
        bkt_list = self.s3bkt_obj.list_bucket()
        for bkt_name in bkt_list:
            self.s3bkt_obj.delete_bucket(bkt_name, force=True)
        if os.path.exists(self.dpath):
            os.removedirs(self.dpath)
        del self.s3bkt_obj

    def test_s3api_bucket_operations(self):
        """Test s3api bucket operations."""
        resp = self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        resp = self.s3bkt_obj.list_bucket()
        self.assertGreater(len(resp), 0, msg="Failed to list buckets: {}.".format(resp))
        resp = self.s3bkt_obj.head_bucket(self.bkt_name1)
        logger.info(resp)
        resp = self.s3bkt_obj.get_bucket_location(self.bkt_name1)
        logger.info(resp)
        resp = self.s3bkt_obj.get_bucket_storage(self.bkt_name1)
        self.assertEqual(resp, 0, msg="Failed to fetch bucket storage: {}".format(resp))
        resp = self.s3bkt_obj.delete_bucket(self.bkt_name1)
        logger.info(resp)

    def test_s3api_object_operations(self):
        """Test s3api object operations."""
        resp = self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        resp = create_file(self.fpath, count=10)
        logger.debug(resp)
        resp = self.s3obj_obj.upload_object(self.bkt_name1, self.obj_name1, self.fpath)
        logger.debug(resp)
        resp = self.s3obj_obj.list_objects(self.bkt_name1)
        logger.debug(resp)
        self.assertNotIn(self.bkt_name1, resp)
        resp = self.s3obj_obj.head_object(self.bkt_name1, self.obj_name1)
        logger.debug(resp)
        resp = self.s3obj_obj.get_object(self.bkt_name1, self.obj_name1)
        logger.debug(resp)
        resp = self.s3obj_obj.download_object(self.bkt_name1, self.obj_name1, self.down_path)
        logger.debug(resp)
        self.assertTrue(os.path.exists(self.down_path),
                        f"Failed to download file: {self.down_path}")
        resp = self.s3bkt_obj.create_bucket(self.bkt_name2)
        logger.debug(resp)
        resp = self.s3obj_obj.copy_object(
            self.bkt_name1,
            self.obj_name1,
            self.bkt_name2,
            self.obj_name2)
        logger.debug(resp)
        resp = self.s3obj_obj.get_object(self.bkt_name2, self.obj_name2, ranges="")
        logger.debug(resp)
        resp = self.s3obj_obj.delete_object(self.bkt_name1, self.obj_name1)
        logger.debug(resp)

    def test_s3api_multipart_operations(self):
        """Test s3api multipart operations."""
        resp = self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.debug(resp)
        resp = self.s3mpart_obj.create_multipart_upload(self.bkt_name1, self.obj_name1)
        logger.debug(resp)
        mpu_id = resp["UploadId"]
        parts = []
        for i in range(1, 10):
            resp = self.s3mpart_obj.upload_part(str(os.urandom(542300)), self.bkt_name1,
                                                self.obj_name1, UploadId=mpu_id, PartNumber=i)
            logger.debug(resp)
            parts.append({"PartNumber": i, "ETag": resp[1]["ETag"]})
        resp = self.s3mpart_obj.list_parts(mpu_id, self.bkt_name1, self.obj_name1)
        logger.debug(resp)
        resp = self.s3mpart_obj.list_multipart_uploads(self.bkt_name1)
        logger.debug(resp)
        resp = self.s3mpart_obj.complete_multipart_upload(
            mpu_id, parts, self.bkt_name1, self.obj_name1)
        logger.debug(resp)


if __name__ == '__main__':
    unittest.main()
