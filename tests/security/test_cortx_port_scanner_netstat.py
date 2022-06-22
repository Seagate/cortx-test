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
#
"""This is cortx port scanner using netstat"""
import logging
import os
import pytest
from kubernetes import client, config
from kubernetes.stream import stream
from commons import constants as const

LOGGER = logging.getLogger(__name__)

@pytest.mark.security
@pytest.mark.tags("TEST-34218")
def test_cortx_port_scanner_netstat():

    """
    This is cortx port scanner
    """

    # Initialization

    netstat_port_list = []

    LOGGER.info(' This is cortx port scanner!')
    k8s_config_file = os.environ.get('KUBECONFIG')
    if k8s_config_file:
        logging.info('Loading kubernetes config from the file %s', k8s_config_file)
        config.load_kube_config(config_file=k8s_config_file)
    else:
        k8s_config_file="/root/.kube/config"
        config.load_kube_config(config_file=k8s_config_file)


    # Read port numbers from file specification
    req_port_list = []

    with open("tests/security/requirement_ports.txt") as file:
        for req_ports in file:
            #LOGGER.info(req_ports.rstrip())
            req_port_list.append(int(req_ports.rstrip()))

    req_port_list.sort()

    # Execute command on a POD

    cmd_install_net_tool = ['/bin/sh', '-c', 'yum install net-tools -y']
    cmd_run_netstat = ['/bin/sh', '-c', 'netstat -plnt | awk \'{print $4}\' | cut -d \":\" -f2']

    ret = client.CoreV1Api().list_pod_for_all_namespaces(watch=False)
    for item in ret.items:
        LOGGER.info("%s\t%s\t%s", item.status.pod_ip,item.metadata.namespace,item.metadata.name)
        if (("cortx-data" in item.metadata.name) or
                ("cortx-ha" in item.metadata.name) or
                ("cortx-server" in item.metadata.name) or
                ("cortx-control" in item.metadata.name)):
            LOGGER.info(" --------------------------------------")
            for list_each_con in item.spec.containers:
                LOGGER.info(" Open Ports for Container: %s",list_each_con.name)
                LOGGER.info(list_each_con.name)
                LOGGER.info(" Installing net-tools")
                resp = stream(client.CoreV1Api().connect_get_namespaced_pod_exec, \
                              item.metadata.name, const.NAMESPACE, container=list_each_con.name, \
                              command=cmd_install_net_tool, stderr=True, stdin=False, \
                              stdout=True, tty=False, _preload_content=True)
                LOGGER.info("Executing netstat")
                resp = stream(client.CoreV1Api().connect_get_namespaced_pod_exec, \
                              item.metadata.name, const.NAMESPACE, container=list_each_con.name, \
                              command=cmd_run_netstat, stderr=True, stdin=False, \
                              stdout=True, tty=False, _preload_content=True)
                for each_port in resp.splitlines():
                    if has_numbers(each_port):
                        netstat_port_list.append(int(each_port))
                LOGGER.info("Response: %s", resp)

            LOGGER.info("--------------------------------------")


    # Print the difference between actual_ports and req_port_list

    LOGGER.info("------------------------------")
    LOGGER.info("List of ports opened in cluster - scanned using netstat")
    LOGGER.info("------------------------------")
    netstat_port_list.sort()
    to_log_netstat_port_list=list(set(netstat_port_list))
    to_log_netstat_port_list.sort()
    LOGGER.info(to_log_netstat_port_list)

    LOGGER.info("------------------------------")
    LOGGER.info("List of ports as per - specification")
    LOGGER.info("------------------------------")
    LOGGER.info(req_port_list)

    LOGGER.info("------------------------------")
    LOGGER.info("List of ports which should not be opened...")
    LOGGER.info("------------------------------")
    final_list_of_fault_ports=list(set(netstat_port_list) - set(req_port_list))
    final_list_of_fault_ports.sort()
    LOGGER.info(final_list_of_fault_ports)
    if final_list_of_fault_ports:
        LOGGER.error(" Test Failed!!")
    else:
        LOGGER.info(" Test Case successful!!")

def has_numbers(input_string):
    """
    Function to check if string is number
    """
    return any(char.isdigit() for char in input_string)
