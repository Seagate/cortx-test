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
Script to deploy k8s on VM
"""


import configparser
import logging
import argparse
import time
from commons import commands as common_cmds
from commons.helpers.node_helper import Node


# Global Constants
config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
LOGGER = logging.getLogger(__name__)
encoding = "utf-8"


def configure_k8s_repo(*hostname, username, password):
    """
    test configure repo
    """
    for host in hostname:
        nd_obj = Node(hostname=host, username=username, password=password)
        LOGGER.info("Disabling SELINUX \n")
        resp = nd_obj.execute_cmd(cmd="setenforce 0", read_lines=True, exc=False)
        if resp:
            LOGGER.info("The selinux is already disabled \n")
        cmd = "sed -i --follow-symlinks 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/sysconfig/selinux"
        LOGGER.info("Setting selinux 0 \n")
        nd_obj.execute_cmd(cmd=cmd, read_lines=False)
        LOGGER.info("Configuring the yum repo for k8s \n")
        cmd = "cat <<EOF > /etc/yum.repos.d/kubernetes.repo \n"\
              "[kubernetes]\n"\
              "name=Kubernetes\n"\
              "baseurl=https://packages.cloud.google.com/yum/repos/kubernetes-el7-x86_64 \n"\
              "enabled=1 \n"\
              "gpgcheck=1 \n"\
              "repo_gpgcheck=1 \n"\
              "gpgkey=https://packages.cloud.google.com/yum/doc/yum-key.gpg" \
              " https://packages.cloud.google.com/yum/doc/rpm-package-key.gpg \n"\
              "EOF"
        nd_obj.execute_cmd(cmd=cmd, read_lines=False)
        LOGGER.info("Installing kubeadm \n")
        nd_obj.execute_cmd(cmd="yum install kubeadm docker -y", read_lines=True)
        LOGGER.info("enabling kubelet \n")
        nd_obj.execute_cmd(cmd="systemctl enable kubelet", read_lines=True)
        LOGGER.info("starting kubelet \n")
        nd_obj.execute_cmd(cmd="systemctl start kubelet", read_lines=True)
        LOGGER.info("enabling docker \n")
        nd_obj.execute_cmd(cmd="systemctl enable docker", read_lines=True)
        LOGGER.info("starting docker \n")
        nd_obj.execute_cmd(cmd="systemctl start docker", read_lines=True)
        LOGGER.info("Disabling the swap")
        nd_obj.execute_cmd(cmd="swapoff -a", read_lines=True)


def initialize_k8s(host, username, password):
    """
    Test function to initialize the kubeadm
    """
    nd_obj = Node(hostname=host, username=username, password=password)
    cmd = "kubeadm init"
    LOGGER.info("Initialize the kubeadm\n")
    result = nd_obj.execute_cmd(cmd=cmd, read_lines=True)
    out = str("".join(result[-2:]))
    out_list = "".join(out.split("\\")).split("--")
    join_cmd = [x.strip() for x in out_list]
    join_cmd = " --".join(join_cmd)
    LOGGER.info("The final o/p is %s", join_cmd)
    LOGGER.info("Creating the dir .kube")
    nd_obj.execute_cmd(cmd="mkdir -p $HOME/.kube", read_lines=False, exc=False)
    LOGGER.info("Copying file to the dir .kube")
    nd_obj.execute_cmd(cmd="\\cp -i /etc/kubernetes/admin.conf $HOME/.kube/config",
                       read_lines=False, exc=False)
    nd_obj.execute_cmd(cmd="chown $(id -u):$(id -g) $HOME/.kube/config",
                       read_lines=False, exc=False)
    return True, join_cmd


def create_network(host, username, password):
    """
    Test function to create the pod network
    """
    nd_obj = Node(hostname=host, username=username, password=password)
    resp = nd_obj.execute_cmd(cmd="export kubever=$(kubectl version | base64 | tr -d '\n') && echo $kubever",
                              read_lines=True, exc=False)

    if resp[0]:
        cmd = "kubectl apply -f https://cloud.weave.works/k8s/net?k8s-version={}".format(resp[0])
        resp = nd_obj.execute_cmd(cmd=cmd, read_lines=False, exc=False)
        LOGGER.info("The o/p of network cmd is %s", resp)


def get_node_status(host, username, password):
    nd_obj = Node(hostname=host, username=username, password=password)
    count = 1
    while count <= 6:
        resp_node = nd_obj.execute_cmd(cmd="kubectl get nodes |cut -d ' ' -f 4",
                                       read_lines=False,
                                       exc=False)
        resp_node = resp_node.decode() if isinstance(resp_node, bytes) else resp_node
        nodes_status = resp_node.strip().split("\n")
        LOGGER.info("The output of get nodes is %s", nodes_status)
        if "NotReady" in nodes_status:
            count += 1
            time.sleep(10)
        return nodes_status


def join_cluster(*hostname, username, password, cmd):
    """
    Test function to join the worker nodes to master node
    """
    for host in hostname[1:]:
        nd_obj = Node(hostname=host, username=username, password=password)
        resp = nd_obj.execute_cmd(cmd=cmd, read_lines=True)
        LOGGER.info("The join cmd o/p is %s", resp)


def main(args):
    """
    main function to deploy Kubernetes
    """
    nodes = args.nodes
    hosts_ip = args.ip
    username = args.username
    password = args.password

    remote_hosts_org = config['default']['etc_host']
    local_copy_hosts = config['default']['etc_host_tmp']
    host_ip_dict = {}

    if not hosts_ip:
        for host in nodes:
            nd_obj = Node(hostname=host, username=username, password=password)
            result = nd_obj.execute_cmd(cmd="ifconfig eth0", read_lines=True)
            test_list = result[1].split(" ")
            test_list = [i for i in test_list if i]
            LOGGER.info(test_list[1])
            host_ip_n = {test_list[1]: host}
            host_ip_dict.update(host_ip_n)

    else:
        for ip, host in hosts_ip, nodes:
            host_ip_s = {ip: host}
            host_ip_dict.update(host_ip_s)

    for host in nodes:
        nd_obj = Node(hostname=host, username=username, password=password)
        nd_obj.copy_file_to_local(remote_hosts_org, local_copy_hosts)
        with open(local_copy_hosts, "a") as f:
            for key, value in host_ip_dict.items():
                line = " ".join([key, value])
                f.write(line)
                f.write("\n")
                nd_obj.execute_cmd(common_cmds.CMD_PING.format(key), read_lines=True)
        nd_obj.copy_file_to_remote(local_copy_hosts, remote_hosts_org)
    configure_k8s_repo(*nodes, username=username, password=password)
    result = initialize_k8s(nodes[0], username=username, password=password)
    LOGGER.info("The token is %s", result[1])
    create_network(nodes[0], username=username, password=password)
    status = get_node_status(nodes[0], username=username, password=password)
    LOGGER.info("The stat is %s", status)
    if "Ready" in status:
        LOGGER.info("Adding the worker node to master node")
        join_cluster(*nodes, username=username, password=password, cmd=result[1])
    status_all = get_node_status(nodes[0], username=username, password=password)
    if "NotReady" in status_all:
        LOGGER.info("Please check after some time, the nodes status is %s", status_all)
    LOGGER.info("Successfully deployed the k8s , Please run \"kubectl get nodes cmd\"")


def parse_args():
    """
    parse user args
    """
    parser = argparse.ArgumentParser(
        description="Multinode server and k8s configuration")
    parser.add_argument("-nodes", "--nodes", help="hostnames for each node", nargs="+")
    parser.add_argument("-username", "--username", type=str,
                        help="username for nodes", required=True)
    parser.add_argument("-password", "--password", type=str,
                        help="password for nodes", required=True)
    parser.add_argument("-IP", "--ip", help="IP for each node", nargs="+")

    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()
    main(opts)

