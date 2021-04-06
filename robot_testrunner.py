import os
import subprocess
import argparse
import logging
from multiprocessing import Process
import datetime
from commons.utils.jira_utils import JiraTask
from commons import report_client
from commons.utils import system_utils
from commons import params
from typing import Tuple
from typing import Optional
from typing import Any
import getpass

LOGGER = logging.getLogger(__name__)

REPORT_CLIENT = None
report_client.ReportClient.init_instance()
REPORT_CLIENT = report_client.ReportClient.get_instance()


def parse_args():
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
        try:
            getattr(CMN_CFG, 'db_user') and getattr(CMN_CFG, 'db_user')
            db_user, db_pwd = CMN_CFG.db_user, CMN_CFG.db_password
        except AttributeError as attr_err:
            LOGGER.exception(str(attr_err))
            db_user = input("DB username: ")
            db_pwd = getpass.getpass("DB password: ")
        os.environ['DB_USER'] = db_user
        os.environ['DB_PASSWORD'] = db_pwd
    return db_user, db_pwd

def get_tests_from_te(jira_obj, args, test_type='ALL'):
    """
    Get tests from given test execution
    """
    test_list, tag = jira_obj.get_test_ids_from_te(str(args.te_ticket), test_type)
    if len(test_list) == 0:
        raise EnvironmentError("Please check TE provided, tests or tag is missing")
    return test_list, tag


def create_report_payload(test_info, d_u, d_pass):
    """Create Report Payload for POST request to put data in Report DB."""
    os_ver = system_utils.get_os_version()
    if test_info['final_result'] == 'FAIL':
        health_chk_res = "TODO"
    else:
        health_chk_res = "NA"


    data_kwargs = dict(os=os_ver,
                       build=test_info['build'],
                       build_type=test_info['build_type'],
                       client_hostname=system_utils.get_host_name(),
                       execution_type="Automated",
                       health_chk_res=health_chk_res,
                       are_logs_collected=test_info['logs_collected'],
                       log_path=test_info['log_path'],
                       testPlanLabel=test_info['tp_label'],  # get from TP    tp.fields.labels
                       testExecutionLabel=test_info['te_label'],  # get from TE  te.fields.labels
                       nodes=0,  # number of target hosts
                       nodes_hostnames=[],
                       test_exec_id=test_info['te_tkt'],
                       test_exec_time=test_info['duration'],
                       test_name=test_info['test_name'],
                       test_id=test_info['test_id'],
                       test_id_labels=test_info['labels'],
                       test_plan_id=test_info['tp_ticket'],
                       test_result=test_info['final_result'],
                       start_time=test_info['start_time'],
                       tags='',  # in mem te_meta
                       test_team=test_info['te_component'],  # TE te.fields.components[0].name
                       test_type='Robot',  # TE Avocado/CFT/Locust/S3bench/ Pytest
                       latest=True,
                       feature='Cluster User Operation (CSM)',
                       # feature Should be read from master test plan board.
                       db_username=d_u,
                       db_password=d_pass
                       )
    return data_kwargs


def collect_te_info(jira_obj, te):
    te_details = jira_obj.get_issue_details(te)
    te_label = ''
    te_comp = ''
    if te_details.fields.labels:  # Optional I.e. Isolated, NearFull, By default: Normal
        te_label = te_details.fields.labels[0]
    if te_details.fields.components:
        te_comp = te_details.fields.components[0].name
    return te_label, te_comp


def collect_tp_info(jira_obj, tp):
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
    test_details = jira_obj.get_issue_details(test)
    test_name = test_details.fields.summary
    test_label = ''
    if test_details.fields.labels:
        test_label = test_details.fields.labels[0]
    return test_name, test_label

def run_robot_cmd(args, te_tag=None, logFile='main.log'):
    """Form a robot command for execution."""   
    
    headless = " -v headless:" + str(args.headless)
    url = " -v url:"+ str(args.csm_url)
    browser = " -v browser:" + str(args.browser)
    username = " -v username:" + str(args.csm_user)
    password = " -v password:" + str(args.csm_pass)
    tag = ' -i ' + te_tag
    directory = " . "

    cmd_line = "cd robot; robot --timestampoutputs -d reports"+url+browser+ \
               username+password+tag+directory+";cd .."
    log = open(logFile, 'a')
    prc = subprocess.Popen(cmd_line, shell=True,stdout=log, stderr=log)
    prc.communicate()

def getTestStatusAndParseLog(logFile = 'main.log'):
    """
    Parse main.log file to get
    a) TestStatus: Pass/Fail
    b) Output filepath: XML
    c) Log filepath: xml/html
    d) Report filepath: xml/html 
    """
    TestStatus = 'PASS'
    outputfilepath = ''
    logfilepath = ''
    reportfilepath = ''
    with open(logFile, 'r') as file:

        for line in file:
            # For each line, check if line contains the string
            if 'FAIL' in line:
                TestStatus = 'FAIL'
            elif 'PASS' in line:
                TestStatus = 'PASS'

            if "Output: " in line:
                outputfilepath = line.split()[-1]
            if "Log: " in line:
                logfilepath = line.split()[-1]
            if "Report:" in line:
                reportfilepath = line.split()[-1]

    return TestStatus, outputfilepath, logfilepath, reportfilepath

def trigger_tests_from_te(args):
    """
    Get the tests from test execution
    Trigger those tests using pytest command
    """
    jira_id, jira_pwd = get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    test_list, te_tag = get_tests_from_te(jira_obj, args, args.test_type)
    
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
        test_id = str(test)
        print(" TEST ID : ", test_id)
        if args.db_update == 'yes':
            test_name, test_label = collect_test_info(jira_obj, test)

        # execute test using test id tag
        start_time = datetime.datetime.now()
        env = os.environ.copy()
        # update jira for status and log file
        test_status = 'EXECUTING'
        jira_obj.update_test_jira_status(args.te_ticket, test, test_status)

        run_robot_cmd(args, test_id, logFile='main.log')
        end_time = datetime.datetime.now()
        
        # parse result json/xml to get test status and duration
        test_status = ''
        test_output = ''
        test_log = ''
        test_report = ''
       
        #parse log
        test_status, test_output, test_log, test_report = getTestStatusAndParseLog(logFile='main.log')
                
        duration = (end_time - start_time)

        # move all log files to nfs share
	
        print("Uploading test log file to NFS server ", test_output)
        remote_path = os.path.join(params.NFS_BASE_DIR, build_number, args.test_plan,
                                   args.te_ticket)
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=test_output)
        if resp[0]:
            print("Output file is uploaded at location : %s", resp[1])

        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=test_log)
        if resp[0]:
            print("Log file is uploaded at location : %s", resp[1]) 

        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=test_report)
        if resp[0]:
            print("Report file is uploaded at location : %s", resp[1])      

        #upload main.log file to NFS share      
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=logFile)
        # update jira for status and log file
        jira_obj.update_test_jira_status(args.te_ticket, test, test_status, remote_path)

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
