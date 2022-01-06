"""Script used to calculate Code Maturity Index for given build."""
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
import argparse
import configparser
import json
import sys
from collections import defaultdict
from http import HTTPStatus

import requests
from jira import JIRA

from report import jira_api

config = configparser.ConfigParser()
config.read('config.ini')
try:
    HOSTNAME = config["REST"]["hostname"]
    DB_USERNAME = config["REST"]["db_username"]
    DB_PASSWORD = config["REST"]["db_password"]
except KeyError:
    print("Could not start REST server. Please verify config.ini file")
    sys.exit(1)

features_weights = {
    "Cluster Manager Operation (Provision)": 10,
    "Cluster User Operation (CSM)": 10,
    "Cluster Monitor Operation (Alerts)": 10,
    "I/O operation (S3bench, CosBench, I/O tools)": 10,
    "Cluster Support (Logging, support bundle, health schema)": 10,
    "High Availability": 10,
    "Security": 10,
    "Data recovery": 10,
    "Application Testing(UDX, BareOS etc..)": 10,
    "Performance": 10,
    "Data Integrity": 10,
    "Longevity": 10,
    "Scalability": 10,
}

bug_priority_weights = {
    "Blocker": 5,
    "Critical": 4,
    "Major": 3,
    "Minor": 2,
    "Trivial": 1
}


def get_selective_tests_for_feature(tp_id: str, feature: str, status: str, username: str,
                                    password: str):
    """Search tests in given test plan, feature and test status"""
    jira_url = "https://jts.seagate.com/"
    options = {'server': jira_url}
    jira = JIRA(options, basic_auth=(username, password))
    if status:
        query = f'issue in testPlanTests(\'{tp_id}\',\'{status}\') AND "Test Domain" = "{feature}"'
    else:
        query = f'issue in testPlanTests(\'{tp_id}\') AND "Test Domain" = "{feature}"'
    issues = jira.search_issues(query, maxResults=300)
    return issues


def get_failed_tests_details(tp_id: str, username: str, password: str):
    """Return all failed tests with/without mapped Bug ID"""
    test_executions = jira_api.get_test_executions_from_test_plan(tp_id, username, password)
    tests = []
    for test_execution in test_executions:
        tests.extend(jira_api.get_test_from_test_execution(test_execution["key"],
                                                           username, password))
    tests = [test for test in tests if test["status"] == "FAIL"]
    return tests


def get_bug_priority_count(total_failed_tests, feature_tests, username, password) -> defaultdict:
    """Return count of Blocker/Critical/Major.. and not mapped failures in given feature"""
    feature_tests = [str(test) for test in feature_tests]
    count = defaultdict(int)
    count["Unmapped"] = 0
    for failed_test in total_failed_tests:
        if failed_test["key"] in feature_tests and "defects" not in failed_test:
            count["unmapped"] += 1
        elif failed_test["key"] in feature_tests and "defects" in failed_test:
            defects = [jira_api.get_issue_details(defect["key"], username, password)
                       for defect in failed_test["defects"]]
            for defect in defects:
                count[defect.fields.priority.name] += 1
    return count


def calculate_cmi(tp_id: str, username, password) -> float:
    """
    Summary: Calculate CMI for given test plan ID

    Description:
        features_cmi = Σ over feature [
            (feature_weight/total_tests_in_feature) *
            (pass_tests - failed_tests - blocked_tests - aborted_tests)
        ]
        where, failed_tests = fail_tests_without_bugs +
                             Σ over bug_priority ( bug_priority_weight * fail_test_with_priority)
    """
    # Total failed test for given build
    total_failed_tests = get_failed_tests_details(tp_id, username, password)
    features_cmi = 0
    for feature, feature_weight in features_weights.items():
        total_tests = get_selective_tests_for_feature(tp_id, feature, "", username, password)
        pass_tests = get_selective_tests_for_feature(tp_id, feature, "PASS", username, password)
        blocked_tests = get_selective_tests_for_feature(tp_id, feature, "BLOCKED", username,
                                                        password)
        aborted_tests = get_selective_tests_for_feature(tp_id, feature, "ABORTED", username,
                                                        password)
        count = get_bug_priority_count(total_failed_tests, total_tests, username, password)
        scaled_failures = + (
                count["Blocker"] * bug_priority_weights["Blocker"] +
                count["Critical"] * bug_priority_weights["Critical"] +
                count["Major"] * bug_priority_weights["Major"] +
                count["Minor"] * bug_priority_weights["Minor"] +
                count["Trivial"] * bug_priority_weights["Trivial"]
        )
        failed_tests = count["Unmapped"] + scaled_failures
        scaled_tests = len(pass_tests) - failed_tests - len(blocked_tests) - len(aborted_tests)
        if total_tests:
            features_cmi += (feature_weight / len(total_tests)) * scaled_tests
    return features_cmi


def save_cmi_in_database(cmi, test_plan_label, build_type, build_no):
    """Save CMI index into database"""
    endpoint = "cmi"
    host = "http://cftic2.pun.seagate.com:5000/"
    payload = {
        "cmi": cmi,
        "testPlanLabel": test_plan_label,
        "buildType": build_type,
        "buildNo": build_no,
        "db_username": DB_USERNAME,
        "db_password": DB_PASSWORD
    }
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", host + endpoint,
                                headers=headers, data=json.dumps(payload))

    if response.status_code != HTTPStatus.OK:
        print(f'POST on {host + endpoint} failed')
        print(f'RESPONSE={response.text}\n'
              f'HEADERS={response.request.headers}\n'
              f'BODY={response.request.body}')
        sys.exit(1)


def main():
    """Calculate CMI for given build."""
    parser = argparse.ArgumentParser()
    parser.add_argument('tp', help='Testplan for current build')

    test_plans = parser.parse_args()
    tp_id = test_plans.tp
    username, password = jira_api.get_username_password()
    test_plan = jira_api.get_issue_details(tp_id, username, password)
    test_plan_label = test_plan.fields.labels[0]
    if "_" in test_plan.fields.environment:
        build_type = test_plan.fields.environment.split("_")[0]
        build_no = test_plan.fields.environment.split("_")[1]
    else:
        build_no = test_plan.fields.environment
        build_type = ""
    if not all((test_plan_label, build_no)):
        print(f"Test Plan Label: {test_plan_label}, "
              f"Build Number: {build_no}\n"
              f"Test Plan Label/Environment is empty for this test plan")
    deploy = 1
    box_index = 1
    raw_cmi = calculate_cmi(tp_id, username, password)
    scaled_cmi = raw_cmi * 100 / sum(features_weights.values())
    cmi = deploy * box_index * scaled_cmi
    save_cmi_in_database(cmi, test_plan_label, build_type, build_no)


if __name__ == '__main__':
    main()
