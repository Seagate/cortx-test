from kubernetes import client, config, watch
from kubernetes.client import configuration
from kubernetes.stream import stream
from commons.utils import assert_utils
import logging

LOGGER = logging.getLogger(__name__)

def main():

    # Initialization

    actual_ports = []
    netstat_port_list = []

    #contexts, active_context = config.list_kube_config_contexts()
    #if not contexts:
    #    print("Cannot find any context in kube-config file.")
    #    return
    #contexts = [context['name'] for context in contexts]
    #active_index = contexts.index(active_context['name'])
    #option, _ = pick(contexts, title="Pick the context to load", default_index=active_index)
    # Configs can be set in Configuration class directly or using helper
    # utility
    # config.load_kube_config(context=option)

    LOGGER.info(' This is cortx port scanner!')

    option="kubernetes-admin@kubernetes"

    config.load_kube_config(context=option)

    # listing all pods

    v1 = client.CoreV1Api()
    LOGGER.info(" Listing pods with their IPs:")
    ret = v1.list_pod_for_all_namespaces(watch=False)
    for item in ret.items:
        LOGGER.info( " %s\t%s\t%s" % (item.status.pod_ip, item.metadata.namespace, item.metadata.name))
        list_containers = item.spec.containers
        for list_each_con in list_containers:
            LOGGER.info(list_each_con.name)

    # listing all services

    LOGGER.info(" Listing All the services running in cluster:")
    ret = v1.list_service_for_all_namespaces(watch=False)
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

    #LOGGER.info(" Complete list of actual ports...")
    actual_ports.sort()
    #LOGGER.info(actual_ports)

    # Read port numbers from file specification
    req_port_list = []

    with open("requirement_ports.txt") as file:
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

    if final_list_of_fault_ports: assert_utils.assert_true(False, "Incorrect ports opened in cortx cluster...")
    else: Logger.info(" Test Case successful!!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, filename='port_scanner_kubectl_svc.log')
    main()

