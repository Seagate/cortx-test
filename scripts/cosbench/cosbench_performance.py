import argparse
import sys
import os
import time
import configparser
from subprocess import Popen, PIPE
import paramiko
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import numpy as np
import logging
from threading import Thread


# Setting the logging parameters
filename = datetime.datetime.today().strftime('%Y%m%d')
logfile = "%s.log" % filename
logging.basicConfig(filename=logfile, format='%(asctime)s - %(message)s', level=logging.DEBUG)


def get_args():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(description='Arguments for executing the Cosbench performance test suit',
                                     epilog="This Program execute the to test the performance of cloud object \
                                      stores (OBS) in a quick and scalable way if no value is provided it will \
                                      run with default values")

    parser.add_argument('--install', default=False, action="store_true",
                        help='Install and Configure the cosbench on controller and drivers nodes')

    parser.add_argument('-w', '--workers', action='store',
                        required=True, type=int,
                        help='Number of worker should be equal to or greater than total number of available \
                        driver nodes and controller')
    
    parser.add_argument('--buildver', action='store',
                        required=True,
                        help='Current Build version of s3 server to be used for workload test')

    parser.add_argument('-b', '--buckets', action='store', type=int,
                        help='Number of buckets that will be created')

    parser.add_argument('-o', '--objects', action='store', type=int,
                        help='Number of objects that will be created')

    parser.add_argument('-os', '--objSize', action='append', type=int,
                        default=[],
                        help='Object Size in MB, repeatd values can be passed')

    parser.add_argument('-r', '--runtime', action='store', type=int,
                        help='Duration of test run in seconds')

    parser.add_argument('-ak', '--accesskey', action='store',
                        help='Access key of the s3 Object storage')

    parser.add_argument('-sk', '--secretkey', action='store',
                        help='Secret key of the s3 Object storage')

    parser.add_argument('-ep', '--endpoint', action='store',
                        help='Endpoint of the s3 Object storage')

    parser.add_argument('-t', '--workloadType', action='store', default="all",
                        help="Supported workload types are 'read', 'write', 'mixed' and 'all' \
                        'read' means 100 pct read only, 'write' means 100 ptc write only, 'mixed' means \
                        read to write ratio will be 50:50, 25:75 and 75:25, 'all' workload type means \
                        it includes all ie: read, write and mixed")

    args = parser.parse_args()
    
    return args


