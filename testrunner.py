import os
import subprocess
import argparse
import csv
from core import runner
from commons.utils.jira_utils import JiraTask
from config import params


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json_file", type=str,
                        help="json file name")
    parser.add_argument("-r", "--html_report", type=str, default='report.html',
                        help="html report name")
    parser.add_argument("-d", "--db_update", type=str, default='n',
                        help="db update required: y/n")
    parser.add_argument("-te", "--te_ticket", type=str,
                        help="jira xray test execution id")
    parser.add_argument("-tp", "--test_plan", type=str, default='None',
                        help="jira xray test plan id")
    parser.add_argument("-b", "--build", type=str, default='000',
                        help="Build number")
    parser.add_argument("-t", "--build_type", type=str, default='Release',
                        help="Build type (Release/Dev)")
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value")
    parser.add_argument("-p", "--prc_cnt", type=int, default=2,
                        help="number of parallel processes")
    parser.add_argument("-f", "--force_serial_run", type=str_to_bool,
                        default=False, nargs='?', const=True,
                        help="Force sequential run if you face problems with parallel run")
    return parser.parse_args()


def str_to_bool(val):
    if isinstance(val, bool):
        return val
    if val.lower() in ('yes', 'true', 'y', '1'):
        return True
    elif val.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def run_pytest_cmd(args, te_tag, parallel_red, env=None):
    """Form a pytest command for execution."""
    build, build_type = args.build, args.build_type
    tag = '-m ' + te_tag
    is_parallel = "--is_parallel=" + parallel_red
    log_level = "--log-cli-level=" + str(args.log_level)
    force_serial_run = "--force_serial_run="
    serial_run = "True" if args.force_serial_run else "False"
    force_serial_run = force_serial_run + serial_run
    prc_cnt = str(args.prc_cnt) + "*popen"
    if parallel_red == "true" and not args.force_sequential_run:
        report_name = "--html=log/parallel_" + args.html_report
        cmd_line = ["pytest", is_parallel, log_level, report_name,
                    '-d', "--tx", prc_cnt, force_serial_run]
    else:
        report_name = "--html=log/non_parallel_" + args.html_report
        cmd_line = ["pytest", is_parallel, log_level, report_name,
                    force_serial_run]
    if args.te_ticket:
        cmd_line = cmd_line + ["--te_tkt=" + str(args.te_ticket)]

    cmd_line = cmd_line + ['--build=' + build, '--build_type=' + build_type,
                           '--tp_ticket=' + args.test_plan]
    import pdb
    pdb.set_trace()
    prc = subprocess.Popen(cmd_line, env=env)
    prc.communicate()


def delete_status_files():
    file_list = ['failed_tests.log', 'passed_tests.log', 'other_test_calls.log']
    for file in file_list:
        if os.path.exists(file):
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
    if os.path.exists(fail_file):
        with open(fail_file) as fp:
            lines = fp.readlines()
            for line in lines:
                if test_name.strip() in line.strip():
                    test_status = 'FAIL'
                    break
    return test_status


def main(args):
    """Main Entry function using argument parser to parse options and forming pyttest command.
    It renames up the latest folder and parses TE ticket to create detailed test details csv.
    """
    runner.cleanup()
    if args.json_file:
        json_dict, cmd, run_using = runner.parse_json(args.json_file)
        cmd_line = runner.get_cmd_line(cmd, run_using, args.html_report, args.log_level)
        prc = subprocess.Popen(cmd_line)
        out, err = prc.communicate()
    elif args.te_ticket:
        jira_id, jira_pwd = runner.get_jira_credential()
        jira_obj = JiraTask(jira_id, jira_pwd)
        test_list, te_tag = jira_obj.get_test_ids_from_te(args.te_ticket)
        if len(test_list) == 0 or te_tag == "":
            assert "Please check TE provided, tests or tag is missing"
        # writing the data into the file
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') as f:
            write = csv.writer(f)
            for test in test_list:
                write.writerow([test])
        _env = os.environ.copy()
        if not args.force_serial_run:
            # First execute all tests with parallel tag which are mentioned in given tag.
            run_pytest_cmd(args, te_tag, 'true', env=_env)
            # Execute all tests having no parallel tag and which are mentioned in given tag.
            run_pytest_cmd(args, te_tag, 'false', env=_env)
        else:
            # Sequentially execute all tests with parallel tag which are mentioned in given tag.
            run_pytest_cmd(args, te_tag, 'false', env=_env)
            # Execute all other tests not having parallel tag with given component tag.
            run_pytest_cmd(args, te_tag, 'false', env=_env)
    else:
        print("Json or test execution id is expected")


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
