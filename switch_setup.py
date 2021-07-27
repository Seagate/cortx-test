import os
import subprocess
import argparse
import csv
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

JOB_DEPLOY_3N = 'VM-Deployment-R2-3Node'
JOB_DEPLOY_1N = 'VM-Deployment-R2-1Node'
JOB_DESTROY_3N = '3-Node-VM-Destroy'
JEN_DEPLOY_URL = "http://eos-jenkins.colo.seagate.com/job/Cortx-Deployment"
JEN_DESTROY_URL = "http://eos-jenkins.colo.seagate.com/job/Provisioner"
LOGGER = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-te", "--te_tickets", type=str,
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


def run_tesrunner_cmd(args, todo=False):
    """Form a testrunner command for execution.
    python3 -u testrunner.py -te=$test_exe -tp=$tp_id -tg=${Target_Node}
     -b=${Build} -t=${Build_Branch} -d=${DB_Update} -p=${Process_Cnt_Parallel_Exe}
      --force_serial_run ${Sequential_Execution}
    """
    cmd_line = ['python3.7 -u testrunner.py ']
    _env = os.environ.copy()
    force_serial_run = "--force_serial_run="
    serial_run = "True" if args.force_serial_run else "False"
    force_serial_run = force_serial_run + serial_run
    if args.te_ticket:
        cmd_line = cmd_line + ["-te=" + str(args.te_ticket)]

    if args.tp_ticket:
        cmd_line = cmd_line + ["-tp=" + str(args.tp_ticket)]

    if args.target:
        cmd_line = cmd_line + ["-tg=" + args.target]

    if not args.db_update:
        cmd_line = cmd_line + ["--db_update=" + str(False)]

    if not args.jira_update:
        cmd_line = cmd_line + ["--jira_update=" + str(False)]

    if not args.force_serial_run:
        cmd_line = cmd_line + [force_serial_run]

    if todo:
        args.test_type = ['TODO']
        cmd_line = cmd_line + ["--test_type=" + args.test_type]

    cmd_line = cmd_line + ['--build=' + args.build, '--build_type=' + args.build_type]

    LOGGER.debug('Running pytest command %s', cmd_line)
    prc = subprocess.Popen(cmd_line, env=_env)
    prc.communicate()
    rc = prc.returncode
    return rc


def trigger_deployment(vm_machines, parameters, token, reties=3):
    """
    Trigger Jenkins N Node job.
    """
    output = Provisioner.build_job(job_name=JOB_DEPLOY_3N,
                                   parameters=parameters,
                                   token=token,
                                   jen_url=JEN_DEPLOY_URL)
    LOGGER.info("Jenkins Build URL: {}".format(output['url']))
    assert_utils.assert_equal(
        output['result'],
        "SUCCESS",
        "Job is not successful, please check the url.")


def set_s3_endpoints(cluster_ip):
    """
    Set s3 endpoints to cluster ip in /etc/hosts
    :param str cluster_ip: IP of the cluster
    :return: None
    """
    print("Setting s3 endpoints on client.")
    system_utils.run_local_cmd(cmd="rm -f /etc/hosts", flg=True)
    with open("/etc/hosts", 'w') as file:
        file.write("127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n")
        file.write("::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n")
        file.write("{} s3.seagate.com sts.seagate.com iam.seagate.com sts.cloud.seagate.com\n"
                   .format(cluster_ip))


def get_vm_creds():
    """Placeholder function to get generic vm credentials."""
    return tuple()


def setup_client(host, clstr_ip):
    uname, usr_passwd = get_vm_creds()
    remote_cert_path = "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
    local_cert_path = "/etc/ssl/stx-s3-clients/s3/ca.crt"
    if os.path.exists(local_cert_path):
        system_utils.run_local_cmd(cmd="rm -f {}".format(local_cert_path), flg=True)
    nd_obj_host = Node(hostname=host, username=uname, password=usr_passwd)
    nd_obj_host.copy_file_to_local(remote_path=remote_cert_path, local_path=local_cert_path)
    set_s3_endpoints(clstr_ip)


def update_vm_db(args):
    """
    Free VM from setup.
    This function would be refactored to use service_acount_access when it is added as
    a module.
    """

    AVAILABLE_VM_CSV = 'available_vms.csv'
    vm_state = VmStateManagement(params.VM_COLLECTION)
    if args.action == "get_setup":
        nodes = int(args.nodes)
        lock_acquired, setup_info = vm_state.get_available_system(nodes)
        if lock_acquired:
            with open(os.path.join(os.getcwd(), AVAILABLE_VM_CSV), 'w', newline='') as vm_info_csv:
                writer = csv.writer(vm_info_csv)
                writer.writerow([setup_info["setup_name"], setup_info["client"],
                                 setup_info["hostnames"], setup_info['m_vip']])
            return lock_acquired
    elif args.action == "mark_setup_free":
        lock_released = vm_state.unlock_system(args.setupname)
        return lock_released
    lock_released = vm_state.unlock_system(args.setupname)


def destroy_vm(hosts, token, build='', mgmt_vip='', node_passwd=None):
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


def post_test_execution_action(*args, **kwargs):
    hosts = kwargs.get('hosts')
    token = kwargs.get('build')
    mgmt_vip = kwargs.get('mgmt_vip')
    node_passwd = kwargs.get('node_pass')
    destroy_vm(hosts, token, build='', mgmt_vip='', node_passwd=None)
    update_vm_db(args=args)


def main(args):
    """Main Entry function and logic of script.
    """
    setup_details = deploy_utils.register_setup_entry(args.hosts, new_entry=False)
    attempts = 1
    te_completed = False
    setup_client(args)
    for te in args.te_tickets:
        te_completed = False
        attempts = 1
        while not te_completed:
            args.te_ticket = te
            if attempts >= 5:
                raise EnvironmentError('More than 5 attempts of executing tests crossed.')

            if attempts == 1:
                status = run_tesrunner_cmd(args=args, todo=False)
            else:
                status = run_tesrunner_cmd(args=args, todo=True)
            attempts += 1
            if status:
                ret = destroy_vm(args.hosts, args.token, node_passwd=None)
                if not ret:
                    raise EnvironmentError('Distroy VM ran into errors')
                ret = trigger_deployment()
                if not ret:
                    raise EnvironmentError('Deployment Job ran into errors')
            if ret:
                status = run_tesrunner_cmd(args=args, todo=True)
            if not status:
                te_completed = True
    else:
        post_test_execution_action(args, kwargs=dict())


if __name__ == '__main__':
    initialize_loghandler(LOGGER)
    opts = parse_args()
    main(opts)
