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
Setup file for multinode server and client configuration for executing
the sanity in K8s environment.
"""
import argparse
import configparser
import json
import logging
import os

from commons import commands as com_cmds
from commons import constants as const
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils as sysutils
from commons.utils import ext_lbconfig_utils as ext_lb

CONF_FILE = 'scripts/cicd_k8s/config.ini'
config = configparser.ConfigParser()
config.read(CONF_FILE)
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-arguments
# pylint: disable-msg=too-many-locals
def create_db_entry(m_node, username: str, password: str,
                    admin_user: str, admin_passwd: str, ext_ip) -> str:
    """
    Creation of new host entry in database.
    :param str m_node: hostname of master node
    :param str username: username of nodes
    :param str password: password of nodes
    :param str admin_user: admin user for cortxcli
    :param str admin_passwd: admin password for cortxcli
    :param str ext_ip: external LB IP
    :return: Target name
    """
    host_list = list()
    host_list.append(m_node)
    json_file = config['default']['setup_entry_json']
    new_setupname = os.getenv("Target_Node")
    node_obj = LogicalNode(hostname=m_node, username=username, password=password)
    mgnt_resp = node_obj.execute_cmd(com_cmds.K8S_GET_MGNT, read_lines=True)
    for line in mgnt_resp:
        if "cortx-control" in line:
            mgmt_vip = line.split()[6]
    print("Cortx control pod running on: ", mgmt_vip)
    output_node = node_obj.execute_cmd(com_cmds.CMD_GET_NODE, read_lines=True)
    for line in output_node:
        if "worker" in line:
            out = line.split()[0]
            host_list.append(out)
    num_nodes = len(host_list) - 1
    print("Total number of nodes in cluster: ", num_nodes)
    print("Creating DB entry for setup: ", new_setupname)
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    json_data["setupname"] = new_setupname
    json_data["product_family"] = "LC"
    json_data["product_type"] = "k8s"
    json_data["lb"] = ext_ip
    json_data["s3_engine"] = 2
    nodes = list()
    node_info = {
        "host": "srv-node-1",
        "hostname": "node 1 hostname",
        "username": "node 1 username",
        "password": "node 1 password",
    }
    for count, host in enumerate(host_list, start=1):
        node = dict()
        node_info["host"] = f"srvnode-{count}"
        node_info["hostname"] = host
        node_info["username"] = username
        node_info["password"] = password
        if count == 1:
            node_info["node_type"] = "master"
        else:
            node_info["node_type"] = "worker"
        node.update(node_info)
        nodes.append(node)

    json_data["nodes"] = nodes
    json_data["csm"]["mgmt_vip"] = mgmt_vip
    json_data["csm"]["csm_admin_user"].update(
        username=admin_user, password=admin_passwd)

    print("new file data: ", json_data)
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

    return new_setupname


def main():
    """
    Main Function.
    """
    parser = argparse.ArgumentParser(
        description="Multinode server and client configuration for executing the R2 regression")
    parser.add_argument("--master_node", help="Hostname for master node", required=True)
    parser.add_argument("--password", help="password for nodes", required=True)
    args = parser.parse_args()
    master_node = args.master_node
    username = "root"
    admin_user = os.getenv("ADMIN_USR")
    admin_passwd = os.getenv("ADMIN_PWD")
    ext_node = os.getenv("EXTERNAL_EXPOSURE_SERVICE")
    print("ext_node: ", ext_node)
    node_obj = LogicalNode(hostname=master_node, username=username, password=args.password)
    iface = config['interface']['centos_vm']
    if ext_node == "NodePort":
        resp = ext_lb.configure_nodeport_lb(node_obj, iface)
        if not resp[0]:
            print("Did not get expected response: {}".format(resp))
        ext_port_ip = resp[1]
        port = resp[2]
        ext_ip = "{}:{}".format(ext_port_ip, port)
        print("External LB value, ip and port will be: {}".format(ext_ip))
    elif ext_node == "LoadBalancer":
        resp = sysutils.execute_cmd(cmd=com_cmds.CMD_GET_IP_IFACE.format(iface))
        ext_ip = resp[1].strip("'\\n'b'")
        print("External LB IP: {}".format(ext_ip))
        print("Creating haproxy.cfg for {} Node setup".format(args.master_node))
        haproxy_cfg = config['default']['haproxy_config']
        ext_lb.configure_haproxy_rgwlb(
            master_node, username=username, password=args.password, ext_ip=ext_ip, iface=iface)
        with open(haproxy_cfg, 'r') as f_read:
            print((45 * "*" + "haproxy.cfg" + 45 * "*" + "\n"))
            print(f_read.read())
            print((100 * "*" + "\n"))

    setupname = create_db_entry(master_node, username=username, password=args.password,
                                admin_user=admin_user, admin_passwd=admin_passwd,
                                ext_ip=ext_ip)
    print("target_name: {}".format(setupname))
    sysutils.execute_cmd(cmd="cp /root/secrets.json .")
    with open("/root/secrets.json", 'r') as file:
        json_data = json.load(file)
    output = sysutils.run_local_cmd("python3.7 tools/setup_update/setup_entry.py --fpath {} "
        "--dbuser {} --dbpassword {}".format(config['default']['setup_entry_json'],
                    json_data['DB_USER'], json_data['DB_PASSWORD']), flg=True)
    print("Output for DB entry: ", output)
    if "Entry already exits" in str(output):
        print("DB already exists for target: %s, so will update it.", setupname)
        out = sysutils.run_local_cmd("python3.7 tools/setup_update/setup_entry.py --fpath {} "
                                     "--dbuser {} --dbpassword {} --new_entry False"
                                     .format(config['default']['setup_entry_json'],
                                             json_data['DB_USER'], json_data['DB_PASSWORD']),
                                     flg=True)
        print("Output for updated DB entry: ", out)
    print("Creating new dir for kube config.")
    sysutils.execute_cmd(cmd="mkdir -p /root/.kube")
    print("Copying config from Master node.")
    local_conf = os.path.join("/root/.kube", "config")
    if os.path.exists(local_conf):
        os.remove(local_conf)
    resp = node_obj.copy_file_to_local(remote_path=local_conf, local_path=local_conf)
    if not resp[0]:
        print("Failed to copy config file, security tests might fail.")
    print("Listing contents of kube dir")
    resp = sysutils.execute_cmd(cmd="ls -l /root/.kube/")
    print(resp)
    print("Setting the current namespace")
    resp_ns = node_obj.execute_cmd(cmd=com_cmds.KUBECTL_SET_CONTEXT.format(const.NAMESPACE),
                                   read_lines=True)
    print(resp_ns)
    print("Mutlinode Server-Client Setup Done.")


if __name__ == "__main__":
    main()