class CosbenchPerf:

    def __init__(self, controller):
        self.cwdir = os.getcwd()
        self.controller = controller
        self.dfile = 'driver-nodes.list'

    def monitor_exec_cmd(self, cmd, end_count=10):
        """
        For executing and monitoring the instllation of cosbench packages on all the nodes
        :param cmd: actual remote command to be executed
        :param end_count: wait time in seconds for installation to finish on all nodes
        :return: None
        """
        counter = 0
        logging.debug('Executing local command : {}'.format(cmd))
        process = Popen(cmd, stderr=PIPE, stdout=PIPE, shell=True, universal_newlines=True, bufsize=8192)
        linebuffer = []
        logging.debug('Listening to the STDOUT PIPE')

        def stream_line_reader(readobj, buffer):
            while True:
                line = readobj.readline()
                if line:
                    buffer.append(line)
                else:
                    break

        t = Thread(target=stream_line_reader, args=(process.stdout, linebuffer))
        t.daemon = True
        t.start()
        while True:
            if linebuffer:
                logging.debug(linebuffer.pop(0))
                counter = 0
            else:
                logging.debug("Empty PIPE....")
                time.sleep(1)
                counter += 1
                if counter == end_count:
                    return

    def ssh_connect(self, host, uname, passwd):
        """
        For executing the remote host commands
        :param host: ip of the remote host
        :param uname: username of the remote host
        :param pwd: password of the remote host
        :return: sshost client object
        """
        logging.debug('Connecting with remote host: {}'.format(host))
        try:
            sshost = paramiko.client.SSHClient()
            sshost.load_system_host_keys()
            sshost.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            sshost.connect(hostname=host, username=uname, password=passwd)
            return sshost
        except paramiko.AuthenticationException as autherr:
            logging.debug('Error : {}'.format(autherr))
            sys.exit(0)

    def enable_ports(self, host, uname, pwd, drivere_flag=False):
        """
        This method enables ports on the controller and driver
        :param host: takes ip of the remote host
        :param uname: takes username of the remote host
        :param pwd: takes password of the remote host
        :param drivere_flag: takes boolean value for the driver node
        :return:
        """
        logging.debug('Allow the ports to be opened on nodes')
        controller_cmd = 'unset http ; iptables -I INPUT -p tcp -m tcp --dport 19088 -j ACCEPT'
        driver_cmd = 'unset http ; iptables -I INPUT -p tcp -m tcp --dport 18088 -j ACCEPT'
        sshost = self.ssh_connect(host, uname, pwd)
        if drivere_flag:
            sshost.exec_command(driver_cmd)
        else:
            sshost.exec_command(controller_cmd)

    def exec_cmd(self, cmd, wait=False):
        """
        For executing long running local commands
        :param cmd: actual command to be executed
        :param wait: wait time for the command execution
        :return:
        """
        logging.debug('Executing local command : {}'.format(cmd))
        process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        if not wait:
            time.sleep(5)
            return
        output_lst = []
        for line in iter(process.stdout.readline, b''):
            line = line.rstrip().decode('utf-8')
            logging.debug(line)
            output_lst.append(line)
            process.stdout.flush()
        return output_lst

    def install_keys(self, pkey, host, uname, pwd, packages=[]):
        """
        Install the public key on localhost and remote hosts
        :param pkey: public key file name
        :param uname: username of the remote host
        :param pwd: password of the remote host
        :param packages: package need to installed
        :return: None
        """
        # Generating the SSH keys and setting the password less property
        logging.debug('Installing public keys on node : {}'.format(host))
        sshost = self.ssh_connect(host, uname, pwd)
        logging.debug('Executing Commands on remote host')
        sshost.exec_command('mkdir -p ~/.ssh/')
        sshost.exec_command('echo "%s" >> ~/.ssh/authorized_keys' % pkey)
        sshost.exec_command('chmod 644 ~/.ssh/authorized_keys')
        sshost.exec_command('chmod 700 ~/.ssh/')
        if packages:
            for package in packages:
                sshost.exec_command('yum install {} -y'.format(package))
                logging.debug('Installing package wait time 80 sec')
                time.sleep(80)
        sshost.close()

        self.exec_cmd('ssh-keyscan -H {} >> ~/.ssh/known_hosts'.format(host))
        logging.debug('Successfully added key on the remote host --> {}'.format(host))

    def check_packages(self, host, uname, pwd):
        """
        This method check for the pre-requisite linux package on the system.
        :param host: ip of the remote host
        :param uname: username of the remote host
        :param pwd: password of the remote host
        :return: list of packages not installed
        """
        packages_lst = []
        check_java_cmd = "yum list installed|grep 'java'"
        check_nmap_cmd = "yum list installed|grep 'nmap'"
        check_wget_cmd = "yum list installed|grep 'wget'"
        check_unzip_cmd = "yum list installed|grep 'unzip'"
        sshost = self.ssh_connect(host, uname, pwd)
        stdin, stdout, stderr = sshost.exec_command(check_java_cmd)
        if stdout.readline() == '':
            logging.debug('Java not installed on the host {}'.format(host))    
            packages_lst.append('java-1.8.0-openjdk')
        stdin, stdout, stderr = sshost.exec_command(check_nmap_cmd)
        if stdout.readline() == '':
            logging.debug('nmap lib not installed on the host {}'.format(host))
            packages_lst.append('nmap')
        stdin, stdout, stderr = sshost.exec_command(check_wget_cmd)
        if stdout.readline() == '':
            logging.debug('wget lib not installed on the host {}'.format(host))
            packages_lst.append('wget')
        stdin, stdout, stderr = sshost.exec_command(check_unzip_cmd)
        if stdout.readline() == '':
            logging.debug('unzip lib not installed on the host {}'.format(host))
            packages_lst.append('unzip')

        return packages_lst           

    def install_configure(self, host_list):
        """
        This method install and configure the cosbench and enable ports on the nodes
        :param: list of remote driver nodes for creating driver node file
        :return: None
        """
        logging.debug('Install the Cosbench tool and configure')
        with open(self.dfile, 'w') as fp:
            fp.write('\n'.join(set(host_list)))
        install_cmd = 'sh cosbench.sh install --controller {} --drivers {}'.format(self.controller, self.dfile)
        logging.debug('Installing Cosbench...')
        self.monitor_exec_cmd(install_cmd, end_count=200)
        logging.debug('Configuring the Cosbench...')
        config_cmd = 'sh {}/cosbench.sh configure --controller {} --drivers {}'.format\
            (self.cwdir, self.controller, self.dfile)
        self.exec_cmd(config_cmd, wait=False)
        time.sleep(10)

    def start_cosbench(self, accessKey, secretKey, label, s3_endpoint):
        """
        It will start the cosbench service on controller as well on the driver nodes
        :param accessKey: access key of the s3 server
        :param secretKey: secret key of the s3 server
        :param label: s3 label for creating the name of the file
        :param s3_endpoint: s3 server url
        :return: None
        """
        logging.debug('Starting the Cosbench...')
        start_cmd = 'sh cosbench.sh start --controller {} --drivers {}'.format(self.controller, self.dfile)
        self.exec_cmd(start_cmd, wait=True)
        logging.debug('Create setup properties file')
        setup_file = label + '.properties'
        with open(setup_file, 'w') as fp: 
            props = "s3_endpoint:{}\naccess_key:{}\nsecret_key:{}\n".format(s3_endpoint, accessKey, secretKey)
            fp.write(props)

        return setup_file

    def create_workload_profile(self, objsize_lst, workers, buckets, workloadtype, runtime, objects, configobj):
        """
        This method creates workload properties file 
        :param:objSize_lst:Object size in MB
        :param:Number clients to emulate
        :param:Number of buckets
        :param:workload type ie:read, write or mixed
        """
        property_file_ls = []
        # Reading multiple object sizes
        if objsize_lst:
            object_sz_lst = objsize_lst
        else:
            object_sz_str = configobj.get('WORKLOADPROPS', 'object_size_in_mb')
            object_sz_lst = [object_sz.strip() for object_sz in object_sz_str.split(',')]
        runtime = runtime if runtime else configobj.get('WORKLOADPROPS', 'run_time_in_seconds')
        no_objects = objects if objects else configobj.get('WORKLOADPROPS', 'no_of_objects')
        no_buckets = buckets if buckets else configobj.get('WORKLOADPROPS', 'no_of_buckets')
        for i in range(len(object_sz_lst)):
            property_str = "no_of_buckets={}\nno_of_objects={}\nobject_size_in_mb={}\n"\
                           "no_of_workers={}\nworkload_type={}\nrun_time_in_seconds={}\n".format(no_buckets,\
                            no_objects, object_sz_lst[i], workers, workloadtype, runtime)
            prop_file = 'workload_{}.properties'.format(i)
            with open(prop_file, 'w') as fp:
                fp.write(property_str)
            property_file_ls.append(prop_file)
        return property_file_ls, runtime

    def start_workload(self, setup_prop, workload_prop_file):
        """
        This method will start the actual workload execution on the s3 server
        :workload_prop: workload properties file for s3 operations such as object size
        :return: workloadid
        """
        run_cosbench_load = "sh run-test.sh --s3setup {} --controller {} " \
                            "--workload {}".format(setup_prop, self.controller, workload_prop_file)
        output = self.exec_cmd(run_cosbench_load, wait=True)
        workloadid = output[-3].split(':')[-1].strip()
        logging.debug('Workload id : {}'.format(workloadid))
        return workloadid

    def monitor_status(self, workid, wait_duration=30):
        """
        This method monitor the current progress of the running workload
        :param workid: workload id of the job in process
        :param wait_duration: wait time after poll to the running workload
        :return: None
        """
        status_cmd = 'sh manage-workload-status.sh --list_running  --controller {}'.format(self.controller)
        while True:
            status = self.exec_cmd(status_cmd, wait=True)
            if status[-1].strip() == 'Total: 0 active workloads':
                return
            else:
                logging.debug('Still the workload is in progress '
                              'for workid {}--> {}'.format(workid, status[-1]))
            logging.debug('Going for sleep {}secs'.format(wait_duration))
            time.sleep(wait_duration)

    def capture_result(self, workid, duration, buildver):
        """
        This method get the raw result and convert it into csv and html file format
        :param workid: workload id of the job executed on the cosbench
        :param duration: duration of the workload run
        :return: None
        """
        #list all the files in the current dir
        list_before = os.listdir(os.getcwd())
        self.monitor_status(workid)
        result_cmd = 'sh {}/capture-artifacts.sh --workloadID {} --output-directory {} --controller {}'.format(
            self.cwdir, workid, self.cwdir, self.controller)
        self.exec_cmd(result_cmd, wait=True)
        time.sleep(5)

        # Filtering out the csv file generated
        list_after = os.listdir(os.getcwd())
        csv_file_set = set(list_after) - set(list_before)
        csv_file = list(csv_file_set)[0]
        logging.debug('Result output file is {}'.format(csv_file))
        self.generate_perf_result(csv_file, duration, build_ver=buildver)

    def generate_perf_result(self, csvfile, duration, reportfilename='report.csv', build_ver=None):
        """
        This method generates the csv formatted csv report and html file with current time and date
        :param csvfile: original file having raw data
        :param duration: total duration of the run
        :param level: description level of the report generated
        :param reportfilename: report csv file having the actual formatted data
        :return: None
        """
        element_dict = {}
        datetimevalue = datetime.datetime.now()
        timestampstr = datetimevalue.strftime("%d-%b-%Y")
        filename = csvfile
        cur_dir = os.getcwd()
        html_filename = timestampstr + '_' + 'report.html'
        html_file = os.path.join(cur_dir, html_filename)
        report_file = os.path.join(cur_dir, reportfilename)
        header_flag = not os.path.exists(report_file)
        workload_details = filename.split('.')[0].split('-')[1:5]
        objSize, buckets, noObjs, workers = workload_details
        col_to_use = [0, 2, 3, 4, 5, 13, 14, 16]
        df = pd.read_csv(filename, header=None, usecols=col_to_use, skiprows=0)
        workload_type = ['write', 'read']
        columns_ls = ['Workload-Read/Write', 'Duration', 'Workload details', 'Op-Count ops',
                      'Byte-Count', 'Avg-ResTime ms', 'Throughput op/s',
                      'Bandwidth Bits/Sec', 'Status', 'BuildVersion']
        mixed_id_list = []
        new_df = df[df[2].isin(workload_type)]
        for row in new_df.values:
            nrow = row.tolist()
            logging.debug(nrow)
            workloadType = nrow.pop(1)
            workload_str = 's3-{}-{}-{}-{}-{}'.format(workloadType, objSize, noObjs, workers, buckets)
            workload_id = nrow.pop(0).split('-')[-1]
            if workload_id == '100r':
                element_dict['READ'] = ['100r']
            if workload_id == '100w':
                element_dict['WRITE'] = ['100w']
            if workload_id == '50r50w':
                mixed_id_list.append('50r50w')
            if workload_id == '25r75w':
                mixed_id_list.append('25r75w')
            if workload_id == '75r25w':
                mixed_id_list.append('75r25w')
            if mixed_id_list:
                element_dict['MIXED'] = mixed_id_list
            nrow.insert(0, workload_id)
            nrow.insert(1, duration)
            nrow.insert(2, workload_str)
            nrow.insert(9, build_ver)
            new_dataframe = pd.DataFrame([nrow], columns=columns_ls)
            new_dataframe.to_csv(report_file, header=header_flag, index=0, mode='a')
            header_flag = False
        time.sleep(2)
        if os.path.exists(report_file):
            report_dataframe = pd.read_csv(report_file, header=0)
            report_dataframe.to_html(html_file)
            self.generate_graphs(report_file, element_dict)
        else:
            logging.debug('No previous file exists : report.csv')

    def generate_graphs(self, report_file, element_dict={}):
        """
        For generating the graphs file in the .png format
        :param report_file: CSV report file with all the workload result
        :param element_dict: dictionary object with current workload details
            eg:element_dict = {'READ': ['100r']}
        :return: None
        """
        # element_dict = {'READ': ['100r'], 'WRITE': ['100w'], 'MIXED': ['50r50w', '25r75w', '75r25w']}
        df = pd.read_csv(report_file, header=0)
        width = 0.25
        fail_build_id = []
        # Filtering the failed data from the existing dataframe
        for row in df.values:
            row_ls = row.tolist()
            if 'terminated' in row_ls or 'aborted' in row_ls:
                fail_build_id.append(row_ls[-1])
        fail_build_id = (set(fail_build_id))
        indexNames = df[(df['BuildVersion'].isin(fail_build_id))].index
        df.drop(indexNames, inplace=True)

        for work_label, values in element_dict.items():
            build_ver_data = []
            logging.debug('Generating graph for the workload {}'.format(work_label))
            if work_label == 'MIXED':
                for wtype in values:
                    fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3, figsize=(11, 9))
                    fig.subplots_adjust(left=0.115, right=0.88)
                    logging.debug('Creating the graph for work load type {}'.format(wtype))
                    bandwidth, response_time, throughput = [], [], []
                    new_df = df[df['Workload-Read/Write'].isin([wtype])]
                    for row in new_df.values:
                        y_row = row.tolist()
                        build_id = y_row[-1]
                        if build_id not in build_ver_data:
                             build_ver_data.append(build_id)
                        bandwidth.append(y_row[7])
                        response_time.append(y_row[5])
                        throughput.append(y_row[6])

                    x = np.arange(len(build_ver_data))
                    y_read_bandwidth, y_write_bandwidth = bandwidth[::2], bandwidth[1::2]
                    y_read_response_time, y_write_response_time = response_time[::2], response_time[1::2]
                    y_read_throughput, y_write_throughput = throughput[::2], throughput[1::2]

                    ax1.bar(x, y_read_bandwidth, width, color='brown', label='read')
                    ax1.bar(x+width, y_write_bandwidth, width, color='green', label='write')
                    ax2.bar(x, y_read_response_time, width, color='brown', label='read')
                    ax2.bar(x+width, y_write_response_time, width, color='green', label='write')
                    ax3.bar(x, y_read_throughput, width, color='brown', label='read')
                    ax3.bar(x+width, y_write_throughput, width, color='green', label='write')

                    ax1.legend()
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(build_ver_data)
                    ax1.set_title('Bandwidth - {}-{}'.format(work_label, wtype, wtype))
                    ax1.set_xlabel('Build Version -->')
                    ax1.set_ylabel('Bandwidth  Bits/Sec')
                    ax2.legend()
                    ax2.set_xticks(x)
                    ax2.set_xticklabels(build_ver_data)
                    ax2.set_title('ResponseTime - {}-{}'.format(work_label, wtype))
                    ax2.set_xlabel('Build Version -->')
                    ax2.set_ylabel('ResponseTime  msec')
                    ax3.legend()
                    ax3.set_xticks(x)
                    ax3.set_xticklabels(build_ver_data)
                    ax3.set_title('ThroughPut - {}-{}'.format(work_label, wtype))
                    ax3.set_xlabel('Build Version -->')
                    ax3.set_ylabel('ThroughPut OP/S')

                    plt.tight_layout()
                    g_filename = work_label + '_{}_workload.png'.format(wtype)
                    plt.savefig(g_filename, format='png')

            else:
                bandwidth, response_time, throughput = [], [], []
                new_df = df[df['Workload-Read/Write'].isin(values)]
                fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3, figsize=(11, 9))
                fig.subplots_adjust(left=0.115, right=0.88)
                build_ver_data = []

                for row in new_df.values:
                    y_row = row.tolist()
                    build_id = y_row[-1]
                    if build_id not in build_ver_data:
                        build_ver_data.append(build_id)
                    bandwidth.append(y_row[7])
                    response_time.append(y_row[5])
                    throughput.append(y_row[6])

                ax1.bar(build_ver_data, bandwidth,  width, color='blue', label='Bandwidth')
                ax2.bar(build_ver_data, response_time, width, color='purple', label='Response Time')
                ax3.bar(build_ver_data, throughput, width, color='green', label='ThroughPut')

                ax1.set_title('Bandwidth - {}'.format(work_label))
                ax1.set_xlabel('Build Version -->')
                ax1.set_ylabel('Bandwidth  Bits/Sec')
                ax2.set_title('ResponseTime - {}'.format(work_label))
                ax2.set_xlabel('Build Version -->')
                ax2.set_ylabel('ResponseTime  msec')
                ax3.set_title('ThroughPut - {}'.format(work_label))
                ax3.set_xlabel('Build Version -->')
                ax3.set_ylabel('ThroughPut op/s')

                plt.tight_layout()
                g_filename = work_label + '_workload.png'
                plt.savefig(g_filename, format='png')


