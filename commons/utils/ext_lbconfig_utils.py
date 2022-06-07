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
Module to maintain External Load Balancer set utils
"""

import json
import logging
import os
import random
from commons import commands as cm_cmd
from commons import constants as cm_const
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import system_utils as sys_utils

# Global Constants
LOGGER = logging.getLogger(__name__)


def configure_rsyslog():
    """
     Configure rsyslog to configure logging of the HAProxy service
     return: rsyslog restart command execution response
    """
    rsysconf_path = "/etc/rsyslog.conf"
    if os.path.exists(rsysconf_path):
        with open(rsysconf_path, 'r') as f_read:
            rsyslog = f_read.readlines()
        with open("/etc/rsyslog_dummy.conf", 'w') as f_write:
            for line in rsyslog:
                if "# Provides UDP syslog reception" in line:
                    f_write.write(line)
                    f_write.write(
                        "$ModLoad imudp\n$UDPServerAddress 127.0.0.1\n$UDPServerRun 514\n")
                    continue
                if "$ModLoad imudp" in line or "$UDPServerAddress 127.0.0.1" in line\
                        or "$UDPServerRun 514" in line:
                    continue
                f_write.write(line)
        sys_utils.execute_cmd("rm -f {}".format(rsysconf_path))
        sys_utils.execute_cmd("mv {} {}".format("/etc/rsyslog_dummy.conf", rsysconf_path))
        sys_utils.execute_cmd("rm -f {}".format("/etc/rsyslog_dummy.conf"))
    else:
        LOGGER.info("Couldn't find %s ", rsysconf_path)
    rsyslogd_path = "/etc/rsyslog.d/haproxy.conf"
    haproxylog_path = "/var/log/haproxy.log"
    if os.path.exists(rsyslogd_path):
        sys_utils.execute_cmd("rm -f {}".format(rsyslogd_path))
    sys_utils.execute_cmd(cmd="mkdir -p /etc/rsyslog.d/")
    with open(rsyslogd_path, 'w') as f_write:
        f_write.write(f"if ($programname == 'haproxy') then -{haproxylog_path}\n")

    if os.path.exists(haproxylog_path):
        sys_utils.execute_cmd("rm -f {}".format(haproxylog_path))
    sys_utils.execute_cmd(f"touch {haproxylog_path}")
    sys_utils.execute_cmd(f"chmod 755 {haproxylog_path}")
    resp = sys_utils.execute_cmd(cmd=cm_cmd.SYSTEM_CTL_RESTART_CMD.format("rsyslog"))
    return resp


# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
def configure_haproxy_lb(m_node: str, username: str, password: str, ext_ip: str):
    """
    Implement external Haproxy LB
    :param m_node: hostname for master node
    :param username: username for node
    :param password: password for node
    :param ext_ip: External LB IP from client node setup
    """
    m_node_obj = LogicalNode(hostname=m_node, username=username, password=password)
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.K8S_WORKER_NODES, read_lines=True)
    pods_list = m_node_obj.get_all_pods(pod_prefix=cm_const.SERVER_POD_NAME_PREFIX)
    worker_node = {resp[index].strip("\n"): dict() for index in range(1, len(resp))}
    for worker in worker_node.keys():
        w_node_obj = LogicalNode(hostname=worker, username=username, password=password)
        resp = w_node_obj.execute_cmd(cmd=cm_cmd.CMD_GET_IP_IFACE.format("eth1"), read_lines=True)
        worker_node[worker].update({"eth1": resp[0].strip("\n")})
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.K8S_GET_SVC_JSON, read_lines=False).decode("utf-8")
    resp = json.loads(resp)
    get_port_data = dict()
    for item_data in resp["items"]:
        if item_data["spec"]["type"] == "LoadBalancer" and \
                "cortx-server" in item_data["spec"]["selector"]["app"]:
            worker = item_data["spec"]["selector"]["app"].split("cortx-server-")[1] \
                     + ".colo.seagate.com"
            get_port_data[worker] = dict()
            if item_data["spec"].get("ports") is not None:
                for port_items in item_data["spec"]["ports"]:
                    get_port_data[worker].update({f"{port_items['targetPort']}":
                                                      port_items["nodePort"]})
            else:
                LOGGER.info("Failed to get ports details from %s", get_port_data.get(worker))
    LOGGER.info("Worker node IP PORTs info for haproxy: %s", get_port_data)
    for worker in worker_node.keys():
        if get_port_data.get(worker) is not None:
            worker_node[worker].update(get_port_data[worker])
        else:
            assert_utils.assert_true(False, f"Can't find port details for {worker} "
                                            f"from {get_port_data}")

    with open(cm_const.HAPROXY_DUMMY_CONFIG, 'r') as f_read:
        haproxy_dummy = f_read.readlines()
    if not os.path.exists("/etc/haproxy"):
        sys_utils.execute_cmd("mkdir -p {}".format("/etc/haproxy"))
    with open(cm_const.const.CFG_FILES[0], "w") as f_write:
        for line in haproxy_dummy:
            if "# cortx_setup_1" in line:
                line = f"    bind {ext_ip}:80\n"
                f_write.write(line)
                continue
            if "# cortx_setup_https" in line:
                line = f"    bind {ext_ip}:443 ssl crt /etc/ssl/stx/stx.pem\n"
                f_write.write(line)
                continue
            if "# auth_port_9080" in line:
                line = f"    bind {ext_ip}:9080\n"
                f_write.write(line)
                continue
            if "# auth_https_port_9443" in line:
                line = f"    bind {ext_ip}:9443 ssl crt /etc/ssl/stx/stx.pem\n"
                f_write.write(line)
                continue
            if "# 80 cortx_setup_1" in line:
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server ha-s3-{index} {worker_node[worker]['eth1']}:" \
                           f"{worker_node[worker]['80']}    #port mapped to 80\n"
                    f_write.write(line)
                continue
            if "# 443 cortx_setup_https" in line:
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server ha-s3-ssl-{index} {worker_node[worker]['eth1']}:" \
                           f"{worker_node[worker]['443']} ssl verify none    #port mapped to 443\n"
                    f_write.write(line)
                continue
            if "# 9080 s3_auth" in line:
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server s3authserver-instance{index} " \
                           f"{worker_node[worker]['eth1']}:{worker_node[worker]['9080']} " \
                           f"#port mapped to 9080\n"
                    f_write.write(line)
                continue
            if "# 9443 s3_auth_https" in line:
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server s3authserver-instance-ssl-{index} " \
                           f"{worker_node[worker]['eth1']}:{worker_node[worker]['9443']} " \
                           f"ssl verify none    #port mapped to 9443\n"
                    f_write.write(line)
                continue
            f_write.write(line)
    LOGGER.info("Configuring rsyslog to Configure Logging for HAProxy")
    resp = configure_rsyslog()
    LOGGER.debug("Configuring rsyslog response = %s", resp)
    LOGGER.info("Coping the ca.crt to %s", cm_const.LOCAL_S3_CERT_PATH)
    if os.path.exists(cm_const.LOCAL_S3_CERT_PATH):
        sys_utils.execute_cmd("rm -f {}".format(cm_const.LOCAL_S3_CERT_PATH))
    sys_utils.execute_cmd(cmd="mkdir -p {}".format(
        os.path.dirname(os.path.abspath(cm_const.LOCAL_S3_CERT_PATH))))
    cmd = cm_cmd.K8S_CP_PV_FILE_TO_LOCAL_CMD.format(
        pods_list[0], cm_const.K8S_CRT_PATH, "/root/ca.crt")
    resp = m_node_obj.execute_cmd(cmd=cmd, read_lines=True)
    LOGGER.debug("Resp : %s", resp)
    m_node_obj.copy_file_to_local("/root/ca.crt", cm_const.LOCAL_S3_CERT_PATH)
    LOGGER.info("Coping the stx.pem to %s", cm_const.LOCAL_PEM_PATH)
    if os.path.exists(cm_const.LOCAL_PEM_PATH):
        sys_utils.execute_cmd("rm -f {}".format(cm_const.LOCAL_PEM_PATH))
    sys_utils.execute_cmd(cmd="mkdir -p {}".format(os.path.dirname(
        os.path.abspath(cm_const.LOCAL_PEM_PATH))))
    cmd = cm_cmd.K8S_CP_PV_FILE_TO_LOCAL_CMD.format(
        pods_list[0], cm_const.K8S_PEM_PATH, "/root/stx.pem")
    resp = m_node_obj.execute_cmd(cmd=cmd, read_lines=True)
    LOGGER.debug("Resp : %s", resp)
    m_node_obj.copy_file_to_local("/root/stx.pem", cm_const.LOCAL_PEM_PATH)
    resp = sys_utils.execute_cmd(cmd=cm_cmd.SYSTEM_CTL_RESTART_CMD.format("haproxy"))
    assert_utils.assert_true(resp[0], resp[1])
    resp = sys_utils.execute_cmd("puppet agent --disable")
    assert_utils.assert_true(resp[0], resp[1])
    LOGGER.info("Setting s3 endpoints of ext LB on client.")
    sys_utils.execute_cmd(cmd="rm -f /etc/hosts")
    with open("/etc/hosts", 'w') as file:
        file.write("127.0.0.1   localhost localhost.localdomain localhost4 "
                   "localhost4.localdomain4\n")
        file.write("::1         localhost localhost.localdomain localhost6 "
                   "localhost6.localdomain6\n")
        file.write("{} s3.seagate.com sts.seagate.com iam.seagate.com "
                   "sts.cloud.seagate.com\n".format(ext_ip))

def configure_nodeport_lb(node_obj: LogicalNode, iface: str):
    """
    Helper function to get node port ports and external IP from master node.
    :param node_obj: Master node object
    :param iface: interface name
    :return: boolean, external ip, http port, https port
    """
    resp = node_obj.execute_cmd(cmd=cm_cmd.CMD_GET_IP_IFACE.format(iface), read_lines=True)
    ext_ip = resp[0].strip("\n")
    LOGGER.info("Data IP from master node: %s", ext_ip)
    resp = node_obj.execute_cmd(cmd=cm_cmd.K8S_GET_SVC_JSON, read_lines=False).decode("utf-8")
    if not resp[0]:
        return False, "Not getting expected response for kubectl get svc command"
    resp = json.loads(resp)
    flag = False
    for item_data in resp["items"]:
        if item_data['metadata']["name"] == "cortx-io-svc-0":
            for item in item_data['spec']['ports']:
                if item['port'] == 443:
                    port_https = item["nodePort"]
                    flag = True
                    LOGGER.info("HTTPS Port for IO is: %s", port_https)
                if item['port'] == 80:
                    port_http = item["nodePort"]
                    flag = True
                    LOGGER.info("HTTP Port for IO is: %s", port_http)

    if flag:
        return True, ext_ip, port_https, port_http
    else:
        return False, "Did not get expected port numbers."


def configure_haproxy_rgwlb(m_node: str, username: str, password: str, ext_ip: str, iface="eth1"):
    """
    Implement external service set as LoadBalancer for RGW
    :param m_node: hostname for master node
    :param username: username for node
    :param password: password for node
    :param ext_ip: External LB IP from client node setup
    :param iface: public data IP interface default is eth1
    """
    m_node_obj = LogicalNode(hostname=m_node, username=username, password=password)
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.K8S_WORKER_NODES, read_lines=True)
    worker_node = {resp[index].strip("\n"): dict() for index in range(1, len(resp))}
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.CMD_GET_IP_IFACE.format(iface), read_lines=True)
    master_eth1 = resp[0].strip("\n")
    LOGGER.info("Data IP from master node: %s", master_eth1)
    for worker in worker_node.keys():
        w_node_obj = LogicalNode(hostname=worker, username=username, password=password)
        resp = w_node_obj.execute_cmd(cmd=cm_cmd.CMD_GET_IP_IFACE.format(iface), read_lines=True)
        worker_node[worker].update({iface: resp[0].strip("\n")})
    worker_eth1 = [worker[iface] for worker in worker_node.values() if iface in worker.keys()]
    print("Worker nodes eth1: ", worker_eth1)
    random.shuffle(worker_eth1)
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.K8S_GET_SVC_JSON, read_lines=False).decode("utf-8")
    resp = json.loads(resp)
    get_iosvc_data = dict()
    for item_data in resp["items"]:
        if item_data["spec"]["type"] == "LoadBalancer" and \
                "cortx-io-svc-" in item_data["metadata"]["name"]:
            svc = item_data["metadata"]["name"]
            get_iosvc_data[svc] = dict()
            if svc == "cortx-io-svc-0":
                get_iosvc_data[svc].update({iface: master_eth1})
            else:
                get_iosvc_data[svc].update({iface: worker_eth1.pop()})
            if item_data["spec"].get("ports") is not None:
                for port_items in item_data["spec"]["ports"]:
                    get_iosvc_data[svc].update({f"{port_items['targetPort']}":
                                                    port_items["nodePort"]})
            else:
                LOGGER.info("Failed to get ports details from %s", get_iosvc_data.get(svc))
    LOGGER.info("io-svc IP PORTs info for haproxy: %s", get_iosvc_data)
    with open(cm_const.HAPROXY_DUMMY_RGW_CONFIG, 'r') as f_read:
        haproxy_dummy = f_read.readlines()
    if not os.path.exists("/etc/haproxy"):
        sys_utils.execute_cmd("mkdir -p {}".format("/etc/haproxy"))
    with open(cm_const.const.CFG_FILES[0], "w") as f_write:
        for line in haproxy_dummy:
            if "# cortx_setup_1" in line:
                line = f"    bind {ext_ip}:80\n"
                f_write.write(line)
                continue
            if "# cortx_setup_https" in line:
                line = f"    bind {ext_ip}:443 ssl crt /etc/ssl/stx/stx.pem\n"
                f_write.write(line)
                continue
            if "# 80 cortx_setup_1" in line:
                for index, svc in enumerate(get_iosvc_data.keys(), 1):
                    line = f"    server ha-s3-{index} {get_iosvc_data[svc]['eth1']}:" \
                           f"{get_iosvc_data[svc]['rgw-http']}    #port mapped to 80\n"
                    f_write.write(line)
                continue
            if "# 443 cortx_setup_https" in line:
                for index, svc in enumerate(get_iosvc_data.keys(), 1):
                    line = f"    server ha-s3-ssl-{index} {get_iosvc_data[svc]['eth1']}:" \
                           f"{get_iosvc_data[svc]['rgw-https']} " \
                           f"ssl verify none    #port mapped to 443\n"
                    f_write.write(line)
                continue
            f_write.write(line)
    LOGGER.info("Configuring rsyslog to Configure Logging for HAProxy")
    resp = configure_rsyslog()
    LOGGER.debug("Configuring rsyslog response = %s", resp)
    if os.path.exists(cm_const.LOCAL_PEM_PATH):
        sys_utils.execute_cmd("rm -f {}".format(cm_const.LOCAL_PEM_PATH))
    sys_utils.execute_cmd(cmd="mkdir -p {}".format(os.path.dirname(
        os.path.abspath(cm_const.LOCAL_PEM_PATH))))
    m_node_obj.copy_file_to_local(cm_const.K8S_PEM_FILE_PATH, cm_const.LOCAL_PEM_PATH)
    resp = sys_utils.execute_cmd(cmd=cm_cmd.SYSTEM_CTL_RESTART_CMD.format("haproxy"))
    assert_utils.assert_true(resp[0], resp[1])
    resp = sys_utils.execute_cmd("puppet agent --disable")
    assert_utils.assert_true(resp[0], resp[1])

    LOGGER.info("External HAProxy is configured.")
