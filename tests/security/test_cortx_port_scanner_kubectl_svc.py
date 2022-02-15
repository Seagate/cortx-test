"""
This is cortx port scanner using kubectl svc
"""
import logging
import os
from kubernetes import client, config
from commons.utils import assert_utils

LOGGER = logging.getLogger(__name__)

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

    # Prepare a list of actual ports

    actual_ports.sort()

    # Read port numbers from file specification
    req_port_list = []

    with open("tests/security/requirement_ports.txt") as file:
        for req_ports in file:
            LOGGER.info(req_ports.rstrip())
            req_port_list.append(int(req_ports.rstrip()))

    req_port_list.sort()

    LOGGER.info("------------------------------")
    LOGGER.info("List of ports opened in cluster - scanned using kubectl get svc")
    LOGGER.info("------------------------------")
    actual_ports.sort()
    to_log_actual_ports=list(set(actual_ports))
    to_log_actual_ports.sort()
    LOGGER.info(to_log_actual_ports)

    LOGGER.info("------------------------------")
    LOGGER.info("List of ports as per - specification")
    LOGGER.info("------------------------------")
    LOGGER.info(req_port_list)

    LOGGER.info("------------------------------")
    LOGGER.info("List of ports which should not be opened...")
    LOGGER.info("------------------------------")
    final_list_of_fault_ports=list(set(to_log_actual_ports) - set(req_port_list))
    final_list_of_fault_ports.sort()
    LOGGER.info(final_list_of_fault_ports)
    if final_list_of_fault_ports:
        LOGGER.error(" Test Failed!!")
    else:
        LOGGER.info(" Test Case successful!!")
