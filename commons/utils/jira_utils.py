"""
JIRA Access Utility Class
"""
import json
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

    def get_test_ids_from_te(self, test_exe_id, status='ALL'):
        """
        Get test jira ids available in test execution jira
        """
        test_list = []
        te_tag = ""
        id_list = []
        test_id_dict = {}

        jira_url = "https://jts.seagate.com/"
        options = {'server': jira_url}
        retries_cnt = 5
        incremental_timeout_sec = 60
        req_success = False
        retry_attempt = 0
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
                print('Error occurred in getting te tag')
                LOGGER.error(f'Error occurred {fault} in getting te_tag from {test_exe_id}')
                retries_cnt = retries_cnt - 1
                retry_attempt = retry_attempt + 1
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
                            if status == 'ALL':
                                test_list.append(test['key'])
                                id_list.append(test['id'])
                            elif status == 'FAIL':
                                if str(test['status']) == 'FAIL':
                                    test_list.append(test['key'])
                                    id_list.append(test['id'])
                            elif status == 'TODO':
                                if str(test['status']) == 'TODO':
                                    test_list.append(test['key'])
                                    id_list.append(test['id'])
                            elif status == 'PASS':
                                if str(test['status']) == 'PASS':
                                    test_list.append(test['key'])
                                    id_list.append(test['id'])
                            elif status == 'ABORTED':
                                if str(test['status']) == 'ABORTED':
                                    test_list.append(test['key'])
                                    id_list.append(test['id'])
                        test_id_dict = dict(zip(test_list, id_list))
        return test_list, te_tag, test_id_dict

    def get_test_list_from_te(self, test_exe_id, status='ALL'):
        """
        Get required test jira information for all tests from test execution jira.
        """
        test_details = []
        test_list, te_tag, test_id_dict = self.get_test_ids_from_te(
            test_exe_id, status)
        for test in test_list:
            test_id = str(test)
            jira_link = 'https://jts.seagate.com/rest/raven/1.0/api/test?keys=' + test_id
            response = requests.get(jira_link, auth=(self.jira_id, self.jira_password))
            test_data = response.json()
            test_to_execute = test_data[0]['definition']
            jira_url = "https://jts.seagate.com/"
            options = {'server': jira_url}
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
        return test_details, te_tag, test_id_dict

    def get_test_plan_details(self, test_plan_id: str) -> [dict]:
        """
        Summary: Get test executions from test plan.

        Description: Returns dictionary of test executions from test plan.

        Args:
            test_plan_id:  (str): Test plan number in JIRA

        Returns:
            List of dictionaries
            Each dict will have id, key, summary, self, testEnvironments
            [{"id": 311993, "key": "TEST-16653", "summary": "TE:Auto-Stability-Release 515",
             "self": "https://jts.seagate.com/rest/api/2/issue/311993",
             "testEnvironments": ["515_full"]},
            ]
        """
        jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/' \
                   f'{test_plan_id}/testexecution'
        response = requests.get(jira_url, auth=(self.jira_id, self.jira_password))
        if response.status_code == HTTPStatus.OK:
            return response.json()
        return response.text

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
        try:
            if not auth_jira or not isinstance(auth_jira, JIRA):
                jira_url = "https://jts.seagate.com/"
                options = {'server': jira_url}
                auth_jira = JIRA(options, basic_auth=self.auth)
            return auth_jira.issue(issue_id)
        except (JIRAError, requests.exceptions.RequestException) as fault:
            LOGGER.error(f'Error occurred {fault} in getting test details for {issue_id}')

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
        jira_url = "https://jts.seagate.com/" + "/rest/raven/1.0/import/execution"
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
        run_id = None
        try:
            url = "https://jts.seagate.com/rest/raven/1.0/testrun/{}/comment".format(test_run_id)

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
