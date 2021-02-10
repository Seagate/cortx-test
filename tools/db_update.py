"""Script to update results of manual test execution into database."""
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
# -*- coding: utf-8 -*-
# !/usr/bin/python

# Basic algorithm
# for each TE:
#     for each Test in TE:
#         result = Search Query by ('buildNo', 'testExecutionID', 'testID', 'valid': True)
#         if test status in db != in JIRA or no entry in db :
#             Patch all present entries to add valid key as false
#             insert new entry with latest data from JIRA

import argparse
import json
import sys

import requests

from csv_report import common

HOSTNAME = "http://cftic2.pun.seagate.com:5000/reportsdb/"
DB_USERNAME = "dataread"
DB_PASSWORD = "seagate@123"

headers = {
    'Content-Type': 'application/json'
}


def patch_db_request(payload: dict) -> None:
    """
    Description: Make a patch request to database using REST API

    Args:
        payload (dict): Payload data
    """
    request = "PATCH"
    endpoint = "update"

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD

    response = requests.request(request, HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    if response.status_code != 200:
        print(f'{request} on {HOSTNAME + endpoint} failed')
        print(f'HEADERS={response.request.headers}\n'
              f'BODY={response.request.body}',
              f'RESPONSE={response.text}')
        sys.exit(1)


def create_db_request(payload: dict) -> None:
    """
    Description: Make a create request to database using REST API

    Args:
        payload (dict): Payload data
    """
    request = "POST"
    endpoint = "create"

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD

    response = requests.request(request, HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    if response.status_code != 200:
        print(f'{request} on {HOSTNAME + endpoint} failed')
        print(f'HEADERS={response.request.headers}\n'
              f'BODY={response.request.body}',
              f'RESPONSE={response.text}')
        sys.exit(1)


def search_db_request(payload: dict):
    """
    Description: Make a search request to database using REST API

    Args:
        payload (dict): Payload data

    Returns:
        Search result
    """
    request = "GET"
    endpoint = "search"

    payload["db_username"] = DB_USERNAME
    payload["db_password"] = DB_PASSWORD

    response = requests.request(request, HOSTNAME + endpoint, headers=headers,
                                data=json.dumps(payload))
    if response.status_code == 200:
        return response.json()["result"]
    elif response.status_code == 404 and "No results" in response.text:
        return None
    else:
        print(f'{request} on {HOSTNAME + endpoint} failed')
        print(f'HEADERS={response.request.headers}\n'
              f'BODY={response.request.body}',
              f'RESPONSE={response.text}')
        sys.exit(1)


def main():
    """Generate csv engineering report from test plan JIRA."""

    # Parse testplan argument
    parser = argparse.ArgumentParser()
    parser.add_argument('tp', help='Testplan for current build')
    test_plans = parser.parse_args()
    tp = test_plans.tp

    username, password = common.get_username_password()
    build = common.get_build_from_test_plan(tp, username, password)
    test_executions = common.get_test_executions_from_test_plan(tp, username, password)
    test_plan_issue = common.get_issue_details(tp, username, password)
    # for each TE:
    for te in test_executions:
        test_execution_issue = common.get_issue_details(te["key"], username, password)
        tests = common.get_test_from_test_execution(te["key"], username, password)
        # for each Test in TE:
        for test in tests:
            payload = {
                "query": {
                    "buildNo": build,
                    "testExecutionID": te["key"],
                    "testID": test["key"],
                    "valid": "true"
                },
            }
            results = search_db_request(payload)

            if len(results) == 0:
                # add one entry
                test_issue = common.get_issue_details(test["key"], username, password)
                payload = {
                    # Unknown data
                    "clientHostname": "",
                    "OSVersion": "",
                    "noOfNodes": 0,
                    "nodesHostname": [""],
                    "testExecutionTime": 0,
                    "healthCheckResult": "",
                    "buildType": "",
                    "testTags": [""],
                    "testType": "",
                    "testTeam": "",
                    # Data from JIRA
                    "testPlanID": tp,
                    "buildNo": build,
                    "logPath": test["comment"],
                    "testResult": test["status"],
                    "testStartTime": test["startedOn"],
                    "testName": test_issue["fields"]["summary"],
                    "testID": test["key"],
                    "testIDLabels": test_issue["fields"]["labels"],
                    "testExecutionID": te["key"],
                    "testExecutionLabel": test_execution_issue["fields"]["labels"][0],
                    "executionType": test_issue["fields"]["customfield_20981"],
                    "testPlanLabel": test_plan_issue["fields"]["labels"][0]
                }
                create_db_request(payload)
            elif len(results) == 1:
                # if test status in db != in JIRA or no entry in db
                if results[0]["testResult"].lower() != test["status"].lower():
                    # Add valid key in entry false
                    payload = {
                        "filter": payload["query"],
                        "update": {
                            "$set": {"valid": False}
                        }
                    }
                    patch_db_request(payload)
                    # Insert new entry with latest data from JIRA
                    payload = {
                        # Unknown data
                        "clientHostname": "",
                        "noOfNodes": "",
                        "OSVersion": "",
                        "nodesHostname": [""],
                        "testExecutionTime": "",
                        "healthCheckResult": "",
                        # Data from JIRA
                        "buildNo": build,
                        "logPath": test["comment"],
                        "testResult": test["status"],
                        "testStartTime": test["startedOn"],
                        # Data from previous database entry
                        "buildType": results[0]["buildType"],
                        "testName": results[0]["testName"],
                        "testID": results[0]["testID"],
                        "testIDLabels": results[0]["testIDLabels"],
                        "testTags": results[0]["testTags"],
                        "testPlanID": results[0]["testPlanID"],
                        "testExecutionID": results[0]["testExecutionID"],
                        "testType": results[0]["testType"],
                        "testExecutionLabel": results[0]["testExecutionLabel"],
                        "executionType": results[0]["executionType"],
                        "testPlanLabel": results[0]["testPlanLabel"]
                    }
                    create_db_request(payload)
            else:
                # ToDo: More than 1 valid entries in database
                print(f"More than one entry in database {results}. Could not update MongoDB data")
                sys.exit(1)


if __name__ == '__main__':
    main()

# ToDo: Add code to update failed tests Bug IDs into database
#       Decide if it will be as standalone script or as part of this script only.
# For each failed or blocked test:
#    PATCH issue in db entry
# Search database by ('buildNo', 'testExecutionID', 'testID', 'valid': True)
