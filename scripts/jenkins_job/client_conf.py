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
from commons.helpers.node_helper import Node


# Global Constants
LOGGER = logging.getLogger(__name__)

def create_db_entry(hostname, username, password):
    """
    Creation of new host entry in database.
    """
    json_file = "/root/SonalK/workspace/cortx-test/tools/setup_update/setup_entry.json"
    new_setupname = hostname.split(".")[0]
    new_setupname = new_setupname.append("RelSanity")
    old_setup_entry = "\"setupname\":\"T2\","
    new_setup_entry = "\"setupname\":\"{}\","
    old_host_entry = "\"hostname\": \"node 0 hostname\","
    new_host_entry = "\"hostname\": \"{}\","
    old_host_user = "\"username\": \"node 0 username\","
    new_host_user = "\"username\": \"{}\","
    old_host_passwd = "\"password\": \"node 0 password\""
    new_host_passwd = "\"password\": \"{}\""

    with open(json_file, 'r+') as file:
        newlines = []
        for line in file.readlines():
            if old_setup_entry in line:
                newlines.append(line.replace(old_setup_entry, new_setup_entry).format(new_setupname))
            if old_host_entry in line:
                newlines.append(line.replace(old_host_entry, new_host_entry).format(hostname))
            if old_host_user in line:
                newlines.append(line.replace(old_host_user, new_host_user).format(username))
            if old_host_passwd in line:
                newlines.append(line.replace(old_host_passwd, new_host_passwd).format(password))
    with open(json_file, "w") as file:
        for line in newlines:
            file.writelines(line)


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



def main():
    host = os.getenv("HOSTNAME")
    client = "ssc-vm-3053.colo.seagate.com"
    uname = "root"
    host_passwd = os.getenv("HOST_PASS")
    client_passwd = "seagate"
    nd_obj_host = Node(hostname=host, username=uname, password=host_passwd)
    nd_obj_client = Node(hostname=client, username=uname, password=client_passwd)
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
    cmd = "mkdir -p /etc/ssl/stx-s3-clients/s3/"
    nd_obj_client.execute_cmd(cmd, read_lines=True)
    remote_path= "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
    local_path= "/etc/ssl/stx-s3-clients/s3/"
    if not os.path.exists("/etc/ssl/stx-s3-clients/s3/ca.crt"):
        nd_obj_host.copy_file_to_local(remote_path=remote_path, local_path=local_path)
    set_s3_endpoints(clstr_ip)
    create_db_entry(host, uname, host_passwd)
    cmd = "python3.7 tools/setup_update/setup_entry.py --dbuser datawrite --dbpassword seagate@123"
    nd_obj_client.execute_cmd(cmd, read_lines=True)
    cur_dir = os.getcwd()
    virtual_env = "venv"
    cmd = "sh scripts/jenkins_job/virt_env_setup.sh {} {}".format(cur_dir, virtual_env)
    nd_obj_client.execute_cmd(cmd, read_lines=True)

if __name__ == "__main__":
    main()