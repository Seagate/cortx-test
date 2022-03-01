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

"""
Script to perform test execution and deployment
"""
import os
import configparser
import subprocess
import argparse
import logging
from core import runner
from commons import params
from commons import cortxlogging
from commons.utils import deploy_utils
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.helpers.node_helper import Node
from commons.constants import LOCAL_S3_CERT_PATH
from testrunner import get_setup_details
from libs.prov.provisioner import Provisioner
from scripts.ssc_cloud.vm_management import VmStateManagement

# Global Constants
CONFIG_FILE = 'scripts/jenkins_job/config.ini'
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)

JOB_DEPLOY_3N = "Partition Main Deploy 3N"
JOB_DEPLOY_1N = 'Partition Main Deploy 1N'
JOB_DESTROY_3N = '3-Node-VM-Destroy'
JEN_DESTROY_URL = "http://eos-jenkins.colo.seagate.com/job/Provisioner"
JEN_DEPLOY_URL = "http://eos-jenkins.colo.seagate.com/job/Cortx-Main/job/centos-7.8.2003"
LOGGER = logging.getLogger(__name__)


def parse_args():
    """
    Argument parser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-te", "--te_tickets", nargs='+', type=str,
                        help="jira xray test execution id")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id")
    parser.add_argument("-b", "--build", type=str, default='',
                        help="Build number")
    parser.add_argument("-t", "--build_type", type=str, default='',
                        help="Build type (Release/Dev)")
    parser.add_argument("-tt", "--test_type", nargs='+', type=str,
                        default=['TODO'], help="Space separated test types")
    parser.add_argument("-d", "--db_update", type=str_to_bool,
                        default=True,
                        help="Update Reports DB. Can be false in case reports db is down")
    parser.add_argument("-u", "--jira_update", type=str_to_bool,
                        default=True,
                        help="Update Jira. Can be false in case Jira is down")
    parser.add_argument("-pe", "--parallel_exe", type=str, default=False,
                        help="parallel_exe: True for parallel, False for sequential")
    parser.add_argument("-tg", "--target", type=str,
                        default='', help="Target setup details")
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value")
    parser.add_argument("-p", "--prc_cnt", type=int, default=2,
                        help="number of parallel processes")
    parser.add_argument("-f", "--force_serial_run", type=str_to_bool,
                        default=False, nargs='?', const=True,
                        help="Force sequential run if you face problems with parallel run")
    parser.add_argument("-i", "--data_integrity_chk", type=str_to_bool,
                        default=False, help="Helps set DI check enabled so that tests "
                                            "perform additional checksum check")
    parser.add_argument("-hs", "--hosts", type=str,
                        help="host list")
    parser.add_argument("-vu", "--vm_user", type=str,
                        default='', help="VM acc id")
    parser.add_argument("-vp", "--vm_pass", type=str,
                        default='', help="VM acc password")
    parser.add_argument("-tk", "--token", type=str,
                        default='', help="deploy job token")
    parser.add_argument("-bp", "--build_path", type=str,
                        default='', help="build path")
    parser.add_argument("-np", "--node_pass", type=str,
                        default='', help="node password")
    parser.add_argument("-sn", "--setupname", type=str,
                        default='', help="setupname")
    parser.add_argument("-cu", "--csm_user", type=str,
                        default='', help="csm_user")
    parser.add_argument("-cp", "--csm_pass", type=str,
                        default='', help="csm_pass")
    parser.add_argument("-ju", "--jira_user", type=str,
                        default='', help="jira_user")
    parser.add_argument("-jp", "--jira_pass", type=str,
                        default='', help="jira_pass")
    parser.add_argument("-du", "--db_user", type=str,
                        default='', help="db_user")
    parser.add_argument("-dp", "--db_pass", type=str,
                        default='', help="db_pass")
    parser.add_argument("-ip", "--data_ip", type=str,
                        default='', help="data_ip")
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


def initialize_loghandler(log) -> None:
    """Initialize test runner logging with stream and file handlers."""
    log.setLevel(logging.DEBUG)
    cwd = os.getcwd()
    dir_path = os.path.join(os.path.join(cwd, params.LOG_DIR_NAME, params.LATEST_LOG_FOLDER))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    name = os.path.splitext(os.path.basename(__file__))[0]
    name = os.path.join(dir_path, name + '.log')
    cortxlogging.set_log_handlers(log, name, mode='w')


# pylint: disable-msg=too-many-locals
def run_tesrunner_cmd(args, attempts, m_vip, todo=False):
    """Form a testrunner command for execution.
    python3 -u testrunner.py -te=$test_exe -tp=$tp_id -tg=${Target_Node}
     -b=${Build} -t=${Build_Branch} -d=${DB_Update} -p=${Process_Cnt_Parallel_Exe}
      --force_serial_run ${Sequential_Execution}
    """
    if attempts > 1:
        # do preboarding/onboarding, aws configure and s3 account creation on client.
        preboarding_cmd = ['python3.7', '-m', 'unittest',
                           'scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_preboarding']
        onboarding_cmd = ['python3.7', '-m', 'unittest',
                          'scripts.jenkins_job.cortx_pre_onboarding.CSMBoarding.test_onboarding']
        run_cmd(preboarding_cmd)
        run_cmd(onboarding_cmd)

        username = os.getenv('ADMIN_USR')
        password = os.getenv('ADMIN_PWD')
        account_name = 'dadmin'
        account_email = 'dadmin@seagate.com'
        acc_creation_cmd = ['python3.7', 'scripts/s3_tools/create_s3_account.py'] + \
                           ['--mgmt_vip=' + str(m_vip)] + \
                           ["--username=" + str(username)] + \
                           ["--password=" + str(password)] + \
                           ["--account_name=" + account_name] + \
                           ["--account_email=" + account_email] + \
                           ["--account_password=" + 'Seagate@1']
        run_cmd(acc_creation_cmd)

        credentials_file = "s3acc_secrets"
        if os.path.exists(credentials_file):
            credentials = ''
            with open(credentials_file) as input_file:
                lines = input_file.readlines()
                for line in lines:
                    credentials = line
                    break
            credentials_list = credentials.split(" ")
            access = credentials_list[0]
            secret = credentials_list[1]
            s3_tool_config_cmd = ["make", "all", "--makefile=scripts/s3_tools/Makefile",
                                  "ACCESS="+access, "SECRET="+secret]
            LOGGER.debug(s3_tool_config_cmd)
            run_cmd(s3_tool_config_cmd)
        else:
            return True

    cwd = os.getcwd()
    cmd_line = ['python3.7', '-u', cwd + "/" + 'testrunner.py']
    _env = os.environ.copy()
    force_serial_run = "--force_serial_run="
    serial_run = "True" if args.force_serial_run else "False"
    force_serial_run = force_serial_run + serial_run
    if args.te_ticket:
        cmd_line = cmd_line + ["-te=" + str(args.te_ticket)]

    if args.test_plan:
        cmd_line = cmd_line + ["-tp=" + str(args.test_plan)]

    if args.setupname:
        cmd_line = cmd_line + ["-tg=" + args.setupname]

    if not args.db_update:
        cmd_line = cmd_line + ["--db_update=" + str(False)]

    if not args.jira_update:
        cmd_line = cmd_line + ["--jira_update=" + str(False)]

    if args.force_serial_run:
        cmd_line = cmd_line + [force_serial_run]

    if todo:
        args.test_type = 'TODO'
        cmd_line = cmd_line + ["--test_type=" + str(args.test_type)]

    cmd_line = cmd_line + ['--build=' + args.build, '--build_type=' + args.build_type]

    LOGGER.debug('Running pytest command %s', cmd_line)
    status = run_cmd(cmd_line)
    return status


def revert_vms(args, vm_list):
    """
    Revert vms to existing snapshot
    """
    vm_machines = vm_list
    _env = os.environ.copy()
    cwd = os.getcwd()
    cmd_line = ['python3.7', '-u', cwd + '/scripts/ssc_cloud/ssc_vm_ops.py', '-a', "revert_vm_snap"]
    if args.vm_user:
        cmd_line = cmd_line + ["-u=" + str(args.vm_user)]
    if args.vm_pass:
        cmd_line = cmd_line + ["-p=" + str(args.vm_pass)]
    for vm_name in vm_machines:
        cmd_line = cmd_line + ["-v=" + str(vm_name)]
        status = run_cmd(cmd_line)
        if status:
            return status


def run_cmd(cmd):
    """
    Execute bash commands on the host
    :param str cmd: command to be executed
    :return: command output
    :rtype: string
    """
    _env = os.environ.copy()
    print("Executing command: {}".format(cmd))
    proc = subprocess.Popen(cmd, env=_env)
    proc.communicate()
    status = proc.returncode
    return status


def trigger_deployment(args, cluster_ip, retries=3):
    """
    Trigger Jenkins N Node job.
    """

    while retries > 0:
        vm_machines = args.hosts.split(',')
        res_status = revert_vms(args, vm_machines)
        if res_status:
            return False

        parameters = dict()
        suffix = 'colo.seagate.com'
        hosts = list()
        for host in vm_machines:
            hosts.append('.'.join([host.strip(), suffix]))

        if len(vm_machines) == 1:
            LOGGER.info("1N deployment job will be triggered")
            job_name = JOB_DEPLOY_1N
            parameters['CORTX_BUILD'] = args.build_path
            parameters['NODE1'] = hosts[0]
            parameters['NODE_PASS'] = args.node_pass
        elif len(vm_machines) == 3:
            job_name = JOB_DEPLOY_3N
            LOGGER.info("3N deployment job will be triggered")
            parameters['CORTX_BUILD'] = args.build_path
            parameters['NODE1'] = hosts[0]
            parameters['NODE2'] = hosts[1]
            parameters['NODE3'] = hosts[2]
            parameters['NODE_PASS'] = args.node_pass
            parameters['NODE_MGMT_VIP'] = cluster_ip
        token = args.token
        token_str = token.replace("'", "")
        output = Provisioner.build_job(job_name=job_name,
                                       parameters=parameters,
                                       token=token_str,
                                       jen_url=JEN_DEPLOY_URL)
        LOGGER.info("Jenkins Build URL: {}".format(output['url']))
        retries = retries - 1
        if output['result'] == 'SUCCESS':
            return True


def set_s3_endpoints(cluster_ip):
    """
    Set s3 endpoints to cluster ip in /etc/hosts
    :param str cluster_ip: IP of the cluster
    :return: None
    """
    print("Setting s3 endpoints on client.")
    system_utils.run_local_cmd(cmd="rm -f /etc/hosts", flg=True)
    with open("/etc/hosts", 'w') as file:
        file.write(
            "127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n")
        file.write(
            "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n")
        file.write("{} s3.seagate.com sts.seagate.com iam.seagate.com sts.cloud.seagate.com\n"
                   .format(cluster_ip))


def get_vm_creds(args):
    """Placeholder function to get generic vm credentials."""
    return 'root', args.node_pass


def single_node_server_changes(hostname, username, password, mg_ip):
    """
    Server side changes for single node
    """
    server_haproxy_cfg = CONFIG['default']['haproxy_config']
    local_haproxy_cfg = CONFIG['default']['tmp_haproxy_config']
    obj = Node(hostname=hostname[0], username=username, password=password)
    # Stopping/disabling firewalld service on node for tests
    print("Doing server side settings for firewalld and haproxy.")
    obj.execute_cmd("systemctl stop firewalld", read_lines=True)
    obj.execute_cmd("systemctl disable firewalld", read_lines=True)
    # Doing changes in haproxy file and restarting it
    if os.path.exists(local_haproxy_cfg):
        run_cmd("rm -f {}".format(local_haproxy_cfg))
    obj.copy_file_to_local(remote_path=server_haproxy_cfg, local_path=local_haproxy_cfg)
    with open(local_haproxy_cfg) as file:
        for num, line in enumerate(file, 1):
            if "option forwardfor" in line:
                indx = num
    with open(local_haproxy_cfg, 'r') as file:
        read_file = file.readlines()
    read_file.insert(indx - 2, "    bind {}:80\n".format(mg_ip))
    read_file.insert(indx - 1, "    bind {}:443 ssl crt /etc/ssl/stx/stx.pem\n".format(mg_ip))
    with open(local_haproxy_cfg, 'w') as file:
        read_file = "".join(read_file)
        file.write(read_file)
    obj.copy_file_to_remote(local_path=local_haproxy_cfg, remote_path=server_haproxy_cfg)
    obj.execute_cmd("systemctl restart haproxy", read_lines=True)


# pylint: disable-msg=too-many-locals
def configure_haproxy_lb(hostname, username, password, mg_ip):
    """
    Configure haproxy as Load Balancer on server
    """
    server_haproxy_cfg = CONFIG['default']['haproxy_config']
    local_haproxy_cfg = CONFIG['default']['tmp_haproxy_config']
    if len(hostname) > 1:
        instance_per_node = 1
        s3instance = "    server s3-instance-{0} srvnode-{1}.data.private:{2} check maxconn 110\n"
        authinstance = "    server s3authserver-instance{0} srvnode-{1}.data.private:28050\n"
        total_s3_instances = list()
        total_auth_instances = list()
        for node in range(len(hostname)):
            start_inst = (node * instance_per_node)
            end_inst = ((node + 1) * instance_per_node)
            for i in range(start_inst, end_inst):
                port = "2807{}".format((i % instance_per_node) + 1)
                total_s3_instances.append(s3instance.format(i + 1, node + 1, port))
            total_auth_instances.append(authinstance.format(node + 1, node + 1))
        LOGGER.debug(total_s3_instances)
        LOGGER.debug(total_auth_instances)
        for host in hostname:
            LOGGER.info("Updating s3 instances in haproxy.cfg on node: %s", host)
            nd_obj = Node(hostname=host, username=username, password=password)
            nd_obj.copy_file_to_local(server_haproxy_cfg, local_haproxy_cfg)
            with open(local_haproxy_cfg, "r") as local_haproxy:
                data = local_haproxy.readlines()
            with open(local_haproxy_cfg, "w") as local_haproxy:
                for line in data:
                    if "server s3-instance-" in line:
                        line = "".join(["#", line] + total_s3_instances)
                    elif "server s3authserver-instance" in line:
                        line = "".join(["#", line] + total_auth_instances)
                    local_haproxy.write(line)
            nd_obj.copy_file_to_remote(local_haproxy_cfg, server_haproxy_cfg)
            nd_obj.execute_cmd("systemctl restart haproxy", read_lines=True)
            LOGGER.info("Restarted haproxy service")
        LOGGER.info("Configured s3 instances in haproxy.cfg on all the nodes")
    else:
        single_node_server_changes(hostname, username, password, mg_ip)


def setup_client(args, hosts, data_ip):
    """
    Perform client settings
    """
    host = hosts[0]
    uname, upasswd = get_vm_creds(args)
    remote_cert_path = "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
    local_cert_path = "/etc/ssl/stx-s3-clients/s3/ca.crt"
    if os.path.exists(local_cert_path):
        system_utils.run_local_cmd(cmd="rm -f {}".format(local_cert_path), flg=True)
    nd_obj_host = Node(hostname=host, username=uname, password=upasswd)
    nd_obj_host.copy_file_to_local(remote_path=remote_cert_path, local_path=local_cert_path)
    if len(hosts) == 1:
        set_s3_endpoints(data_ip)
    # configure_haproxy_lb(hosts, uname, upasswd, cluster_ip)


def update_vm_db(args):
    """
    Free VM from setup.
    This function would be refactored to use service_acount_access when it is added as
    a module.
    """

    vm_state = VmStateManagement(params.VM_COLLECTION)
    lock_released = vm_state.unlock_system(args.setupname)
    return lock_released


def destroy_vm(hosts, token, node_passwd=None):
    """
    Destroy VM from setup.
    """
    if not hosts:
        raise EnvironmentError('list of hosts is mandatory')
    job_name = JOB_DESTROY_3N
    parameters = dict()
    jenkins_url = JEN_DESTROY_URL
    valid_parameters = False
    if hosts % 3 == 0:
        valid_parameters = True
        LOGGER.info("Multi nodes destroy job will be triggered")
        parameters['NODE1'] = hosts[0]
        parameters['NODE2'] = hosts[1]
        parameters['NODE3'] = hosts[2]
        parameters['NODE_PASS'] = node_passwd
    if not valid_parameters:
        LOGGER.error('Please check provided parameters')
        raise EnvironmentError('Please check provided parameters')
    output = Provisioner.build_job(
        job_name, parameters, token, jenkins_url)
    LOGGER.info("Jenkins Build URL: {}".format(output['url']))
    assert_utils.assert_equal(output['result'], "SUCCESS",
                              "Job is not successful, please check the url.")


def post_test_execution_action(args):
    """
    Perform post actions
    """
    update_vm_db(args=args)
    # revert_vms(args, hosts_list)



def main(args):
    """Main Entry function and logic of script.
    """
    os.environ["DB_USER"] = args.db_user
    os.environ["DB_PASSWORD"] = args.db_pass
    hosts_list = args.hosts.split(',')
    # Get setup details
    suffix = 'colo.seagate.com'
    hosts = list()
    for host in hosts_list:
        hosts.append('.'.join([host.strip(), suffix]))
    setup_details = deploy_utils.register_setup_entry(hosts, args.setupname, args.csm_user,
                                                      args.csm_pass, args.node_pass)
    cluster_ip = setup_details['csm']['mgmt_vip']
    data_ip = args.data_ip
    setup_client(args, hosts, data_ip)
    te_list = args.te_tickets
    for te_num in te_list:
        te_completed = False
        attempts = 1
        while not te_completed:
            args.te_ticket = te_num
            if attempts >= 5:
                post_test_execution_action(args)
                raise EnvironmentError('More than 5 attempts of executing tests crossed.')

            if attempts == 1:
                status = run_tesrunner_cmd(args, attempts, cluster_ip, todo=False)
            else:
                status = run_tesrunner_cmd(args, attempts, cluster_ip, todo=True)
            attempts += 1
            if status:
                ret = trigger_deployment(args, cluster_ip, retries=3)
                if not ret:
                    post_test_execution_action(args)
                    raise EnvironmentError('Deployment or VM revert ran into errors')
            else:
                te_completed = True
    else:
        post_test_execution_action(args)


if __name__ == '__main__':
    initialize_loghandler(LOGGER)
    opts = parse_args()
    main(opts)
