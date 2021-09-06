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
import argparse
import time
from commons.helpers.node_helper import Node
from commons import commands as cmn_cmd


# Global Constants
CONFIG_FILE = 'scripts/jenkins_job/config.ini'
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)


def configure_k8s_repo(*hostname, username, password):
    """
    test configure repo
    """
    for host in hostname:
        nd_obj = Node(hostname=host, username=username, password=password)
        print("Disabling SELINUX \n")
        resp = nd_obj.execute_cmd(cmd="setenforce 0", read_lines=True, exc=False)
        if resp:
            print("The selinux is already disabled \n")
        cmd = "sed -i --follow-symlinks 's/SELINUX=enforcing/SELINUX=disabled/g'" \
              " /etc/sysconfig/selinux"
        print("Setting selinux 0 \n")
        nd_obj.execute_cmd(cmd=cmd, read_lines=False)
        print("Configuring the yum repo for k8s \n")
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
        print("Installing kubeadm \n")
        nd_obj.execute_cmd(cmd="yum install kubeadm docker -y", read_lines=True)
        print("enabling kubelet \n")
        nd_obj.execute_cmd(cmd="systemctl enable kubelet", read_lines=True)
        print("starting kubelet \n")
        nd_obj.execute_cmd(cmd="systemctl start kubelet", read_lines=True)
        print("enabling docker \n")
        nd_obj.execute_cmd(cmd="systemctl enable docker", read_lines=True)
        print("starting docker \n")
        nd_obj.execute_cmd(cmd="systemctl start docker", read_lines=True)
        print("Disabling the swap")
        nd_obj.execute_cmd(cmd="swapoff -a", read_lines=True)


def initialize_k8s(host, username, password):
    """
    Test function to initialize the kubeadm
    """
    nd_obj = Node(hostname=host, username=username, password=password)
    cmd = "kubeadm init"
    print("Initialize the kubeadm\n")
    result = nd_obj.execute_cmd(cmd=cmd, read_lines=True)
    out = str("".join(result[-2:]))
    out_list = "".join(out.split("\\")).split("--")
    join_cmd = [x.strip() for x in out_list]
    join_cmd = " --".join(join_cmd)
    print("The final o/p is %s", join_cmd)
    print("Creating the dir .kube")
    nd_obj.execute_cmd(cmd="mkdir -p $HOME/.kube", read_lines=False, exc=False)
    print("Copying file to the dir .kube")
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
    resp = nd_obj.execute_cmd(cmd="export kubever=$(kubectl version | base64 | tr -d '\n')"
                                  " && echo $kubever",
                              read_lines=True, exc=False)

    if resp[0]:
        cmd = "kubectl apply -f https://cloud.weave.works/k8s/net?k8s-version={}"\
            .format(resp[0])
        resp = nd_obj.execute_cmd(cmd=cmd, read_lines=False, exc=False)
        print("The o/p of network cmd is %s", resp)


def get_node_status(host, username, password):
    """
    This function fetches the node status
    """
    nd_obj = Node(hostname=host, username=username, password=password)
    count = 1
    while count <= 6:
        resp_node = nd_obj.execute_cmd(cmd="kubectl get nodes |cut -d ' ' -f 4",
                                       read_lines=False,
                                       exc=False)
        resp_node = resp_node.decode() if isinstance(resp_node, bytes) else resp_node
        nodes_status = resp_node.strip().split("\n")
        print("The output of get nodes is %s", nodes_status)
        if "Ready" in nodes_status:
            return nodes_status
        count += 1
        time.sleep(10)


def join_cluster(*hostname, username, password, cmd):
    """
    Test function to join the worker nodes to master node
    """
    for host in hostname[1:]:
        nd_obj = Node(hostname=host, username=username, password=password)
        resp = nd_obj.execute_cmd(cmd=cmd, read_lines=True)
        print("The join cmd o/p is %s", resp)


def main(args):
    """
    main function to deploy Kubernetes
    """
    k8s_input = dict()

    k8s_input['nodes'] = args.nodes
    k8s_input['hosts_ip'] = args.ip
    k8s_input['username'] = args.username
    k8s_input['password'] = args.password

    nodes = k8s_input['nodes']
    hosts_ip = k8s_input['hosts_ip']
    username = k8s_input['username']
    password = k8s_input['password']

    remote_hosts_org = CONFIG['default']['etc_host']
    local_copy_hosts = CONFIG['default']['etc_host_tmp']
    host_ip_dict = {}

    if not hosts_ip:
        for host in nodes:
            nd_obj = Node(hostname=host, username=username, password=password)
            result = nd_obj.execute_cmd(cmd="ifconfig eth0", read_lines=True)
            test_list = result[1].split(" ")
            test_list = [i for i in test_list if i]
            host_ip_n = {test_list[1]: host}
            host_ip_dict.update(host_ip_n)

    else:
        for node_ip, host in hosts_ip, nodes:
            host_ip_s = {node_ip: host}
            host_ip_dict.update(host_ip_s)

    for host in nodes:
        nd_obj = Node(hostname=host, username=username, password=password)
        nd_obj.copy_file_to_local(remote_hosts_org, local_copy_hosts)
        with open(local_copy_hosts, "a") as file:
            for key, value in host_ip_dict.items():
                line = " ".join([key, value])
                file.write(line)
                file.write("\n")
                nd_obj.execute_cmd(cmn_cmd.CMD_PING.format(key), read_lines=True)
        nd_obj.copy_file_to_remote(local_copy_hosts, remote_hosts_org)
    configure_k8s_repo(*nodes, username=username, password=password)
    result = initialize_k8s(nodes[0], username=username, password=password)
    print("The token is %s", result[1])
    create_network(nodes[0], username=username, password=password)
    status = get_node_status(nodes[0], username=username, password=password)
    print("The stat is %s", status)
    if "Ready" in status:
        print("Adding the worker node to master node")
        join_cluster(*nodes, username=username, password=password, cmd=result[1])
    status_all = get_node_status(nodes[0], username=username, password=password)
    if "NotReady" in status_all:
        print("Please check after some time,"
              "the nodes status is %s", status_all)
    print("Successfully deployed the k8s ,"
          "Please run \"kubectl get nodes cmd\"")


def parse_args():
    """
    parse user args
    """
    parser = argparse.ArgumentParser(
        description="Multinode server and k8s configuration")
    parser.add_argument("-nodes", "--nodes",
                        help="hostnames for each node", nargs="+")
    parser.add_argument("-username", "--username", type=str,
                        help="username for nodes", required=True)
    parser.add_argument("-password", "--password", type=str,
                        help="password for nodes", required=True)
    parser.add_argument("-IP", "--ip", help="IP for each node", nargs="+")

    return parser.parse_args()


if __name__ == '__main__':
    opts = parse_args()
    main(opts)
