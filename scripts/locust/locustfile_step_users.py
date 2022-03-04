#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""
Locust tasks set for put object, get object and delete object from bucket
with step users and constant object size
"""
import glob
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
    utils = UTILS_OBJ

    @events.test_start.add_listener
    def on_test_start(**kwargs):
        LOGGER.info("Starting test setup with %s %s", kwargs.get('--u'), kwargs.get('--t'))
        UTILS_OBJ.create_buckets(BUCKET_COUNT)

    @task(2)
    def put_object(self):
        for bucket in BUCKET_LIST:
            self.utils.put_object(bucket, OBJECT_SIZE)

    @task(1)
    def get_object(self):
        self.utils.download_object()

    @task(1)
    def delete_object(self):
        self.utils.delete_object()

    @events.test_stop.add_listener
    def on_test_stop(**kwargs):
        LOGGER.info("Starting test cleanup.")
        UTILS_OBJ.delete_buckets(BUCKET_LIST)
        for object_files in glob.glob(f"{locust_utils.OBJ_NAME}*"):
            UTILS_OBJ.delete_local_obj(object_files)
        for object_files in glob.glob(f"{locust_utils.GET_OBJ_PATH}*"):
            UTILS_OBJ.delete_local_obj(object_files)
        LOGGER.info("Log path: %s", kwargs.get('--logfile'))
        LOGGER.info("HTML path: %s", kwargs.get('--html'))


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
    max_user = int(os.getenv('MAX_USERS', 30))

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.time_limit:
            return None

        current_step = math.floor(run_time / self.step_time) + 1
        total_new_users = current_step * self.step_load
        if total_new_users > self.max_user:
            total_new_users = self.max_user

        return total_new_users, self.spawn_rate
