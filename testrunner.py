import os
import subprocess
import argparse
import csv
import json
from core import runner
from core import kafka_consumer
from core.locking_server import LockingServer
from commons.utils.jira_utils import JiraTask
from commons import configmanager
from commons.utils import config_utils
from commons import params


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
    parser.add_argument("-b", "--build", type=str, default='',
                        help="Build number")
    parser.add_argument("-t", "--build_type", type=str, default='',
                        help="Build type (Release/Dev)")
    parser.add_argument("-tg", "--target", type=str,
                        default='', help="Target setup details")
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value")
    parser.add_argument("-p", "--prc_cnt", type=int, default=2,
                        help="number of parallel processes")
    parser.add_argument("-f", "--force_serial_run", type=str_to_bool,
                        default=False, nargs='?', const=True,
                        help="Force sequential run if you face problems with parallel run")
    return parser.parse_args()


def str_to_bool(val):
    """To convert a string value to bool."""
    if isinstance(val, bool):
        return val
    if val.lower() in ('yes', 'true', 'y', '1'):
        return True
    elif val.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def run_pytest_cmd(args, te_tag=None, parallel_exe=False, env=None, re_execution=False):
    """Form a pytest command for execution."""
    env['TARGET'] = args.target
    build, build_type = args.build, args.build_type
    tag = '-m ' + te_tag
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
    force_serial_run = "--force_serial_run="
    serial_run = "True" if args.force_serial_run else "False"
    force_serial_run = force_serial_run + serial_run
    prc_cnt = str(args.prc_cnt) + "*popen"
    if re_execution:
        report_name = "--html=log/re_non_parallel_" + args.html_report
        cmd_line = ["pytest", "--continue-on-collection-errors", is_parallel, is_distributed,
                    log_level, report_name]
    else:
        if parallel_exe and not args.force_serial_run:
            report_name = "--html=log/parallel_" + args.html_report
            cmd_line = ["pytest", is_parallel, is_distributed,
                        log_level, report_name, '-d', "--tx",
                        prc_cnt, force_serial_run]
        elif parallel_exe and args.force_serial_run:
            report_name = "--html=log/parallel_" + args.html_report
            cmd_line = ["pytest", is_parallel, is_distributed,
                        log_level, report_name, force_serial_run]
        else:
            report_name = "--html=log/non_parallel_" + args.html_report
            cmd_line = ["pytest", is_parallel, is_distributed,
                        log_level, report_name, force_serial_run]

    if args.te_ticket:
        cmd_line = cmd_line + ["--te_tkt=" + str(args.te_ticket)]

    if args.target:
        cmd_line = cmd_line + ["--target=" + args.target]

    if te_tag:
        cmd_line = cmd_line + [tag]
    read_metadata = "--readmetadata=" + str(True)
    cmd_line = cmd_line + [read_metadata]
    cmd_line = cmd_line + ['--build=' + build, '--build_type=' + build_type,
                           '--tp_ticket=' + args.test_plan]
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


def get_ticket_meta_from_test_list():
    """Creates a json file which can be used by cache for data that is static to test.
    This file saves test metadata once in test runner cycle.
    :argument file_path  Fix codacy issue.
    """
    pass


def get_tests_from_te(jira_obj, args, test_type='ALL'):
    """
    Get tests from given test execution
    """
    test_list, tag = jira_obj.get_test_ids_from_te(args.te_ticket, test_type)
    if len(test_list) == 0 or tag == "":
        raise EnvironmentError("Please check TE provided, tests or tag is missing")
    return test_list, tag


def trigger_unexecuted_tests(args, test_list):
    """
    Check if some tests are not executed in earlier TE
    Rerun those tests in seqential manner.
    """
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    te_test_list, tag = get_tests_from_te(jira_obj, args, 'TODO')
    if len(te_test_list) != 0:
        # check if there are any selected tests with todo status
        unexecuted_test_list = [test for test in test_list if test in te_test_list]
        if len(unexecuted_test_list) != 0:
            # run those selected todo tests sequential
            args.parallel_exe = False
            with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME,
                                   params.JIRA_DIST_TEST_LIST), 'w') as test_file:
                write = csv.writer(test_file)
                for test in unexecuted_test_list:
                    write.writerow([test])
            _env = os.environ.copy()
            _env['pytest_run'] = 'distributed'
            run_pytest_cmd(args, te_tag=None, parallel_exe=args.parallel_exe,
                           env=_env, re_execution=True)


def create_test_meta_data_file(args, test_list):
    """
    Create test meta data file
    """
    tp_meta = dict()  # test plan meta
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    # Create test meta file for reporting TR.
    tp_meta_file = os.path.join(os.getcwd(),
                                params.LOG_DIR_NAME,
                                params.JIRA_TEST_META_JSON)
    with open(tp_meta_file, 'w') as t_meta:

        test_meta = list()
        tp_resp = jira_obj.get_issue_details(args.test_plan)  # test plan id
        tp_meta['test_plan_label'] = tp_resp.fields.labels
        tp_meta['environment'] = tp_resp.fields.environment
        te_resp = jira_obj.get_issue_details(args.te_ticket)  # test execution id
        if te_resp.fields.components:
            te_components = te_resp.fields.components[0].name
        tp_meta['te_meta'] = dict(te_id=args.te_ticket,
                                  te_label=te_resp.fields.labels,
                                  te_components=te_components)
        # test_name, test_id, test_id_labels, test_team, test_type
        for test in test_list:
            item = dict()
            item['test_id'] = test
            resp = jira_obj.get_issue_details(test)
            item['test_name'] = resp.fields.summary
            item['labels'] = resp.fields.labels
            if resp.fields.components:
                component = resp.fields.components[0].name  # First items is of interest
            else:
                component = list()
            item['component'] = component
            test_meta.append(item)
        tp_meta['test_meta'] = test_meta
        json.dump(tp_meta, t_meta, ensure_ascii=False)
    return tp_meta


