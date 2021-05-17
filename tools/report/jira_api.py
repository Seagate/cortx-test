# -*- coding: utf-8 -*-
"""Common functions used while generating engineering and executive csv reports."""
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

import getpass
import os
import sys
from collections import Counter
from datetime import date
from http import HTTPStatus

import requests
from jira import JIRA

BUGS_PRIORITY = ["Blocker", "Critical", "Major", "Minor", "Trivial"]
TEST_STATUS = ["PASS", "FAIL", "ABORTED", "BLOCKED", "TODO"]
FEATURES = [
    " Longevity",
    " Performance",
    " Security",
    "Application Testing (UDX, BearOS etc..)",
    "Capacity tests",
    "Cluster Health Operations",
    "Cluster Manager Operation (Provision)",
    "Cluster Monitor Operation (Alerts)",
    "Cluster Support (Logging, support bundle, health schema)",
    "Cluster User Operation (CSM)",
    "CSM GUI Cluster User Operation Tests",
    "Data Integrity",
    "Data recovery",
    "Failure Tests",
    "FRU Replacement Validation",
    "Functionality",
    "High Availability",
    "Interface",
    "IO Workload",
    "Lyve Pilot Tests",
    "Open-Source Tests",
    "Platform Operations",
    "Robustness and Reliability",
    "S3 IO load tests",
    "S3 Operations",
    "Scalability",
    "Stress Tests",
    "System Integration",
]


def get_test_executions_from_test_plan(test_plan: str, username: str, password: str) -> [dict]:
    """
    Summary: Get test executions from test plan.

    Description: Returns dictionary of test executions from test plan.

    Args:
        test_plan (str): Test plan number in JIRA
        username (str): JIRA Username
        password (str): JIRA Password

    Returns:
        List of dictionaries
        Each dict will have id, key, summary, self, testEnvironments
        [{"id": 311993, "key": "TEST-16653", "summary": "TE:Auto-Stability-Release 515",
         "self": "https://jts.seagate.com/rest/api/2/issue/311993",
         "testEnvironments": ["515_full"]},
        {"id": 311992, "key": "TEST-16652", "summary": "TE:Manual-RAS_Release 515",
         "self": "https://jts.seagate.com/rest/api/2/issue/311992",
         "testEnvironments": ["515_full"]}]
    """
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/{test_plan}/testexecution'
    response = requests.get(jira_url, auth=(username, password))
    if response.status_code == HTTPStatus.OK:
        return response.json()
    print(f'get_test_executions GET on {jira_url} failed')
    print(f'HEADERS={response.request.headers}\n'
          f'BODY={response.request.body}')
    sys.exit(1)


def get_test_list_from_test_plan(test_plan: str, username: str, password: str) -> [dict]:
    """
    Args:
        test_plan (str): Test plan number in JIRA
        username (str): JIRA Username
        password (str): JIRA Password

    Returns:
        List of dictionaries
        Each dict will have id, key, latestStatus keys
        [{'id': 265766, 'key': 'TEST-4871', 'latestStatus': 'PASS'},
         {'id': 271956, 'key': 'TEST-6930', 'latestStatus': 'PASS'}]
    """
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/{test_plan}/test'
    responses = []
    all_tests = False
    i = 0
    while not all_tests:
        i = i + 1
        query = {'limit': 100, 'page': i}
        response = requests.get(jira_url, auth=(username, password), params=query)
        if response.status_code == HTTPStatus.OK and response.json():
            responses.extend(response.json())
        elif response.status_code == HTTPStatus.OK and not response.json():
            all_tests = True
        else:
            print(f'get_test_list GET on {jira_url} failed')
            print(f'RESPONSE={response.text}\n'
                  f'HEADERS={response.request.headers}\n'
                  f'BODY={response.request.body}')
            sys.exit(1)
    return responses


def get_test_from_test_execution(test_execution: str, username: str, password: str):
    """

    Args:
        test_execution (str): Test execution number in JIRA
        username (str): JIRA Username
        password (str): JIRA Password

    Returns:
        [{"key":"TEST-10963", "status":"FAIL", "defects": []}, {...}]
        "defects" = [{key:"EOS-123", "summary": "Bug Title", "status": "New/Started/Closed"},{}]
    """
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testexec/{test_execution}/test'
    query = {'detailed': "true"}
    response = requests.get(jira_url, auth=(username, password), params=query)
    if response.status_code == HTTPStatus.OK and response.json():
        return response.json()
    if response.status_code == HTTPStatus.OK and not response.json():
        print("No tests associated with this test execution")
        sys.exit(1)
    print(f'get_test_from_test_execution GET on {jira_url} failed')
    print(f'RESPONSE={response.text}\n'
          f'HEADERS={response.request.headers}\n'
          f'BODY={response.request.body}')
    sys.exit(1)


