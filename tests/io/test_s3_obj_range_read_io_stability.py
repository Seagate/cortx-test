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

from botocore.exceptions import ClientError

from libs.io.s3api.s3_bucket_ops import S3Bucket
from libs.io.s3api.s3_object_ops import S3Object

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods, too-many-statements
class TestOjbectRangeReadOps(S3Object, S3Bucket):
    """S3 Object range read operations class for executing given io stability workload"""

    # pylint: disable=too-many-arguments, too-many-locals, too-many-instance-attributes
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: str, obj_start_size: int, obj_end_size: int, range_read,
                 duration: timedelta = None) -> None:
        """
        s3 object operations init class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint with http or https.
        :param test_id: Test ID string.
        :param use_ssl: To use secure connection.
        :param obj_start_size: Object size start range
        :param obj_end_size: Object size end range
        :param duration: Duration timedelta object, if not given will run for 100 days.
        """
        super().__init__(access_key, secret_key, endpoint_url=endpoint_url, use_ssl=use_ssl)
        self.duration = duration
        self.obj_start_size = obj_start_size
        self.obj_end_size = obj_end_size
        self.test_id = test_id
        self.min_duration = 10  # In seconds
        self.finish_time = datetime.now() + duration if duration else datetime.now() + \
                                                                      timedelta(hours=int(100 * 24))
        self.object_per_iter = 500
        self.iteration = 1
        self.range_read = range_read

    def execute_object_range_read_workload(self):
        """Execute bucket operations workload for specific duration."""
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            try:
                file_size = random.randrange(self.obj_start_size, self.obj_end_size)
                bucket_name = f'bucket-op-{time.perf_counter_ns()}'
                logger.info("Create bucket %s", bucket_name)
                self.create_bucket(bucket_name)
                # Put object in bucket1
                logger.info("Upload object to bucket %s", bucket_name)
                file_name = f'object-range-op-{time.perf_counter_ns()}'
                with open(file_name, 'wb') as fout:
                    fout.write(os.urandom(file_size))
                self.upload_object(bucket_name, file_name, file_name)
                # Head object
                logger.info("Perform Head object")
                self.head_object(bucket_name, file_name)
                # Consider three logical parts, select random offset, read given number of bytes and compare checksum for each part
                # part = int(file_size/3)
                # first_part_start = 0
                # first_part_end = part
                # second_part_start = part + 1
                # second_part_end = part * 2
                # third_part_start = second_part_end + 1
                # third_part_end = file_size
                # byte_range_loc_1 = random.randrange(first_part_start, first_part_end)
                # byte_range_loc_2 = random.randrange(second_part_start, second_part_end)
                # byte_range_loc_3 = random.randrange(third_part_start, third_part_end)
                # checksum1 = self.get_s3object_checksum(bucket_name, file_name, 1024, f'byte={byte_range_loc_1}-{byte_range_loc_1 + self.range_read}')
                # checksum2 = self.get_s3object_checksum(bucket_name, file_name, 1024, f'byte={byte_range_loc_2}-{byte_range_loc_1 + self.range_read}')
                # checksum3 = self.get_s3object_checksum(bucket_name, file_name, 1024, f'byte={byte_range_loc_3}-{byte_range_loc_1 + self.range_read}')
                # checksum4 = self.calculate_checksum(file_name, byte_range_loc_1, self.range_read)
                # checksum5 = self.calculate_checksum(file_name, byte_range_loc_2, self.range_read)
                # checksum6 = self.calculate_checksum(file_name, byte_range_loc_3, self.range_read)
                # assert checksum1 == checksum4, "part checksum is not matching for first part"
                # assert checksum2 == checksum5, "part checksum is not matching for second part"
                # assert checksum3 == checksum6, "part checksum is not matching for third part"

                               
                 # Delete object
                logger.info("Delete %s object of bucket %s", file_name, bucket_name)
                self.delete_object(bucket_name, file_name)
                
                #azahar
            except (ClientError, IOError, AssertionError) as err:
                logger.exception(err)
                return False, str(err)
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                return True, "Bucket operation execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
