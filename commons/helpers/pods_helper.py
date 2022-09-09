#!/usr/bin/python
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

"""Pods helper impl. Command builder should not be part of this class.
However validation of sub commands and options can be done in command issuing functions
like send_k8s_cmd.
"""

import logging
import os
import random
import time
from typing import Tuple
import json

from commons import commands
from commons import constants as const
from commons.helpers.host import Host

log = logging.getLogger(__name__)

namespace_map = {}


class LogicalNode(Host):
    """Pods helper class. The Command builder should be written separately and will be
    using this class.
    """

    kube_commands = ('create', 'apply', 'config', 'get', 'explain',
                     'autoscale', 'patch', 'scale', 'exec')

    def get_service_logs(self, svc_name: str, namespace: str, options: '') -> Tuple:
        """Get logs of a pod or service."""
        cmd = commands.FETCH_LOGS.format(svc_name, namespace, options)
        res = self.execute_cmd(cmd)
        return res

    def send_k8s_cmd(
            self,
            operation: str,
            pod: str,
            namespace: str,
            command_suffix: str,
            decode=False,
            **kwargs) -> bytes:
        """send/execute command on logical node/pods."""
        if operation not in LogicalNode.kube_commands:
            raise ValueError(
                "command parameter must be one of %r." % str(LogicalNode.kube_commands))
        log.debug("Performing %s on service %s in namespace %s...", operation, pod, namespace)
        cmd = commands.KUBECTL_CMD.format(operation, pod, namespace, command_suffix)
        resp = self.execute_cmd(cmd, **kwargs)
        if decode:
            resp = (resp.decode("utf8")).strip()
        return resp

    def shutdown_node(self, options=None):
        """Function to shutdown any of the node."""
        try:
            cmd = "shutdown {}".format(options if options else "")
            log.debug(
                "Shutting down %s node using cmd: %s.",
                self.hostname,
                cmd)
            resp = self.execute_cmd(cmd, shell=False)
            log.debug(resp)
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.shutdown_node.__name__, error)
            return False, error

        return True, "Node shutdown successfully"

    def get_pod_name(self, pod_prefix: str = const.POD_NAME_PREFIX):
        """Function to get pod name with given prefix."""
        output = self.execute_cmd(commands.CMD_POD_STATUS +
                                  " -o=custom-columns=NAME:.metadata.name", read_lines=True)
        for lines in output:
            if pod_prefix in lines:
                return True, lines.strip()
        return False, f"pod with prefix \"{pod_prefix}\" not found"

    def send_sync_command(self, pod_prefix):
        """
        Helper function to send sync command to all containers of given pod category
        :param pod_prefix: Prefix to define the pod category
        :return: Bool
        """
        log.info("Run sync command on all containers of pods %s", pod_prefix)
        pod_dict = self.get_all_pods_containers(pod_prefix=pod_prefix)
        if pod_dict:
            for pod, containers in pod_dict.items():
                for cnt in containers:
                    res = self.send_k8s_cmd(
                        operation="exec", pod=pod, namespace=const.NAMESPACE,
                        command_suffix=f"-c {cnt} -- sync", decode=True)
                    log.info("Response for pod %s container %s: %s", pod, cnt, res)

        return True

    def get_all_pods_containers(self, pod_prefix, pod_list=None):
        """
        Helper function to get all pods with containers of given pod_prefix
        :param pod_prefix: Prefix to define the pod category
        :param pod_list: List of pods
        :return: Dict
        """
        pod_containers = {}
        if not pod_list:
            log.info("Get all data pod names of %s", pod_prefix)
            output = self.execute_cmd(commands.CMD_POD_STATUS +
                                      " -o=custom-columns=NAME:.metadata.name", read_lines=True)
            for lines in output:
                if pod_prefix in lines:
                    pod_list.append(lines.strip())

        for pod in pod_list:
            cmd = commands.KUBECTL_GET_POD_CONTAINERS.format(pod)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            output = output[0].split()
            pod_containers[pod] = output

        return pod_containers

    def create_pod_replicas(self, num_replica, deploy=None, pod_name=None, set_name=None):
        """
        Helper function to delete/remove/create pod by changing number of replicas
        :param num_replica: Number of replicas to be scaled
        :param deploy: Name of the deployment of pod
        :param pod_name: Name of the pod
        :param set_name: Name of the Statefulset of the pod
        (User should provide atleast one parameter from set_name, deploy or pod_name)
        :return: Bool, string
        """
        try:
            if set_name:
                set_type = const.STATEFULSET
            elif deploy:
                set_type = const.REPLICASET
            elif pod_name:
                log.info("Getting set name and set type of pod %s", pod_name)
                set_type, set_name = self.get_set_type_name(pod_name=pod_name)
                deploy = set_name
            else:
                return False, "Please provide atleast one of the parameters set_name, deploy or " \
                              "pod_name"
            if set_type == const.REPLICASET:
                log.info("Scaling %s replicas for deployment %s", num_replica, deploy)
                cmd = commands.KUBECTL_CREATE_REPLICA.format(num_replica, deploy)
                output = self.execute_cmd(cmd=cmd, read_lines=True)
                log.info("Response: %s", output)
                time.sleep(60)
                log.info("Check if pod of deployment %s exists", deploy)
                cmd = commands.KUBECTL_GET_POD_DETAILS.format(deploy)
                output = self.execute_cmd(cmd=cmd, read_lines=True, exc=False)
                status = True if output else False
                return status, deploy
            if set_type == const.STATEFULSET:
                resp = self.get_num_replicas(set_type, set_name)
                exp_replicas = int(resp[2]) if num_replica < int(resp[2]) else num_replica
                log.info("Scaling %s replicas for statefulset %s", num_replica, set_name)
                cmd = commands.KUBECTL_CREATE_STATEFULSET_REPLICA.format(set_name, num_replica)
                output = self.execute_cmd(cmd=cmd, read_lines=True)
                log.info("Response: %s", output)
                time.sleep(60)
                log.info("Check if correct number of replicas are created for %s", set_name)
                resp = self.get_num_replicas(set_type, set_name)
                if int(resp[1]) != num_replica:
                    return False, set_name
                status = True if exp_replicas == int(resp[1]) else False
                return status, set_name
            return False, "Set type should be either ReplicaSet or StatefulSet"
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.create_pod_replicas.__name__, error)
            return False, error

    def delete_pod(self, pod_name, force=False):
        """
        Helper function to delete pod gracefully or forcefully using kubectl delete command
        :param pod_name: Name of the pod
        :param force: Flag to indicate forceful or graceful deletion
        :return: Bool, output
        """
        try:
            log.info("Deleting pod %s", pod_name)
            extra_param = " --grace-period=0 --force" if force else ""
            cmd = commands.K8S_DELETE_POD.format(pod_name) + extra_param
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.info("Response: %s", output)
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.delete_pod.__name__, error)
            return False, error

        log.info("Successfully deleted pod %s", pod_name)
        return True, output

    def get_deploy_replicaset(self, pod_name):
        """
        Helper function to get deployment name and replicaset name of the given pod
        :param pod_name: Name of the pod
        :return: Bool, str, str (status, deployment name, replicaset name)
        """
        try:
            log.info("Getting details of pod %s", pod_name)
            cmd = commands.KUBECTL_GET_POD_DETAILS.format(pod_name)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.info("Response: %s", output)
            output = (output[0].split())[-1].split(',')
            deploy = output[0].split('=')[-1]
            replicaset = deploy + "-" + output[-1].split('=')[-1]
            return True, deploy, replicaset
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.get_deploy_replicaset.__name__, error)
            return False, error

    def get_num_replicas(self, set_type, set_name):
        """
        Helper function to get number of desired, current and ready replicas for given pod's set
        type and set name
        :param set_type: Type of the set (replica set or statefulset)
        :param set_name: Name of the set
        :return: Bool, str, str, str (Status, Desired replicas, Current replicas, Ready replicas)
        """
        try:
            log.debug("Set type: %s\n Set name: %s", set_type, set_name)
            log.info("Getting details of replicaset %s", set_name)
            if set_type == const.REPLICASET:
                cmd = commands.KUBECTL_GET_REPLICASET.format(set_name)
                output = self.execute_cmd(cmd=cmd, read_lines=True)
                log.info("Response: %s", output)
                output = output[0].split()
                log.info("Desired replicas: %s \nCurrent replicas: %s \nReady replicas: %s",
                         output[1], output[2], output[3])
                return True, output[1], output[2], output[3]
            if set_type == const.STATEFULSET:
                cmd = commands.KUBECTL_GET_STATEFULSET.format(set_name)
                output = self.execute_cmd(cmd=cmd, read_lines=True)
                log.info("Response: %s", output)
                ready_replicas, desired_replicas = ((output[0].split()[1]).strip().split("/"))
                log.info("Desired replicas: %s \nReady replicas: %s", desired_replicas,
                         ready_replicas)
                return True, ready_replicas, desired_replicas
            return False, "Please provide valid set type"
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.get_num_replicas.__name__, error)
            return False, error

    def delete_deployment(self, pod_name):
        """
        Helper function to delete deployment of given pod
        :param pod_name: Name of the pod
        :return: Bool, str, str (status, backup path of deployment, deployment name)
        """
        try:
            resp = self.get_deploy_replicaset(pod_name)
            deploy = resp[1]
            log.info("Deployment for pod %s is %s", pod_name, deploy)
            log.info("Taking deployment backup")
            resp = self.backup_deployment(deploy)
            backup_path = resp[1]
            log.info("Deleting deployment %s", pod_name)
            cmd = commands.KUBECTL_DEL_DEPLOY.format(deploy)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.info("Response: %s", output)
            time.sleep(60)
            log.info("Check if pod of deployment %s exists", deploy)
            cmd = commands.KUBECTL_GET_POD_DETAILS.format(deploy)
            output = self.execute_cmd(cmd=cmd, read_lines=True, exc=False)
            status = True if output else False
            return status, backup_path, deploy
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.delete_deployment.__name__, error)
            return False, error

    def recover_deployment_helm(self, deployment_name):
        """
        Helper function to recover the deleted deployment using helm
        :param deployment_name: Name of the deployment to be recovered
        :return: Bool, str, str (status, helm release name, release revision)
        """
        try:
            resp = self.get_helm_rel_name_rev(deployment_name)
            helm_rel = resp[1]
            rel_revision = resp[2]
            log.info("Rolling back the deployment %s using release %s and revision %s",
                     deployment_name, helm_rel, rel_revision)
            cmd = commands.HELM_ROLLBACK.format(helm_rel, rel_revision)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.info("Response: %s", output)
            time.sleep(60)
            log.info("Check if pod of deployment %s exists", deployment_name)
            cmd = commands.KUBECTL_GET_POD_DETAILS.format(deployment_name)
            output = self.execute_cmd(cmd=cmd, read_lines=True, exc=False)
            status = True if output else False
            return status, helm_rel, rel_revision
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.recover_deployment_helm.__name__, error)
            return False, error

    def recover_deployment_k8s(self, backup_path, deployment_name):
        """
        Helper function to recover the deleted deployment using kubectl
        :param deployment_name: Name of the deployment to be recovered
        :param backup_path: Path of the backup taken for given deployment
        :return: Bool, str (status, output)
        """
        try:
            log.info("Recovering deployment using kubectl")
            cmd = commands.KUBECTL_RECOVER_DEPLOY.format(backup_path)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.info("Response: %s", output)
            time.sleep(60)
            log.info("Check if pod of deployment %s exists", deployment_name)
            cmd = commands.KUBECTL_GET_POD_DETAILS.format(deployment_name)
            output = self.execute_cmd(cmd=cmd, read_lines=True, exc=False)
            status = True if output else False
            return status, output
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.recover_deployment_k8s.__name__, error)
            return False, error

    def backup_deployment(self, deployment_name):
        """
        Helper function to take backup of the given deployment
        :param deployment_name: Name of the deployment
        :return: Bool, str (status, path of the backup)
        """
        try:
            filename = deployment_name + "_backup.yaml"
            backup_path = os.path.join("/root", filename)
            log.info("Taking backup for deployment %s", deployment_name)
            cmd = commands.KUBECTL_DEPLOY_BACKUP.format(deployment_name, backup_path)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.debug("Backup for %s is stored at %s", deployment_name, backup_path)
            log.info("Response: %s", output)
            return True, backup_path
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.backup_deployment.__name__, error)
            return False, error

    def get_helm_rel_name_rev(self, deployment_name):
        """
        Helper function to get help release name and revision for given deployment
        :param deployment_name: Name of the deployment
        :return: Bool, str, str (status, helm rel name, helm rel revision)
        """
        try:
            search_str = deployment_name.split('-')[-1]
            log.info("Getting helm release details")
            cmd = commands.HELM_LIST + f" | grep {search_str}"
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            releases = []
            for out in output:
                releases.append(out.split()[0])
            for rel in releases:
                cmd = commands.HELM_GET_VALUES.format(rel)
                output = self.execute_cmd(cmd=cmd, read_lines=True)
                if any(deployment_name in s for s in output):
                    cmd = commands.HELM_HISTORY.format(rel)
                    output = self.execute_cmd(cmd=cmd, read_lines=True)
                    rev = output[-1].split()[0]
                    log.info("Release name: %s\nRevision: %s\n", rel, rev)
                    return True, rel, rev

            log.info("Couldn't find relevant release in helm")
            return False, releases
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      LogicalNode.get_helm_rel_name_rev.__name__, error)
            return False, error

    def get_all_pods_and_ips(self, pod_prefix) -> dict:
        """
        Helper function to get pods name with pod_prefix and their IPs
        :param: pod_prefix: Prefix to define the pod category
        :return: dict
        """
        pod_dict = {}
        output = self.execute_cmd(cmd=commands.KUBECTL_GET_POD_IPS, read_lines=True)
        for lines in output:
            if pod_prefix in lines:
                data = lines.strip()
                pod_name = data.split()[0]
                pod_ip = data.split()[1].replace("\n", "")
                pod_dict[pod_name.strip()] = pod_ip.strip()
        return pod_dict

    def get_container_of_pod(self, pod_name, container_prefix):
        """
        Gets containers with container_prefix (str) from the specified pod_name
        :param: pod_name : Pod name to query container of
        :param: container_prefix: Prefix to define container category
        :return: list
        """
        cmd = commands.KUBECTL_GET_POD_CONTAINERS.format(pod_name)
        output = self.execute_cmd(cmd=cmd, read_lines=True)
        output = output[0].split()
        container_list = []
        for each in output:
            if container_prefix in each:
                container_list.append(each)

        return container_list

    def get_recent_pod_name(self, deployment_name=None):
        """
        Helper function to get name of recently created pod
        :param deployment_name: Name of the deployment (Optional)
        :return: str (pod name)
        """
        if deployment_name:
            log.info("Getting recently created pod by deployment %s", deployment_name)
            cmd = commands.KUBECTL_GET_RECENT_POD_DEPLOY.format(deployment_name)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            pod_name = output[0].strip()
        else:
            log.info("Getting recently created pod in cluster")
            cmd = commands.KUBECTL_GET_RECENT_POD
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            pod_name = output[0].strip()
        return pod_name

    def get_all_pods(self, pod_prefix=None) -> list:
        """
        Helper function to get all pods name with pod_prefix
        :param: pod_prefix: Prefix to define the pod category
        :return: list
        """
        pods_list = []
        log.debug("Executing : %s", commands.KUBECTL_GET_POD_NAMES)
        output = self.execute_cmd(cmd=commands.KUBECTL_GET_POD_NAMES, read_lines=True)
        pods = [line.strip().replace("\n", "") for line in output]
        if pod_prefix is not None:
            for each in pods:
                if pod_prefix in each:
                    pods_list.append(each)
        else:
            pods_list = pods
        log.debug("Pods list : %s", pods_list)
        return pods_list

    def copy_file_to_container(self, local_file_path, pod_name, container_path, container_name):
        """
        Helper function to copy file on node to specified container inside the specified pod at \
            the specified path
        :param: local_file_path : Absolute local file path on the node
        :param: pod_name: Pod name where container resides
        :param: container_path: Path inside container where the file will be copied
        :param: container_name: Name of the container where the file will be copied
        """
        try:
            cmd = commands.K8S_CP_TO_CONTAINER_CMD.format(local_file_path, pod_name, \
                container_path, container_name)
            output = self.execute_cmd(cmd=cmd, exc=False)
            return True, output
        except Exception as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                    LogicalNode.copy_file_to_container.__name__, error)
            return False, error

    def get_machine_id_for_pod(self, pod_name: str):
        """
        Getting machine id for given pod
        """
        log.info("Getting machine id for pod: %s", pod_name)
        resp = self.send_k8s_cmd(operation="exec", pod=pod_name, namespace=const.NAMESPACE,
                                 command_suffix="cat /etc/machine-id",
                                 decode=True)
        return resp

    def get_pods_node_fqdn(self, pod_prefix):
        """
        Helper function to get pods name with pod_prefix and their node fqdn
        :param: pod_prefix: Prefix to define the pod category
        :return: dict
        """
        pod_dict = {}
        output = self.execute_cmd(cmd=commands.K8S_GET_CUSTOM_MGNT, read_lines=True)
        for line in output:
            if pod_prefix in line:
                data = line.strip()
                pod_name = data.split()[0]
                node_fqdn = data.split()[1]
                pod_dict[pod_name.strip()] = node_fqdn.strip()
        return pod_dict

    def get_pod_hostname(self, pod_name):
        """
        Helper function to get pod hostname
        :param pod_name: name of the pod
        :return: str
        """
        log.info("Getting pod hostname for pod %s", pod_name)
        cmd = commands.KUBECTL_GET_POD_HOSTNAME.format(pod_name)
        output = self.execute_cmd(cmd=cmd, read_lines=True)
        hostname = output[0].strip()
        return hostname

    def get_pod_fqdn(self, pod_name):
        """
        Helper function to get pod hostname
        :param pod_name: name of the pod
        :return: str
        """
        log.info("Getting pod hostname for pod %s", pod_name)
        cmd = commands.KUBECTL_GET_POD_FQDN.format(pod_name)
        output = self.execute_cmd(cmd=cmd, read_lines=True)
        hostname = output[0].strip()
        return hostname

    def kill_process_in_container(self, pod_name, container_name, process_name):
        """
        Kill specific process in container
        :param pod_name: Pod Name
        :param container_name: Container name
        :param process_name: Process name to be killed
        :return resp: String.
        """
        log.info("Getting PID of %s", process_name)
        cmd = commands.PIDOF_CMD.format(process_name)
        resp = self.send_k8s_cmd(operation="exec", pod=pod_name, namespace=const.NAMESPACE,
                                 command_suffix=f"-c {container_name} -- {cmd}",
                                 decode=True)
        log.info("Killing PID %s", resp)
        cmd = commands.KILL_CMD.format(resp)
        resp = self.send_k8s_cmd(operation="exec", pod=pod_name, namespace=const.NAMESPACE,
                                 command_suffix=f"-c {container_name} -- {cmd}",
                                 decode=True)
        return resp

    def get_all_cluster_processes(self, pod_name, container_name):
        """
        Function to get all cluster processes from consul
        :param pod_name: Name of the pod
        :param container_name: Name of the container
        :return: list (list of the processes running on container)
        """
        cmd = commands.GET_CLUSTER_PROCESSES_CMD
        resp = self.send_k8s_cmd(operation="exec", pod=pod_name, namespace=const.NAMESPACE,
                                 command_suffix=f"-c {container_name} -- {cmd}",
                                 decode=True)
        process_list = resp.splitlines()
        return process_list

    def get_deployment_name(self, pod_prefix=None):
        """
        Get deployment name using kubectl get deployment
        :param pod_prefix: Pod prefix(optional)
        return: list
        """
        resp_node = self.execute_cmd(cmd=commands.KUBECTL_GET_DEPLOYMENT, read_lines=True,
                                     exc=False)

        resp = [each.split()[0] for each in resp_node]
        deploy_list = resp
        if pod_prefix is not None:
            deploy_list = [each for each in resp if pod_prefix in each]
        return deploy_list

    def apply_k8s_deployment(self, file_path: str):
        """
        Apply the modified deployment file for pods, containers.
        :param file_path: Changed deployment file path from master node
        return Tuple
        """
        if not self.path_exists(file_path):
            return False, f"{file_path} does not exist on node {self.hostname}"
        log.info("Applying deployment from %s", file_path)
        resp = self.execute_cmd(cmd=commands.K8S_APPLY_YAML_CONFIG.format(file_path),
                                read_lines=True,exc=False)
        return True, resp

    def select_random_pod_container(self, pod_prefix: str,
                                    container_prefix: str, **kwargs):
        """
        Select random pod and container for the given pods and container prefix
        :param pod_prefix: Pod prefix/ Pod name in case of specific_pod: True
        :param container_prefix: Container Prefix
        :keyword bool specific_pod: True for retrieving containers from specific pod
        return pod_selected,container_selected
        """
        specific_pod = kwargs.get("specific_pod", False)
        if specific_pod:
            pod_selected = pod_prefix
        else:
            pod_list = self.get_all_pods(pod_prefix=pod_prefix)
            sys_random = random.SystemRandom()
            pod_selected = pod_list[sys_random.randint(0, len(pod_list) - 1)]
        log.info("Pod selected : %s", pod_selected)
        container_list = self.get_container_of_pod(pod_name=pod_selected,
                                                   container_prefix=container_prefix)
        container = container_list[sys_random.randint(0, len(container_list) - 1)]
        log.info("Container selected : %s", container)
        return pod_selected, container

    def restart_container_in_pod(self, pod_name, container_name):
        """Restarts a container within a pod. Prefer pod restart for single container pods."""
        raise NotImplementedError()

    def get_set_type_name(self, pod_name):
        """
        Function to get set type (i.e. Replicaset or Statefulset) and set name
        :param pod_name: Name of the pod
        :return: str, str
        """
        cmd = commands.KUBECTL_DESCRIBE_POD_CMD.format(pod_name)
        output = self.execute_cmd(cmd=cmd, read_lines=True)
        output = ([s for s in output if "Controlled By:" in s][0]).strip()
        set_type, set_name = ((output.split(":")[-1]).strip()).split("/")
        log.debug("Set type is: %s\n Set name is: %s\n", set_type, set_name)
        return set_type, set_name

    def get_sts_pods(self, pod_prefix=""):
        """
        Function to get name of the statefulset and its pods
        :param pod_prefix: Pod prefix
        :return: dict
        """
        sts_dict = dict()
        cmd = commands.KUBECTL_GET_STATEFULSET.format(pod_prefix)
        output = self.execute_cmd(cmd=cmd, read_lines=True)
        log.info("Response: %s", output)
        sts_list = [line.split()[0].strip() for line in output]
        if pod_prefix == "":
            sts_list.pop(0)
        for sts in sts_list:
            sts_dict[sts] = self.get_all_pods(sts)
        log.debug("Statefulsets with pods: %s", sts_dict)
        return sts_dict

    def get_pod_ports(self, pod_list, port_name="rgw-https"):
        """
        Function to get endpoint/container ports for given port name
        :param pod_list: List of the pods
        :param port_name: Name of the port
        :return: dict
        """
        pod_ip_dict = dict()
        for pod in pod_list:
            cmd = commands.KUBECTL_GET_POD_PORTS.format(pod)
            output = self.execute_cmd(cmd=cmd, read_lines=True)
            log.info("Response: %s", output)
            output = output[0].split()
            for out in output:
                json_obj = json.loads(out)
                for j_obj in json_obj:
                    if j_obj["name"] == port_name:
                        pod_ip_dict[pod] = j_obj["containerPort"]

        return pod_ip_dict
