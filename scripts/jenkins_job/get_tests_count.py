from http import HTTPStatus
import argparse
import csv
import os
#import requests
from commons.utils import jira_utils

# CSV file contain test count in sequence[total,passed,fail,skip,todo]
TOTAL_COUNT_CSV = 'total_count.csv'

'''
def get_test_plan_test_count(test_plan_id, jira_id, jira_password):
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/' \
                   f'{test_plan_id}/test'
    response = requests.get(jira_url, auth=(jira_id, jira_password))
    if response.status_code == HTTPStatus.OK:
        res = response.json()
        total = len(res)
        todo = len([test for test in res if test['latestStatus'] == 'TODO'])
        passed = len([test for test in res if test['latestStatus'] == 'PASS'])
        fail = len([test for test in res if test['latestStatus'] == 'FAIL'])
        skip = len([test for test in res if test['latestStatus'] == 'SKIPPED'])
        with open(os.path.join(os.getcwd(), TOTAL_COUNT_CSV), 'w', newline='') as tp_info_csv:
            writer = csv.writer(tp_info_csv)
            writer.writerow([total, passed, fail, skip, todo])
'''

def main():
    parser = argparse.ArgumentParser(description="TODO count")
    parser.add_argument("-tp", help="test plan", required=True)
    parser.add_argument("-ji", help="jira password", required=True)
    parser.add_argument("-jp", help="jira id", required=True)
    args = parser.parse_args()
    test_plan_id = args.tp
    jira_password = args.jp
    jira_id = args.ji
    res = jira_utils.JiraTask.get_test_list_from_test_plan(test_plan_id, jira_id, jira_password)
    #get_test_plan_test_count(test_plan_id, jira_id, jira_password)
    total = len(res)
    todo = len([test for test in res if test['latestStatus'] == 'TODO'])
    passed = len([test for test in res if test['latestStatus'] == 'PASS'])
    fail = len([test for test in res if test['latestStatus'] == 'FAIL'])
    skip = len([test for test in res if test['latestStatus'] == 'SKIPPED'])
    with open(os.path.join(os.getcwd(), TOTAL_COUNT_CSV), 'w', newline='') as tp_info_csv:
        writer = csv.writer(tp_info_csv)
        writer.writerow([total, passed, fail, skip, todo])


if __name__ == "__main__":
    main()