def trigger_tests_from_kafka_msg(args, kafka_msg):
    """
    Trigger pytest execution for received test list
    """
    # writing the data into the file
    with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME,
                           params.JIRA_DIST_TEST_LIST), 'w') as f:
        write = csv.writer(f)
        for test in kafka_msg.test_list:
            write.writerow([test])

    create_test_meta_data_file(args, kafka_msg.test_list)  # why this data is needed in kafka exec
    _env = os.environ.copy()
    _env['pytest_run'] = 'distributed'

    # First execute all tests with parallel tag which are mentioned in given tag.
    run_pytest_cmd(args, te_tag=None, parallel_exe=kafka_msg.parallel, env=_env)


def read_selected_tests_csv():
    """
    Read tests which were selected for last execution
    """
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
    """
    Get the tests from test execution
    Trigger those tests using pytest command
    """
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    # test_list, te_tag = jira_obj.get_test_ids_from_te(args.te_ticket)
    # if len(test_list) == 0 or te_tag == "":
    #     assert False, "Please check TE provided, tests or tag is missing"
    test_list, te_tag = get_tests_from_te(jira_obj, args)
    # writing the data into the file
    with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') \
            as test_file:
        write = csv.writer(test_file)
        for test in test_list:
            write.writerow([test])

    tp_metadata = create_test_meta_data_file(args, test_list)
    if not args.build and not args.build_type:
        if 'environment' in tp_metadata and tp_metadata.get('environment'):
            test_env = tp_metadata.get('environment')
            try:
                _build_type, _build = test_env.split('_')
            except ValueError:
                raise EnvironmentError('Test plan env needs to be in format <build_type>_<build#>')
            args.build, args.build_type = _build, _build_type

    _env = os.environ.copy()
    if not args.force_serial_run:
        # First execute all tests with parallel tag which are mentioned in given tag.
        run_pytest_cmd(args, te_tag, True, env=_env)

        # Sequentially executes test which didn't execute during parallel execution
        test_list = read_selected_tests_csv()
        trigger_unexecuted_tests(args, test_list)

        # Execute all tests having no parallel tag and which are mentioned in given tag.
        run_pytest_cmd(args, te_tag, False, env=_env)
    else:
        # Sequentially execute all tests with parallel tag which are mentioned in given tag.
        run_pytest_cmd(args, te_tag, True, env=_env)
        # Execute all other tests not having parallel tag with given component tag.
        run_pytest_cmd(args, te_tag, False, env=_env)


def get_available_target(kafka_msg):
    """
    Check available target from target list
    Get lock on target if available
    """
    lock_task = LockingServer()
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
    """
    Get message from kafka consumer
    Trigger tests specified in kafka message
    """
    consumer = kafka_consumer.get_consumer()
    print(consumer)
    received_stop_signal = False
    lock_task = LockingServer()
    while not received_stop_signal:
        try:
            # SIGINT can't be handled when polling, limit timeout to 60 seconds.
            msg = consumer.poll(60)
            if msg is None:
                continue
            kafka_msg = msg.value()
            print(kafka_msg)
            if kafka_msg is None:
                continue
            if kafka_msg.te_ticket == "STOP":
                received_stop_signal = True
            else:
                execution_done = False
                while not execution_done:
                    # acquired_target = get_available_target(kafka_msg)
                    # execute te id on acquired target
                    # release lock on acquired target
                    args.te_ticket = kafka_msg.te_ticket
                    args.parallel_exe = kafka_msg.parallel
                    args.build = kafka_msg.build
                    args.build_type = kafka_msg.build_type
                    args.test_plan = kafka_msg.test_plan
                    trigger_tests_from_kafka_msg(args, kafka_msg)
                    # rerun unexecuted tests in case of parallel execution
                    if kafka_msg.parallel:
                        trigger_unexecuted_tests(args, kafka_msg.test_list)
                    # Release lock on acquired target.
                    # lock_task.release_target_lock(acquired_target, acquired_target)
                    execution_done = True
        except KeyboardInterrupt:
            break
    consumer.close()


def get_setup_details():
    if not os.path.exists(params.LOG_DIR_NAME):
        os.mkdir(params.LOG_DIR_NAME)
    if os.path.exists(params.SETUPS_FPATH):
        os.remove(params.SETUPS_FPATH)
    setups = configmanager.get_config_db(setup_query={})
    config_utils.create_content_json(params.SETUPS_FPATH, setups)


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
        trigger_tests_from_te(args)
    else:
        check_kafka_msg_trigger_test(args)


if __name__ == '__main__':
    get_setup_details()
    opts = parse_args()
    main(opts)
