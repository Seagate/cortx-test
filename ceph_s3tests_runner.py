#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Test runner for ceph/s3-tests nosetests based tests"""
import argparse
import datetime
import logging
import os
import subprocess
from core import runner
from commons import params
from commons.utils import system_utils
from commons.utils.jira_utils import JiraTask


LOGGER = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--jira_update", type=bool, default=False,
                        help="Update Jira. Can be False in case Jira is down")
    parser.add_argument("-te", "--te_ticket", type=str,
                        help="Jira Xray Test Execution ID")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="Jira Xray Test Plan ID")
    parser.add_argument("-tt", "--test_type", type=str,
                        help="Type of tests to execute")
    return parser.parse_args()


def get_tests_from_te(jira_obj, args, test_type=None):
    """Get tests from given test execution"""
    if test_type is None:
        test_type = ['ALL']
    test_list, _ = jira_obj.get_test_ids_from_te(str(args.te_ticket), test_type)
    if len(test_list) == 0:
        raise EnvironmentError("Please check TE provided, tests or tag is missing")
    return test_list


def collect_test_info(jira_obj, test):
    """Collect Test information"""
    test_details = jira_obj.get_issue_details(test)
    test_name = test_details.fields.summary
    test_to_run = test_details.fields.customfield_20984
    test_label = ''
    if test_details.fields.labels:
        test_label = test_details.fields.labels[0]
    return test_name, test_label, test_to_run


def run_nose_cmd(test_to_run=None, log_file='nosetest.log'):
    """Run nosetests command for execution"""
    cmd_line = f"{params.VIRTUALENV_DIR}/bin/nosetests {test_to_run}"
    log = open(log_file, 'a')
    LOGGER.debug('Running nosetests command %s', cmd_line)
    prc = subprocess.Popen(cmd_line, shell=True, stdout=log, stderr=log, cwd=params.S3TESTS_DIR)
    prc.communicate()
    return "PASS" if prc.returncode == 0 else "FAIL"


def trigger_tests_from_te(args):
    """
    Get the tests from test execution
    Trigger those tests using nosetests command
    """
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    test_list = get_tests_from_te(jira_obj, args, args.test_type)

    timestamp = datetime.datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
    reports = "reports_" + str(args.test_plan) + "_" + args.te_ticket + "_" + str(timestamp)
    reports_dir = os.path.join(params.S3TESTS_DIR, params.REPORTS_DIR, reports)
    if not system_utils.path_exists(reports_dir):
        system_utils.make_dirs(reports_dir)

    tp_details = jira_obj.get_issue_details(args.test_plan)
    tp_build = tp_details.fields.customfield_22980
    build_number = tp_build[0] if tp_build else 0

    os.environ[params.S3TESTS_CONF_ENV] = params.S3TESTS_CONF_FILE

    for test in test_list:
        test_id = str(test[0])
        LOGGER.debug("TEST ID : ", test_id)
        test_name, test_label, test_to_run = collect_test_info(jira_obj, test)

        log_file_name = f"{test_id}_{test_to_run}.log"
        log_file = os.path.join(reports_dir, log_file_name)

        # Update Jira with test status and log file
        test_status = "EXECUTING"
        jira_obj.update_test_jira_status(args.te_ticket, test_id, test_status)

        test_status = run_nose_cmd(test_to_run, log_file=log_file)

        remote_path = os.path.join(params.NFS_BASE_DIR, build_number, args.test_plan,
                                   args.te_ticket, test_id)

        # Upload nosetests log file to NFS share
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=log_file)
        if resp[0]:
            LOGGER.debug("Log file is uploaded at location : %s", resp[1])
        else:
            LOGGER.debug("Failed to upload log file at location : %s", resp[1])

        # Update Jira for status and log file
        jira_obj.update_test_jira_status(args.te_ticket, test_id, test_status, remote_path)


def main(args):
    trigger_tests_from_te(args)


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
