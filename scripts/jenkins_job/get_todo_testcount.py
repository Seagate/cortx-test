import argparse
import requests
from http import HTTPStatus

parser = argparse.ArgumentParser(description="TODO count")
parser.add_argument("-tp", help="test plan", required=True)
parser.add_argument("-ji", help="jira password", required=True)
parser.add_argument("-jp", help="jira id", required=True)
args=parser.parse_args()
test_plan_id = args.tp
jira_password = args.jp
jira_id = args.ji
jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/' \
                   f'{test_plan_id}/test'
response = requests.get(jira_url, auth=(jira_id, jira_password))
if response.status_code == HTTPStatus.OK:
    res = response.json()
    print(len([test for test in res if test['latestStatus'] == 'TODO']))


'''
def get_test_plan_details(test_plan_id,jira_id,jira_password) -> [dict]:
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/' \
                   f'{test_plan_id}/test'
    response = requests.get(jira_url, auth=(jira_id, jira_password))
    if response.status_code == HTTPStatus.OK:
       res = response.json()
       return(len([test for test in res if test['latestStatus']=='TODO']))
    return response.text

def main():
    parser=argparse.ArgumentParser(description="TODO count")
    parser.add_argument("-tp", help="test plan", required=True)
    parser.add_argument("-ji", help="jira password", required=True)
    parser.add_argument("-jp", help="jira id", required=True)
    args=parser.parse_args()
    test_plan_id = args.tp
    jira_password = args.jp
    jira_id = args.ji 
    x = get_test_plan_details(test_plan_id,jira_id,jira_password)
    print(x)

if __name__ == "__main__":
  main()
'''