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

import os
import logging
import json
from commons.helpers.pods_helper import LogicalNode
from commons import commands as cm_cmd
from commons import constants as cm_const
from commons.utils import assert_utils
from commons.utils import system_utils as sys_utils

# Global Constants
LOGGER = logging.getLogger(__name__)


def configure_rsyslog():
    """
     Configure rsyslog to configure logging of the HAProxy service
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
                        f"$ModLoad imudp\n$UDPServerAddress 127.0.0.1\n$UDPServerRun 514\n")
                    continue
                if "$ModLoad imudp" in line or "$UDPServerAddress 127.0.0.1" in line\
                        or "$UDPServerRun 514" in line:
                    continue
                f_write.write(line)
        sys_utils.execute_cmd("rm -f {}".format(rsysconf_path))
        sys_utils.execute_cmd("mv {} {}".format("/etc/rsyslog_dummy.conf", rsysconf_path))
        sys_utils.execute_cmd("rm -f {}".format("/etc/rsyslog_dummy.conf"))
    else:
        LOGGER.info(f"Couldn't find {rsysconf_path}")
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
    assert_utils.assert_true(resp[0], resp[1])


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
    worker_node = {resp[index].strip("\n"): dict() for index in range(1, len(resp))}
    for worker in worker_node.keys():
        w_node_obj = LogicalNode(hostname=worker, username=username, password=password)
        resp = w_node_obj.execute_cmd(cmd=cm_cmd.CMD_GET_IP_IFACE.format("eth1"), read_lines=True)
        worker_node[worker].update({"eth1": resp[0].strip("\n")})
    resp = m_node_obj.execute_cmd(cmd=cm_cmd.K8S_GET_SVC_JSON, read_lines=False).decode("utf-8")
    resp = json.loads(resp)
    for item_data in resp["items"]:
        if item_data["spec"]["type"] == "LoadBalancer" and \
                "cortx-data-pod" in item_data["spec"]["selector"]["app"]:
            worker = item_data["spec"]["selector"]["app"].split("pod-")[1] + ".colo.seagate.com"
            for port_items in item_data["spec"]["ports"]:
                worker_node[worker].update({f"{port_items['targetPort']}": port_items["nodePort"]})
    LOGGER.info("Worker node IP PORTs info for haproxy: %s", worker_node)
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
    configure_rsyslog()
    LOGGER.info("Coping the PEM from /Seagate/cortx-s3server/kubernetes/scripts/haproxy/ssl/")
    pem_local_path = "/etc/ssl/stx/stx.pem"
    if os.path.exists(pem_local_path):
        sys_utils.execute_cmd("rm -f {}".format(pem_local_path))
    sys_utils.execute_cmd(cmd="mkdir -p /etc/ssl/stx/")
    sys_utils.execute_cmd("curl https://raw.githubusercontent.com/Seagate/cortx-s3server/"
                          "kubernetes/scripts/haproxy/ssl/s3.seagate.com.crt"
                          " -o /etc/ssl/stx-s3-clients/s3/ca.crt")
    sys_utils.execute_cmd("curl https://raw.githubusercontent.com/"
                          "Seagate/cortx-prvsnr/4c2afe1c19e269ecb6fbf1cba62fdb7613508182/srv/"
                          "components/misc_pkgs/ssl_certs/files/stx.pem -o /etc/ssl/stx/stx.pem")
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
