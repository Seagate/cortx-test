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
from collections import Counter
from datetime import date
from http import HTTPStatus
import sys

import requests

bugs_priority = ["Blocker", "Critical", "Major", "Minor", "Trivial"]
test_status = ["PASS", "FAIL", "ABORTED", "BLOCKED", "TODO"]
features = ["User Operations", "Scalability", "Availability", "Longevity", "Usecases",
            "Data Recovery", "CrossConnect"]


def get_test_executions_from_test_plan(test_plan: str, username: str, password: str) -> [dict]:
    """
    Args:
        test_plan (str): Test plan number in JIRA
        username (str): JIRA Username
        password (str): JIRA Password

    Returns:
        List of dictionaries
        Each dict will have id, key, summary, self, testEnvironments
        [{'id': 311993, 'key': 'TEST-16653', 'summary': 'TE:Auto-Stability-Release 515',
         'self': 'https://jts.seagate.com/rest/api/2/issue/311993',
         'testEnvironments': ['515_full']},
        {'id': 311992, 'key': 'TEST-16652', 'summary': 'TE:Manual-RAS_Release 515',
         'self': 'https://jts.seagate.com/rest/api/2/issue/311992',
         'testEnvironments': ['515_full']}]
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
        if response.status_code == HTTPStatus.OK and len(response.json()):
            responses.extend(response.json())
        elif response.status_code == HTTPStatus.OK and not len(response.json()):
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
        "defects" = [{key:"TEST-123", "summary": "Bug Title", "status": "New/Started/Closed"},{}]
    """
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testexec/{test_execution}/test'
    query = {'detailed': "true"}
    response = requests.get(jira_url, auth=(username, password), params=query)
    if response.status_code == HTTPStatus.OK and len(response.json()):
        return response.json()
    elif response.status_code == HTTPStatus.OK and not len(response.json()):
        print("No tests associated with this test execution")
        sys.exit(1)
    else:
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
                "environment":"515"},
                "components":[
                    {
                        "name": "CSM"
                    },
                    {
                        "name": "CFT"
                    }
                "priority":{"name": "Critical"},
                "summary": "JIRA Title",
                "status": {"name": "In Progress"},
                "issuelinks": [{"inwardIssue": {"key": "TEST-5342"}},
                               {"inwardIssue": {"key": "TEST-1034"}}}]
                ],
        }
    """
    jira_url = f'https://jts.seagate.com/rest/api/latest/issue/{issue_id}'
    response = requests.get(jira_url, auth=(username, password))
    if response.status_code == HTTPStatus.OK:
        return response.json()
    print(f'get_bug_details GET on {jira_url} failed')
    print(f'RESPONSE={response.text}\n'
          f'HEADERS={response.request.headers}\n'
          f'BODY={response.request.body}')
    sys.exit(1)


def get_defects_from_test_plan(test_plan: str, username: str, password: str) -> set:
    defects = set()

    # Get test execution keys from test plan
    test_executions = get_test_executions_from_test_plan(test_plan, username, password)
    te_keys = [te["key"] for te in test_executions]

    # Get test and defect details for each test execution
    test_keys = {te: get_test_from_test_execution(te, username, password) for te in
                 te_keys}

    # Collect defects
    for te, tests in test_keys.items():
        for test in tests:
            if test["status"] == "FAIL" and test["defects"]:
                for defect in test["defects"]:
                    defects.add(defect["key"])
    return defects


def get_build_from_test_plan(test_plan: str, username: str, password: str):
    test_plan_details = get_issue_details(test_plan, username, password)
    test_plan_details = test_plan_details["fields"]
    build_no = "None"
    if test_plan_details["environment"]:
        build_no = test_plan_details["environment"]
    else:
        print(f"Test Plan {test_plan} has environment field empty. Setup it to build number.")
        sys.exit(1)
    return build_no


def get_main_table_data(test_plan: str, username: str, password: str):
    build_no = get_build_from_test_plan(test_plan, username, password)
    data = [["CFT Exec Report"], ["Product", "Lyve Rack"],
            ["Build", build_no],
            ["Date", date.today().strftime("%B %d, %Y")], ["System", ""]]
    return data, build_no


def get_reported_bug_table_data(test_plan: str, username: str, password: str):
    test_bugs = {x: 0 for x in bugs_priority}
    cortx_bugs = {x: 0 for x in bugs_priority}
    defects = get_defects_from_test_plan(test_plan, username, password)
    for defect in defects:
        defect = get_issue_details(defect, username, password)
        components = [component["name"] for component in defect["fields"]["components"]]
        if "CFT" in components:
            test_bugs[defect["fields"]["priority"]["name"]] += 1
        else:
            cortx_bugs[defect["fields"]["priority"]["name"]] += 1
    data = [
        ["Reported Bugs"], ["Priority", "Test Setup", "Cortx Stack"],
        ["Total", sum(test_bugs.values()), sum(cortx_bugs.values())],
    ]
    for priority in bugs_priority:
        data.extend([[priority, test_bugs[priority], cortx_bugs[priority]]])

    return data


def get_overall_qa_report_table_data(test_plan: str, test_plan1: str,
                                     build: str, username: str, password: str):
    tests = get_test_list_from_test_plan(test_plan, username, password)
    count_0 = Counter(test['latestStatus'] for test in tests)
    build1 = "NA"
    count_1 = Counter()
    if test_plan1:
        build1 = get_build_from_test_plan(test_plan1, username, password)
        tests = get_test_list_from_test_plan(test_plan1, username, password)
        count_1 = Counter(test['latestStatus'] for test in tests)

    data = [
        ["Overall QA Report"], ["", build, build1],
        ["Total", sum(count_0.values()), sum(count_1.values())],
    ]
    for status in test_status:
        data.extend([
            [status.capitalize(), count_0[status], count_1[status]],
        ])
    return data


def get_timing_summary():
    """
    ToDo: Need to decide on how to figure out these timings from test JIRAs? DO we need to add or
          remove some timings for R2
    """
    data = [
        ["Timing Summary (Seconds)"],
        ["Parameters", 515, 463, 403, 398, 394],
        ["Update", 1440.0, "NA", "NA", "NA", "NA"],
        ["Deployment", 5220.0, "NA", 5400.0, "NA", "NA"],
        ["Boxing", 240.0, "NA", "NA", "NA", "NA"],
        ["Unboxing", 1380.0, "NA", "NA", "NA", "NA", ],
        ["Onboarding", "NA", "NA", 240.0, "NA", "NA"],
        ["Firmware Update", "NA", "NA", "NA", "NA", "NA"],
        ["Reboot Node", 278.0, "NA", 345.0, "NA", "NA"],
        ["Start Node", "NA", "NA", "NA", "NA", "NA"],
        ["Stop Node", "NA", "NA", 10.0, "NA", "NA"],
        ["Stop all Services", 170.0, "NA", 167.0, "NA", "NA"],
        ["Node Failover", 180.0, "NA", 183.0, "NA", "NA"],
        ["Node Failback", 160.0, "NA", 205.0, "NA", "NA"],
        ["Start All Services", 196.0, "NA", 205.0, "NA", "NA"],
        ["Bucket Creation", 1.0, "NA", 1.0, "NA", "NA"],
        ["Bucket Deletion", 5.0, "NA", 4.0, "NA", "NA"]
    ]
    return data
