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
print(test_plan_id)
jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/' \
                   f'{test_plan_id}/test'
response = requests.get(jira_url, auth=(jira_id, jira_password))
if response.status_code == HTTPStatus.OK:
    res = response.json()
    print(len([test for test in res if test['latestStatus'] == 'TODO']))


'''def get_test_plan_details(test_plan_id: str):
    jira_url = f'https://jts.seagate.com/rest/raven/1.0/api/testplan/' \
               f'{test_plan_id}/test'
    response = requests.get(jira_url, auth=("938337", "Rohit@2006"))
    if response.status_code == HTTPStatus.OK:
        res = response.json()
        print(len([i for i in res if i['latestStatus'] == 'TODO']))
    return response.text


def main():
    """
    Main Function.
    """
    parser = argparse.ArgumentParser(description="TODO count")
    parser.add_argument("-tp", help="test plan", required=True)
    args = parser.parse_args()
    test_plan_id = args.tp
    x = get_test_plan_details(test_plan_id)
    # print(x)


if __name__ == "__main__":
    main()
'''