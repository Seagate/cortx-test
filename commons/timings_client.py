# -*- coding: utf-8 -*-
# !/usr/bin/python
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
""" Report Server client to update test results to Mongo DB."""

import json
import logging
from http import HTTPStatus

import requests

from core import runner

REPORT_SRV = "http://cftic2.pun.seagate.com:5000/"
TIMING_EP = REPORT_SRV + "timings"

DB_USERNAME, DB_PASSWORD = runner.get_db_credential()

LOGGER = logging.getLogger(__name__)


def create_timings_db_entry(payload):
    """
    Create a timings DB entry for given parameter.
    {
        "buildNo": "515",
        "logs": "",
        "testID": "",
        "testPlanID": "",
        "testExecutionID": "",
        "testStartTime": "2021-03-01T06:17:45+00:00",
        "nodeRebootTime": 45.5,
    }
    """
    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", TIMING_EP, headers=headers, data=json.dumps(payload))
    if response.status_code == HTTPStatus.OK:
        LOGGER.info("Stored timings data into database.")
    else:
        LOGGER.error(f"POST request on {TIMING_EP} failed with "
                     f"{response.status_code}, {response.text}.")
