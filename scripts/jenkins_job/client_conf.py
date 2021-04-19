#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""
Setup file for client configuration for executing the R2 regression.
"""

import os
import logging
import json
import subprocess
import shutil
from zipfile import ZipFile
from commons.helpers.node_helper import Node


# Global Constants
LOGGER = logging.getLogger(__name__)

def run_cmd(cmd):
    """
    Execute bash commands on the host
    :param str cmd: command to be executed
    :return: command output
    :rtype:
    """
    print("Executing command: {}".format(cmd))
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    result = str(proc.communicate())
    #print("output = {}".format(result))
    return result

def create_db_entry(hostname, username, password, ip_addr):
    """
    Creation of new host entry in database.
    """
    json_file = "tools/setup_update/setup_entry.json"
    new_setupname = hostname.split(".")[0]
    LOGGER.info("Creating DB entry for setup: {}".format(new_setupname))

    with open(json_file, 'r') as file:
        json_data = json.load(file)

    for item in json_data:
        if item == "setupname":
           json_data[item] = new_setupname
    json_data_nodes = json_data["nodes"]
    for item in json_data_nodes:
        if item['host'] == "eos-node-0":
            item['host'] = "eosnode-1"
        if item['hostname'] == "node 0 hostname":
            item['hostname'] = hostname
        if item['username'] == "node 0 username":
            item['username'] = username
        if item['password'] == "node 0 password":
            item['password'] = password
        if item['ip'] == "node 0 ip":
            item['ip'] = ip_addr

    print("new file data: {}".format(json_data))
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

def set_s3_endpoints(cluster_ip):
    """
    Set s3 endpoints to cluster ip in /etc/hosts
    :return: None
    """
    with open("/etc/hosts", 'r+') as fp:
        for line in fp:
            if cluster_ip in line:
                if "s3.seagate.com iam.seagate.com" in line:
                    break
                else:
                    fp.write("{} s3.seagate.com iam.seagate.com".format(cluster_ip))
                    break
        else:
            fp.write("{} s3.seagate.com iam.seagate.com".format(cluster_ip))

def setup_chrome():
    """
    Method to install chrome and chromedriver
    :return:
    """
    run_cmd(cmd="wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm")
    run_cmd(cmd="yum install -y google-chrome-stable_current_x86_64.rpm")
    run_cmd(cmd="wget https://chromedriver.storage.googleapis.com/89.0.4389.23/chromedriver_linux64.zip")
    with ZipFile('chromedriver_linux64.zip', 'r') as zipObj:
        # Extract all the contents of zip file in current directory
        zipObj.extractall()
    os.chmod("chromedriver", 0o777)
    bin_path = os.path.join("venv", "bin")
    shutil.copy("chromedriver", bin_path)

def main():
    host = os.getenv("HOSTNAME")
    uname = "root"
    host_passwd = os.getenv("HOST_PASS")
    nd_obj_host = Node(hostname=host, username=uname, password=host_passwd)
    # Get the cluster and mgnt IPs
    cmd = "cat /etc/hosts"
    output = nd_obj_host.execute_cmd(cmd, read_lines=True)
    for line in output:
        if "srvnode-1.mgmt.public" in line:
            mgmnt_ip = line.split( )[0]
        if "srvnode-1.data.public" in line:
            clstr_ip = line.split( )[0]
    os.environ["CLUSTR_IP"] = clstr_ip
    os.environ["CSM_MGMT_IP"] = mgmnt_ip
    run_cmd("mkdir -p /etc/ssl/stx-s3-clients/s3/")
    remote_path= "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
    local_path= "/etc/ssl/stx-s3-clients/s3/ca.crt"
    if os.path.exists(local_path):
        run_cmd("rm -f {}".format(local_path))
    nd_obj_host.copy_file_to_local(remote_path=remote_path, local_path=local_path)
    set_s3_endpoints(clstr_ip)
    create_db_entry(host, uname, host_passwd, mgmnt_ip)
    run_cmd("python3.7 tools/setup_update/setup_entry.py "
            "--dbuser datawrite --dbpassword seagate@123")
    print("Setting up chrome")
    setup_chrome()
    run_cmd("cp /root/secrets.json .")

if __name__ == "__main__":
    main()