def main():
    # Reading the arguments from CLI
    args = get_args()
    config_file = 'config.ini'
    config = configparser.ConfigParser()
    config.read(config_file)

    workeropt = args.workers
    bucketopt = args.objects
    objsizeopt = args.objSize
    duration = args.runtime
    workloadtype = args.workloadType
    objects = args.objects
    install_flag = args.install
    build_ver = args.buildver
    accesskey_args = args.accesskey
    secretkey_args = args.secretkey
    enpoint_args = args.endpoint
    label = 's3setup'

    # Reading the config file
    controller_ip = config['DEFAULT']['controller_ip'].split(',')[0].strip()
    access_key = accesskey_args if accesskey_args else config.get('AWSCREDENTIALS', 'access_key')
    secret_key = secretkey_args if secretkey_args else config.get('AWSCREDENTIALS', 'secret_key')
    s3_endpoint = enpoint_args if enpoint_args else config.get('AWSCREDENTIALS', 's3_endpoint')
    cosperf = CosbenchPerf(controller_ip)
    host_lst = []
    # Installing the keys on all the nodes
    if install_flag:
        logging.debug('Checking pre-requisite packages installed on the driver and controller nodes')
        logging.debug('Starting the installation of public keys on all the nodes')
        sshkey_gen = "ssh-keygen -f $HOME/.ssh/id_rsa -t rsa -N ''"
        cosperf.exec_cmd(sshkey_gen)
        time.sleep(4)
        pub_key = open(os.path.expanduser('~/.ssh/id_rsa.pub')).read()
        for (host_tag, val) in config.items('DEFAULT'):
            logging.debug('Installing keys on : {}'.format(host_tag))
            host, username, password = (item.strip() for item in val.split(','))
            host_lst.append(host)
            logging.debug('Checking pre-requisite packages installed on the driver and controller nodes')
            package_list = cosperf.check_packages(host, username, password)
            logging.debug('Installing keys on : {}'.format(host_tag))
            cosperf.install_keys(pub_key, host, username, password, package_list)
            # Enabling the ports
            if 'driver' in host_tag:
                logging.debug('Enabling port on the driver node')
                cosperf.enable_ports(host, username, password, drivere_flag=True)
            else:
                logging.debug('Enabling port on the controller node')
                cosperf.enable_ports(host, username, password, drivere_flag=False)
        # Start the installation and configuration of hosts
        cosperf.install_configure(host_lst)
        logging.debug('Cosbench installation and configuration done on all the nodes...wait for 10secs to start')
        time.sleep(10)
    setup_file = cosperf.start_cosbench(access_key, secret_key, label, s3_endpoint)
    # Start Workload Execution
    logging.debug('\n****Workload Profile is ****')
    prop_ls, runtime = cosperf.create_workload_profile(objsizeopt, workeropt, bucketopt, workloadtype, duration, objects, config)
    # logging.debug the values to used for the workload
    for prop_file in prop_ls:
        with open(prop_file, 'r') as fp:
            lines = [line.strip() for line in fp.readlines()]
            logging.debug('\n'.join(lines))
        workload_id = cosperf.start_workload(setup_file, prop_file)
        cosperf.capture_result(workload_id, runtime, build_ver)
    logging.debug('Completed running the workload run')


if __name__ == "__main__":
    main()
