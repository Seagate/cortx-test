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

"""Python Library to perform bucket operations using boto3 module."""
import logging
import os
import random
import time
from datetime import timedelta, datetime

from libs.io.s3api.s3_bucket_ops import S3Bucket
from libs.io.s3api.s3_object_ops import S3Object

logger = logging.getLogger()


class TestS3Object(S3Bucket, S3Object):
    """Class for bucket operations."""

    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: bool, object_size: dict, duration: timedelta = None):
        super().__init__(access_key, secret_key, endpoint_url=endpoint_url, use_ssl=use_ssl)
        self.duration = duration
        self.start_object_size = object_size["start"]
        self.end_object_size = object_size["end"]
        self.test_id = test_id
        self.iteration = 1
        self.min_duration = 10  # In seconds
        if duration:
            self.finish_time = datetime.now() + duration
        else:
            self.finish_time = datetime.now() + timedelta(hours=int(100 * 24))

    async def execute_object_workload(self):
        """Execute object workload with given parameters"""
        bucket = f'bucket-op-{time.perf_counter_ns()}'
        logger.info("Create bucket %s", bucket)
        await self.create_bucket(bucket)
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            try:
                file_size = random.randrange(self.start_object_size, self.end_object_size)
                file_name = f'object-bucket-op-{time.perf_counter_ns()}'
                with open(file_name, 'wb') as fout:
                    fout.write(os.urandom(file_size))
                checksum_in = self.checksum_file(file_name)
                logger.info("Checksum IN = %s", checksum_in)
                await self.upload_object(bucket, file_name, file_name)
                logger.info("Uploaded s3://%s/%s", bucket, file_name)
                logger.info("Perform Head bucket")
                await self.head_object(bucket, file_name)
                logger.info("Get Object")
                checksum_out = await self.get_s3object_checksum(bucket, file_name)
                assert checksum_in == checksum_out, "Checksum are not equal"
                logger.info("Checksum Out = %s", checksum_out)
                logger.info("Delete object")
                await self.delete_object(bucket, file_name)
                os.remove(file_name)
            except Exception as err:
                logger.exception(err)
                raise err
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                await self.delete_bucket(bucket, True)
                return True, "Multipart execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
