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
"""Test runner for ceph/s3-tests nosetests based tests."""
import argparse
import datetime
import logging
import os
import shutil
import subprocess  # nosec
from configparser import ConfigParser
from http import HTTPStatus

from commons import params
from commons.report_client import ReportClient
from commons.utils import jira_utils, system_utils
from config import CMN_CFG
from core.client_config import ClientConfig
from core.runner import get_db_credential, get_jira_credential
from libs.csm.csm_interface import csm_api_factory
from testrunner import str_to_bool

LOGGER = logging.getLogger(__name__)

CONFIG_FILE = os.path.join("s3-tests", "s3tests.conf")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--jira_update", type=bool, default=True, help="Update Jira")
    parser.add_argument("-te", "--te_ticket", type=str, help="Jira Xray Test Execution ID")
    parser.add_argument("-tp", "--test_plan", type=str, help="Jira Xray Test Plan ID")
    parser.add_argument("-tt", "--test_type", nargs='+', type=str, default=['ALL'],
                        help="Space separated test types")
    parser.add_argument("-ll", "--log_level", type=int, default=20,
                        help="log level value as defined below" +
                             "CRITICAL = 50" +
                             "FATAL = CRITICAL" +
                             "ERROR = 40" +
                             "WARNING = 30 WARN = WARNING" +
                             "INFO = 20 DEBUG = 10"
                        )
    parser.add_argument("-b", "--build", type=str, default='', help="Build number")
    parser.add_argument("-t", "--build_type", type=str, default='', help="Build type (Release/Dev)")
    parser.add_argument("-c", "--validate_certs", type=str_to_bool, default=True,
                        help="Validate HTTPS/SSL certificate to S3 endpoint.")
    parser.add_argument("-s", "--use_ssl", type=str_to_bool, default=True,
                        help="Use HTTPS/SSL connection for S3 endpoint.")
    parser.add_argument("-d", "--db_update", type=str_to_bool, default=True,
                        help="Update Reports DB.")
    parser.add_argument("--target", type=str, help="Target setup details")
    return parser.parse_args()


def get_tests_from_te(jira_obj, args, test_type=None):
    """Get tests from given test execution."""
    LOGGER.info("Fetching test list from TE : %s", args.te_ticket)
    if test_type is None:
        test_type = ['ALL']
    test_list, _ = jira_obj.get_test_ids_from_te(str(args.te_ticket), test_type)
    if len(test_list) == 0:
        raise EnvironmentError("Could not find tests matching given test type.")
    return test_list


def collect_test_info(jira_obj, test):
    """Collect Test information."""
    test_details = jira_obj.get_issue_details(test)
    test_to_run = test_details.fields.customfield_20984
    if not test_to_run:
        raise EnvironmentError(f"Definition field for {test} JIRA is empty.")
    return test_to_run


def setup_configurations(args):
    """Setup host:port and security protocol"""
    setup_details = ClientConfig(get_db_credential()).get_setup_details(args.target)
    LOGGER.info("Copying default config file")
    shutil.copyfile("scripts/ceph_s3_tests/cortx_rgw_template.conf", CONFIG_FILE)
    config = ConfigParser()
    config.read(CONFIG_FILE)
    LOGGER.info({section: dict(config[section]) for section in config.sections()})
    config.set('DEFAULT', 'host', str(setup_details['lb'].split(":")[0]))
    config.set('DEFAULT', 'port', str(setup_details['lb'].split(":")[1]))
    config.set('DEFAULT', 'is_secure', str(args.use_ssl))
    config.set('DEFAULT', 'ssl_verify', str(args.validate_certs))
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)


def check_or_create_accounts():
    """Create IAM accounts required for ceph test execution if accounts does not exit already"""
    iam_users_sections = ["s3 main", "s3 alt", "s3 tenant", "iam"]
    csm_obj = csm_api_factory("rest")

    resp = csm_obj.list_iam_users_rgw()
    if resp.status_code != HTTPStatus.OK:
        raise EnvironmentError(f"Unable to list IAM users. Response = {resp}")
    users_list = resp.json()["users"]

    config = ConfigParser()
    config.read(CONFIG_FILE)
    for section in config.sections():
        if section in iam_users_sections:
            userid = config.get(section, "user_id")
            payload = {"access_key": config.get(section, "access_key"),
                       "secret_key": config.get(section, "secret_key")}
            if section == "iam":
                payload.update({"user_caps": "user-policy=*"})
            if userid not in users_list:
                LOGGER.info("Creating user %s", userid)
                payload.update({"uid": userid,
                                "display_name": config.get(section, "display_name"),
                                "email": config.get(section, "email")})
                resp = csm_obj.create_iam_user_rgw(payload=payload)
                if resp.status_code != HTTPStatus.CREATED:
                    raise EnvironmentError(f"Unable to create {userid}. Response = {resp}")
            else:
                LOGGER.info("User account %s already exist", userid)


