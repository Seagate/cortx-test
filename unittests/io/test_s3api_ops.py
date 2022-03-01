#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""UTs for s3api."""

import os
import shutil
import unittest
from time import perf_counter_ns
from config import S3_CFG
from unittests.io import logger
from commons.utils.system_utils import create_file
from libs.io.s3api.s3_bucket_ops import S3Bucket
from libs.io.s3api.s3_object_ops import S3Object
from libs.io.s3api.s3_multipart_ops import S3MultiParts


# pylint: disable-msg=too-many-instance-attributes
class TestS3APIOperation(unittest.TestCase):
    """Tests suite for s3api operations."""

    def setUp(self) -> None:
        """Test pre-requisite."""
        self.s3bkt_obj = S3Bucket(S3_CFG.access_key, S3_CFG.secret_key,
                                  endpoint_url=S3_CFG.endpoint)
        self.s3obj_obj = S3Object(S3_CFG.access_key, S3_CFG.secret_key,
                                  endpoint_url=S3_CFG.endpoint)
        self.s3mpart_obj = S3MultiParts(S3_CFG.access_key, S3_CFG.secret_key,
                                        endpoint_url=S3_CFG.endpoint)
        self.bkt_name1 = "s3bkt1-{}".format(perf_counter_ns())
        self.bkt_name2 = "s3bkt2-{}".format(perf_counter_ns())
        self.obj_name1 = "s3obj1-{}".format(perf_counter_ns())
        self.obj_name2 = "s3obj2-{}".format(perf_counter_ns())
        self.dpath = os.path.join(os.getcwd(), "TestData")
        if not os.path.exists(self.dpath):
            os.makedirs(self.dpath)
        self.fpath = os.path.join(self.dpath, self.obj_name1)
        self.down_path = os.path.join(self.dpath, self.obj_name2)

    def tearDown(self) -> None:
        """Test post-requisite."""
        bkt_list = self.s3bkt_obj.list_bucket()
        for bkt_name in bkt_list:
            self.s3bkt_obj.delete_bucket(bkt_name, force=True)
        if os.path.exists(self.dpath):
            shutil.rmtree(self.dpath)
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
        logger.info(resp)
        self.assertEqual(resp, 0, msg="Failed to fetch bucket storage: {}".format(resp))
        resp = self.s3bkt_obj.delete_bucket(self.bkt_name1)
        logger.info(resp)

    def test_s3api_object_operations(self):
        """Test s3api object operations."""
        resp = self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        resp = create_file(self.fpath, count=10)
        logger.info(resp)
        resp = self.s3obj_obj.upload_object(self.bkt_name1, self.obj_name1, self.fpath)
        logger.info(resp)
        resp = self.s3obj_obj.list_objects(self.bkt_name1)
        logger.info(resp)
        self.assertNotIn(self.bkt_name1, resp)
        resp = self.s3obj_obj.head_object(self.bkt_name1, self.obj_name1)
        logger.info(resp)
        resp = self.s3obj_obj.get_object(self.bkt_name1, self.obj_name1)
        logger.info(resp)
        resp = self.s3obj_obj.download_object(self.bkt_name1, self.obj_name1, self.down_path)
        logger.info(resp)
        self.assertTrue(os.path.exists(self.down_path),
                        f"Failed to download file: {self.down_path}")
        resp = self.s3bkt_obj.create_bucket(self.bkt_name2)
        logger.info(resp)
        resp = self.s3obj_obj.copy_object(
            self.bkt_name1,
            self.obj_name1,
            self.bkt_name2,
            self.obj_name2)
        logger.info(resp)
        resp = self.s3obj_obj.get_object(self.bkt_name2, self.obj_name2, ranges="")
        logger.info(resp)
        resp = self.s3obj_obj.delete_object(self.bkt_name1, self.obj_name1)
        logger.info(resp)

    def test_s3api_multipart_operations(self):
        """Test s3api multipart operations."""
        resp = self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        resp = self.s3mpart_obj.create_multipart_upload(self.bkt_name1, self.obj_name1)
        logger.info(resp)
        mpu_id = resp["UploadId"]
        parts = []
        for i in range(1, 10):
            resp = self.s3mpart_obj.upload_part(str(os.urandom(5242880 * i)), self.bkt_name1,
                                                self.obj_name1, upload_id=mpu_id, part_number=i)
            logger.info(resp)
            parts.append({"PartNumber": i, "ETag": resp["ETag"]})
        resp = self.s3mpart_obj.list_parts(mpu_id, self.bkt_name1, self.obj_name1)
        logger.info(resp)
        resp = self.s3mpart_obj.list_multipart_uploads(self.bkt_name1)
        logger.info(resp)
        resp = self.s3mpart_obj.complete_multipart_upload(
            mpu_id, parts, self.bkt_name1, self.obj_name1)
        logger.info(resp)


if __name__ == '__main__':
    unittest.main()
