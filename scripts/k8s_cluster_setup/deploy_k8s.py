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
from __future__ import absolute_import
import argparse
import time
import json
import re
import configparser
from commons.helpers.pods_helper import LogicalNode
from commons import commands as cmn_cmd

# Global Constants
CONFIG_FILE = 'scripts/k8s_cluster_setup/config.ini'
CONFIG = configparser.ConfigParser()
CONFIG.read(CONFIG_FILE)
REMOTE_HOSTS_ORG = CONFIG['default']['etc_host']
LOCAL_COPY_HOSTS = CONFIG['default']['etc_host_tmp']
DAEMON_JSON_FILE = CONFIG['default']['daemon_json_file']
DAEMON_JSON_FILE_LOCAL = CONFIG['default']['daemon_json_file_tmp']


def install_docker(*hostname, username, password):
    """
    Function to install docker
    """
    for host in hostname:
        nd_obj = LogicalNode(hostname=host, username=username, password=password)
        print("Installing docker on host\n", host)
        cmd = "yum install -y yum-utils && " \
              "yum-config-manager -y" \
              " --add-repo https://download.docker.com/linux/centos/docker-ce.repo && " \
              "yum install -y docker-ce docker-ce-cli containerd.io"
        resp = nd_obj.execute_cmd(cmd=cmd, read_lines=True, exc=False)
        if resp:
            print("docker is Installed on host\n", host)
            print("enabling docker \n")
            nd_obj.execute_cmd(cmd="systemctl enable docker", read_lines=True)
            print("starting docker \n")
            nd_obj.execute_cmd(cmd="systemctl start docker", read_lines=True)


def configure_iptables(*hostname, username, password):
    """
    Configure iptables
    """
    for host in hostname:
        nd_obj = LogicalNode(hostname=host, username=username, password=password)
        print("Configuring iptables \n")
        cmd = "cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf\n"\
              "br_netfilter\n"\
              "EOF"
        cmd2 = "cat <<EOF > /etc/sysctl.d/k8s.conf\n"\
               "net.bridge.bridge-nf-call-ip6tables = 1\n"\
               "net.bridge.bridge-nf-call-iptables = 1\n"\
               "EOF"
        nd_obj.execute_cmd(cmd=cmd, read_lines=False)
        nd_obj.execute_cmd(cmd=cmd2, read_lines=False)


def create_daemon_file(*hostname, username, password):
    """
    Create file etc/docker/daemon.json
    """
    for host in hostname:
        nd_obj = LogicalNode(hostname=host, username=username, password=password)
        print("Creating daemon.json \n")

        daemon_json = {
            "exec-opts": ["native.cgroupdriver=systemd"]
        }
        json_object = json.dumps(daemon_json, indent=1)
        with open(DAEMON_JSON_FILE_LOCAL, "w") as outfile:
            outfile.write(json_object)
        nd_obj.copy_file_to_remote(DAEMON_JSON_FILE_LOCAL, DAEMON_JSON_FILE)
        print("restarting docker \n")
        nd_obj.execute_cmd(cmd="systemctl restart docker", read_lines=True)


def configure_k8s_repo(*hostname, username, password):
    """
    test configure repo
    """
    for host in hostname:
        nd_obj = LogicalNode(hostname=host, username=username, password=password)
        print("Disabling SELINUX \n")
        resp = nd_obj.execute_cmd(cmd="setenforce 0", read_lines=True, exc=False)
        if resp:
            print("The selinux is already disabled \n")
        cmd = "sed -i --follow-symlinks 's/SELINUX=enforcing/SELINUX=disabled/g'" \
              " /etc/sysconfig/selinux"
        print("Setting selinux 0 \n")
        nd_obj.execute_cmd(cmd=cmd, read_lines=False)
        print("Check firewall status\n")
        response = nd_obj.execute_cmd(cmd="systemctl status firewalld",
                                      read_lines=True, exc=False)
        response = response.decode() if isinstance(response, bytes) else response
        print("The firewall status is %s", response)
        if "inactive" in response:
            print("The Firewall is disabled \n")
        else:
            print("Disabling the firewall \n")
            nd_obj.execute_cmd(cmd="systemctl disable firewalld",
                               read_lines=True, exc=False)
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
        nd_obj.execute_cmd(cmd="yum install -y kubelet kubeadm kubectl", read_lines=True)
        print("enabling kubelet \n")
        nd_obj.execute_cmd(cmd="systemctl enable kubelet", read_lines=True)
        print("starting kubelet \n")
        nd_obj.execute_cmd(cmd="systemctl start kubelet", read_lines=True)
        print("Disabling the swap")
        nd_obj.execute_cmd(cmd="swapoff -a", read_lines=True)


def initialize_k8s(host, username, password):
    """
    Test function to initialize the kubeadm
    """
    nd_obj = LogicalNode(hostname=host, username=username, password=password)
    cmd = "kubeadm init --pod-network-cidr=192.168.0.0/16"
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
    nd_obj = LogicalNode(hostname=host, username=username, password=password)
    cmd = "curl https://docs.projectcalico.org/manifests/calico.yaml -O &&"\
          "kubectl apply -f calico.yaml"
    resp = nd_obj.execute_cmd(cmd=cmd, read_lines=True, exc=False)
    print("The o/p of network cmd is %s", resp)


