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

"""
Setup file for client configuration for executing the R2 regression.
"""

import os
import logging
import json
import shutil
import configparser
from zipfile import ZipFile
from commons.helpers.node_helper import Node
from commons.utils import system_utils as sysutils

# Global Constants
config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
LOGGER = logging.getLogger(__name__)

def create_db_entry(hostname, username, password, ip_addr,
                    admin_user, admin_passwd, public_ip, private_ip):
    """
    Creation of new host entry in database.
    :param str hostname: hostname of the node
    :param str username: username of the node
    :param str password: password of the node
    :param str ip_addr: management IP for the node
    :param str admin_user: admin user for cortxcli
    :param str admin_passwd: admin password for cortxcli
    :param str public_ip: public data IP
    :param str private_ip: private data IP
    :return: none
    """
    json_file = config['default']['setup_entry_json']
    new_setupname = os.getenv("Target_Node")
    LOGGER.info("Creating DB entry for setup: {}".format(new_setupname))
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    json_data["setupname"] = new_setupname
    nodes = list()
    node_info = {
        "host": "srvnode-1",
        "hostname": hostname,
        "ip": ip_addr,
        "username": username,
        "password": password,
        "public_data_ip": public_ip,
        "private_data_ip": private_ip,
        "mgmt_ip": ip_addr
    }
    nodes.append(node_info)

    json_data["nodes"] = nodes
    json_data["csm"]["mgmt_vip"] = ip_addr
    json_data["csm"]["csm_admin_user"].update(
        username=admin_user, password=admin_passwd)

    LOGGER.info("new file data: {}".format(json_data))
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

    return new_setupname


def set_s3_endpoints(cluster_ip):
    """
    Set s3 endpoints to cluster ip in /etc/hosts
    :param str cluster_ip: IP of the cluster
    :return: None
    """
    # Removing contents of /etc/hosts file and writing new contents
    print("Setting s3 endpoints on client.")
    sysutils.execute_cmd(cmd="rm -f /etc/hosts")
    with open("/etc/hosts", 'w') as file:
        file.write("127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n")
        file.write("::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n")
        file.write("{} s3.seagate.com sts.seagate.com iam.seagate.com sts.cloud.seagate.com\n"
                   .format(cluster_ip))


def setup_chrome():
    """
    Method to install chrome and chromedriver
    :return: none
    """
    cmd = "wget -N https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"
    sysutils.execute_cmd(cmd=cmd)
    sysutils.execute_cmd(cmd="yum install -y google-chrome-stable_current_x86_64.rpm")
    cm = "wget -N https://chromedriver.storage.googleapis.com/91.0.4472.19/chromedriver_linux64.zip"
    sysutils.execute_cmd(cmd=cm)
    with ZipFile('chromedriver_linux64.zip', 'r') as zipObj:
        # Extract all the contents of zip file in current directory
        zipObj.extractall()
    os.chmod("chromedriver", 0o700)
    bin_path = os.path.join("venv", "bin")
    shutil.copy("chromedriver", bin_path)


def configure_server_node(obj, mg_ip):
    """
    Method to configure server node for firewall and haproxy
    :return: None
    """
    # Stopping/disabling firewalld service on node for tests
    print("Doing server side settings for firewalld and haproxy.")
    cmd = "systemctl stop firewalld"
    obj.execute_cmd(cmd, read_lines=True)
    cmd = "systemctl disable firewalld"
    obj.execute_cmd(cmd, read_lines=True)
    # Doing changes in haproxy file and restarting it
    remote_path = "/etc/haproxy/haproxy.cfg"
    local_path = "/tmp/haproxy.cfg"
    if os.path.exists(local_path):
        sysutils.execute_cmd("rm -f {}".format(local_path))
    obj.copy_file_to_local(remote_path=remote_path, local_path=local_path)
    line_src = "option forwardfor"
    with open(local_path) as file:
        for num, line in enumerate(file, 1):
            if line_src in line:
                indx = num
    with open(local_path, 'r') as file:
        read_file = file.readlines()
    read_file.insert(indx - 2, "    bind {}:80\n".format(mg_ip))
    read_file.insert(indx - 1, "    bind {}:443 ssl crt /etc/ssl/stx/stx.pem\n".format(mg_ip))

    with open(local_path, 'w') as file:
        read_file = "".join(read_file)
        file.write(read_file)
    obj.copy_file_to_remote(local_path=local_path, remote_path=remote_path)
    cmd = "systemctl restart haproxy"
    obj.execute_cmd(cmd, read_lines=True)


def main():
    host = os.getenv("HOSTNAME")
    uname = "root"
    host_passwd = os.getenv("HOST_PASS")
    admin_user = os.getenv("ADMIN_USR")
    admin_passwd = os.getenv("ADMIN_PWD")
    nd_obj_host = Node(hostname=host, username=uname, password=host_passwd)
    # Get the cluster and mgnt IPs
    cmd = "cat /etc/hosts"
    output = nd_obj_host.execute_cmd(cmd, read_lines=True)
    for line in output:
        if "srvnode-1.mgmt.public" in line:
            mgmnt_ip = line.split( )[0]
        if "srvnode-1.data.public" in line:
            clstr_ip = line.split( )[0]
        if "srvnode-1.data.private" in line:
            private_ip = line.split( )[0]
    os.environ["CLUSTR_IP"] = clstr_ip
    os.environ["CSM_MGMT_IP"] = mgmnt_ip
    sysutils.execute_cmd("mkdir -p /etc/ssl/stx-s3-clients/s3/")
    remote_path= "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
    local_path= "/etc/ssl/stx-s3-clients/s3/ca.crt"
    if os.path.exists(local_path):
        sysutils.execute_cmd("rm -f {}".format(local_path))
    nd_obj_host.copy_file_to_local(remote_path=remote_path, local_path=local_path)
    set_s3_endpoints(clstr_ip)
    setupname = create_db_entry(host, uname, host_passwd, mgmnt_ip,
                                admin_user, admin_passwd, clstr_ip, private_ip)
    sysutils.execute_cmd("cp /root/secrets.json .")
    with open("/root/secrets.json", 'r') as file:
        json_data = json.load(file)
    output = sysutils.execute_cmd("python3.7 tools/setup_update/setup_entry.py "
                     "--dbuser {} --dbpassword {}".format(json_data['DB_USER'], json_data['DB_PASSWORD']))
    if "Entry already exits" in str(output):
        print("DB already exists for target: {}, so will update it.".format(setupname))
        sysutils.execute_cmd("python3.7 tools/setup_update/setup_entry.py "
                "--dbuser {} --dbpassword {} --new_entry False".format(json_data['DB_USER'], json_data['DB_PASSWORD']))
    os.environ["TARGET"] = setupname
    print("Setting up chrome")
    setup_chrome()
    configure_server_node(nd_obj_host, clstr_ip)


if __name__ == "__main__":
    main()
