"""Common functions for jira access."""
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
import getpass
import os
import sys
from http import HTTPStatus
from jira import JIRA
import requests


def create_new_test_exe(te, jira_id, jira_pwd, tp_info):
    """
    create new test execution using existing te
    """
    print("Create new test execution from {}".format(te))
    test_exe_details = get_issue_details(te, jira_id, jira_pwd)

    summary = test_exe_details.fields.summary
    # description = test_plan_details.fields.description
    description = "Test Execution for Build : {}, Build type: {}, Setup type: {}".format(
        tp_info['build'], tp_info['build_type'], tp_info['setup_type'])
    components = []
    for i in range(len(test_exe_details.fields.components)):
        d = dict()
        d['name'] = test_exe_details.fields.components[i].name
        components.append(d)

    labels = test_exe_details.fields.labels
    env_field = tp_info['build_type'] + "_" + tp_info['build']
    test_eve_labels = test_exe_details.fields.customfield_21006

    tp_dict = {'project':'TEST',
               'summary':summary,
               'description':description,
               'issuetype':{'name':'Test Execution'},
               'components':components,
               'labels':labels,
               'environment':env_field,
               'customfield_21006':test_eve_labels}
    try:
        jira_url = "https://jts.seagate.com/"
        options = {'server':jira_url}
        auth_jira = JIRA(options, basic_auth=(jira_id, jira_pwd))
        new_issue = auth_jira.create_issue(fields=tp_dict)
    except Exception as e:
        sys.exit('Test execution creation failed with exception {}'.format(e))
    else:
        print("Test Execution created Successfully {}".format(new_issue))
        return new_issue.key


def create_new_test_plan(test_plan, jira_id, jira_pwd, tp_info):
    """
    create new test plan using existing test plan
    """
    print("Create new test plan from existing {}".format(test_plan))
    test_plan_details = get_issue_details(test_plan, jira_id, jira_pwd)

    summary = test_plan_details.fields.summary
    # description = test_plan_details.fields.description
    description = "Test Plan for Build : {}, Build type: {}, Setup type: {}".format(
        tp_info['build'], tp_info['build_type'], tp_info['setup_type'])
    components = []
    for i in range(len(test_plan_details.fields.components)):
        d = dict()
        d['name'] = test_plan_details.fields.components[i].name
        components.append(d)

    # labels = test_plan_details.fields.labels
    labels = [tp_info['setup_type']]
    env_field = tp_info['build_type'] + "_" + tp_info['build']

    tp_dict = {'project':'TEST',
               'summary':summary,
               'description':description,
               'issuetype':{'name':'Test Plan'},
               'components':components,
               'labels':labels,
               'environment':env_field}
    try:
        jira_url = "https://jts.seagate.com/"
        options = {'server':jira_url}
        auth_jira = JIRA(options, basic_auth=(jira_id, jira_pwd))
        new_issue = auth_jira.create_issue(fields=tp_dict)
    except Exception as e:
        print(e)
        return ''
    else:
        print("Test plan created Successfully {}".format(new_issue))
        return new_issue.key


def add_te_to_tp(te_list, test_plan, jira_id, jira_password):
    """
    add test executiona tp test plan
    """
    print("Adding test executions to test plan {}".format(test_plan))
    response = requests.post(
        "https://jts.seagate.com/rest/raven/1.0/api/testplan/" + test_plan + "/testexecution",
        headers={'Content-Type':'application/json'}, json={"add":te_list},
        auth=(jira_id, jira_password))
    print(response.status_code)
    if response.status_code == HTTPStatus.OK:
        return True
    elif response.status_code == HTTPStatus.UNAUTHORIZED:
        print('JIRA Unauthorized access')
        return False
    elif response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
        print('JIRA Service Unavailable')
        return False


def add_tests_to_te_tp(existing_te, new_te, new_tp, jira_id, jira_password):
    """
    Add tests to test execution and test plan
    """
    test_list = get_test_ids_from_te(existing_te, jira_id, jira_password)
    if len(test_list) == 0:
        sys.exit("Received no tests from te")
    print("adding tests to test execution {}".format(new_te))
    response = requests.post(
        "https://jts.seagate.com/rest/raven/1.0/api/testexec/" + new_te + "/test",
        headers={'Content-Type':'application/json'}, json={"add":test_list},
        auth=(jira_id, jira_password))

    print(response.status_code)
    if response.status_code == HTTPStatus.UNAUTHORIZED:
        print('JIRA Unauthorized access')
        return False
    elif response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
        print('JIRA Service Unavailable')
        return False
    elif response.status_code != HTTPStatus.OK:
        print('Error while adding tests to test execution')
        return False

    print("adding tests to test plan {}".format(new_tp))
    response = requests.post(
        "https://jts.seagate.com/rest/raven/1.0/api/testplan/" + new_tp + "/test",
        headers={'Content-Type':'application/json'}, json={"add":test_list},
        auth=(jira_id, jira_password))
    print(response.status_code)
    if response.status_code == HTTPStatus.OK:
        return True
    elif response.status_code == HTTPStatus.UNAUTHORIZED:
        print('JIRA Unauthorized access')
        return False
    elif response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
        print('JIRA Service Unavailable')
        return False


def get_test_executions_from_test_plan(test_plan, username, password):
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
    print("Get test executions from test plan")
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/{test_plan}/testexecution'
    response = requests.get(jira_url, auth=(username, password))
    if response.status_code == HTTPStatus.OK:
        return response.json()
    print('get_test_executions GET on {} failed'.format(jira_url))
    print('HEADERS={},BODY={}'.format(response.request.headers, response.request.body))
    sys.exit(1)


def get_test_ids_from_te(test_exe_id, jira_id, jira_password):
    """
        Get test jira ids available in test execution jira
        """
    print("Get test ids from te {}".format(test_exe_id))
    test_list = []
    page_not_zero = 1
    page_cnt = 1
    while page_not_zero:
        jira_url = "https://jts.seagate.com/rest/raven/1.0/api/testexec/{}/test?page={}" \
            .format(test_exe_id, page_cnt)

        try:
            headers = {
                'content-type':"application/json",
                'accept':"application/json",
            }
            response = requests.request("GET", jira_url, data=None,
                                        auth=(jira_id, jira_password),
                                        headers=headers, params=None)
            data = response.json()
        except requests.exceptions.RequestException as ex:
            print(ex)
        else:
            if len(data) == 0:
                page_not_zero = 0
            else:
                page_cnt = page_cnt + 1
                for test in data:
                    test_list.append(test['key'])
    return test_list



def get_issue_details(issue_id, username, password):
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
    options = {'server':jira_url}
    auth_jira = JIRA(options, basic_auth=(username, password))
    return auth_jira.issue(issue_id)


def get_username_password():
    """Get username and password from JIRA."""
    try:
        username = os.environ["JIRA_ID"]
        password = os.environ["JIRA_PASSWORD"]
    except KeyError:
        username = input("JIRA username: ")
        password = getpass.getpass("JIRA password: ")
    return username, password
