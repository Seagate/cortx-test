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
"""This file contains S3 object range read operations test script for io stability."""

import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import Union

from botocore.exceptions import ClientError

from libs.io.s3api.s3_bucket_ops import S3Bucket
from libs.io.s3api.s3_object_ops import S3Object

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods, too-many-statements
class TestObjectRangeReadOps(S3Object, S3Bucket):
    """S3 Object range read operations class for executing given io stability workload"""

    # pylint: disable=too-many-arguments, too-many-locals, too-many-instance-attributes
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: str, object_size: Union[int, dict], seed: int,
                 range_read: Union[int, dict],
                 duration: timedelta = None) -> None:
        """
        s3 object operations init class.

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
        self.test_id = test_id
        self.min_duration = 10  # In seconds
        if duration:
            self.finish_time = datetime.now() + duration
        else:
            self.finish_time = datetime.now() + timedelta(hours=int(100 * 24))
        self.iteration = 1
        self.range_read = range_read
        self.parts = 3

    async def execute_object_range_read_workload(self):
        """Execute object range read operations workload for specific duration."""
        bucket_name = f'range-read-op-{self.test_id}-{time.perf_counter_ns()}'.lower()
        logger.info("Create bucket %s", bucket_name)
        await self.create_bucket(bucket_name)
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            try:
                if not isinstance(self.object_size, dict):
                    file_size = self.object_size
                else:
                    file_size = random.randrange(self.object_size["start"], self.object_size["end"])
                if not isinstance(self.range_read, dict):
                    range_read = self.range_read
                else:
                    range_read = random.randrange(self.range_read["start"], self.range_read["end"])
                # Put object in bucket1
                logger.info("Upload object to bucket %s", bucket_name)
                file_name = f'object-range-op-{time.perf_counter_ns()}'
                with open(file_name, 'wb') as fout:
                    fout.write(os.urandom(file_size))
                await self.upload_object(bucket_name, file_name, file_path=file_name)
                # Head object
                logger.info("Perform Head object")
                await self.head_object(bucket_name, file_name)
                # Consider three logical parts, select random offset, read given number of bytes
                # and compare checksum for each part
                part = int(file_size / self.parts)
                first_part_start = 0
                first_part_end = part
                second_part_start = part + 1
                second_part_end = part * 2
                third_part_start = second_part_end + 1
                third_part_end = file_size - range_read
                byte_range_loc_1 = random.randrange(first_part_start, first_part_end)
                byte_range_loc_2 = random.randrange(second_part_start, second_part_end)
                byte_range_loc_3 = random.randrange(third_part_start, third_part_end)
                checksum1 = await self.get_s3object_checksum(
                    bucket_name, file_name, 1024,
                    f'bytes={byte_range_loc_1}-{byte_range_loc_1 + range_read - 1}')
                checksum2 = await self.get_s3object_checksum(
                    bucket_name, file_name, 1024,
                    f'bytes={byte_range_loc_2}-{byte_range_loc_2 + range_read - 1}')
                checksum3 = await self.get_s3object_checksum(
                    bucket_name, file_name, 1024,
                    f'bytes={byte_range_loc_3}-{byte_range_loc_3 + range_read - 1}')
                checksum4 = self.checksum_part_file(file_name, byte_range_loc_1, range_read)
                checksum5 = self.checksum_part_file(file_name, byte_range_loc_2, range_read)
                checksum6 = self.checksum_part_file(file_name, byte_range_loc_3, range_read)
                assert checksum1 == checksum4, f"part {checksum1} is not matching for first part " \
                                               f"with {checksum4} "
                assert checksum2 == checksum5, f"part {checksum2} is not matching for first part " \
                                               f"with {checksum5} "
                assert checksum3 == checksum6, f"part {checksum3} is not matching for first part " \
                                               f"with {checksum6} "
                # Delete object
                logger.info("Delete %s object of bucket %s", file_name, bucket_name)
                await self.delete_object(bucket_name, file_name)
                os.remove(file_name)
            except (ClientError, IOError, AssertionError) as err:
                logger.exception(err)
                raise err
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                logger.info("Delete all objects of bucket %s", bucket_name)
                await self.delete_bucket(bucket_name, True)
                return True, "Bucket operation execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
