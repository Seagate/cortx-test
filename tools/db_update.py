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
import configparser
import json
import sys
from http import HTTPStatus

import requests
from jira import JIRA

from report import jira_api

headers = {
    'Content-Type': 'application/json'
}

config = configparser.ConfigParser()
config.read('config.ini')
try:
    HOSTNAME = config["REST"]["hostname"]
    HOSTNAME = HOSTNAME + "reportsdb/"
    DB_USERNAME = config["REST"]["db_username"]
    DB_PASSWORD = config["REST"]["db_password"]
except KeyError:
    print("Could not start REST server. Please verify config.ini file")
    sys.exit(1)


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
    if response.status_code != HTTPStatus.OK:
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
    if response.status_code != HTTPStatus.OK:
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
    if response.status_code == HTTPStatus.OK:
        return response.json()["result"]
    if response.status_code == HTTPStatus.NOT_FOUND and "No results" in response.text:
        return None
    print(f'{request} on {HOSTNAME + endpoint} failed')
    print(f'HEADERS={response.request.headers}\n'
          f'BODY={response.request.body}',
          f'RESPONSE={response.text}')
    sys.exit(1)


def get_features_from_test_plan(test_plan: str, username: str, password: str) -> dict:
    """
    Description: Get feature from test plan board

    Returns:
        Feature String
    """
    jira_url = 'https://jts.seagate.com/'
    options = {'server': jira_url}
    jira = JIRA(options, basic_auth=(username, password))
    features = {}
    for feature in jira_api.FEATURES:
        tests = jira.search_issues(
            f'issue in testPlanFolderTests({test_plan},\'{feature}\',\'true\')', maxResults=500)
        features[feature] = [test.key for test in tests]
    return features


def get_feature(features: dict, test: str) -> str:
    """Return feature from features dictionary"""
    for feature, tests in features.items():
        if test in tests:
            return feature
    return "Orphan"


# pylint: disable-msg=too-many-locals
def main():
    """Update test executions from JIRA to MongoDB."""

    username, password = jira_api.get_username_password()
    build = jira_api.get_build_from_test_plan(tp_key, username, password)
    test_executions = jira_api.get_test_executions_from_test_plan(tp_key, username, password)
    test_plan_issue = jira_api.get_issue_details(tp_key, username, password)
    features = get_features_from_test_plan(tp_key, username, password)
    # for each TE:
    for test_execution in test_executions:
        test_execution_issue = jira_api.get_issue_details(test_execution["key"], username, password)
        tests = jira_api.get_test_from_test_execution(test_execution["key"], username, password)
        # for each Test in TE:
        for test in tests:
            query_payload = {
                "query": {
                    "buildNo": build,
                    "testExecutionID": test_execution["key"],
                    "testID": test["key"],
                    "latest": True
                },
            }
            results = search_db_request(query_payload)

            if len(results) == 0:
                # add one entry
                test_issue = jira_api.get_issue_details(test["key"], username, password)
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
                    # Data from JIRA
                    "testPlanID": tp_key,
                    "buildNo": build,
                    "logPath": test["comment"],
                    "testResult": test["status"],
                    "testStartTime": test["startedOn"],
                    "testName": test_issue["fields"]["summary"],
                    "testID": test["key"],
                    "testTeam": test_execution_issue["fields"]["components"][0]["name"],
                    "testIDLabels": test_issue["fields"]["labels"],
                    "testExecutionID": test_execution["key"],
                    "testExecutionLabel": test_execution_issue["fields"]["labels"][0],
                    "executionType": test_issue["fields"]["customfield_20981"],
                    "testPlanLabel": test_plan_issue["fields"]["labels"][0],
                    "feature": get_feature(features, test["key"]),
                    "latest": True
                }
                create_db_request(payload)
            else:
                # if test status in db != in JIRA or no entry in db
                if results[0]["testResult"].lower() != test["status"].lower():
                    # Add valid key in entry false
                    patch_payload = {
                        "filter": query_payload["query"],
                        "update": {
                            "$set": {"latest": False}
                        }
                    }
                    patch_db_request(patch_payload)
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
                        "testPlanLabel": results[0]["testPlanLabel"],
                        "feature": results[0]["feature"],
                        "latest": True
                    }
                    create_db_request(payload)

            if "fail" in test["status"].lower():
                # Get BUG ID from JIRA
                if "defects" not in test:
                    print("WARNING: Failure is not mapped to any issue in JIRA "
                          "TEST - {0}, Test Execution - {1}, "
                          "Test Plan = {2}".format(test["key"], test_execution["key"], tp_key))
                defects = [defect["key"] for defect in test["defects"]]
                if defects:
                    # PATCH issue in db entry
                    patch_payload = {
                        "filter": query_payload["query"],
                        "update": {
                            "$set": {"issueIDs": defects}
                        }
                    }
                    patch_db_request(patch_payload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('tp', help='Testplan for current build')
    test_plans = parser.parse_args()
    tp_key = test_plans.tp
    main()
