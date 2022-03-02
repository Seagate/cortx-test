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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""UTs for s3api."""

import os
import shutil
import asyncio
from time import perf_counter_ns
from config import S3_CFG
from unittests.io import logger
from commons.utils.system_utils import create_file
from libs.io.s3api.s3_bucket_ops import S3Bucket
from libs.io.s3api.s3_object_ops import S3Object
from libs.io.s3api.s3_multipart_ops import S3MultiParts


# pylint: disable-msg=too-many-instance-attributes
class TestS3APIOperation:
    """Tests suite for s3api operations."""

    def __init__(self) -> None:
        """Test pre-requisite."""
        self.s3bkt_obj = S3Bucket(
            S3_CFG.access_key, S3_CFG.secret_key, endpoint_url=S3_CFG.endpoint)
        self.s3obj_obj = S3Object(
            S3_CFG.access_key, S3_CFG.secret_key, endpoint_url=S3_CFG.endpoint)
        self.s3mpart_obj = S3MultiParts(
            S3_CFG.access_key, S3_CFG.secret_key, endpoint_url=S3_CFG.endpoint)
        self.bkt_name1 = "s3bkt1-{}".format(perf_counter_ns())
        self.bkt_name2 = "s3bkt2-{}".format(perf_counter_ns())
        self.obj_name1 = "s3obj1-{}".format(perf_counter_ns())
        self.obj_name2 = "s3obj2-{}".format(perf_counter_ns())
        self.dpath = os.path.join(os.getcwd(), "TestData")
        if not os.path.exists(self.dpath):
            os.makedirs(self.dpath)
        self.fpath = os.path.join(self.dpath, self.obj_name1)
        self.down_path = os.path.join(self.dpath, self.obj_name2)

    async def cleanup(self) -> None:
        """Test post-requisite."""
        bkt_list = await self.s3bkt_obj.list_buckets()
        for bkt_name in bkt_list:
            response = await self.s3bkt_obj.delete_bucket(bkt_name, force=True)
            logger.info(response)
        if os.path.exists(self.dpath):
            shutil.rmtree(self.dpath)
        del self.s3bkt_obj, self.obj_name1, self.s3mpart_obj

    async def test_s3api_bucket_operations(self):
        """Test s3api bucket operations."""
        logger.info("STARTED: Test bucket operations api.")
        logger.info("Created bucket.")
        resp = await self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        logger.info("List bucket.")
        resp = await self.s3bkt_obj.list_buckets()
        logger.info(resp)
        assert len(resp) > 0, "Failed to list buckets: {}.".format(resp)
        logger.info("Head bucket.")
        resp = await self.s3bkt_obj.head_bucket(self.bkt_name1)
        logger.info(resp)
        logger.info("Get bucket location.")
        resp = await self.s3bkt_obj.get_bucket_location(self.bkt_name1)
        logger.info(resp)
        logger.info("Delete bucket.")
        resp = await self.s3bkt_obj.delete_bucket(self.bkt_name1, force=True)
        logger.info(resp)
        logger.info("ENDED: Test bucket operations api.")

    async def test_s3api_object_operations(self):
        """Test s3api object operations."""
        resp = await self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        resp = create_file(self.fpath, count=10)
        logger.info(resp)
        resp = await self.s3obj_obj.upload_object(self.bkt_name1, self.obj_name1, self.fpath)
        logger.info(resp)
        resp = await self.s3obj_obj.list_objects(self.bkt_name1)
        logger.info(resp)
        assert self.bkt_name1 not in resp, f"Failed to create bucket: {resp}"
        resp = await self.s3obj_obj.head_object(self.bkt_name1, self.obj_name1)
        logger.info(resp)
        resp = await self.s3obj_obj.get_object(self.bkt_name1, self.obj_name1)
        logger.info(resp)
        resp = await self.s3obj_obj.download_object(self.bkt_name1, self.obj_name1, self.down_path)
        logger.info(resp)
        assert os.path.exists(self.down_path), f"Failed to download file: {self.down_path}"
        resp = await self.s3bkt_obj.create_bucket(self.bkt_name2)
        logger.info(resp)
        resp = await self.s3obj_obj.copy_object(
            self.bkt_name1,
            self.obj_name1,
            self.bkt_name2,
            self.obj_name2)
        logger.info(resp)
        resp = await self.s3obj_obj.get_object(self.bkt_name2, self.obj_name2, ranges="")
        logger.info(resp)
        resp = await self.s3obj_obj.delete_object(self.bkt_name1, self.obj_name1)
        logger.info(resp)

    async def test_s3api_multipart_operations(self):
        """Test s3api multipart operations."""
        logger.info("STARTED: Test multipart operations api.")
        logger.info("Create bucket.")
        resp = await self.s3bkt_obj.create_bucket(self.bkt_name1)
        logger.info(resp)
        logger.info("Create multipart upload.")
        resp = await self.s3mpart_obj.create_multipart_upload(self.bkt_name1, self.obj_name1)
        logger.info(resp)
        mpu_id = resp["UploadId"]
        parts = []
        logger.info("Upload parts.")
        for i in range(1, 21):
            resp = await self.s3mpart_obj.upload_part(os.urandom(5242880 * i), self.bkt_name1,
                                                      self.obj_name1, upload_id=mpu_id,
                                                      part_number=i)
            logger.info(resp)
            parts.append({"PartNumber": i, "ETag": resp["ETag"]})
        logger.info("List parts.")
        resp = await self.s3mpart_obj.list_parts(mpu_id, self.bkt_name1, self.obj_name1)
        logger.info(resp)
        assert len(resp) == 20, f"Failed to list parts: {len(resp)}"
        logger.info("List multipart uploads")
        resp = await self.s3mpart_obj.list_multipart_uploads(self.bkt_name1)
        logger.info(resp)
        logger.info("Complete multipart upload.")
        resp = await self.s3mpart_obj.complete_multipart_upload(
            mpu_id, parts, self.bkt_name1, self.obj_name1)
        logger.info(resp)
        logger.info("ENDED: Test multipart operations api.")


async def main():
    """main method."""
    s3api_obj = TestS3APIOperation()
    await s3api_obj.test_s3api_bucket_operations()
    await asyncio.sleep(10)
    await s3api_obj.test_s3api_multipart_operations()
    await s3api_obj.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
