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
Setup file for multinode server and client configuration for executing the R2 regression.
"""
import os
import configparser
import json
import logging
import argparse
from scripts.jenkins_job import client_conf
from commons.helpers.node_helper import Node
from commons.utils import system_utils as sysutils

config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
LOGGER = logging.getLogger(__name__)


def create_db_entry(
    *hostname,
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
    json_file = config['default']['setup_entry_json']
    new_setupname = os.getenv("Target_Node")
    cmd = "cat /etc/hosts"
    output_host = node_obj.execute_cmd(cmd, read_lines=True)
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
        for line in output_host:
            if f"srvnode-{count}.mgmt.public" in line:
                node_info["ip"] = line.split()[0]
                node_info["mgmt_ip"] = line.split()[0]
            if f"srvnode-{count}.data.public" in line:
                node_info["public_data_ip"] = line.split()[0]
            if f"srvnode-{count}.data.private" in line:
                node_info["private_data_ip"] = line.split()[0]
        node.update(node_info)
        nodes.append(node)

    json_data["nodes"] = nodes
    json_data["csm"]["mgmt_vip"] = mgmt_vip
    json_data["csm"]["csm_admin_user"].update(
        username=admin_user, password=admin_passwd)

    LOGGER.info("new file data: {}".format(json_data))
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
    server_haproxy_cfg = config['default']['haproxy_config']
    local_haproxy_cfg = config['default']['tmp_haproxy_config']
    s3instance = "    server s3-instance-{0} srvnode-{1}.data.private:{2} check maxconn 110\n"
    authinstance = "    server s3authserver-instance{0} srvnode-{1}.data.private:28050\n"
    total_s3_instances = list()
    total_auth_instances = list()
    if os.path.exists(local_haproxy_cfg):
        cmd = "rm -f {}".format(local_haproxy_cfg)
        sysutils.run_local_cmd(cmd)
    for node in range(len(hostname)):
        start_inst = (node * instance_per_node)
        end_inst = ((node + 1) * instance_per_node)
        for i in range(start_inst, end_inst):
            port = "2807{}".format((i%instance_per_node)+1)
            total_s3_instances.append(s3instance.format(i+1, node+1, port))
        total_auth_instances.append(authinstance.format(node+1, node+1))
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
        cmd = "systemctl restart haproxy"
        nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("Restarted haproxy service")
    LOGGER.info("Configured s3 instances in haproxy.cfg on all the nodes")

def main():
    parser = argparse.ArgumentParser(
        description="Multinode server and client configuration for executing the R2 regression")
    parser.add_argument("nodes", help="hostnames for each node", nargs="+")
    parser.add_argument("--node_count", help="Number of nodes in cluster", required=True, type=int)
    parser.add_argument("--password", help="password for nodes", required=True)
    parser.add_argument("--mgmt_vip", help="csm mgmt vip", required=True)
    args = parser.parse_args()
    nodes = args.nodes
    node_count = args.node_count
    assert len(nodes) == node_count, "Number of nodes provided does not match with node_count"
    username = "root"
    admin_user = os.getenv("ADMIN_USR")
    admin_passwd = os.getenv("ADMIN_PWD")

    nd_obj_host = Node(
        hostname=nodes[0],
        username=username,
        password=args.password)
    # Get the cluster IP
    output = nd_obj_host.execute_cmd("cat /etc/hosts", read_lines=True)
    for line in output:
        if "srvnode-1.data.public" in line:
            clstr_ip = line.split()[0]
    client_conf.set_s3_endpoints(clstr_ip)

    remote_crt_path = config['default']['s3_crt_path']
    local_crt_path = config['default']['s3_crt_local']
    client_conf.run_cmd("mkdir -p {}".format(os.path.dirname(local_crt_path)))
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
