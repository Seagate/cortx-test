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
# You should have received a copy of the GNU Affero General Public License along with this program.
# If not, see <https://www.gnu.org/licenses/>.# For any questions about this software or
# licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""This file contains s3 multipart partcopy fixed sizes test script for io stability."""

from __future__ import division

import hashlib
import logging
import os
import random
from datetime import datetime, timedelta
from time import perf_counter_ns
from typing import Union
from botocore.exceptions import ClientError
from libs.io.s3api.s3_multipart_ops import S3MultiParts
from libs.io.s3api.s3_object_ops import S3Object
from libs.io.s3api.s3_bucket_ops import S3Bucket

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods, too-many-statements
class TestMultiPartsPartCopy(S3MultiParts, S3Object, S3Bucket):
    """S3 multipart class for executing given io stability workload"""

    # pylint: disable=too-many-arguments, too-many-instance-attributes
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, use_ssl: bool,
                 object_size: Union[dict, int, bytes], part_range: dict, seed: int,
                 test_id: str = None, range_read: bytes = None, duration: timedelta = None) -> None:
        """
        s3 multipart init class.
        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint with http or https.
        :param test_id: Test ID string.
        :param use_ssl: To use secure connection.
        :param duration: Duration timedelta object, if not given will run for 100 days.
        """
        super().__init__(access_key, secret_key, endpoint_url=endpoint_url, use_ssl=use_ssl)
        random.seed(seed)
        self.duration = duration
        self.object_size = object_size
        self.part_range = part_range
        self.range_read = range_read
        self.iteration = 1
        self.min_duration = 10  # In seconds
        self.test_id = test_id if test_id else random.randrange(24, 240)
        self.finish_time = datetime.now() + duration if duration else datetime.now() + \
            timedelta(hours=int(100 * 24))

    # pylint: disable=too-many-locals
    async def execute_multipart_partcopy_workload(self):
        """Execute multipart workload for specific duration."""
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            try:
                s3_object = "s3-obj-{}-{}".format(self.test_id, perf_counter_ns())
                mpart_bucket = "s3mpart-bkt-{}-{}".format(self.test_id, perf_counter_ns())
                mpart_object = "s3mpart-obj-{}-{}".format(self.test_id, perf_counter_ns())
                logger.info("Multipart Bucket name: %s", mpart_bucket)
                logger.info("Object name: %s", s3_object)
                logger.info("Multipart Object name: %s", mpart_object)
                number_of_parts = random.randrange(self.part_range["start"], self.part_range["end"])
                logger.info("Number of parts: %s", number_of_parts)
                assert number_of_parts > 10000, "Number of parts should be equal/less than 10k"
                single_part_size = self.object_size // number_of_parts
                logger.info("single part size: %s MB", single_part_size / (1024 ** 2))
                assert single_part_size > 5120,\
                    "Single part size should be within range and should not be greater than 5GB."
                logger.info("Create s3 bucket: %s", mpart_bucket)
                resp = await self.create_bucket(mpart_bucket)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200, \
                    f"Failed to create bucket: {mpart_bucket}"
                logger.info("Create multipart upload: s3://%s/%s", mpart_bucket, mpart_object)
                resp = await self.create_multipart_upload(mpart_bucket, mpart_object)
                assert resp["UploadId"] is not None, f"Failed to initiate multipart upload: {resp}"
                mpu_id = resp["UploadId"]
                logger.info("Upload id: %s", mpu_id)
                parts = list()
                file_hash = hashlib.sha256()
                random_part = random.randrange(1, number_of_parts + 1)
                logger.info("Started multipart upload.")
                for i in range(1, number_of_parts + 1):
                    byte_s = os.urandom(single_part_size)
                    if i == random_part:
                        resp = await self.upload_object(body=byte_s, bucket=mpart_bucket,
                                                        key=s3_object)
                        assert resp["ETag"] is not None, f"Failed upload part: {resp}"
                        resp = await self.upload_part_copy(f"{mpart_bucket}/{s3_object}",
                                                           mpart_bucket, s3_object, part_number=i,
                                                           upload_id=mpu_id)
                        parts.append({"PartNumber": i, "ETag": resp[1]["CopyPartResult"]["ETag"]})
                    else:
                        resp = await self.upload_part(byte_s, mpart_bucket, mpart_object,
                                                      upload_id=mpu_id, part_number=i)
                        assert resp["ETag"] is not None, f"Failed upload part: {resp}"
                        parts.append({"PartNumber": i, "ETag": resp["ETag"]})
                    file_hash.update(byte_s)
                upload_obj_checksum = file_hash.hexdigest()
                logger.info("uploaded object checksum: %s", upload_obj_checksum)
                logger.info("List parts from mpu: %s.", mpu_id)
                resp = await self.list_parts(mpu_id, mpart_bucket, mpart_object)
                assert resp, f"Failed to list parts: {resp}"
                logger.info("List multipart uploads: s3://%s", mpart_bucket)
                resp = await self.list_multipart_uploads(mpart_bucket)
                assert resp, f"Failed to list multipart uploads: {resp}"
                logger.info("Complete multipart uploads: s3://%s/%s", mpart_bucket, mpart_object)
                resp = await self.complete_multipart_upload(mpu_id, parts, mpart_bucket,
                                                            mpart_object)
                assert resp, f"Failed to completed multi parts: {resp}"
                logger.info("Check object '%s' uploaded using head object operation.", mpart_object)
                resp = await self.head_object(mpart_bucket, mpart_object)
                assert resp, f"Failed to do head object on {mpart_object}"
                logger.info("Get s3 object '%s' and calculate checksum.", mpart_object)
                download_obj_checksum = await self.get_s3object_checksum(
                    mpart_bucket, mpart_object, single_part_size)
                logger.info("Checksum of s3 object: %s", download_obj_checksum)
                if upload_obj_checksum != download_obj_checksum:
                    raise ClientError(
                        f"Failed to match checksum: {upload_obj_checksum}, {download_obj_checksum}",
                        operation_name="Match checksum")
                if self.range_read:
                    logger.info("Get object using suggested range read '%s'.", self.range_read)
                    resp = await self.get_object(bucket=mpart_bucket,
                                                 key=mpart_object,
                                                 ranges=f"'bytes=0-{self.range_read}'")
                    assert resp['Body'].read() is not None, f"Failed to read bytes " \
                                                            f"{self.range_read} from " \
                                                            f"s3://{mpart_bucket}/{mpart_object}"
                logger.info("Delete bucket: s3://%s", mpart_bucket)
                resp = await self.delete_bucket(mpart_bucket, force=True)
                assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204, \
                    f"Failed to delete s3 bucket: {mpart_bucket}"
            except Exception as err:
                logger.exception(err)
                raise err
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                return True, "Multipart execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
