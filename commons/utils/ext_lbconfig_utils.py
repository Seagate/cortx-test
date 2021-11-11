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

    with open(cm_const.const.CFG_FILES[0], "w") as f_write:
        for line in haproxy_dummy:
            if "# *frontend main" in line:
                line = f"    bind {ext_ip}:80\n    bind {ext_ip}:443 ssl crt /etc/ssl/stx/stx.pem\n"
                f_write.write(line)
                continue
            if "# *s3 auth server port" in line:
                line = f"    bind {ext_ip}:9080\n" \
                       f"    bind {ext_ip}:9443 ssl crt /etc/ssl/stx/stx.pem\n"
                f_write.write(line)
                continue
            if "# *backend cortx-setup-1" in line:
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server ha-s3-{index} {worker_node[worker]['eth1']}:" \
                           f"{worker_node[worker]['80']}    #port mapped to 80\n"
                    f_write.write(line)
                f_write.write("\n")
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server ha-s3-ssl-{index} {worker_node[worker]['eth1']}:" \
                           f"{worker_node[worker]['443']}    #port mapped to 443\n"
                    f_write.write(line)
                continue
            if "# *backend s3-auth" in line:
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server s3authserver-instance{index} " \
                           f"{worker_node[worker]['eth1']}:{worker_node[worker]['9080']}    " \
                           f"#port mapped to 9080\n"
                    f_write.write(line)
                f_write.write("\n")
                for index, worker in enumerate(worker_node.keys(), 1):
                    line = f"    server s3authserver-instance-ssl-{index} " \
                           f"{worker_node[worker]['eth1']}:{worker_node[worker]['9443']} " \
                           f"check ssl verify none    #port mapped to 9443\n"
                    f_write.write(line)
                continue
            f_write.write(line)
    LOGGER.info("Coping the PEM from one of the nodes of CORTX deployment to the LB host.")
    pem_local_path = "/etc/ssl/stx/stx.pem"
    if os.path.exists(pem_local_path):
        sys_utils.execute_cmd("rm -f {}".format(pem_local_path))
    m_node_obj.copy_file_to_local(remote_path=cm_const.K8s_PEM_PATH, local_path=pem_local_path)

    resp = sys_utils.execute_cmd(cmd=cm_cmd.SYSTEM_CTL_RESTART_CMD.format("haproxy"))
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
