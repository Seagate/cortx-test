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

"""Test Runner for robot test-cases"""
import os
import subprocess
import argparse
import logging
import datetime
import glob
import getpass
from typing import Tuple
from typing import Optional
from commons import params
from commons.utils.jira_utils import JiraTask
from commons.utils import system_utils

LOGGER = logging.getLogger(__name__)

def parse_args():
    """Parse arguments function
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-du", "--db_update", type=str, default='no',
                        help="db update required: yes/no")
    parser.add_argument("-te", "--te_ticket", type=str,
                        help="jira xray test execution id")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id")
    parser.add_argument("-b", "--build_number", type=str,
                        help="build number")
    parser.add_argument("-u", "--csm_url", type=str,
                        help="CSM URL")
    parser.add_argument("-bs", "--browser", type=str,
                        help="browser")
    parser.add_argument("-cu", "--csm_user", type=str,
                        help="username")
    parser.add_argument("-cp", "--csm_pass", type=str,
                        help="password")
    parser.add_argument("-hl", "--headless", type=str,
                        help="headless")
    parser.add_argument("-tt", "--test_type", type=str,
                        help="test_type")
    return parser.parse_args()

def get_jira_credential() -> Tuple[str, Optional[str]]:
    """
    Adapter function to get Jira Credentials.
    :return: Credentials Tuple
    """
    try:
        jira_id = os.environ['JIRA_ID']
        jira_pd = os.environ['JIRA_PASSWORD']
    except KeyError:
        print("JIRA credentials not found in environment")
        jira_id = input("JIRA username: ")
        jira_pd = getpass.getpass("JIRA password: ")
        os.environ['JIRA_ID'] = jira_id
        os.environ['JIRA_PASSWORD'] = jira_pd
    return jira_id, jira_pd

def get_db_credential() -> Tuple[str, Optional[str]]:
    """ Function to get DB credentials from env or common config or secret.json."""
    db_user = None
    db_pwd = None
    try:
        db_user = os.environ['DB_USER']
        db_pwd = os.environ['DB_PASSWORD']
    except KeyError:
        print("DB credentials not found in environment")
        db_user = input("DB username: ")
        db_pwd = getpass.getpass("DB password: ")
        os.environ['DB_USER'] = db_user
        os.environ['DB_PASSWORD'] = db_pwd
    return db_user, db_pwd

def get_tests_from_te(jira_obj, args, test_type='ALL'):
    """
    Get tests from given test execution
    :return: Test List
    """
    test_list, tag = jira_obj.get_test_ids_from_te(str(args.te_ticket), test_type)
    if len(test_list) == 0:
        raise EnvironmentError("Please check TE provided, tests or tag is missing")
    return test_list


def collect_te_info(jira_obj, te):
    """
    Collect Test Execution
    :return: Test Label, Test Component
    """
    te_details = jira_obj.get_issue_details(te)
    te_label = ''
    te_comp = ''
    if te_details.fields.labels:  # Optional I.e. Isolated, NearFull, By default: Normal
        te_label = te_details.fields.labels[0]
    if te_details.fields.components:
        te_comp = te_details.fields.components[0].name
    return te_label, te_comp


def collect_tp_info(jira_obj, tp):
    """
    Collect Test Plan information
    :return: build, build_type, test_plan_label
    """
    tp_details = jira_obj.get_issue_details(tp)
    build = ''
    build_type = "stable"
    test_plan_label = "regular"
    if tp_details.fields.environment:
        branch_build = tp_details.fields.environment
        if "_" in branch_build:
            b_str = branch_build.split("_")
            build = b_str[-1]
            build_type = "_".join(b_str[:-1])
        else:
            build = branch_build

    if tp_details.fields.labels:  # Optional I.e. Isolated, NearFull, By default: Normal
        test_plan_label = tp_details.fields.labels[0]

    return build, build_type, test_plan_label


def collect_test_info(jira_obj, test):
    """
    Collect Test information
    :return: test_name, test_label
    """

    test_details = jira_obj.get_issue_details(test)
    test_name = test_details.fields.summary
    test_label = ''
    if test_details.fields.labels:
        test_label = test_details.fields.labels[0]
    return test_name, test_label

def run_robot_cmd(args,te_tag=None, logFile='main.log'):
    """Form a robot command for execution."""

    cwd = os.getcwd()
    headless = " -v headless:" + str(args.headless)
    url = " -v url:"+ str(args.csm_url)
    browser = " -v browser:" + str(args.browser)
    username = " -v username:" + str(args.csm_user)
    password = " -v password:" + str(args.csm_pass)
    tag = ' -i ' + te_tag
    directory = " . "
    resource= " -v RESOURCES:" + str(cwd) + "/robot_gui/"
    timestamp = datetime.datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
    reports = "reports_" + str(args.test_plan) + "_" + te_tag + "_" + str(timestamp)
    cmd_line = ""
    cmd_line = "cd robot_gui; robot --timestampoutputs -d "+ reports+url+resource+browser+ \
               username+headless+password+tag+directory+";cd .."
    log = open(logFile, 'a')
    print(cmd_line)
    prc = subprocess.Popen(cmd_line,shell=True,stdout=log,stderr=log)
    prc.communicate()

    report_path =  str(cwd) + "/robot_gui/" + reports

    return report_path

def getTestStatusAndParseLog(logFile = 'main.log'):
    """
    Parse main.log file to get
    a) TestStatus: Pass/Fail
    """

    TestStatus = 'PASS'

    with open(logFile, 'r') as file:

        for line in file:
            # For each line, check if line contains the string
            if 'FAIL' in line:
                TestStatus = 'FAIL'

    return TestStatus

def trigger_tests_from_te(args):
    """
    Get the tests from test execution
    Trigger those tests using robot command
    """
    jira_id, jira_pwd = get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    test_list = get_tests_from_te(jira_obj, args, args.test_type)

    if os.path.exists("main.log"):
        os.remove("main.log")

    logFile = 'main.log'
    test_info = dict()

    if args.db_update == 'yes':
        build_number, build_type, test_plan_label = collect_tp_info(jira_obj, args.test_plan)
        te_label, te_comp = collect_te_info(jira_obj, args.te_ticket)
        test_info['build'] = build_number
        test_info['build_type'] = build_type
        test_info['tp_label'] = test_plan_label
        test_info['te_label'] = te_label
        test_info['te_tkt'] = args.te_ticket
        test_info['tp_ticket'] = args.test_plan
        test_info['te_component'] = te_comp
    else:
        build_number = args.build_number

    for test in test_list:
        test_id = str(test[0])
        print(" TEST ID : ", test_id)
        if args.db_update == 'yes':
            test_name, test_label = collect_test_info(jira_obj, test)

        # execute test using test id tag
        start_time = datetime.datetime.now()
        # update jira for status and log file
        test_status = 'EXECUTING'
        jira_obj.update_test_jira_status(args.te_ticket, test_id, test_status)
        #Clear main.log from previous Test.
        if os.path.exists("main.log"):
            os.remove("main.log")

        log_dir = run_robot_cmd(args, test_id, logFile='main.log')
        end_time = datetime.datetime.now()
        test_status = ''

        #parse log
        test_status = getTestStatusAndParseLog(logFile='main.log')
 
        duration = (end_time - start_time)

        # move all log files to nfs share
        log_dir =glob.glob(log_dir + "/*")
        remote_path = os.path.join(params.NFS_BASE_DIR, build_number, args.test_plan,
                                   args.te_ticket, test_id)
        for log_file in log_dir:
            resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                       mnt_dir=params.MOUNT_DIR,
                                                       remote_path=remote_path,
                                                       local_path=log_file)
            if resp[0]:
                print("Log file is uploaded at location : %s", resp[1])
            else:
                print("Failed to upload log file at location : %s", resp[1])
        #upload main.log file to NFS share
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=logFile)
        if resp[0]:
            print("Log file is uploaded at location : %s", resp[1])
        else:
            print("Failed to upload log file at location : %s", resp[1])
        # update jira for status and log file
        jira_obj.update_test_jira_status(args.te_ticket, test_id, test_status, remote_path)

        # update db entry
        if args.db_update == 'yes':
            test_info['log_path'] = remote_path
            test_info['logs_collected'] = 'yes'
            test_info['start_time'] = start_time
            test_info['duration'] = duration
            test_info['test_name'] = test_name
            test_info['test_id'] = test
            test_info['labels'] = test_label
            test_info['final_result'] = test_status

            db_user, db_pass = get_db_credential()
            payload = create_report_payload(test_info, db_user, db_pass)
            REPORT_CLIENT.create_db_entry(**payload)


def main(args):
    """Main Entry function using argument parser to parse options and forming pyttest command.
    It renames up the latest folder and parses TE ticket to create detailed test details csv.
    """
    trigger_tests_from_te(args)


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
