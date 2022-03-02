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
"""This file contains s3 multipart test script for io stability."""

from __future__ import division
import logging
import os
import random
import hashlib
from datetime import datetime, timedelta
from time import perf_counter_ns
from typing import Union
from botocore.exceptions import ClientError
from libs.io.s3api.s3_multipart_ops import S3MultiParts
from libs.io.s3api.s3_object_ops import S3Object
from libs.io.s3api.s3_bucket_ops import S3Bucket

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods, too-many-statements
class TestMultiParts(S3MultiParts, S3Object, S3Bucket):
    """S3 multipart class for executing given io stability workload"""

    # pylint: disable=too-many-arguments, too-many-locals, too-many-instance-attributes
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: bool, object_size: Union[dict, int, bytes], part_range: dict,
                 duration: timedelta = None) -> None:
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
        self.duration = duration
        self.mpart_bucket = "s3mpart-bkt-{}-{}".format(
            test_id.lower() if test_id else "sample", perf_counter_ns())
        self.s3mpart_object = "s3mpart-obj-{}-{}".format(
            test_id.lower() if test_id else "sample", perf_counter_ns())
        self.object_size = object_size
        self.part_range = part_range
        self.test_id = test_id
        self.iteration = 1
        self.min_duration = 10  # In seconds
        self.finish_time = datetime.now() + duration if duration else datetime.now() + \
            timedelta(hours=int(100 * 24))

    async def execute_multipart_workload(self):
        """Execute multipart workload for specific duration."""
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            try:
                file_size = random.randrange(
                    self.object_size["start"], self.object_size["end"]) if isinstance(
                    self.object_size, dict) else self.object_size
                number_of_parts = random.randrange(self.part_range["start"], self.part_range["end"])
                single_part_size = file_size // number_of_parts
                logger.info("single part size: %s MB", single_part_size / (1024 ** 2))
                response = await self.create_bucket(self.mpart_bucket)
                assert response["ResponseMetadata"]["HTTPStatusCode"] == 200, \
                    f"Failed to create bucket: {self.mpart_bucket}"
                response = await self.create_multipart_upload(
                    self.mpart_bucket, self.s3mpart_object)
                assert response["UploadId"] is not None, \
                    f"Failed to initiate multipart upload: {response}"
                mpu_id = response["UploadId"]
                parts = list()
                file_hash = hashlib.sha256()
                for i in range(1, number_of_parts + 1):
                    byte_s = os.urandom(single_part_size)
                    response = await self.upload_part(byte_s, self.mpart_bucket,
                                                      self.s3mpart_object, upload_id=mpu_id,
                                                      part_number=i)
                    assert response["ETag"] is not None, f"Failed upload part: {response}"
                    parts.append({"PartNumber": i, "ETag": response["ETag"]})
                    file_hash.update(byte_s)
                upload_obj_checksum = file_hash.hexdigest()
                logger.info("Checksum of uploaded object: %s", upload_obj_checksum)
                response = await self.list_parts(mpu_id, self.mpart_bucket, self.s3mpart_object)
                assert response, f"Failed to list parts: {response}"
                response = await self.list_multipart_uploads(self.mpart_bucket)
                assert response, f"Failed to list multipart uploads: {response}"
                response = await self.complete_multipart_upload(
                    mpu_id, parts, self.mpart_bucket, self.s3mpart_object)
                assert response, f"Failed to completed multi parts: {response}"
                response = await self.head_object(self.mpart_bucket, self.s3mpart_object)
                assert response, f"Failed to do head object on {self.s3mpart_object}"
                download_obj_checksum = await self.get_s3object_checksum(
                    self.mpart_bucket, self.s3mpart_object, single_part_size)
                logger.info("Checksum of s3 object: %s", download_obj_checksum)
                if upload_obj_checksum != download_obj_checksum:
                    raise ClientError(
                        f"Failed to match checksum: {upload_obj_checksum}, {download_obj_checksum}",
                        operation_name="Match checksum")
                response = await self.delete_bucket(self.mpart_bucket, force=True)
                assert response["ResponseMetadata"][
                    "HTTPStatusCode"] == 204, f"Failed to delete s3 bucket: {self.mpart_bucket}"
            except (ClientError, IOError, AssertionError) as err:
                logger.exception(err)
                raise ClientError(
                    error_response=str(err), operation_name="Execute multipart workload") from err
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                return True, "Multipart execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