def get_test_data(jira_obj, test_ticket):
    """Get TEST data from TEST JIRA ticket"""
    test = jira_obj.get_issue_details(test_ticket)
    test_definition = test.fields.customfield_20984
    summary = test.fields.summary
    components = test.fields.components
    test_team = components[0].name if components and isinstance(components, list) else "CortxQA"
    feature = test.fields.customfield_21087.value if test.fields.customfield_21087 else "None"
    dr_id = test.fields.customfield_22882 if test.fields.customfield_22882 else ['DR-0']
    feature_id = test.fields.customfield_22881 if test.fields.customfield_22881 else ['F-0']
    labels = test.fields.labels if test.fields.labels else []
    execution_type = labels[0] if labels and isinstance(labels, list) else 'R2Automated'
    data = {"test_team": test_team, "feature": feature, "dr_id": dr_id, "feature_id": feature_id,
            "labels": labels, "execution_type": execution_type, "summary": summary,
            "test_definition": test_definition}
    return data


def get_test_plan_data(jira_obj, test_plan):
    """Get Test Plan data from Test Plan JIRA ticket"""
    test_plan = jira_obj.get_issue_details(test_plan)
    tp_label = test_plan.fields.labels[0] if test_plan.fields.labels else 'default'
    platform_type = test_plan.fields.customfield_22982[
        0] if test_plan.fields.customfield_22982 else 'VM_HW'
    server_type = test_plan.fields.customfield_22983[
        0] if test_plan.fields.customfield_22983 else 'VM'
    enclosure_type = test_plan.fields.customfield_22984[
        0] if test_plan.fields.customfield_22984 else '5U84'
    data = {"tp_label": tp_label, "platform_type": platform_type, "server_type": server_type,
            "enclosure_type": enclosure_type}
    return data


def create_db_payload(args, db_data, test):
    """Create DB Payload"""
    # Get data from JIRA
    jira_id, jira_pwd = get_jira_credential()
    jira_obj = jira_utils.JiraTask(jira_id, jira_pwd)
    test_execution = jira_obj.get_issue_details(args.te_ticket)
    test_plan = get_test_plan_data(jira_obj, args.test_plan)
    te_label = test_execution.fields.labels[0] if test_execution.fields.labels else "None"
    health_chk_res = 'NA'
    if db_data["test_status"] == 'FAIL':
        health_chk_res = 'TODO'
    nodes = len(CMN_CFG['nodes'])
    nodes_hostnames = [n['hostname'] for n in CMN_CFG['nodes']]
    # Create DB payload
    payload = dict(os=system_utils.get_os_version(),
                   build=args.build,
                   build_type=args.build_type,
                   client_hostname=system_utils.get_host_name(),
                   execution_type=test["execution_type"],
                   health_chk_res=health_chk_res,
                   are_logs_collected=True,
                   log_path=db_data["log_path"],
                   testPlanLabel=test_plan["tp_label"],  # get from TP
                   testExecutionLabel=te_label,  # get from TE
                   nodes=nodes,
                   nodes_hostnames=nodes_hostnames,
                   test_exec_id=args.te_ticket,
                   test_exec_time=db_data["execution_time"],
                   test_name=test["summary"],
                   test_id=db_data["test_id"],
                   test_id_labels=test["labels"],
                   test_plan_id=args.test_plan,
                   test_result=db_data["test_status"],
                   start_time=db_data["start_time"].strftime('%Y-%m-%d %H:%M:%S'),
                   test_team=test["test_team"],
                   test_type='nosetest',
                   latest=True,
                   failure_string='',
                   feature=test["feature"],
                   dr_id=test["dr_id"],
                   feature_id=test["feature_id"],
                   platform_type=test_plan["platform_type"],
                   server_type=test_plan["server_type"],
                   enclosure_type=test_plan["enclosure_type"],
                   db_username=db_data["db_user"],
                   db_password=db_data["db_pass"]
                   )
    return payload


