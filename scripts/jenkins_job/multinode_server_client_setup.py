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
import json
import logging
import argparse
from scripts.jenkins_job import client_conf
from commons.helpers.node_helper import Node

LOGGER = logging.getLogger(__name__)


def create_db_entry(
    *hostname,
    username: str,
    password: str,
    mgmt_vip: str,
    admin_user: str,
        admin_passwd: str) -> str:
    """
    Creation of new host entry in database.
    :param str hostname: hostnames of all the nodes
    :param str username: username of nodes
    :param str password: password of nodes
    :param str mgmt_vip: csm mgmt vip
    :param str admin_user: admin user for cortxcli
    :param str admin_passwd: admin password for cortxcli
    :return: Target name
    """
    json_file = "setup_entry.json"
    new_setupname = hostname[0].split(".")[0]
    LOGGER.info("Creating DB entry for setup: {}".format(new_setupname))
    with open(json_file, 'r') as file:
        json_data = json.load(file)

    json_data["setupname"] = new_setupname
    nodes = list()
    node_info = {
        "host": "srv-node-1",
        "hostname": "node 1 hostname",
        "ip": "node 1 ip address",
        "username": "node 1 username",
        "password": "node 1 password",
        "public_data_ip": "",
        "private_data_ip": "",
        "mgmt_ip": ""
    }
    for count, host in enumerate(hostname, start=1):
        node = dict()
        node_info["host"] = f"srvnode-{count}"
        node_info["hostname"] = host
        node_info["username"] = username
        node_info["password"] = password
        node.update(node_info)
        nodes.append(node)

    json_data["nodes"] = nodes
    json_data["csm"]["mgmt_vip"] = mgmt_vip
    json_data["csm"]["csm_admin_user"].update(
        username=admin_user, password=admin_passwd)

    print("new file data: {}".format(json_data))
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

    return new_setupname


def configure_haproxy_lb(*hostname, username: str, password: str):
    """
    Configure haproxy as Load Balancer on server
    :param str hostname: hostnames of all the nodes
    :param str username: username of nodes
    :param str password: password of nodes
    :return: None
    """
    instance_per_node = 1
    server_haproxy_cfg = "/etc/haproxy/haproxy.cfg"
    local_haproxy_cfg = "/tmp/haproxy.cfg"
    s3instance = "    server s3-instance-{0} srvnode-{1}.data.private:2808{2} check maxconn 110\n"
    authinstance = "    server s3authserver-instance1 srvnode-{0}.data.private:28050\n"
    total_s3_instances = list()
    total_auth_instances = list()
    for node in range(len(hostname)):
        for i in range(instance_per_node):
            total_s3_instances.append(s3instance.format(i, node, i))
        total_auth_instances.append(authinstance.format(node))
    LOGGER.debug(total_s3_instances)
    LOGGER.debug(total_auth_instances)

    for host in hostname:
        LOGGER.info("Updating s3 instances in haproxy.cfg on node: %s", host)
        nd_obj = Node(hostname=host, username=username, password=password)
        nd_obj.copy_file_to_local(server_haproxy_cfg, local_haproxy_cfg)
        with open(local_haproxy_cfg, "r") as f:
            data = f.readlines()
        with open(local_haproxy_cfg, "w") as f:
            for line in data:
                if "server s3-instance-" in line:
                    line = "".join(["#", line] + total_s3_instances)
                elif "server s3authserver-instance" in line:
                    line = "".join(["#", line] + total_auth_instances)
                f.write(line)
        nd_obj.copy_file_to_remote(local_haproxy_cfg, server_haproxy_cfg)
    LOGGER.info("Configured s3 instances in haproxy.cfg on all the nodes")

def main():
    parser = argparse.ArgumentParser(
        description="Multinode server and client configuration for executing the R2 regression")
    parser.add_argument("nodes", help="hostnames for each node", nargs="+")
    parser.add_argument("--password", help="password for nodes", required=True)
    parser.add_argument("--mgmt_vip", help="csm mgmt vip", required=True)
    args = parser.parse_args()
    print(args.nodes)
    nodes = args.nodes
    username = "root"

    nd_obj_host = Node(
        hostname=nodes[0],
        username="root",
        password=args.password)
    # Get the cluster IP
    output = nd_obj_host.execute_cmd("cat /etc/hosts", read_lines=True)
    for line in output:
        if "srvnode-1.data.public" in line:
            clstr_ip = line.split()[0]
    client_conf.set_s3_endpoints(clstr_ip)

    client_conf.run_cmd("mkdir -p /etc/ssl/stx-s3-clients/s3/")
    remote_crt_path = "/opt/seagate/cortx/provisioner/srv/components/s3clients/files/ca.crt"
    local_crt_path = "/etc/ssl/stx-s3-clients/s3/ca.crt"
    if os.path.exists(local_crt_path):
        client_conf.run_cmd("rm -f {}".format(local_crt_path))
    nd_obj_host.copy_file_to_local(
        remote_path=remote_crt_path,
        local_path=local_crt_path)

    setupname = create_db_entry(
        *nodes,
        username=username,
        password=args.password,
        mgmt_vip=args.mgmt_vip,
        admin_user="admin",
        admin_passwd="seagate@1")
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


if __name__ == "__main__":
    main()