def get_node_status(host, username, password):
    """
    This function fetches the node status
    """
    nd_obj = LogicalNode(hostname=host, username=username, password=password)
    count = 1
    while count <= 6:
        resp_node = nd_obj.execute_cmd(cmd="kubectl get nodes |cut -d ' ' -f 4",
                                       read_lines=False,
                                       exc=False)
        resp_node = resp_node.decode() if isinstance(resp_node, bytes) else resp_node
        nodes_status = resp_node.strip().split("\n")
        print("The output of get nodes is %s", nodes_status)
        status = all(element == "Ready" for element in nodes_status)
        if status:
            return nodes_status
        count += 1
        time.sleep(10)
        if "NotReady" in nodes_status:
            cmd = "kubectl get pods -n kube-system"
            result = nd_obj.execute_cmd(cmd=cmd, read_lines=True, exc=True)
            for res in result:
                print(res.strip())
                if re.search(r'ImagePullBackOff', res):
                    return nodes_status


def troubleshoot(*hostname, username, password, status):
    """
    This Functions troubleshoots the calico issue
    """
    if "NotReady" in status:
        for host in hostname:
            nd_obj = LogicalNode(hostname=host, username=username, password=password)
            cmd = "wget https://github.com/projectcalico/calico/releases/" \
                  "download/v3.20.0/release-v3.20.0.tgz && "\
                  "tar -xvf release-v3.20.0.tgz && "\
                  "cd release-v3.20.0/images && "\
                  "docker load -i calico-node.tar && "\
                  "docker load -i calico-kube-controllers.tar && "\
                  "docker load -i calico-cni.tar && "\
                  "docker load -i calico-pod2daemon-flexvol.tar \n"
            result = nd_obj.execute_cmd(cmd=cmd, read_lines=True, exc=False)
            print("The result is", result)


def join_cluster(*hostname, username, password, cmd):
    """
    Test function to join the worker nodes to master node
    """
    for host in hostname[1:]:
        nd_obj = LogicalNode(hostname=host, username=username, password=password)
        resp = nd_obj.execute_cmd(cmd=cmd, read_lines=True)
        print("The join cmd o/p is %s", resp)

# pylint: disable-msg=too-many-locals


def main(args):
    """
    main function to deploy Kubernetes
    """
    k8s_input = dict()
    k8s_input['nodes'] = args.nodes
    k8s_input['hosts_ip'] = args.ip
    k8s_input['username'] = args.username
    k8s_input['password'] = args.password
    host_ip_dict = {}

    if not k8s_input['hosts_ip']:
        for host in k8s_input['nodes']:
            nd_obj = LogicalNode(hostname=host, username=k8s_input['username'],
                          password=k8s_input['password'])
            result = nd_obj.execute_cmd(cmd="ifconfig eth0", read_lines=True)
            test_list = result[1].split(" ")
            test_list = [i for i in test_list if i]
            host_ip_n = {test_list[1]: host}
            host_ip_dict.update(host_ip_n)

    else:
        for node_ip, host in zip(k8s_input['hosts_ip'], k8s_input['nodes']):
            host_ip_s = {node_ip: host}
            host_ip_dict.update(host_ip_s)
        print("The hostname and ip dict is %s", host_ip_dict)

    for host in k8s_input['nodes']:
        nd_obj = LogicalNode(hostname=host, username=k8s_input['username'],
                      password=k8s_input['password'])
        nd_obj.copy_file_to_local(REMOTE_HOSTS_ORG, LOCAL_COPY_HOSTS)
        with open(LOCAL_COPY_HOSTS, "a") as file:
            for key, value in host_ip_dict.items():
                line = " ".join([key, value])
                file.write(line)
                file.write("\n")
                nd_obj.execute_cmd(cmn_cmd.CMD_PING.format(key), read_lines=True)
        nd_obj.copy_file_to_remote(LOCAL_COPY_HOSTS, REMOTE_HOSTS_ORG)
    install_docker(*k8s_input['nodes'], username=k8s_input['username'],
                   password=k8s_input['password'])
    configure_iptables(*k8s_input['nodes'], username=k8s_input['username'],
                       password=k8s_input['password'])
    create_daemon_file(*k8s_input['nodes'], username=k8s_input['username'],
                       password=k8s_input['password'])
    configure_k8s_repo(*k8s_input['nodes'], username=k8s_input['username'],
                       password=k8s_input['password'])
    result = initialize_k8s(k8s_input['nodes'][0], username=k8s_input['username'],
                            password=k8s_input['password'])
    print("The token is ", result[1])
    create_network(k8s_input['nodes'][0], username=k8s_input['username'],
                   password=k8s_input['password'])
    status = get_node_status(k8s_input['nodes'][0], username=k8s_input['username'],
                             password=k8s_input['password'])
    print("The stat is ", status)
    if "Ready" in status:
        print("Adding the worker node to master node")
        join_cluster(*k8s_input['nodes'], username=k8s_input['username'],
                     password=k8s_input['password'], cmd=result[1])
    else:
        print("To troubleshoot run cmd: kubectl get pods -n kube-system \n")
        troubleshoot(*k8s_input['nodes'], username=k8s_input['username'],
                     password=k8s_input['password'], status=status)
        join_cluster(*k8s_input['nodes'], username=k8s_input['username'],
                     password=k8s_input['password'], cmd=result[1])

    status_all = get_node_status(k8s_input['nodes'][0], username=k8s_input['username'],
                                 password=k8s_input['password'])
    if "NotReady" in status_all:
        print("Please check after some time,"
              "the nodes status is", status_all)
        troubleshoot(*k8s_input['nodes'], username=k8s_input['username'],
                     password=k8s_input['password'], status=status_all)
    print("Successfully deployed the k8s ,"
          "Please run \"kubectl get nodes cmd\" on ", k8s_input['nodes'][0])


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
