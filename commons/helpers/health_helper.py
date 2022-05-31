#!/usr/bin/python
"""File consists methods related to the health of the cluster."""
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

import json
import logging
import re
import time
from typing import Tuple, List, Any

import xmltodict

from commons import commands
from commons import constants as const
from commons.helpers.host import Host
from commons.helpers.pods_helper import LogicalNode
from commons.utils.assert_utils import assert_true
from commons.utils.system_utils import check_ping
from commons.utils.system_utils import run_remote_cmd
from config import CMN_CFG
from config import RAS_VAL

LOG = logging.getLogger(__name__)


class Health(Host):
    """Class for health related methods."""

    def get_ports_of_service(self, service: str) -> List[str] or None:
        """
        Find all TCP ports for given running service
        """
        output = self.execute_cmd(
            commands.NETSAT_CMD.format(service), read_lines=True)
        ports = list()
        for line in output:
            out_list = line.split()
            ports.append(out_list[3].split(':')[-1])
        if not ports:
            LOG.error("Does Not Found Running Service %s", service)
            return None
        return ports

    def get_ports_for_firewall_cmd(self, service: str) -> List[str] or None:
        """
        Find all ports exposed through firewall permanent service for given
        component
        """
        try:
            output = self.execute_cmd(
                commands.FIREWALL_CMD.format(service), read_lines=True)
            ports = list()
            for port in output[0].split():
                ports.append(port.split("/")[0])
            if not ports:
                LOG.error("Does Not Found Running Service %s", service)
                return None
        except OSError as error:
            LOG.error(error)
            return None
        return ports

    def get_disk_usage(self, dir_path: str, field_val: int = 3,
                       pod_name: str = None,
                       container_name: str = const.HAX_CONTAINER_NAME,
                       namespace: str = const.NAMESPACE) -> float:
        """
        Function will return disk usage associated with given path
        :param dir_path: Directory path of which size is to be calculated
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and
        percent used space respectively
        :param pod_name: name of the pod
        :param container_name: name of the container
        :param namespace: namespace name
        :return: float value of the disk usage
        """

        cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'" \
            .format(a=str(dir_path), b=int(field_val))
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            LOG.debug("Running python command %s", cmd)
            res = self.execute_cmd(cmd)
            LOG.debug(res)
            res = res.decode("utf-8")
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            node = LogicalNode(hostname=self.hostname, username=self.username,
                               password=self.password)
            if pod_name is None:
                resp = node.get_pod_name(pod_prefix=const.POD_NAME_PREFIX)
                assert_true(resp[0], resp[1])
                pod_name = resp[1]

            res = node.send_k8s_cmd(operation="exec", pod=pod_name, namespace=namespace,
                                    command_suffix=f"-c {container_name} -- {cmd}", decode=True)
            LOG.debug("Response of %s:\n %s ", cmd, res)
        return float(res.replace('\n', ''))

    def get_cpu_usage(self, pod_name: str = None,
                      container_name: str = const.HAX_CONTAINER_NAME,
                      namespace: str = const.NAMESPACE) -> float:
        """
        Function with fetch the system cpu usage percentage from remote host
        :param pod_name: name of the pod
        :param container_name: name of the container
        :param namespace: namespace name
        :return: system cpu usage
        """
        LOG.debug("Fetching system cpu usage from node %s", self.hostname)
        LOG.debug(commands.CPU_USAGE_CMD)
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            res = self.execute_cmd(commands.CPU_USAGE_CMD)
            LOG.debug(res)
            res = res.decode("utf-8")
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            node = LogicalNode(hostname=self.hostname, username=self.username,
                               password=self.password)
            if pod_name is None:
                resp = node.get_pod_name(pod_prefix=const.POD_NAME_PREFIX)
                assert_true(resp[0], resp[1])
                pod_name = resp[1]
            res = node.send_k8s_cmd(operation="exec", pod=pod_name, namespace=namespace,
                                    command_suffix=f"-c {container_name} -"
                                                   f"- {commands.CPU_USAGE_CMD}", decode=True)
            LOG.debug("Response of %s:\n %s ", commands.CPU_USAGE_CMD, res)
        cpu_usage = float(res.replace('\n', ''))
        return cpu_usage

    def get_memory_usage(self, namespace: str = const.NAMESPACE):
        """
        Function with fetch the system memory usage percentage from remote host
        :param namespace: namespace name
        :return: system memory usage in percent
        """
        LOG.debug("Fetching system memory usage from node %s", self.hostname)
        LOG.debug(commands.MEM_USAGE_CMD)
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            res = self.execute_cmd(commands.MEM_USAGE_CMD)
            LOG.debug(res)
            res = res.decode("utf-8")
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            container = const.HAX_CONTAINER_NAME
            node = LogicalNode(hostname=self.hostname, username=self.username,
                               password=self.password)
            resp = node.get_pod_name(pod_prefix=const.POD_NAME_PREFIX)
            assert_true(resp[0], resp[1])
            pod_name = resp[1]
            res = node.send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=namespace,
                command_suffix=f"-c {container} -- {commands.MEM_USAGE_CMD}", decode=True)
            LOG.debug("Response of %s:\n %s ", commands.MEM_USAGE_CMD, res)
        mem_usage = float(res.replace('\n', ''))
        return mem_usage

    def get_pcs_service_systemd(self, service: str) -> Any:
        """
        Function to return pcs service systemd service name.
        This function will be usefull when service is not under systemctl
        :param service: Name of the pcs resource service
        :return: name of the service mentioned in systemd
        """
        cmd = commands.GREP_PCS_SERVICE_CMD.format(service)
        LOG.debug("Executing cmd:%s", cmd)
        resp = self.execute_cmd(cmd, read_lines=False)
        LOG.debug(resp)
        if not resp:
            return None

        resp = resp.decode().strip().replace("\t", "")
        resp1 = resp.split("):")
        for element in resp1:
            if "systemd:" in element:
                res = element.split("(systemd:")
                LOG.debug(res)
                return res[1]
        return None

    def pcs_cluster_start_stop(self, node_name: str, stop_flag: bool) -> \
            str or None:
        """
        This function Gracefully shutdown the given node using pcs cluster
        stop command
        :param node_name: Name of the node
        :param stop_flag: Shutdown if flag is True else Start the node
        """
        if stop_flag:
            cmd = commands.PCS_CLUSTER_STOP.format(node_name)
        else:
            cmd = commands.PCS_CLUSTER_START.format(node_name)

        LOG.debug("Executing cmd: %s", cmd)
        resp = self.execute_cmd(cmd, read_lines=False)
        LOG.debug(resp)

        return resp[1]

    def pcs_status_grep(self, service: str) -> str or None:
        """
        Function to return grepped pcs status services
        :param str service: Name of the pcs resource service
        :return: pcs status str response
        """
        cmd = commands.GREP_PCS_SERVICE_CMD.format(service)
        LOG.debug("Executing cmd: %s", cmd)
        resp = self.execute_cmd(cmd, read_lines=False)
        LOG.debug(resp)

        return resp

    def pcs_resource_cleanup(self, options: str = None) -> str or None:
        """
        Perform pcs resource cleanup
        :param options: option supported in resource cleanup
        eg: [<resource id>] [--node <node>]
        :return:  pcs str response
        """
        if options:
            cmd = commands.PCS_RESOURCES_CLEANUP.format(options)
        else:
            options = " "
            cmd = commands.PCS_RESOURCES_CLEANUP.format(options)
        LOG.debug("Executing cmd: %s", cmd)
        resp = self.execute_cmd(cmd, read_lines=False)
        LOG.debug(resp)

        return resp

    def is_motr_online(self) -> bool:
        """
        Check whether all services are online in motr cluster.
        :return: hctl response.
        """
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            output = self.execute_cmd(commands.MOTR_STATUS_CMD, read_lines=True)
            LOG.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOG.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            result = self.hctl_status_json()
            for node in result["nodes"]:
                pod_name = node["name"]
                services = node["svcs"]
                for service in services:
                    if service["name"] != const.MOTR_CLIENT:
                        if service["status"] != "started":
                            LOG.error("%s service not started on pod %s", service["name"],
                                      pod_name)
                            return False
                if not services:
                    LOG.critical("No service found on pod %s", pod_name)
                    return False
        return True

    def is_machine_already_configured(self, namespace: str = const.NAMESPACE) -> bool:
        """
        This method checks that machine is already configured or not.
        ex - mero_status_cmd = "hctl status"
        :param namespace: namespace name
        :return: boolean
        """
        motr_status_cmd = commands.MOTR_STATUS_CMD
        LOG.debug("command %s:", motr_status_cmd)
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            cmd_output = self.execute_cmd(motr_status_cmd, read_lines=True)
            if not cmd_output[0] or "command not found" in str(cmd_output[1]):
                LOG.debug("Machine is not configured..!")
                return False
            cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
            for output in cmd_output:
                if ('[' and ']') in output:
                    LOG.debug(output)
            LOG.debug("Machine is already configured..!")
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            container = const.HAX_CONTAINER_NAME
            node = LogicalNode(hostname=self.hostname, username=self.username,
                               password=self.password)
            resp = node.get_pod_name(pod_prefix=const.POD_NAME_PREFIX)
            assert_true(resp[0], resp[1])
            pod_name = resp[1]
            cmd_output = node.send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=namespace,
                command_suffix=f"-c {container} -- {motr_status_cmd}",
                decode=True)
            LOG.debug("Response of %s:\n %s ", motr_status_cmd, cmd_output)
            if not cmd_output[0] or "command not found" in str(cmd_output[1]):
                LOG.debug("Machine is not configured..!")
                return False
            cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
            for output in cmd_output:
                if ('[' and ']') in output:
                    LOG.debug(output)
            LOG.debug("Machine is already configured..!")
        return True

    def all_cluster_services_online(self, timeout=400) -> Tuple[bool, str]:
        """
        Function will verify hctl status commands output. Check for
        all cluster services are online using hctl mero status command.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = commands.MOTR_STATUS_CMD
        LOG.debug("command :%s", mero_status_cmd)
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            cmd_output = self.execute_cmd(mero_status_cmd, timeout=timeout, read_lines=True)
            if not cmd_output[0]:
                LOG.error("Command %s failed..!", mero_status_cmd)
                return False, cmd_output[1]
            # removing \n character from each line of output
            cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
            for output in cmd_output:
                # fetching all services status
                if ']' in output:
                    service_status = output.split(']')[0].split('[')[1].strip()
                    if 'started' not in service_status:
                        LOG.error("services not starts successfully")
                        return False, "Services are not online"
                elif ("command not found" in output) or \
                        ("Cluster is not running." in output):
                    LOG.debug("Machine is not configured..!")
                    return False, f"{commands.MOTR_STATUS_CMD} command not found"
                else:
                    LOG.debug("All other services are online")
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            result = self.is_motr_online()
            if not result:
                return False, "Services are not online"
        return True, "Server is Online"

    def hctl_status_json(self, pod_name=None, namespace: str = const.NAMESPACE):
        """
        This will Check Node status, Logs the output in debug.log file and
        returns the response in json format
        :param pod_name: Running data pod name to fetch the hctl status
        :param namespace: namespace name
        :return: Json response of stdout
        :rtype: dict
        """
        result = dict()
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            LOG.info("Executing command for LR product family....")
            hctl_command = commands.HCTL_STATUS_CMD_JSON
            LOG.info("Executing Command %s on node %s",
                     hctl_command, self.hostname)
            result = self.execute_cmd(hctl_command, read_lines=False)
            result = result.decode("utf-8")
            # LOG.info("Response of the command %s:\n %s ",
            #          hctl_command, result)
            result = json.loads(result)
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            LOG.info("Executing command for LC product family....")
            container = const.HAX_CONTAINER_NAME
            node = LogicalNode(hostname=self.hostname, username=self.username,
                               password=self.password)
            if pod_name is None:
                resp = node.get_pod_name(pod_prefix=const.POD_NAME_PREFIX)
                assert_true(resp[0], resp[1])
                pod_name = resp[1]
            out = node.send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=namespace,
                command_suffix=f"-c {container} -- {commands.HCTL_STATUS_CMD_JSON}",
                decode=True)
            LOG.debug("Response of %s:\n %s ", commands.HCTL_STATUS_CMD_JSON, out)
            result = json.loads(out)
        return result

    def hctl_disk_status(self, pod_name=None, namespace: str = const.NAMESPACE):
        """
        This will Check disk status of the nodes
        returns the response in json format.
        :param pod_name: Running data pod name to fetch the hctl status
        :param namespace: namespace name
        :return: disk dict{'ssc-vm-g3-rhev4-1330': {'/dev/sdb': 'online', '/dev/sdc': 'online'},
            'ssc-vm-g3-rhev4-1331': {'/dev/sdb': 'online', '/dev/sdc':'failed'}}
        :rtype: dict
        """
        result = {}
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            LOG.info("Executing command for LR product family....")
            cmd = "| sed -e '1,/Devices:/ d' -e 's/^[ \t]*//'"
            hctl_command = commands.HCTL_DISK_STATUS + cmd
            LOG.info("Executing Command %s on node %s",
                     hctl_command, self.hostname)
            result = self.execute_cmd(hctl_command, read_lines=False)
            result = result.decode("utf-8")
        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            LOG.info("Executing command for LC product family....")
            container = const.HAX_CONTAINER_NAME
            node = LogicalNode(hostname=self.hostname, username=self.username,
                               password=self.password)
            cmd = "| sed -e '1,/Devices:/ d' -e 's/^[ \t]*//' | sed -n '/cortx-data/p;/\[/p'"
            if pod_name is None:
                resp = node.get_pod_name(pod_prefix=const.POD_NAME_PREFIX)
                assert_true(resp[0], resp[1])
                pod_name = resp[1]
            result = node.send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=namespace,
                command_suffix=f"-c {container} -- {commands.HCTL_DISK_STATUS} {cmd}",
                decode=True)
            LOG.debug("Response of %s:\n %s ", commands.HCTL_DISK_STATUS, result)
        node_disks_dict = {}
        for line in result.split("\n"):
            if '/dev' not in line:
                key = line.strip()
                node_disks_dict[key] = {}
            else:
                status, disk = line.strip().split("  ")
                node_disks_dict[key][disk] = status.strip("[]")
        LOG.info("Node with Disk status %s:\n", node_disks_dict)
        return node_disks_dict

    def hctl_status_service_status(self, service_name: str) -> Tuple[bool, dict]:
        """
        Checks all the services with given name are started using hctl status
        :param service_name: Service name to be checked in hctl status.
        :return: False if no services found or given service_name not started else returns True
        """
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            result = self.hctl_status_json()
            for node in result["nodes"]:
                pod_name = node["name"]
                services = node["svcs"]
                fids = list()
                for service in services:
                    if service_name in service["name"]:
                        fid = service["fid"]
                        fids.append(fid)
                        if service["status"] != "started":
                            LOG.error("%s service (%s) not started on pod %s", service_name, fid,
                                      pod_name)
                            return False, result
                if not services:
                    LOG.critical("No service found on pod %s", pod_name)
                    return False, result
                if not fids:
                    LOG.critical("No %s service found on pod %s", service_name, pod_name)
                    return False, result
            return True, result
        LOG.error("Product family: %s Unimplemented method", CMN_CFG.get("product_family"))
        return False, {}

    def get_sys_capacity(self):
        """Parse the hctl response to extract used, available and total capacity
        :return [tuple]: total_cap,avail_cap,used_cap
        """
        response = self.hctl_status_json()
        # LOG.info("HCTL response : \n%s", response)
        avail_cap = response['filesystem']['stats']['fs_avail_disk']
        LOG.info("Available Capacity : %s", avail_cap)
        total_cap = response['filesystem']['stats']['fs_total_disk']
        LOG.info("Total Capacity : %s", total_cap)
        used_cap = total_cap - avail_cap
        LOG.info("Used Capacity : %s", used_cap)
        return total_cap, avail_cap, used_cap

    def restart_pcs_resource(self, resource: str, wait_time: int = 30) \
            -> Tuple[bool, str]:
        """
        Restart given resource using pcs resource command
        :param resource: resource name from pcs resource
        :param wait_time: Wait time in sec after restart
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        LOG.info("Restarting resource : %s", resource)
        cmd = commands.PCS_RESOURCE_RESTART_CMD.format(resource)

        resp = self.execute_cmd(cmd, read_lines=True)
        resp = re.sub(r'[^\w-]', ' ', resp[0]).strip()
        time.sleep(wait_time)
        success_msg = "{} successfully restarted".format(resource)
        if success_msg == resp:
            LOG.info("Successfully restarted service %s", format(resource))
            return True, resp

        return False, resp

    def pcs_service_status(self, resource: str = None) -> Tuple[bool, str]:
        """
        Get status of given resource using pcs resource command
        :param resource: resource name from pcs resource
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        cmd = commands.PCS_RESOURCE_STATUS_CMD.format(resource)
        LOG.info("Running command : %s", cmd)

        resp = self.execute_cmd(cmd, read_lines=True)
        resp = ''.join(resp)
        check_msg = "Stopped"
        if check_msg in resp:
            LOG.info("%s is in stopped state", format(resource))
            return False, resp

        return True, resp

    def check_node_health(self, resource_cleanup: bool = False) -> tuple:
        """
        Check the node health (pcs and hctl status) and return True if all services up and running.
        1. Checking online status of node.
        2. Check hctl status response for all resources
        3. Check pcs status response for all resources
        :param resource_cleanup: If True will do pcs resources cleanup.
        :return: True or False, response/dictionary of failed hctl/pcs resources status.
        """
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LR and \
                CMN_CFG.get("product_type") == const.PROD_TYPE_NODE:
            LOG.info("Checking online status of %s node", self.hostname)
            response = check_ping(self.hostname)
            if not response:
                return response, "Node {} is offline.".format(self.hostname)
            LOG.info("Node %s is online.", self.hostname)

            LOG.info("Checking hctl status for %s node", self.hostname)
            status, hctl_result = run_remote_cmd(
                cmd=commands.MOTR_STATUS_CMD,
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                read_lines=True)
            if not status:
                return False, f"Failed to get HCTL status {hctl_result}"

            resp = self.hctl_status_json()
            hctl_services_failed = dict()
            svcs_elem = {'service': None, 'status': None}
            for node_data in resp['nodes']:
                hctl_services_failed[node_data['name']] = list()
                for svcs in node_data['svcs']:
                    temp_svc = svcs_elem.copy()
                    is_data = False
                    if svcs['name'] != const.MOTR_CLIENT and svcs['status'] != 'started':
                        temp_svc['service'] = svcs['name']
                        temp_svc['status'] = svcs['status']
                        is_data = True
                    if is_data:
                        hctl_services_failed[node_data['name']].append(temp_svc)
            node_hctl_failure = dict()
            for key, val in hctl_services_failed.items():
                if val:
                    node_hctl_failure[key] = val

            if resource_cleanup:
                LOG.info("cleanup pcs resources for %s node", self.hostname)
                response = self.pcs_resource_cleanup(options="--all")
                if "Cleaned up all resources on all nodes" not in str(response):
                    return False, "Failed to clean up all resources on all nodes"
                time.sleep(10)

            LOG.info("Checking pcs status for %s node", self.hostname)
            status, pcs_result = run_remote_cmd(
                cmd=commands.PCS_STATUS_CMD,
                hostname=self.hostname,
                username=self.username,
                password=self.password,
                read_lines=True)
            if not status:
                return False, f"Failed to get PCS status {pcs_result}"

            pcs_failed_data = dict()
            daemons = ["corosync:", "pacemaker:", "pcsd:"]
            LOG.info("Checking status of Daemons: %s", daemons)
            for daemon in daemons:
                for line in pcs_result:
                    if daemon in line:
                        if "active/enabled" not in line:
                            pcs_failed_data[daemon] = line
                            LOG.debug("Daemon %s status: %s", daemon, line)

            response = self.execute_cmd(cmd=commands.CMD_PCS_GET_XML, read_lines=False, exc=False)
            if isinstance(response, bytes):
                response = str(response, 'UTF-8')
            json_format = self.get_node_health_xml(pcs_response=response)
            crm_mon_res = json_format['crm_mon']['resources']
            no_node = int(json_format['crm_mon']['summary']['nodes_configured']['@number'])

            clone_set_dict = self.get_clone_set_status(crm_mon_res, no_node)
            for key, val in clone_set_dict.items():
                if "stonith" in key:
                    for srvnode, status in val.items():
                        currentnode = "srvnode-{}".format(key.split("-")[2])
                        if srvnode != currentnode and status != "Started":
                            pcs_failed_data[key] = val
                    continue
                for status in val.values():
                    if status != "Started":
                        pcs_failed_data[key] = val

            resource_dict = self.get_resource_status(crm_mon_res)
            for resource, value in resource_dict.items():
                if value['status'] != 'Started':
                    pcs_failed_data[resource] = value

            group_dict = self.get_group_status(crm_mon_res)
            for group, value in group_dict.items():
                if value['status'] != 'Started':
                    pcs_failed_data[group] = value
            node_health_failure = dict()
            if pcs_failed_data:
                LOG.debug(" ********* PCS status Response for %s ********* \n %s \n",
                          self.hostname, pcs_result)
                LOG.debug(" ********* PCS Clone set Response for %s ********* \n %s \n",
                          self.hostname, clone_set_dict)
                LOG.debug(" ********* PCS Resource Response for %s ********* \n %s \n",
                          self.hostname, resource_dict)
                LOG.debug(" ********* PCS Group Response for %s ********* \n %s \n",
                          self.hostname, group_dict)
                node_health_failure['PCS_STATUS'] = pcs_failed_data
            if node_hctl_failure:
                LOG.debug(" ********* HCTL status Response for %s ********* \n %s \n",
                          self.hostname, hctl_result)
                node_health_failure['HCTL_STATUS'] = node_hctl_failure
            if node_health_failure:
                LOG.error("Node health failure: %s", node_health_failure)
                return False, node_health_failure

        elif CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            resp = self.is_motr_online()
            if not resp:
                return resp, "cluster health is not good"
        return True, "cluster on {} up and running.".format(self.hostname)

    def reboot_node(self):
        """Reboot node
        """
        LOG.info("Restarting Node")
        cmd = commands.REBOOT_NODE_CMD
        resp = self.execute_cmd(cmd, read_lines=True, exc=False)
        LOG.info("Waiting for Node to Come UP %s", resp)
        time.sleep(RAS_VAL["ras_sspl_alert"]["reboot_delay"])
        return True

    @staticmethod
    def get_node_health_xml(pcs_response: str):
        """
        Get the node health pcs response in xml
        param: pcs_response: pcs response from pcs status xml command
        return: dict conversion of pcs status xml response command
        """
        formatted_data = pcs_response.replace("\n  ", "").replace(
            "\n", ",").replace(",</", "</").split(",")[1:-1]
        temp_dict = json.dumps(xmltodict.parse(formatted_data[0]))
        json_format = json.loads(temp_dict)
        return json_format

    # pylint: disable-msg=too-many-nested-blocks
    # pylint: disable-msg=too-many-statements
    # pylint: disable-msg=too-many-branches
    # pylint: disable=broad-except
    @staticmethod
    def get_clone_set_status(crm_mon_res: dict, no_node: int):
        """
        Get the clone set from node health pcs response
        param: crm_mon_res: pcs response from pcs status xml command
        param: no_node: no of nodes
        return: dict
        """
        clone_set = dict()
        node_dflt = [f'srvnode-{node}.data.private' for node in range(1, no_node + 1)]
        setup_type = ''
        try:
            setup_type = CMN_CFG["setup_type"]
        except Exception as error:
            LOG.debug("setup_type not found %s", error)
        if setup_type == "OVA":
            for clone_elem_resp in crm_mon_res['clone']:
                resources = list()
                if clone_elem_resp["@id"] == 'monitor_group-clone':
                    resources.append(clone_elem_resp['group']['resource'])
                elif clone_elem_resp["@id"] == 'io_group-clone':
                    for resource_ele in clone_elem_resp['group']['resource']:
                        resources.append(resource_ele)
                temp_dict = dict()
                clone_set[clone_elem_resp["@id"]] = dict()
                for resource in resources:
                    if int(resource['@nodes_running_on']):
                        node = resource['node']['@name']
                        if resource['@blocked'] == 'true':
                            temp_dict[node] = 'FAILED'
                        else:
                            temp_dict[node] = resource['@role']
                    else:
                        temp_dict[node_dflt[0]] = resource['@role']
                clone_set[clone_elem_resp["@id"]] = temp_dict
        else:
            for clone_elem_resp in crm_mon_res['clone']:
                if clone_elem_resp["@id"] == 'monitor_group-clone':
                    if no_node != 1:
                        resource = list()
                        for val in clone_elem_resp['group']:
                            resource.append(val['resource'])
                    else:
                        resource = clone_elem_resp['group']['resource']
                else:
                    resource = clone_elem_resp['resource']
                temp_dict = dict()
                clone_set[clone_elem_resp["@id"]] = dict()
                if no_node == 1:
                    if int(resource['@nodes_running_on']):
                        node = resource['node']['@name']
                        if resource['@blocked'] == 'true':
                            temp_dict[node] = 'FAILED'
                        else:
                            temp_dict[node] = resource['@role']
                    else:
                        temp_dict[node_dflt[0]] = resource['@role']
                    clone_set[clone_elem_resp["@id"]] = temp_dict
                else:
                    temp_nodes = node_dflt[:]
                    for elem in resource:
                        if int(elem['@nodes_running_on']):
                            node = elem['node']['@name']
                            if elem['@blocked'] == 'true':
                                temp_dict[node] = 'FAILED'
                            else:
                                temp_dict[node] = elem['@role']
                            temp_nodes.remove(node)
                        else:
                            for node in temp_nodes:
                                temp_dict[node] = elem['@role']
                                clone_set[clone_elem_resp["@id"]] = temp_dict
                        clone_set[clone_elem_resp["@id"]] = temp_dict
        return clone_set

    @staticmethod
    def get_resource_status(crm_mon_res: dict):
        """
        Get the resource status from node health pcs response
        param: crm_mon_res: pcs response from pcs status xml command
        return: dict
        """
        clone_set = dict()
        for resource_elem in crm_mon_res['resource']:
            temp_dict = {'status': None, 'srvnode': None}
            clone_set[resource_elem["@id"]] = dict()
            if int(resource_elem['@nodes_running_on']):
                if resource_elem['@blocked'] == 'true':
                    temp_dict['status'] = 'FAILED'
                    temp_dict['srvnode'] = resource_elem['node']['@name']
                else:
                    temp_dict['status'] = resource_elem['@role']
                    temp_dict['srvnode'] = resource_elem['node']['@name']
            else:
                temp_dict['status'] = resource_elem['@role']
            clone_set[resource_elem["@id"]] = temp_dict
        return clone_set

    @staticmethod
    def get_group_status(crm_mon_res: dict):
        """
        Get the group status from node health pcs response
        param: crm_mon_res: pcs response from pcs status xml command
        return: dict
        """
        clone_set = dict()
        for group in crm_mon_res['group']:
            resource = list()
            if isinstance(group['resource'], dict):
                resource.append(group['resource'])
            elif isinstance(group['resource'], list):
                resource = group['resource']
            else:
                LOG.warning("Resource group info format is not as expected : %s",
                            group['resource'])

            for group_elem in resource:
                temp_dict = {'status': None, 'srvnode': None}
                clone_set[group_elem["@id"]] = dict()
                if int(group_elem['@nodes_running_on']):
                    if group_elem['@blocked'] == 'true':
                        temp_dict['status'] = 'FAILED'
                        temp_dict['srvnode'] = group_elem['node']['@name']
                    else:
                        temp_dict['status'] = group_elem['@role']
                        temp_dict['srvnode'] = group_elem['node']['@name']
                else:
                    temp_dict['status'] = group_elem['@role']
                clone_set[group_elem["@id"]] = temp_dict
        return clone_set

    def pcs_restart_cluster(self):
        """
        Function starts and stops the cluster using the pcs command.
        command used:
            pcs cluster stop --all
            pcs cluster start --all
            pcs resource cleanup --all
        :return: (Boolean and response)
        """
        resp = self.pcs_cluster_start_stop("--all", stop_flag=True)
        LOG.info(resp)
        time.sleep(10)
        resp = self.pcs_cluster_start_stop("--all", stop_flag=False)
        LOG.info(resp)
        time.sleep(30)  # Hardcoded: Default time is between 10 and 30 seconds.
        response = self.pcs_resource_cleanup(options="--all")
        if "Cleaned up all resources on all nodes" not in str(response):
            return False, "Failed to clean up all resources on all nodes"
        time.sleep(10)
        response = self.check_node_health()
        time.sleep(10)
        LOG.info(response)

        return response

    def pcs_resource_ops_cmd(self, command: str, resources: list, srvnode: str = "",
                             wait_time: int = 30) -> bool:
        """
        Perform given operation on pcs resource using pcs resource command
        :param command: pcs operation to be performed on resource
        :param resources: list of resource names from pcs resource
        :param srvnode: Name of the server on which command to be performed
        :param wait_time: Wait time in sec after performing operation
        :return: boolean
        :rtype: bool
        """
        valid_commands = {"ban", "clear", "enable", "disable", "restart"}
        if command not in valid_commands:
            raise ValueError("Invalid command")
        for rsrc in resources:
            LOG.info("Performing %s on resource %s", command, rsrc)
            cmd = commands.PCS_RESOURCE_CMD.format(command, rsrc, srvnode)
            LOG.info("Running command: %s", cmd)
            resp = self.execute_cmd(cmd, read_lines=True)
            LOG.debug("Response: %s", resp)
            time.sleep(wait_time)
            LOG.info("Successfully performed %s on %s", command, rsrc)

        return True

    def check_nw_interface_status(self, nw_infcs: list = None):
        """
        Function to get status of all available network interfaces on node.
        """
        LOG.info("Getting all network interfaces on host")
        if nw_infcs is None:
            LOG.debug("Running command: %s", commands.GET_ALL_NW_IFCS_CMD)
            res = self.execute_cmd(commands.GET_ALL_NW_IFCS_CMD)
            nw_infcs = list(filter(None, res.decode("utf-8").split('\n')))
        LOG.debug(nw_infcs)
        LOG.info("Check status of all available network interfaces")
        status = dict()
        for net_work in nw_infcs:
            stat_cmd = commands.IP_LINK_SHOW_CMD.format(net_work, "DOWN")
            nw_st = self.execute_cmd(stat_cmd, exc=False)
            nw_st = list(filter(None, nw_st.decode("utf-8").split('\n')))
            status[net_work] = nw_st

        return status

    def get_current_srvnode(self) -> dict:
        """
        Returns: Bool, Name of current server
        rtype: bool, str
        """
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|:')
        node = list()
        h_list = list()
        cmd = commands.CMD_SALT_GET_HOST
        LOG.info("Running command: %s", cmd)
        resp = self.execute_cmd(cmd)
        resp = (resp.decode("utf-8").split('\n'))
        for ele in resp:
            if 'srvnode' not in ansi_escape.sub('', ele).strip():
                node.append(ansi_escape.sub('', ele).strip())
            else:
                h_string = ansi_escape.sub('', ele).strip() + ".data.private"
                h_list.append(h_string)

        d_node = dict(zip(node, h_list))
        return d_node

    def disable_pcs_resource(self, resource: str, wait_time: int = 30) \
            -> bool:
        """
        Disable given resource using pcs resource command
        :param resource: resource name from pcs resource
        :param wait_time: Wait time in sec after restart
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        LOG.info("Disabling resource : %s", resource)
        cmd = commands.PCS_RESOURCE_DISABLE_CMD.format(resource)

        self.execute_cmd(cmd, read_lines=True)
        time.sleep(wait_time)

        return True

    def enable_pcs_resource(self, resource: str, wait_time: int = 30) \
            -> bool:
        """
        Enable given resource using pcs resource command
        :param resource: resource name from pcs resource
        :param wait_time: Wait time in sec after restart
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        LOG.info("Enabling resource : %s", resource)
        cmd = commands.PCS_RESOURCE_ENABLE_CMD.format(resource)

        self.execute_cmd(cmd, read_lines=True)
        time.sleep(wait_time)

        return True

    @staticmethod
    def check_cortx_cluster_health(node, retry=3):
        """
        Function to check cortx cluster health
        :param node: node of a cluster
        :param retry: number of attempts to perform health check
        :return bool
        :True for healthy
        """
        r_try = 1
        hostname = node['hostname']
        health = Health(hostname=hostname,
                        username=node['username'],
                        password=node['password'])
        health_result = False
        capacity_result = False
        while r_try <= retry:
            try:
                health_result = health.check_node_health(node)
                ha_result = health.get_sys_capacity()
                ha_used_percent = round((ha_result[2] / ha_result[0]) * 100, 1)
                capacity_result = ha_used_percent < 98.0
                health.disconnect()
                break
            except BaseException as error:
                LOG.warning("%s exception occurred while performing Health check", error)
                delay = pow(r_try, 4)
                LOG.info("Retrying in %s seconds", delay)
                time.sleep(delay)
                r_try += 1
        if health_result and capacity_result:
            return True
        return False

    def get_pod_svc_status(self, pod_list, fail=True, hostname=None, pod_name=None):
        """
        Helper function to get pod wise service status
        :param pod_list: List pof pods
        :param fail: Flag to check failed/started status of services
        :param hostname: Hostname of the pod
        :param pod_name: Running pod to fetch the hctl status
        :return: Bool, list
        """
        pod_obj = LogicalNode(hostname=self.hostname, username=self.username,
                              password=self.password)
        try:
            results = list()
            if fail:
                search_str = ["failed", "offline", "unknown"]
            else:
                search_str = ["started", "online"]
            LOG.info("Getting services status for all pods")
            hctl_output = self.hctl_status_json(pod_name=pod_name)
            for pod in pod_list:
                if hostname is None:
                    hostname = pod_obj.get_pod_hostname(pod_name=pod)
                for node in hctl_output["nodes"]:
                    if hostname == node["name"]:
                        services = node["svcs"]
                        for svc in services:
                            status = True if svc["status"] in search_str else False
                            if not status:
                                results.append(status)
                        break
            return True, results
        except Exception as error:
            LOG.error("*ERROR* An exception occurred in %s: %s",
                      Health.get_pod_svc_status.__name__, error)
            return False, error

    def hctl_status_get_svc_fids(self):
        """
        Get FIDs for all services using hctl status command
        :return: Bool, List of FIDs
        """
        pod_fids = dict()
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            result = self.hctl_status_json()
            for node in result["nodes"]:
                pod_name = node["name"]
                services = node["svcs"]
                for service in services:
                    if service["name"] not in pod_fids:
                        pod_fids[service["name"]] = [service["fid"]]
                    else:
                        pod_fids[service["name"]].append(service["fid"])
                LOG.info("Extracted FIDs from pod %s", pod_name)
            if not pod_fids:
                LOG.critical("No services found in cluster")
                return False, result
            return True, pod_fids

        return False, f"Expected Product family is {const.PROD_FAMILY_LC}. " \
                      f"\nActual product family is {CMN_CFG.get('product_family')}"
