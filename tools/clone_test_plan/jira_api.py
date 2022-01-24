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
import concurrent.futures
import getpass
import os
import sys
from http import HTTPStatus
from jira import JIRA
import time

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

DEFAULT_TIMEOUT = 180  # seconds


class TimeoutHTTPAdapter(HTTPAdapter):
    """
    Timeout adapater
    """

    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """
        Set timeout
        """
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


class JiraTask:
    """
    Jira Task for clone for test plan tool
    """

    def __init__(self):
        try:
            self.jira_id = os.environ["JIRA_ID"]
            self.jira_password = os.environ["JIRA_PASSWORD"]
        except KeyError:
            self.jira_id = input("JIRA username: ")
            self.jira_password = getpass.getpass("JIRA password: ")

        self.jira_url = "https://jts.seagate.com/"
        self.options = {'server': self.jira_url}
        self.auth_jira = JIRA(self.options, basic_auth=(self.jira_id, self.jira_password))

        self.auth = (self.jira_id, self.jira_password)
        self.headers = {
            'content-type': "application/json",
            'accept': "application/json",
        }
        self.retry_strategy = Retry(
            total=1,
            backoff_factor=10,
            status_forcelist=[429, 500, 502, 503, 504, 400, 404, 408],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"]
        )
        self.http = requests.Session()
        self.http.mount("https://", TimeoutHTTPAdapter(max_retries=self.retry_strategy))
        self.http.mount("http://", TimeoutHTTPAdapter(max_retries=self.retry_strategy))

    def check_test_environment_platform(self, tests, tp_info):
        """
        Check environment, core category and platform of test case and test plan.
        If it matches then add test to test plan.
        """
        valid_tests = []
        tp_env = tp_info['env']
        tp_platform = tp_info['platform']
        num_nodes = tp_info['nodes']
        core_category = tp_info['core_category']
        for test_id in tests:
            is_valid_platform = False
            is_valid_env = False
            is_valid_category = False
            details = self.get_issue_details(test_id)
            if details:
                tp_platform = tp_platform.lower()
                if ('vm' in tp_platform) and ('hw' in tp_platform):
                    is_valid_platform = True
                else:
                    platform_field = details.fields.customfield_22982
                    if platform_field:
                        platform_field = platform_field[0].lower()
                        if tp_platform.strip() in platform_field.strip():
                            is_valid_platform = True
                    else:
                        is_valid_platform = True
                env_field = details.fields.environment
                if num_nodes == '':
                    is_valid_env = True
                else:
                    if env_field:
                        env_field = env_field.lower()
                        tp_env = tp_env.lower()
                        if env_field.strip() == "multinode":
                            is_valid_env = True
                        elif env_field.strip() == "1node" and num_nodes == 1:
                            is_valid_env = True
                        elif tp_env.strip() == env_field.strip():
                            is_valid_env = True
                    else:
                        is_valid_env = True
                if core_category == 'NA':
                    is_valid_category = True
                else:
                    if details.fields.customfield_21085:
                        test_category = details.fields.customfield_21085.value
                        if core_category.lower().strip() in test_category.lower():
                            is_valid_category = True
                    else:
                        is_valid_category = True
            if is_valid_platform and is_valid_env and is_valid_category:
                valid_tests.append(test_id)
            else:
                print("{} is not valid for this test plan".format(test_id))
        return valid_tests

    def create_new_test_exe(self, te, tp_info, skip_te, product_family):
        """
        create new test execution using existing te
        """
        print("Create new test execution from {}".format(te))
        is_te_skipped = False
        test_list = self.get_test_ids_from_te(te)
        if len(test_list) == 0:
            print("Skipping creating new TE as existing TE has no tests")
            return '', is_te_skipped, ''
        else:
            test_exe_details = self.get_issue_details(te)

            summary = test_exe_details.fields.summary
            # description = test_plan_details.fields.description
            description = "Test Execution for Build : {}, Build Branch: {}, Setup type: {}".format(
                tp_info['build'], tp_info['build_branch'], tp_info['setup_type'])
            components = []
            for i in range(len(test_exe_details.fields.components)):
                d = dict()
                d['name'] = test_exe_details.fields.components[i].name
                components.append(d)

            labels = test_exe_details.fields.labels
            env_field = tp_info['build_branch'] + "_" + tp_info['build']
            test_eve_labels = test_exe_details.fields.customfield_21006
            if te in skip_te:
                is_te_skipped = True

            affect_ver = []
            affect_ver_dict = dict()
            if product_family == 'LR':
                affect_ver_dict['name'] = 'LR-R2'
            else:
                affect_ver_dict['name'] = 'CORTX-R2'
            affect_ver.append(affect_ver_dict)

            te_dict = {'project': 'TEST',
                       'summary': summary,
                       'description': description,
                       'issuetype': {'name': 'Test Execution'},
                       'components': components,
                       'labels': labels,
                       'versions': affect_ver,
                       'environment': env_field,
                       'customfield_21006': test_eve_labels}
            issue_key = self.create_issue(te_dict)
            return issue_key, is_te_skipped, test_list

    def create_new_test_plan(self, test_plan, tp_info):
        """
        create new test plan using existing test plan
        """
        print("Create new test plan from existing {}".format(test_plan))
        test_plan_details = self.get_issue_details(test_plan)

        # description = test_plan_details.fields.description
        description = "Test Plan for Build : {}, Build Branch: {}, Setup type: {}, Nodes: {}". \
            format(tp_info['build'], tp_info['build_branch'], tp_info['setup_type'],
                   tp_info['nodes'])
        components = []
        for i in range(len(test_plan_details.fields.components)):
            d = dict()
            d['name'] = test_plan_details.fields.components[i].name
            components.append(d)

        # labels = test_plan_details.fields.labels
        labels = [tp_info['setup_type']]

        fix_versions = []
        fix_dict = dict()
        for i in range(len(test_plan_details.fields.fixVersions)):
            fix_dict['name'] = test_plan_details.fields.fixVersions[i].name
            fix_versions.append(fix_dict)

        affect_ver = []
        affect_ver_dict = dict()
        for i in range(len(test_plan_details.fields.versions)):
            affect_ver_dict['name'] = test_plan_details.fields.versions[i].name
            affect_ver.append(affect_ver_dict)

        env_field = str(tp_info['nodes']) + 'Node'

        if tp_info['product_family'] == 'LR':
            if not fix_versions:
                fix_dict['name'] = tp_info['fix_version']
                fix_versions.append(fix_dict)

            if not affect_ver:
                affect_ver_dict['name'] = tp_info['affect_version']
                affect_ver.append(affect_ver_dict)

            # TP LR2 {Environment}_{Platform Type}_{Branch}_{Build}
            summary = "TP LR2 " + str(env_field) + "_" + str(tp_info['platform']) + "_" + tp_info[
                'build_branch'] + "_" + tp_info['build']
        else:
            if not fix_versions:
                fix_dict['name'] = 'CORTX-R2'
                fix_versions.append(fix_dict)

            if not affect_ver:
                affect_ver_dict['name'] = 'CORTX-R2'
                affect_ver.append(affect_ver_dict)

            # env_field = 'K8'
            # TP CORTX-R2 {Environment}_{Platform Type}_{Branch}_{Build}
            summary = "TP K8 CORTX-R2 " + str(env_field) + "_" + str(tp_info['platform']) + "_" \
                      + tp_info['build_branch'] + "_" + tp_info['build']

        tp_dict = {'project': 'TEST',
                   'summary': summary,
                   'description': description,
                   'issuetype': {'name': 'Test Plan'},
                   'components': components,
                   'labels': labels,
                   'environment': env_field,
                   'fixVersions': fix_versions,
                   'versions': affect_ver,
                   'customfield_22980': [tp_info['build']],
                   'customfield_22981': [tp_info['build_branch']],
                   'customfield_22982': [tp_info['platform']],
                   'customfield_22983': [tp_info['server_type']],
                   'customfield_22984': [tp_info['enclosure_type']]}
        issue_key = self.create_issue(tp_dict)
        return issue_key, env_field

    def create_issue(self, issue_dict):
        """
        create the issue based on dict provided
        """
        retries_cnt = 5
        incremental_timeout_sec = 60
        retry_attempt = 0
        new_issue_created = ''
        while retries_cnt:
            try:
                new_issue = self.auth_jira.create_issue(fields=issue_dict)
                new_issue_created = new_issue.key
            except Exception as e:
                print(e)
                retries_cnt = retries_cnt - 1
                retry_attempt = retry_attempt + 1
                time.sleep(incremental_timeout_sec * retry_attempt)
            else:
                print("Issue created Successfully {}".format(new_issue))
                return new_issue_created
        return new_issue_created

    def add_te_to_tp(self, te_list, test_plan):
        """
        add test executiona tp test plan
        """
        print("Adding test executions to test plan {}".format(test_plan))
        try:
            response = self.http.post(
                "https://jts.seagate.com/rest/raven/1.0/api/testplan/" +
                test_plan + "/testexecution",
                headers={'Content-Type': 'application/json'}, json={"add": te_list},
                auth=(self.jira_id, self.jira_password))
            print(response.status_code)
            if response.status_code == HTTPStatus.OK:
                return True
            elif response.status_code == HTTPStatus.UNAUTHORIZED:
                print('JIRA Unauthorized access')
                return False
            elif response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
                print('JIRA Service Unavailable')
                return False
        except Exception as e:
            print(f"Exception {e} in adding te to tp")

    def add_tests_to_te_tp(self, new_te, new_tp, tp_info, test_list):
        """
        Add tests to test execution and test plan
        """
        if len(test_list) == 0:
            return False
        else:
            valid_tests = []

            # Divide test list into multiple parts for parallel processing
            sub_list_len = len(test_list)
            if sub_list_len > 10:
                sub_list_len = int(sub_list_len / 10)

            test_lists = [test_list[i:i + sub_list_len] for i in
                          range(0, len(test_list), sub_list_len)]

            with concurrent.futures.ProcessPoolExecutor() as executor:
                valid_list = {executor.submit(self.check_test_environment_platform, tests, tp_info):
                                  tests for tests in test_lists}
                for future in concurrent.futures.as_completed(valid_list):
                    try:
                        data = future.result()
                        valid_tests.extend(data)
                    except Exception as exc:
                        print(exc)
            if valid_tests:
                print("adding {} tests to test execution {}".format(len(valid_tests), new_te))
                try:
                    response = self.http.post(
                        "https://jts.seagate.com/rest/raven/1.0/api/testexec/" + new_te + "/test",
                        headers={'Content-Type': 'application/json'}, json={"add": valid_tests},
                        auth=(self.jira_id, self.jira_password))
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
                except Exception as e:
                    print(f"Exception {e} in adding tests to te")

                print("adding {} tests to test plan {}".format(len(valid_tests), new_tp))
                try:
                    response = self.http.post(
                        "https://jts.seagate.com/rest/raven/1.0/api/testplan/" + new_tp + "/test",
                        headers={'Content-Type': 'application/json'}, json={"add": valid_tests},
                        auth=(self.jira_id, self.jira_password))
                    print(response.status_code)
                    if response.status_code == HTTPStatus.OK:
                        return True
                    elif response.status_code == HTTPStatus.UNAUTHORIZED:
                        print('JIRA Unauthorized access')
                        return False
                    elif response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
                        print('JIRA Service Unavailable')
                        return False
                except Exception as e:
                    print(f"Exception {e} in adding tests to tp")

    def get_test_executions_from_test_plan(self, test_plan):
        """
        Summary: Get test executions from test plan.

        Description: Returns dictionary of test executions from test plan.

        Args:
            test_plan (str): Test plan number in JIRA

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
        try:
            jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/{test_plan}/' \
                       f'testexecution'
            response = self.http.get(jira_url, auth=(self.jira_id, self.jira_password))
            if response.status_code == HTTPStatus.OK:
                return response.json()
        except Exception as e:
            print(f"Exception {e} in get_test_executions")
            sys.exit(1)

    def get_test_ids_from_te(self, test_exe_id):
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
                    'content-type': "application/json",
                    'accept': "application/json",
                }
                response = self.http.get(jira_url, data=None,
                                         auth=(self.jira_id, self.jira_password),
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

    def get_issue_details(self, issue_id):
        """

        Args:
          issue_id : test id to get details from
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
        retries_cnt = 5
        incremental_timeout_sec = 60
        retry_attempt = 0
        issue_details = ''
        while retries_cnt:
            try:
                if not self.auth_jira or not isinstance(self.auth_jira, JIRA):
                    auth_jira = JIRA(self.options, basic_auth=self.auth)
                    issue_details = auth_jira.issue(issue_id)
                else:
                    if not hasattr(self.auth_jira._session, 'max_retries'):
                        setattr(self.auth_jira._session, 'max_retries', 3)
                    if not hasattr(self.auth_jira._session, 'timeout'):
                        setattr(self.auth_jira._session, 'timeout', 30)
                    issue_details = self.auth_jira.issue(issue_id)
            except Exception as e:
                print(e)
                retries_cnt = retries_cnt - 1
                retry_attempt = retry_attempt + 1
                time.sleep(incremental_timeout_sec * retry_attempt)
            else:
                return issue_details
        return issue_details

    def add_comment(self, test_id, comment):
        """
        Add comment to test jira
        """
        retries_cnt = 5
        incremental_timeout_sec = 60
        retry_attempt = 0
        comment_added = False
        while (not comment_added) and retries_cnt:
            try:
                self.auth_jira.add_comment(test_id, comment)
            except Exception as e:
                print(e)
                retries_cnt = retries_cnt - 1
                retry_attempt = retry_attempt + 1
                time.sleep(incremental_timeout_sec * retry_attempt)
            else:
                print("Comment Added to jira {}".format(test_id))
                comment_added = True
