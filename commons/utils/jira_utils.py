"""
JIRA Access Utility Class
"""
import json
import traceback
import requests
import datetime
from jira import JIRA, JIRAError
from http import HTTPStatus


class JiraTask:
    def __init__(self, jira_id, jira_password):
        self.jira_id = jira_id
        self.jira_password = jira_password
        self.auth = (self.jira_id, self.jira_password)
        self.headers = {
            'content-type': "application/json",
            'accept': "application/json",
        }

    def get_test_ids_from_te(self, test_exe_id, status='ALL'):
        """
        Get test jira ids available in test execution jira
        """
        try:
            jira_url = 'https://jts.seagate.com/rest/raven/1.0/testruns?testExecKey=' + test_exe_id
            response = requests.get(jira_url, auth=(self.jira_id, self.jira_password))
            if response.status_code != HTTPStatus.OK:
                print("Response code/text from Jira is {} and {}".format(response.status_code,
                                                                         str(response)))
        except requests.exceptions.RequestException:
            print(traceback.print_exc())
        test_list = []
        te_tag = ""
        if response.status_code == HTTPStatus.OK:
            data = response.json()
            if len(data[0]['testEnvironments']) > 0:
                te_tag = data[0]['testEnvironments'][0]
                te_tag = te_tag.lower()
            page_not_zero = 1
            page_cnt = 1
            while page_not_zero:
                jira_url = "https://jts.seagate.com/rest/raven/1.0/api/testexec/{}/test?page={}" \
                    .format(test_exe_id, page_cnt)

                try:
                    response = requests.request("GET", jira_url, data=None, auth=(self.jira_id, self.jira_password),
                                                headers=self.headers, params=None)
                    data = response.json()
                except Exception as e:
                    print(e)
                else:
                    if len(data) == 0:
                        page_not_zero = 0
                    else:
                        page_cnt = page_cnt + 1
                        for test in data:
                            if status == 'ALL':
                                test_list.append(test['key'])
                            elif status == 'FAIL':
                                if str(test['status']) == 'FAIL':
                                    test_list.append(test['key'])
                            elif status == 'TODO':
                                if str(test['status']) == 'TODO':
                                    test_list.append(test['key'])
                            elif status == 'PASS':
                                if str(test['status']) == 'PASS':
                                    test_list.append(test['key'])
                            elif status == 'ABORTED':
                                if str(test['status']) == 'ABORTED':
                                    test_list.append(test['key'])
            return test_list, te_tag
        elif response.status_code == HTTPStatus.UNAUTHORIZED:
            print('JIRA Unauthorized access')
        elif response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            print('JIRA Service Unavailable')
        return test_list, te_tag

    def get_test_list_from_te(self, test_exe_id, status='ALL'):
        """
        Get required test jira information for all tests from test execution jira.
        """
        test_details = []
        test_list, te_tag = self.get_test_ids_from_te(test_exe_id, status)
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
        return test_details, te_tag

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

    def get_issue_details(self, issue_id: str):
        """
        Get issue details from Jira.
        Args:
            issue_id (str): Bug ID or TEST ID string
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
        auth_jira = JIRA(options, basic_auth=self.auth)
        return auth_jira.issue(issue_id)

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
        response = requests.request("POST", jira_url, data=data, auth=(self.jira_id, self.jira_password),
                                    headers=self.headers,
                                    params=None)
        return response

    def get_test_details(self, test_exe_id):
        """
        Get details of the test cases in a test execution ticket
        """
        jira_url = "https://jts.seagate.com/rest/raven/1.0/api/testexec/{}/test".format(test_exe_id)
        response = requests.get(jira_url, auth=(self.jira_id, self.jira_password))
        data = response.json()
        return data

    def update_execution_details(self, data, test_id, comment):
        """
        Add comment to the mentioned jira id
        """
        run_id = None
        try:
            if not data:
                print("No test details found in test execution tkt")
                return False

            for test in data:
                if test['key'] == test_id:
                    run_id = test['id']

            if run_id is None:
                print("Test ID %s not found in test execution ticket details",
                      test_id)
                return False

            url = "https://jts.seagate.com/rest/raven/1.0/testrun/{}/comment".format(run_id)

            response = requests.request("PUT", url, data=comment,
                                        auth=(self.jira_id, self.jira_password),
                                        headers=self.headers,
                                        params=None)
            return response
        except JIRAError as err:
            print(err.status_code, err.text)
