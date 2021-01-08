import os
import subprocess
import argparse
from core import runner
from commons.utils.jira_utils import JiraTask

import getpass

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json_file", type=str,
                        help="json file name")
    parser.add_argument("-r", "--html_report", type=str, default='report.html',
                        help="html report name")
    parser.add_argument("-d", "--db_update", type=str, default='n',
                        help="db update required: y/n")
    parser.add_argument("-te", "--test_exe", type=str,
                        help="jira xray test execution id")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id")
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value")

    return parser.parse_args()


def get_jira_credential():
    jira_id = ''
    jira_pwd = ''
    try :
        jira_id = os.environ['JIRA_ID']
        jira_pwd = os.environ['JIRA_PASSWORD']
    except KeyError :
        print("JIRA credentials not found in environment")
        jira_id = input("JIRA username: ")
        jira_pwd = getpass.getpass("JIRA password: ")
    return jira_id, jira_pwd


def run_pytest_cmd(cmd_line):
    # Run py-test cmd line
    prc = subprocess.Popen(cmd_line)
    out, err = prc.communicate()

    # TODO Get test execution information for upload in DB

    # TODO Call DB API to upload test execution information
    # if str(db_update[0]).lower() == 'y' :
    #    pass


def delete_status_files():
    file_list = ['failed_tests.log', 'passed_tests.log', 'other_test_calls.log']
    for file in file_list :
        if os.path.exists(file) :
            os.remove(file)


def process_test_list(test):
    """
    Get test list in format [test_id, test_summary,test_to_run]
    process the input list to get pytest cmd/test to run
    """
    test_name = test[2]
    cmd = test_name.replace('test_name:', '')
    test_id = test[0]
    test_html_report = str(test_id) + '.html'
    return cmd, test_id, test_html_report


def check_test_status(test_name):
    """
    Check whether test name is present in failed_tests.log file
    If its present, then that means given test is failed.
    """
    fail_file = 'failed_tests.log'
    test_status = 'PASS'
    test_name = test_name.replace("\\", "/")
    if os.path.exists(fail_file) :
        with open(fail_file) as fp :
            lines = fp.readlines()
            for line in lines :
                if test_name.strip() in line.strip() :
                    test_status = 'FAIL'
                    break
    return test_status


def main(args):
    if args.json_file:
        json_dict, cmd, run_using = runner.parse_json(args.json_file)
        cmd_line = runner.get_cmd_line(cmd, run_using, args.html_report, args.log_level)
        run_pytest_cmd(cmd_line)
    elif args.test_exe:
        jira_id, jira_pwd = get_jira_credential()
        jira_obj = JiraTask(jira_id, jira_pwd)
        test_list = jira_obj.get_test_list_from_te(args.test_exe)
        print('final list is {}'.format(test_list))
        for test in test_list:
            delete_status_files()
            cmd, test_id, test_html_report = process_test_list(test)
            cmd_line = runner.get_cmd_line(cmd.strip(), 'test_name', test_html_report, args.log_level)
            # Set initial test status in xray to executing
            jira_obj.update_test_jira_status(args.test_exe, test_id, 'Executing')
            run_pytest_cmd(cmd_line)
            test_status = check_test_status(cmd)
            jira_obj.update_test_jira_status(args.test_exe, test_id, test_status, '')  # TODO: ADD log path
    else :
        print("Json or test execution id is expected")


if __name__ == '__main__' :
    opts = parse_args()
    main(opts)