def create_db_entry(args, db_data, test_data):
    """Create DB entry for execution"""
    ReportClient.init_instance()
    report_client = ReportClient.get_instance()
    db_user, db_pass = get_db_credential()
    db_data.update({"db_user": db_user, "db_pass": db_pass})
    payload = create_db_payload(args, db_data, test_data)
    report_client.create_db_entry(**payload)


def run_nose_cmd(test_to_run=None, log_file='nosetest.log'):
    """Run nosetests command for execution."""
    cmd_line = [
        f"{params.VIRTUALENV_DIR}/bin/nosetests",
        f"{test_to_run}"
    ]
    log = open(log_file, 'a')
    LOGGER.info('Running nosetests command %s', cmd_line)
    prc = subprocess.Popen(cmd_line, stdout=log, stderr=log, cwd=params.S3TESTS_DIR)  # nosec
    prc.communicate()
    return "PASS" if prc.returncode == 0 else "FAIL"


# pylint: disable-msg=too-many-locals
def trigger_tests_from_te(args):
    """Trigger tests from the provided test execution."""
    LOGGER.info("Starting test execution")
    jira_id, jira_pwd = get_jira_credential()
    jira_obj = jira_utils.JiraTask(jira_id, jira_pwd)
    test_list = get_tests_from_te(jira_obj, args, args.test_type)

    timestamp = datetime.datetime.now().strftime("%m_%d_%Y_%H_%M_%S")
    reports = "reports_" + str(args.test_plan) + "_" + args.te_ticket + "_" + str(timestamp)
    reports_dir = os.path.join(params.LOG_DIR, reports)
    if not system_utils.path_exists(reports_dir):
        system_utils.make_dirs(reports_dir)

    tp_details = jira_obj.get_issue_details(args.test_plan)
    tp_build = tp_details.fields.customfield_22980
    build_number = tp_build[0] if tp_build else 0

    os.environ[params.S3TESTS_CONF_ENV] = params.S3TESTS_CONF_FILE

    for test in test_list:
        test_id = str(test[0])
        LOGGER.info("%s Executing TEST ID : %s %s", "=" * 30, test_id, "=" * 30)
        test_data = get_test_data(jira_obj, test)
        test_to_run = test_data["test_definition"]
        log_file_name = f"{test_id}_{test_to_run}.log"
        log_file = os.path.join(reports_dir, log_file_name)

        # Update Jira with test status and log file
        test_status = "EXECUTING"
        if args.jira_update:
            jira_obj.update_test_jira_status(args.te_ticket, test_id, test_status)
        start_time = datetime.datetime.now()
        test_status = run_nose_cmd(test_to_run, log_file=log_file)
        end_time = datetime.datetime.now()
        execution_time = end_time - start_time
        LOGGER.info("%s TEST %s Execution %s %s", "=" * 30, test_id, test_status, "=" * 30)
        remote_path = os.path.join(params.NFS_BASE_DIR, build_number, args.test_plan,
                                   args.te_ticket, test_id,
                                   datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))
        if os.path.exists(remote_path):
            os.makedirs(remote_path)

        # Upload nosetests log file to NFS share
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=log_file)
        if resp[0]:
            LOGGER.info("Log file is uploaded at location : %s", resp[1])
        else:
            LOGGER.info("Failed to upload log file at location : %s", resp[1])
        if args.db_update:
            db_data = {"test_id": test_id, "test_status": test_status, "log_path": remote_path,
                       "start_time": start_time, "execution_time": execution_time.total_seconds()}
            create_db_entry(args, db_data, test_data)
        # Update Jira for status and log file
        if args.jira_update:
            jira_obj.update_test_jira_status(args.te_ticket, test_id, test_status, remote_path)


def initialize_loghandler(level=logging.DEBUG):
    """Initialize ceph s3tests runner logging."""
    logging.basicConfig(level=level)


def main(args):
    """Main function to start ceph s3-tests execution."""
    setup_configurations(args)
    check_or_create_accounts()
    trigger_tests_from_te(args)


if __name__ == '__main__':
    opts = parse_args()
    initialize_loghandler(opts.log_level)
    main(opts)
