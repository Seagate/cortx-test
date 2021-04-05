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
with step users and constant object size
"""
import os
import math
import logging
from locust import LoadTestShape
from locust import events
from locust import HttpUser
from locust import task, constant
from scripts.locust import locust_utils
from scripts.locust import LOCUST_CFG

UTILS_OBJ = locust_utils.LocustUtils()
LOGGER = logging.getLogger(__name__)
BUCKET_COUNT = int(
    os.getenv(
        'BUCKET_COUNT',
        LOCUST_CFG['default']['BUCKET_COUNT']))
OBJECT_SIZE = int(
    os.getenv(
        'OBJECT_SIZE',
        LOCUST_CFG['default']['OBJECT_SIZE']))
BUCKET_LIST = UTILS_OBJ.bucket_list


class LocustUser(HttpUser):
    """
    Locust user class
    """
    wait_time = constant(1)

    @events.test_start.add_listener
    def on_test_start(**kwargs):
        LOGGER.info("Starting test setup")
        UTILS_OBJ.create_buckets(BUCKET_COUNT)

    @task(1)
    def put_object(self):
        for bucket in BUCKET_LIST:
            UTILS_OBJ.put_object(bucket, OBJECT_SIZE)

    @task(1)
    def get_object(self):
        for bucket in BUCKET_LIST:
            UTILS_OBJ.download_object(bucket)

    @task(1)
    def delete_object(self):
        for bucket in BUCKET_LIST:
            UTILS_OBJ.delete_object(bucket)

    @events.test_stop.add_listener
    def on_test_stop(**kwargs):
        UTILS_OBJ.delete_buckets(BUCKET_LIST)


class StepLoadShape(LoadTestShape):
    """
    A step load shape
    Keyword arguments:
        step_time -- Time between steps
        step_load -- User increase amount at each step
        spawn_rate -- Users to stop/start per second at every step
        time_limit -- Time limit in seconds
    """

    step_time = int(os.getenv('STEP_TIME', LOCUST_CFG['default']['STEP_TIME']))
    step_load = int(os.getenv('STEP_LOAD', LOCUST_CFG['default']['STEP_LOAD']))
    spawn_rate = int(
        os.getenv(
            'SPAWN_RATE',
            LOCUST_CFG['default']['HATCH_RATE']))
    time_limit = int(os.getenv('DURATION', step_time * 2))

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        return current_step * self.step_load, self.spawn_rate
