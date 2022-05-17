# -*- coding: utf-8 -*-
# !/usr/bin/python
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
""" Report Server client to update test results to Mongo DB."""

import json
import logging
from http import HTTPStatus

import requests

from commons.params import REPORT_SRV
from commons.utils import jira_utils
from core import runner

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
    try:
        if tp_details.fields.environment:
            branch_build = tp_details.fields.environment
            if "_" in branch_build:
                build_type = "".join(branch_build.split("_")[:-1])
    except ValueError:
        build_type = "stable"

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
        LOGGER.error("POST request on %s failed with %s, %s.", TIMING_EP,
                     response.status_code, response.text)
