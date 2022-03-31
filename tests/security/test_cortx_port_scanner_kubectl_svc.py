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
"""
This is cortx port scanner using kubectl svc
"""
import logging
import os
import pytest
from kubernetes import client, config

LOGGER = logging.getLogger(__name__)

@pytest.mark.security
@pytest.mark.tags("TEST-34217")
def test_cortx_port_scanner_kubectl_svc():

    """
    This is cortx port scanner
    """
    # Initialization

    actual_ports = []

    LOGGER.info(' This is cortx port scanner!')

    k8s_config_file = os.environ.get('KUBECONFIG')
    if k8s_config_file:
        logging.info('Loading kubernetes config from the file %s', k8s_config_file)
        config.load_kube_config(config_file=k8s_config_file)
    else:
        k8s_config_file="/root/.kube/config"
        config.load_kube_config(config_file=k8s_config_file)

    # listing all pods

    core_client = client.CoreV1Api()
    LOGGER.info(" Listing pods with their IPs:")
    ret = core_client.list_pod_for_all_namespaces(watch=False)
    for item in ret.items:
        LOGGER.info( " %s\t%s\t%s",item.status.pod_ip,item.metadata.namespace,item.metadata.name)
        list_containers = item.spec.containers
        for list_each_con in list_containers:
            LOGGER.info(list_each_con.name)

    # listing all services

    LOGGER.info(" Listing All the services running in cluster:")
    ret = core_client.list_service_for_all_namespaces(watch=False)
    for item in ret.items:
        LOGGER.info(item.spec.cluster_ip)
        if item.spec.cluster_ip != "None":
            list_of_ports=item.spec.ports
            LOGGER.info(" Listing all ports")
            for port_item in list_of_ports:
                LOGGER.info(port_item.name)
                LOGGER.info(port_item.port)
                if port_item.port != "NoneType":
                    actual_ports.append(int(port_item.port))
                if port_item.node_port is not None:
                    # Check if node port is >= 30000 and <=32767
                    # if node port is in this range, then it can be ignored from
                    # adding to actual_ports. Such that those ports are expected and
                    # will not be part of the comparison
                    # So add the node_port only if its outside the range of 30000 to 32767
                    if int(port_item.node_port) < 30000 or int(port_item.node_port) > 32767:
                        actual_ports.append(int(port_item.node_port))


    # Prepare a list of actual ports

    actual_ports.sort()

    # Read port numbers from file specification
    req_port_list = []

    with open("tests/security/requirement_ports.txt") as file:
        for req_ports in file:
            LOGGER.info(req_ports.rstrip())
            req_port_list.append(int(req_ports.rstrip()))

    req_port_list.sort()
    final_list_of_fault_ports = verify_ports(actual_ports, req_port_list)
    if final_list_of_fault_ports:
        LOGGER.error(" Test Failed!!")
    else:
        LOGGER.info(" Test Case successful!!")


def verify_ports(actual_ports, req_port_list):
    """Ports verification will be added once ports are frozen."""
    LOGGER.info("------------------------------")
    LOGGER.info("List of ports opened in cluster - scanned using kubectl get svc")
    LOGGER.info("------------------------------")
    actual_ports.sort()
    to_log_actual_ports = list(set(actual_ports))
    to_log_actual_ports.sort()
    LOGGER.info(to_log_actual_ports)
    LOGGER.info("------------------------------")
    LOGGER.info("List of ports as per - specification")
    LOGGER.info("------------------------------")
    LOGGER.info(req_port_list)
    LOGGER.info("------------------------------")
    LOGGER.info("List of ports which should not be opened...")
    LOGGER.info("------------------------------")
    final_list_of_fault_ports = list(set(to_log_actual_ports) - set(req_port_list))
    final_list_of_fault_ports.sort()
    LOGGER.info(final_list_of_fault_ports)
    return final_list_of_fault_ports
