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
Setup file for multinode server and client configuration for executing the R2 regression.
"""
import os
import configparser
import json
import logging
import argparse
from scripts.jenkins_job import client_conf
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils as sysutils
from commons import commands as com_cmds

config_file = 'scripts/cicd_k8s/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
LOGGER = logging.getLogger(__name__)


def create_db_entry(
    m_node,
    username: str,
    password: str,
    mgmt_vip: str,
    admin_user: str,
    admin_passwd: str,
    node_obj) -> str:
    """
    Creation of new host entry in database.
    :param str hostname: hostnames of all the nodes
    :param str username: username of nodes
    :param str password: password of nodes
    :param str mgmt_vip: csm mgmt vip
    :param str admin_user: admin user for cortxcli
    :param str admin_passwd: admin password for cortxcli
    :param node_obj: node helper object to run cmd and get IPs
    :return: Target name
    """
    host_list = []
    host_list.append(m_node)
    json_file = config['default']['setup_entry_json']
    new_setupname = os.getenv("Target_Node")
    output_node = node_obj.execute_cmd(com_cmds.CMD_GET_NODE, read_lines=True)
    for line in output_node:
        if "worker" in line:
            out = line.split()[0]
            host_list.append(out)
    LOGGER.info("Creating DB entry for setup: {}".format(new_setupname))
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    json_data["setupname"] = new_setupname
    json_data["product_family"] = "LC"
    json_data["product_type"] = "k8s"
    json_data["lb"] = "ext LB IP" # TODO
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
        node.update(node_info)
        nodes.append(node)
        if count == 1:
            node_info["node_type"] = "master"
        else:
            node_info["node_type"] = "worker"

    json_data["nodes"] = nodes
    json_data["csm"]["mgmt_vip"] = mgmt_vip
    json_data["csm"]["csm_admin_user"].update(
        username=admin_user, password=admin_passwd)

    LOGGER.info("new file data: {}".format(json_data))
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

    return new_setupname

def main():
    parser = argparse.ArgumentParser(
        description="Multinode server and client configuration for executing the R2 regression")
    parser.add_argument("--master_node", help="Hostname for master node", nargs="+")
    parser.add_argument("--node_count", help="Number of nodes in cluster", required=True, type=int)
    parser.add_argument("--password", help="password for nodes", required=True)
    parser.add_argument("--mgmt_vip", help="csm mgmt vip", required=True)
    args = parser.parse_args()
    master_node = args.master_node
    node_count = args.node_count
    LOGGER.info("Total number of nodes in cluster: %s", node_count)
    username = "root"
    admin_user = os.getenv("ADMIN_USR")
    admin_passwd = os.getenv("ADMIN_PWD")

    nd_obj_host = LogicalNode(
        hostname=master_node,
        username=username,
        password=args.password)

    setupname = create_db_entry(
        master_node,
        username=username,
        password=args.password,
        mgmt_vip=args.mgmt_vip,
        admin_user=admin_user,
        admin_passwd=admin_passwd,
        node_obj=nd_obj_host)
    print("target_name: %s", setupname)
    client_conf.run_cmd("cp /root/secrets.json .")
    with open("/root/secrets.json", 'r') as file:
        json_data = json.load(file)
    output = client_conf.run_cmd(
        "python3.7 tools/setup_update/setup_entry.py "
        "--dbuser {} --dbpassword {}".format(
            json_data['DB_USER'],
            json_data['DB_PASSWORD']))
    if "Entry already exits" in str(output):
        print("DB already exists for target: {}, so will update it.".format(setupname))
        client_conf.run_cmd(
            "python3.7 tools/setup_update/setup_entry.py "
            "--dbuser {} --dbpassword {} --new_entry False".format(
                json_data['DB_USER'], json_data['DB_PASSWORD']))

    client_conf.setup_chrome()
    configure_haproxy_lb(*nodes, username=username, password=args.password)
    print("Mutlinode Server-Client Setup Done.")


if __name__ == "__main__":
    main()
