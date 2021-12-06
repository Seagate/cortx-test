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
#
"""
Locust tasks set for put object, get object and delete object from bucket
"""
import glob
import logging
import os
import secrets

from locust import HttpUser
from locust import events
from locust import task, constant

from scripts.locust import LOCUST_CFG
from scripts.locust import locust_utils

UTILS_OBJ = locust_utils.LocustUtils()
LOGGER = logging.getLogger(__name__)
BUCKET_COUNT = int(
    os.getenv(
        'BUCKET_COUNT',
        LOCUST_CFG['default']['BUCKET_COUNT']))
MIN_OBJECT_SIZE = int(
    os.getenv(
        'MIN_OBJECT_SIZE',
        LOCUST_CFG['default']['MIN_OBJECT_SIZE']))
MAX_OBJECT_SIZE = int(
    os.getenv(
        'MAX_OBJECT_SIZE',
        LOCUST_CFG['default']['MAX_OBJECT_SIZE']))
BUCKET_LIST = UTILS_OBJ.bucket_list


class LocustUser(HttpUser):
    """
    Locust user class
    """
    wait_time = constant(1)
    utils = UTILS_OBJ
    secure_range = secrets.SystemRandom()

    @events.test_start.add_listener
    def on_test_start(**kwargs):
        LOGGER.info("Starting test setup")
        UTILS_OBJ.create_buckets(BUCKET_COUNT)

    @task(2)
    def put_object(self):
        object_size = self.secure_range.randint(MIN_OBJECT_SIZE, MAX_OBJECT_SIZE)
        bucket = secrets.choice(BUCKET_LIST)
        self.utils.put_object(bucket, object_size)

    @task(1)
    def get_object(self):
        self.utils.download_object()

    @task(1)
    def head_object(self):
        self.utils.head_object()

    @task(1)
    def delete_object(self):
        self.utils.delete_object()

    @events.test_stop.add_listener
    def on_test_stop(**kwargs):
        UTILS_OBJ.delete_buckets(BUCKET_LIST)
        for object_files in glob.glob(f"{locust_utils.OBJ_NAME}*"):
            UTILS_OBJ.delete_local_obj(object_files)
        for object_files in glob.glob(f"{locust_utils.GET_OBJ_PATH}*"):
            UTILS_OBJ.delete_local_obj(object_files)
