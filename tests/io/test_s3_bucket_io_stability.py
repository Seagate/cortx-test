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
"""This file contains S3 Bucket operations test script for io stability."""

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
class TestBucketOps(S3Object, S3Bucket):
    """S3 Bucket Operations class for executing given io stability workload"""

    # pylint: disable=too-many-arguments, too-many-locals, too-many-instance-attributes
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: str, object_size: Union[int, dict], seed: int,
                 duration: timedelta = None) -> None:
        """
        s3 bucket operations init class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint with http or https.
        :param test_id: Test ID string.
        :param use_ssl: To use secure connection.
        :param obj_start_size: Object size start range
        :param obj_end_size: Object size end range
        :param seed: Seed to be used for random data generator
        :param duration: Duration timedelta object, if not given will run for 100 days.
        """
        super().__init__(access_key, secret_key, endpoint_url=endpoint_url, use_ssl=use_ssl)
        random.seed(seed)
        self.duration = duration
        self.object_size = object_size
        self.test_id = test_id
        self.min_duration = 10  # In seconds
        self.finish_time = datetime.now() + duration \
            if duration else datetime.now() + timedelta(hours=int(100 * 24))
        self.object_per_iter = 500
        self.iteration = 1

    async def execute_bucket_workload(self):
        """Execute bucket operations workload for specific duration."""
        while True:
            logger.info("Iteration %s is started...", self.iteration)
            try:
                file_size = self.object_size if not isinstance(
                    self.object_size, dict) else random.randrange(
                    self.object_size["start"], self.object_size["end"])
                bucket_name = f'bucket-op-{self.test_id}-{time.perf_counter_ns()}'.lower()
                logger.info("Create bucket %s", bucket_name)
                await self.create_bucket(bucket_name)
                logger.info("Upload %s objects to bucket %s", self.object_per_iter, bucket_name)
                for _ in range(0, self.object_per_iter):
                    file_name = f'object-bucket-op-{time.perf_counter_ns()}'
                    with open(file_name, 'wb') as fout:
                        fout.write(os.urandom(file_size))
                    await self.upload_object(bucket_name, file_name, file_path=file_name)
                    logger.info("Delete generated file")
                    os.remove(file_name)
                logger.info("List all buckets")
                await self.list_buckets()
                logger.info("List objects of created %s bucket", bucket_name)
                await self.list_objects(bucket_name)
                logger.info("Perform Head bucket")
                await self.head_bucket(bucket_name)
                logger.info("Delete all objects of bucket %s", bucket_name)
                await self.delete_bucket(bucket_name, True)
            except (ClientError, IOError, AssertionError) as err:
                logger.exception(err)
                raise err
            timedelta_v = (self.finish_time - datetime.now())
            timedelta_sec = timedelta_v.total_seconds()
            if timedelta_sec < self.min_duration:
                return True, "Bucket operation execution completed successfully."
            logger.info("Iteration %s is completed...", self.iteration)
            self.iteration += 1
