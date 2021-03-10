# -*- coding: utf-8 -*-
"""Helper functions to generate csv report."""
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

import configparser
import json
import sys
from http import HTTPStatus
from urllib.parse import quote_plus

import requests

TIMINGS_PARAMETERS = {
    "nodeRebootTime": "Node Reboot",
    "allServicesStartTime": "Start All Services",
    "allServicesStopTime": "Stop All Services",
    "nodeFailoverTime": "Node Failover",
    "nodeFailbackTime": "Node Failback",
    "bucketCreationTime": "Bucket Creation",
    "bucketDeletionTime": "Bucket Deletion",
    "softwareUpdateTime": "Software Update",
    "firmwareUpdateTime": "Firmware Update",
    "startNodeTime": "Start Node",
    "stopNodeTime": "Stop Node"
}


def get_timings_db_details():
    """Read DB details from config.init file"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        rest = config["TimingsDB"]["rest"]
        db_username = config["TimingsDB"]["db_username"]
        db_password = config["TimingsDB"]["db_password"]
    except KeyError:
        print("Could not get Timings DB information. Please verify config.ini file")
        sys.exit(1)

    if not db_username or not db_password:
        print("Please set username and password for Timings DB in config.ini file")
        sys.exit(1)

    return rest, db_username, db_password


def get_perf_db_details():
    """Read DB details from config.init file"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        db_hostname = config["PerfDB"]["db_hostname"]
        db_name = config["PerfDB"]["db_name"]
        db_collection = config["PerfDB"]["db_collection"]
        db_username = config["PerfDB"]["db_username"]
        db_password = config["PerfDB"]["db_password"]
    except KeyError:
        print("Could not get performance DB information. Please verify config.ini file")
        sys.exit(1)

    if not db_username or not db_password:
        print("Please set username and password for performance DB in config.ini file")
        sys.exit(1)

    uri = "mongodb://{0}:{1}@{2}".format(quote_plus(db_username),
                                         quote_plus(db_password),
                                         db_hostname)
    return uri, db_name, db_collection


def keys_exists(element, *keys):
    """Check if *keys (nested) exists in `element` (dict)."""
    if not isinstance(element, dict):
        raise AttributeError('keys_exists() expects dict as first argument.')
    if len(keys) == 0:
        raise AttributeError('keys_exists() expects at least two arguments, one given.')

    _element = element
    for key in keys:
        try:
            _element = _element[key]
        except KeyError:
            return False
    return True


def round_off(value, base=1):
    """
    Summary: Round off to nearest int

    Input : (number) - number
            (base) - round off to nearest base
    Returns: (int) - rounded off number
    """
    if value < 1:
        return round(value, 2)
    if value < 26:
        return int(value)
    return base * round(value / base)


def get_timings_data_from_db(payload, rest_ep):
    """Read timings data from database"""
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("GET", rest_ep, headers=headers, data=json.dumps(payload))

    if response.status_code == HTTPStatus.OK:
        return response.json()["result"]
    if response.status_code == HTTPStatus.NOT_FOUND:
        return []
    print(f'get_timings_data_from_db GET on {rest_ep} failed')
    print(f'RESPONSE={response.text}\n'
          f'HEADERS={response.request.headers}\n'
          f'BODY={response.request.body}')
    sys.exit(1)


def get_timing_summary(test_plan_ids, builds, rest_ep, db_username, db_password):
    """Timings data from database"""
    data = [["Timing Summary (Seconds)"]]
    row = ["Parameters"]
    row.extend(builds)
    data.extend([row])
    for param, val in TIMINGS_PARAMETERS.items():
        row = [val]
        for build, tp_id in zip(builds, test_plan_ids):
            payload = {
                "query": {'testPlanID': tp_id, param: {"$exists": True}},
                "projection": {param: True},
                "db_username": db_username, "db_password": db_password
            }
            parameter_data = get_timings_data_from_db(payload, rest_ep)
            if parameter_data:
                row.append(round_off(sum(x[param] for x in parameter_data) / len(parameter_data)))
            else:
                row.append("NA")
        data.extend([row])
    return data
