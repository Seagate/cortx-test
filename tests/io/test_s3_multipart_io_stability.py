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
"""This file contains s3 multipart test script for io stability."""

import logging
import os
import sys
import shutil
from datetime import datetime, timedelta
from time import perf_counter_ns
from botocore.exceptions import ClientError
from libs.io.s3api.s3_multipart_ops import S3MultiParts
from libs.io.s3api.s3_object_ops import S3Object
from libs.io.s3api.s3_bucket_ops import S3Bucket

logger = logging.getLogger(__name__)


class S3MutiParts(S3MultiParts, S3Object, S3Bucket):
    """S3 multipart class for executing given io stability workload"""

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, test_id: str,
                 use_ssl: str, object_size: int, part_range: list, duration: timedelta = None) -> None:
        """
        s3 multipart init class.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint with http or https.
        :param test_id: Test ID string, used for log file name.
        :param use_ssl: To use secure connection.
        :param duration: Duration timedelta object, if not given will run for 100 days.
        """
        super().__init__(access_key, secret_key, endpoint_url, use_ssl=use_ssl)
        self.duration = duration
        self.mpart_bucket = "s3mpart_bkt_{}_{}".format(
            test_id.lower() if test_id else "sample", perf_counter_ns())
        self.s3mpart_object = "s3mpart_obj_{}_{}".format(
            test_id.lower() if test_id else "sample", perf_counter_ns())
        self.object_size = object_size
        self.part_range = part_range
        self.test_id = test_id
        self.iteration = 1
        if not duration:
            self.finish_time = datetime.now() + timedelta(hours=int(100 * 24))
        else:
            self.finish_time = datetime.now() + duration

    def run_workload(self):
        """Execute multipart workload for specific duration."""
        logger.info("Iteration {} is started...", self.iteration)
        response = self.create_bucket(self.mpart_bucket)
        