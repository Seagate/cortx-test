import os
import subprocess
import argparse
import csv
from core import runner, kafka_consumer
from commons.utils.jira_utils import JiraTask
from commons.utils.db_locking_utils import LockingTask
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
    parser.add_argument("-pe", "--parallel_exe", type=str, default=False,
                        help="parallel_exe: True for parallel, False for sequential")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id")
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value")
    parser.add_argument("-p", "--prc_cnt", type=int, default=2,
                        help="number of parallel processes")
    parser.add_argument('-b', dest="bootstrap_servers", required=True,
                        help="Bootstrap broker(s) (host[:port])")
    parser.add_argument('-s', dest="schema_registry", required=True,
                        help="Schema Registry (http(s)://host[:port]")
    parser.add_argument('-t', dest="topic", default="example_serde_json",
                        help="Topic name")
    parser.add_argument('-g', dest="group", default="example_serde_json",
                        help="Consumer group")
    return parser.parse_args()


def run_pytest_cmd(args, parallel_exe, env=None, re_execution=False):
    """Form a pytest command for execution."""
    # tag = '-m ' + te_tag
    run_type = ''
    is_distributed = ''
    try:
        run_type = env['pytest_run']
    except (KeyError, AttributeError):
        is_distributed = "--distributed=" + str(False)

    if run_type == 'distributed':
        is_distributed = "--distributed=" + str(True)

    is_parallel = "--is_parallel=" + str(parallel_exe)
    log_level = "--log-cli-level=" + str(args.log_level)
    prc_cnt = str(args.prc_cnt) + "*popen"
    if re_execution:
        report_name = "--html=log/re_non_parallel_" + args.html_report
        cmd_line = ["pytest", "--continue-on-collection-errors", is_parallel, is_distributed,
                    log_level, report_name]
    else:
        if parallel_exe:
            report_name = "--html=log/parallel_" + args.html_report
            cmd_line = ["pytest", "--continue-on-collection-errors", is_parallel, is_distributed,
                        log_level, report_name, '-d', "--tx", prc_cnt]
        else :
            report_name = "--html=log/non_parallel_" + args.html_report
            cmd_line = ["pytest", "--continue-on-collection-errors", is_parallel, is_distributed,
                        log_level, report_name]
    if args.te_ticket:
        cmd_line = cmd_line + ["--te_tkt=" + str(args.te_ticket)]
    prc = subprocess.Popen(cmd_line, env=env)
    # prc = subprocess.Popen(cmd_line)
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


def get_tests_from_te(args, test_type='ALL'):
    '''
    Get tests from given test execution
    '''
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    test_list = jira_obj.get_test_ids_from_te(args.te_ticket, test_type)
    return test_list


def trigger_unexecuted_tests(args, test_list):
    '''
    Check if some tests are not executed in earlier TE
    Rerun those tests in seqential manner.
    '''
    te_test_list = get_tests_from_te(args, 'TODO')
    if len(te_test_list) != 0:
        unexecuted_test_list = []
        # check if there are any selected tests with todo status
        for test in test_list:
            if test in te_test_list:
                unexecuted_test_list.append(test)
        if len(unexecuted_test_list) != 0:
            # run those selected todo tests sequential
            args.parallel_exe = False
            with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') \
                    as test_file:
                write = csv.writer(test_file)
                for test in unexecuted_test_list:
                    write.writerow([test])
            _env = os.environ.copy()
            _env['pytest_run'] = 'distributed'
            run_pytest_cmd(args, args.parallel_exe, env=_env, re_execution=True)


def trigger_tests_from_kafka_msg(args, kafka_msg):
    '''
    Trigger pytest execution for received test list
    '''
    # writing the data into the file
    with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') as f:
        write = csv.writer(f)
        for test in kafka_msg.test_list:
            write.writerow([test])
    _env = os.environ.copy()
    _env['pytest_run'] = 'distributed'
    # First execute all tests with parallel tag which are mentioned in given tag.
    run_pytest_cmd(args, kafka_msg.parallel, env=_env)


def read_selected_tests_csv():
    '''
    Read tests which were selected for last execution
    '''
    tests = list()
    try:
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_SELECTED_TESTS)) \
                as test_file:
            reader = csv.reader(test_file)
            test_list = list(reader)
            for test_row in test_list:
                if not test_row:
                    continue
                tests.append(test_row[0])
        return tests
    except EnvironmentError:
        return tests


def trigger_tests_from_te(args):
    '''
    Get the tests from test execution
    Trigger those tests using pytest command
    '''
    test_list = get_tests_from_te(args)
    if len(test_list) == 0:
        assert False, "Please check TE provided, tests are missing"
    # writing the data into the file
    with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') \
            as test_file:
        write = csv.writer(test_file)
        for test in test_list:
            write.writerow([test])
    _env = os.environ.copy()
    # First execute all tests with parallel tag which are mentioned in given tag.
    run_pytest_cmd(args, True, env=_env)

    # Sequentially executes test which didn't execute during parallel execution
    test_list = read_selected_tests_csv()
    trigger_unexecuted_tests(args, test_list)

    # Execute all tests having no parallel tag and which are mentioned in given tag.
    run_pytest_cmd(args, False, env=_env)


def get_available_target(kafka_msg):
    '''
    Check available target from target list
    Get lock on target if available
    '''
    lock_task = LockingTask()
    acquired_target = ""
    while acquired_target == "":
        target = lock_task.check_available_target(kafka_msg.target_list)
        if target != "":
            print("target found {}".format(target))
            lock_success = lock_task.take_target_lock(target)
            if lock_success:
                acquired_target = target
                print("lock acquired {}".format(target))
    return acquired_target


def check_kafka_msg_trigger_test(args):
    '''
    Get message from kafka consumer
    Trigger tests specified in kafka message
    '''
    consumer = kafka_consumer.get_consumer(args)
    received_stop_signal = False
    lock_task = LockingTask()
    while not received_stop_signal:
        try:
            # SIGINT can't be handled when polling, limit timeout to 60 seconds.
            msg = consumer.poll(60)
            if msg is None:
                continue
            kafka_msg = msg.value()
            if kafka_msg is None:
                continue
            if kafka_msg.te_id == "STOP":
                received_stop_signal = True
            else:
                execution_done = False
                while not execution_done:
                    acquired_target = get_available_target(kafka_msg)
                    # execute te id on acquired target
                    # release lock on acquired target
                    args.te_ticket = kafka_msg.te_tickets
                    args.parallel_exe = kafka_msg.parallel
                    trigger_tests_from_kafka_msg(args, kafka_msg)
                    # rerun unexecuted tests in case of parallel execution
                    if kafka_msg.parallel:
                        trigger_unexecuted_tests(args, kafka_msg.test_list)
                    # Release lock on acquired target.
                    lock_task.release_target_lock(acquired_target, acquired_target)
                    execution_done = True
        except KeyboardInterrupt:
            break
    consumer.close()


def main(args):
    runner.cleanup()
    if args.json_file:
        json_dict, cmd, run_using = runner.parse_json(args.json_file)
        cmd_line = runner.get_cmd_line(cmd, run_using, args.html_report, args.log_level)
        prc = subprocess.Popen(cmd_line)
        out, err = prc.communicate()
    elif args.te_ticket:
        trigger_tests_from_te(args)
    else:
        check_kafka_msg_trigger_test(args)


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