def get_issue_details(issue_id: str, username: str, password: str):
    """

    Args:
        issue_id (str): Bug ID or TEST ID string
        username (str): JIRA Username
        password (str): JIRA Password

    Returns:
        {
            "fields":{
                "labels":["Integration","QA"],
                "environment":"515",
                "components":[
                    {
                        "name": "CSM"
                    },
                    {
                        "name": "CFT"
                    }
                ],
                "priority":{"name": "Critical"},
                "summary": "JIRA Title",
                "status": {"name": "In Progress"},
                "issuelinks": [{"inwardIssue": {"key": "TEST-5342"}},
                               {"inwardIssue": {"key": "TEST-1034"}}]
                },
        }
    """
    jira_url = "https://jts.seagate.com/"
    options = {'server': jira_url}
    auth_jira = JIRA(options, basic_auth=(username, password))
    return auth_jira.issue(issue_id)


def get_defects_from_test_plan(test_plan: str, username: str, password: str) -> set:
    """Get defect list from given test plan."""
    defects = set()

    # Get test execution keys from test plan
    test_executions = get_test_executions_from_test_plan(test_plan, username, password)
    te_keys = [te["key"] for te in test_executions]

    # Get test and defect details for each test execution
    test_keys = {te: get_test_from_test_execution(te, username, password) for te in te_keys}

    # Collect defects
    for _, tests in test_keys.items():
        for test in tests:
            if test["status"] == "FAIL" and test["defects"]:
                for defect in test["defects"]:
                    defects.add(defect["key"])
    return defects


def get_details_from_test_plan(test_plan: str, username: str, password: str) -> dict:
    """Get details for given test plan."""
    test_plan_details = get_issue_details(test_plan, username, password)
    fields = {"platformType": test_plan_details.fields.customfield_22982,
              "serverType": test_plan_details.fields.customfield_22983,
              "enclosureType": test_plan_details.fields.customfield_22984,
              "branch": test_plan_details.fields.customfield_22981,
              "buildNo": test_plan_details.fields.customfield_22980}
    out_dict = {}
    for key, value in fields.items():
        if value:
            out_dict.update({key: value[0]})
        else:
            print(f"Test Plan {test_plan} has {key} field empty.")
            sys.exit(1)
    return out_dict


def get_main_table_data(build_no: str):
    """Get header table data."""
    data = [["CFT Exec Report"], ["Product", "Lyve Rack"],
            ["Build", build_no],
            ["Date", date.today().strftime("%B %d, %Y")], ["System", ""]]
    return data


def get_reported_bug_table_data(test_plan: str, username: str, password: str):
    """Get reported bug table data."""
    test_bugs = {x: 0 for x in BUGS_PRIORITY}
    cortx_bugs = {x: 0 for x in BUGS_PRIORITY}
    defects = get_defects_from_test_plan(test_plan, username, password)
    for defect in defects:
        defect = get_issue_details(defect, username, password)
        components = [component.name for component in defect.fields.components]
        if "CFT" in components or "Automation" in components:
            test_bugs[defect.fields.priority.name] += 1
        else:
            cortx_bugs[defect.fields.priority.name] += 1
    data = [
        ["Reported Bugs"], ["Priority", "Test Setup", "Cortx Stack"],
        ["Total", sum(test_bugs.values()), sum(cortx_bugs.values())],
    ]
    for priority in BUGS_PRIORITY:
        data.extend([[priority, test_bugs[priority], cortx_bugs[priority]]])

    return data


def get_overall_qa_report_table_data(test_plan: str, test_plan1: str,
                                     build: str, username: str, password: str):
    """Get overall qa report table data."""
    tests = get_test_list_from_test_plan(test_plan, username, password)
    count_0 = Counter(test['latestStatus'] for test in tests)
    build1 = "NA"
    count_1 = Counter()
    if test_plan1:
        build1 = get_details_from_test_plan(test_plan1, username, password)["buildNo"]
        tests = get_test_list_from_test_plan(test_plan1, username, password)
        count_1 = Counter(test['latestStatus'] for test in tests)

    data = [
        ["Overall QA Report"], ["", build, build1],
        ["Total", sum(count_0.values()), sum(count_1.values())],
    ]
    for status in TEST_STATUS:
        data.extend([
            [status.capitalize(), count_0[status], count_1[status]],
        ])
    return data


def get_username_password():
    """Get username and password from JIRA."""
    try:
        username = os.environ["JIRA_ID"]
        password = os.environ["JIRA_PASSWORD"]
    except KeyError:
        username = input("JIRA username: ")
        password = getpass.getpass("JIRA password: ")
    return username, password
