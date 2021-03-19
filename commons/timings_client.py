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

from commons.utils import jira_utils
from core import runner
from params import REPORT_SRV

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
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = jira_utils.JiraTask(jira_id, jira_pwd)
    tp_details = jira_obj.get_issue_details(payload["testPlanID"])

    build_type = "stable"
    if tp_details.fields.environment:
        branch_build = tp_details.fields.environment
        if "_" in branch_build:
            build_type = "".join(branch_build.split("_")[:-1])

    if tp_details.fields.labels:
        test_plan_label = tp_details.fields.labels[0]
    else:
        test_plan_label = "regular"
    headers = {
        'Content-Type': 'application/json'
    }

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD
    payload["buildType"] = build_type
    payload["testPlanLabel"] = test_plan_label
    response = requests.request("POST", TIMING_EP, headers=headers, data=json.dumps(payload))
    if response.status_code == HTTPStatus.OK:
        LOGGER.info("Stored timings data into database.")
    else:
        LOGGER.error(f"POST request on {TIMING_EP} failed with "
                     f"{response.status_code}, {response.text}.")
