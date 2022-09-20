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
"""
JIRA Access Utility Class
"""
import json
import sys
import traceback
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import datetime
import logging
import time
from jira import JIRA
from jira import JIRAError
from jira import Issue
from http import HTTPStatus

LOGGER = logging.getLogger(__name__)


class JiraTask:
    def __init__(self, jira_id, jira_password):
        self.jira_id = jira_id
        self.jira_password = jira_password
        self.auth = (self.jira_id, self.jira_password)
        self.headers = {
            'content-type': "application/json",
            'accept': "application/json",
        }
        self.retry_strategy = Retry(
            total=10,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 400, 404, 408],
            method_whitelist=["HEAD", "GET", "OPTIONS"]
        )
        self.adapter = HTTPAdapter(max_retries=self.retry_strategy)
        self.http = requests.Session()
        self.http.mount("https://", self.adapter)
        self.http.mount("http://", self.adapter)
        self.jira_url = "https://jts.seagate.com/"

    def get_test_ids_from_te(self, test_exe_id, status=None):
        """
        Get test jira ids available in test execution jira
        """
        if status is None:
            status = ['ALL']
        test_list = []
        te_tag = ""
        options = {'server': self.jira_url}
        retries_cnt = 5
        incremental_timeout_sec = 60
        req_success = False
        retry_attempt = 0
        id_list = []
        test_tuple = ()
        while (not req_success) and retries_cnt:
            try:
                auth_jira = JIRA(options, basic_auth=self.auth)
                te = auth_jira.issue(test_exe_id)
                if te:
                    te_tags = te.fields.customfield_21006
                    if te_tags:
                        te_tag = te_tags[0]
                        te_tag = te_tag.lower()
                    req_success = True
            except (JIRAError, requests.exceptions.RequestException) as fault:
                if fault.status_code == HTTPStatus.UNAUTHORIZED:
                    raise EnvironmentError("Unauthorized JIRA credentials") from fault
                print('Error occurred in getting te tag')
                LOGGER.error('Error occurred %s in getting te_tag from %s', fault, test_exe_id)
                retries_cnt = retries_cnt - 1
                retry_attempt = retry_attempt + 1
                if retries_cnt == 0:
                    raise EnvironmentError(
                        "Unable to access JIRA. Please check above errors.") from fault
                time.sleep(incremental_timeout_sec * retry_attempt)
        if te_tag != "":
            page_not_zero = 1
            page_cnt = 1
            while page_not_zero:
                jira_url = "https://jts.seagate.com/rest/raven/1.0/api/testexec/{}/test?" \
                           "page={}&limit=50".format(test_exe_id, page_cnt)
                try:
                    response = self.http.get(jira_url, data=None,
                                             auth=(self.jira_id, self.jira_password),
                                             headers=self.headers, params=None)
                    data = response.json()
                except Exception as fault:
                    print(fault)
                    LOGGER.error('An error %s occurred in fetching tests from TE.', fault)
                else:
                    if len(data) == 0:
                        page_not_zero = 0
                    else:
                        page_cnt = page_cnt + 1
                        for test in data:
                            if 'ALL' in status:
                                test_list.append(test['key'])
                                id_list.append(test['id'])
                            elif str(test['status']) in status:
                                test_list.append(test['key'])
                                id_list.append(test['id'])
                        test_tuple = tuple(zip(test_list, id_list))
        return test_tuple, te_tag

    def get_test_list_from_te(self, test_exe_id, status=None):
        """
        Get required test jira information for all tests from test execution jira.
        """
        if status is None:
            status = ['ALL']
        test_details = []
        test_tuple, te_tag = self.get_test_ids_from_te(test_exe_id, status)
        test_list = list(list(zip(*test_tuple))[0])
        for test in test_list:
            test_id = str(test)
            jira_link = 'https://jts.seagate.com/rest/raven/1.0/api/test?keys=' + test_id
            response = requests.get(jira_link, auth=(self.jira_id, self.jira_password))
            test_data = response.json()
            test_to_execute = test_data[0]['definition']
            options = {'server': self.jira_url}
            auth_jira = JIRA(options, basic_auth=(self.jira_id, self.jira_password))
            issue = auth_jira.issue(test_id)
            comments = issue.fields.comment.comments
            timeout_sec = 0
            for com in comments:
                com.body = com.body.lower()
                if "test timeout" in com.body:
                    try:
                        print("test timeout found : {}".format(com.body))
                        timeout_jira = int(com.body.split(":")[1])
                        timeout_sec = timeout_jira * 60
                    except Exception as ex:
                        print("Exception found during parsing timeout {}".format(com.body))
                        print("Exception : {}".format(ex))

            # label = issue.fields.labels
            # s = issue.fields.summary
            test_name = issue.fields.summary
            # test_name_full = test_id + "_" + test_name.replace(" ", "_")
            test_details.append([test_id, test_name, test_to_execute])
        else:
            print("Returned code from xray jira request: {}".format(response.status_code))
        return test_details, te_tag

    def get_test_plan_details(self, test_plan: str) -> [dict]:
        """
        Summary: Get test executions from test plan.

        Description: Returns dictionary of test executions from test plan.

        Args:
            test_plan:  (str): Test plan number in JIRA

        Returns:
            List of dictionaries
            Each dict will have id, key, summary, self, testEnvironments
            [{"id": 311993, "key": "TEST-16653", "summary": "TE:Auto-Stability-Release 515",
             "self": "https://jts.seagate.com/rest/api/2/issue/311993",
             "testEnvironments": ["515_full"]},
            ]
        """
        jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/{test_plan}/testexecution'
        try:
            response = self.http.get(jira_url, auth=self.auth, headers=self.headers)
        except (JIRAError, requests.exceptions.RequestException) as fault:
            raise EnvironmentError("Unable to access JIRA. Please check above errors.") from fault
        return response.json()

    @staticmethod
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
        i = 0
        while True:
            i = i + 1
            query = {'limit': 100, 'page': i}
            response = requests.get(jira_url, auth=(username, password), params=query)
            if response.status_code == HTTPStatus.OK and response.json():
                responses.extend(response.json())
            elif response.status_code == HTTPStatus.OK and not response.json():
                break
            else:
                LOGGER.info("get_test_list GET on %s failed", jira_url)
                LOGGER.info("RESPONSE=%s\n", response.text)
                LOGGER.info("HEADERS=%s\n", response.request.headers)
                LOGGER.info("BODY=%s", response.request.body)
                sys.exit(1)
        return responses

    def get_issue_details(self, issue_id: str, auth_jira: JIRA = None) -> Issue:
        """
        Get issue details from Jira.
        Args:
            issue_id (str): Bug ID or TEST ID string
            auth_jira: Jira obj passed to function
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
        retry = 0
        while True:
            try:
                if not auth_jira or not isinstance(auth_jira, JIRA):
                    options = {'server': self.jira_url}
                    auth_jira = JIRA(options, basic_auth=self.auth)
                return auth_jira.issue(issue_id)
            except (JIRAError, requests.exceptions.RequestException, Exception) as fault:
                LOGGER.error(f'Error occurred {fault} in getting test details for {issue_id}')
                retry += 1
                if retry > 3:
                    return None

    def update_test_jira_status(self, test_exe_id, test_id, test_status, log_path=''):
        """
        Update test jira status in xray jira.
        """
        state = {}
        status = {}
        state["testExecutionKey"] = test_exe_id
        status["testKey"] = test_id
        if test_status == 'Executing':
            status["start"] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        else:
            status["finish"] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
            status["comment"] = log_path
        status["status"] = test_status
        state["tests"] = []
        state['tests'].append(status)
        data = json.dumps(state)
        jira_url = self.jira_url + "/rest/raven/1.0/import/execution"
        response = requests.request("POST", jira_url, data=data,
                                    auth=(self.jira_id, self.jira_password),
                                    headers=self.headers,
                                    params=None)
        return response

    def get_test_details(self, test_exe_id: str) -> list:
        """
        Get details of the test cases in a test execution ticket.
        """
        test_info = list()
        try:
            jira_url = "https://jts.seagate.com/rest/raven/1.0/api/testexec/{}/test".format(
                test_exe_id)
            response = requests.get(jira_url, auth=(self.jira_id, self.jira_password))
            if response is not None:
                if response.status_code != HTTPStatus.OK:
                    page_not_zero = 1
                    page_cnt = 1
                    timeout_sec = 180
                    timeout_start = time.time()
                    while page_not_zero and (time.time() < timeout_start + timeout_sec):
                        jira_url = "https://jts.seagate.com/rest/raven/1.0/api/testexec/{}/" \
                                   "test?page={}".format(test_exe_id, page_cnt)
                        try:
                            response = requests.get(jira_url,
                                                    auth=(self.jira_id, self.jira_password))
                            data = response.json()
                            test_info.append(data)
                        except Exception as e:
                            LOGGER.error('Exception in get_test_details: %s', e)
                        else:
                            if len(data) == 0:
                                page_not_zero = 0
                            else:
                                page_cnt = page_cnt + 1
                else:
                    data = response.json()
                    test_info.append(data)
            return test_info
        except requests.exceptions.RequestException as re:
            LOGGER.error('Request exception in get_test_details %s', re)
            return test_info
        except ValueError as ve:
            LOGGER.error('Value exception in get_test_details %s', ve)
            return test_info
        except Exception as e:
            LOGGER.error('Exception in get_test_details: %s', e)
            return test_info

    def update_execution_details(self, test_run_id: str, test_id: str,
                                 comment: str) -> bool:
        """
        Add comment to the mentioned jira id.
        """
        try:
            url = f"https://jts.seagate.com/rest/raven/1.0/api/testrun/{test_run_id}/comment"

            response = requests.request("PUT", url, data=comment,
                                        auth=(self.jira_id, self.jira_password),
                                        headers=self.headers,
                                        params=None)
            print("Response code: %s", response.status_code)
            if response.status_code == HTTPStatus.OK:
                print(f"Updated execution details successfully for test id {test_id}")
                return True
            return False
        except JIRAError as err:
            print(err.status_code, err.text)
            return False
