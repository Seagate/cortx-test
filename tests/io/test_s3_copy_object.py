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
"""This file contains s3 Copy Object test script for io stability."""

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


class TestS3CopyObjects(S3Object, S3Bucket):
    """S3 Copy Object class for executing given io stability workload"""

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: str, object_size: Union[int, dict],seed: int,
                 duration: timedelta = None) -> None:
        """
        s3 Copy Object init class.

        :param access_key: access key
        :param secret_key: secret key
        :param endpoint_url: endpoint with http or https
        :param test_id: Test ID string
        :param use_ssl: To use secure connection
        :param object_size: Object size
        :param seed: Seed to be used for random data generator
        :param duration: Duration timedelta object, if not given will run for 100 days
        """
        super().__init__(access_key, secret_key, endpoint_url=endpoint_url, use_ssl=use_ssl)
        random.seed(seed)
        self.duration = duration
        self.object_size = object_size
        self.test_id = test_id
        self.iteration = 1
        self.min_duration = 10  # In seconds
        if duration:
            self.finish_time = datetime.now() + duration
        else:
            datetime.now() + timedelta(hours=int(100 * 24))
        self.buf_size = 1024 * 1024 * 50

    def execute_copy_object_workload(self):
        """Execute copy object workload for specific duration."""
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            bucket1 = f"bucket-1-{self.iteration}-{time.perf_counter_ns()}"
            bucket2 = f"bucket-2-{self.iteration}-{time.perf_counter_ns()}"
            object1 = f"object-1-{self.iteration}-{time.perf_counter_ns()}"
            object2 = f"object-2-{self.iteration}-{time.perf_counter_ns()}"
            try:
                self.create_bucket(bucket1)
                logger.info(f"Created bucket {bucket1}")
                self.create_bucket(bucket2)
                logger.info(f"Created bucket {bucket2}")
                # Put object in bucket1
                if not isinstance(self.object_size, dict):
                    file_size = self.object_size
                else:
                    file_size = random.randrange(self.object_size["start"], self.object_size["end"])
                with open(object1, 'wb') as fout:
                    fout.write(os.urandom(file_size))
                self.upload_object(bucket1, object1, object1)
                ret1 = self.head_object(bucket1, object1)
                # copy object from bucket-1 to bucket-2 in same account
                self.copy_object(bucket1, object1, bucket2, object2)
                ret2 = self.head_object(bucket2, object2)
                assert ret1["etag"] == ret2["etag"]
                # Download source and destination object and compare checksum
                self.download_object(bucket2, object2, object2)
                assert self.get_s3object_checksum(object1), self.get_s3object_checksum(object2)
                # Delete source object from bucket-1
                self.delete_object(bucket1, object1)
                # List destination object from bucket-2
                self.head_object(bucket2, object2)
                # Delete destination object from bucket-2
                self.delete_object(bucket2, object2)
                self.delete_bucket(bucket1)
                self.delete_bucket(bucket2)
            except (ClientError, IOError, AssertionError) as err:
                logger.exception(err)
                return False, str(err)
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                return True, "Copy Object execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
