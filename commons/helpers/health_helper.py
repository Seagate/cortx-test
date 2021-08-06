#!/usr/bin/python

"""File consists methods related to the health of the cluster."""

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
#

import logging
import json
import time
import xmltodict
import re
from typing import Tuple, List, Any
from commons.helpers.host import Host
from commons import commands
from commons.utils.system_utils import check_ping
from commons.utils.system_utils import run_remote_cmd
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
        ports = []
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
            ports = []
            for port in output[0].split():
                ports.append(port.split("/")[0])
            if not ports:
                LOG.error("Does Not Found Running Service %s", service)
                return None
        except OSError as error:
            LOG.error(error)
            return None
        return ports

    def get_disk_usage(self, dir_path: str, field_val: int = 3) -> float:
        """
        Function will return disk usage associated with given path.

        :param dir_path: Directory path of which size is to be calculated
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and
        percent used space respectively
        :return: float value of the disk usage
        """

        cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'" \
            .format(a=str(dir_path), b=int(field_val))
        LOG.debug("Running python command %s", cmd)
        res = self.execute_cmd(cmd)
        LOG.debug(res)
        res = res.decode("utf-8")
        return float(res.replace('\n', ''))

    def get_cpu_usage(self) -> float:
        """
        Function with fetch the system cpu usage percentage from remote host

        :return: system cpu usage
        """
        LOG.debug("Fetching system cpu usage from node %s", self.hostname)
        LOG.debug(commands.CPU_USAGE_CMD)
        res = self.execute_cmd(commands.CPU_USAGE_CMD)
        LOG.debug(res)
        res = res.decode("utf-8")
        cpu_usage = float(res.replace('\n', ''))
        return cpu_usage

    def get_memory_usage(self):
        """
        Function with fetch the system memory usage percentage from remote host

        :return: system memory usage in percent
        """
        LOG.debug(
            "Fetching system memory usage from node %s", self.hostname)
        LOG.debug(commands.MEM_USAGE_CMD)
        res = self.execute_cmd(commands.MEM_USAGE_CMD)
        LOG.debug(res)
        res = res.decode("utf-8")
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
        Function to return grepped pcs status services.

        :param str service: Name of the pcs resource service
        :return: pcs staus str response)
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
        output = self.execute_cmd(commands.MOTR_STATUS_CMD, read_lines=True)
        LOG.debug(output)
        fail_list = ['failed', 'not running', 'offline']
        LOG.debug(fail_list)
        for line in output:
            if any(fail_str in line for fail_str in fail_list):
                return False

        return True

    def is_machine_already_configured(self) -> bool:
        """
        This method checks that machine is already configured or not.

        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        motr_status_cmd = commands.MOTR_STATUS_CMD
        LOG.debug("command %s:", motr_status_cmd)
        cmd_output = self.execute_cmd(motr_status_cmd, read_lines=True)
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
        cmd_output = self.execute_cmd(
            mero_status_cmd, timeout=timeout, read_lines=True)
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
                return True, "Server is Online"
        return True, "Server is Online"

    def hctl_status_json(self):
        """
        This will Check Node status, Logs the output in debug.log file and
        returns the response in json format.
        :param str node: Node on which status to be checked
        :return: Json response of stdout
        :rtype: dict
        """
        hctl_command = commands.HCTL_STATUS_CMD_JSON
        LOG.info("Executing Command %s on node %s",
                 hctl_command, self.hostname)
        result = self.execute_cmd(hctl_command, read_lines=False)
        result = result.decode("utf-8")
        # LOG.info("Response of the command %s:\n %s ",
        #          hctl_command, result)
        result = json.loads(result)

        return result

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
        hctl_services_failed = {}
        svcs_elem = {'service': None, 'status': None}
        for node_data in resp['nodes']:
            hctl_services_failed[node_data['name']] = list()
            for svcs in node_data['svcs']:
                temp_svc = svcs_elem.copy()
                is_data = False
                if svcs['name'] != "m0_client" and svcs['status'] != 'started':
                    temp_svc['service'] = svcs['name']
                    temp_svc['status'] = svcs['status']
                    is_data = True
                if is_data:
                    hctl_services_failed[node_data['name']].append(temp_svc)
        node_hctl_failure = {}
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

        pcs_failed_data = {}
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
        node_health_failure = {}
        if pcs_failed_data:
            LOG.debug(" ********* PCS status Response for %s ********* \n %s \n", self.hostname,
                      pcs_result)
            LOG.debug(" ********* PCS Clone set Response for %s ********* \n %s \n",
                      self.hostname, clone_set_dict)
            LOG.debug(" ********* PCS Resource Response for %s ********* \n %s \n",
                      self.hostname, resource_dict)
            LOG.debug(" ********* PCS Group Response for %s ********* \n %s \n",
                      self.hostname, group_dict)
            node_health_failure['PCS_STATUS'] = pcs_failed_data
        if node_hctl_failure:
            LOG.debug(" ********* HCTL status Response for %s ********* \n %s \n", self.hostname,
                      hctl_result)
            node_health_failure['HCTL_STATUS'] = node_hctl_failure
        if node_health_failure:
            LOG.error("Node health failure: %s", node_health_failure)
            return False, node_health_failure

        return True, "cluster on {} up and running.".format(self.hostname)

    def reboot_node(self):
        """Reboot node
        """
        LOG.info("Restarting Node")
        cmd = commands.REBOOT_NODE_CMD
        resp = self.execute_cmd(cmd, read_lines=True, exc=False)
        LOG.info("Waiting for Node to Come UP")
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

    @staticmethod
    def get_clone_set_status(crm_mon_res: dict, no_node: int):
        """
        Get the clone set from node health pcs response
        param: crm_mon_res: pcs response from pcs status xml command
        param: no_node: no of nodes
        return: dict
        """
        clone_set = {}
        node_dflt = [f'srvnode-{node}.data.private' for node in range(1, no_node+1)]
        for clone_elem_resp in crm_mon_res['clone']:
            if clone_elem_resp["@id"] == 'monitor_group-clone':
                if no_node != 1:
                    resource = []
                    for val in clone_elem_resp['group']:
                        resource.append(val['resource'])
                else:
                    resource = clone_elem_resp['group']['resource']
            else:
                resource = clone_elem_resp['resource']
            temp_dict = {}
            clone_set[clone_elem_resp["@id"]] = {}
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
        clone_set = {}
        for resource_elem in crm_mon_res['resource']:
            temp_dict = {'status': None, 'srvnode': None}
            clone_set[resource_elem["@id"]] = {}
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
        clone_set = {}
        for group in crm_mon_res['group']:
            resource = []
            if group['@id'] == 'ha_group':
                resource.append(group['resource'])
            else:
                resource = group['resource']

            for group_elem in resource:
                temp_dict = {'status': None, 'srvnode': None}
                clone_set[group_elem["@id"]] = {}
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
        time.sleep(30)  # Hardcoded: Default time is between 10 to 30 seconds.
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

    def check_nw_interface_status(self):
        """
        Function to get status of all available network interfaces on node.
        """
        LOG.info("Getting all network interfaces on host")
        LOG.debug("Running command: %s", commands.GET_ALL_NW_IFCS_CMD)
        res = self.execute_cmd(commands.GET_ALL_NW_IFCS_CMD)
        nw_ifcs = list(filter(None, res.decode("utf-8").split('\n')))
        LOG.debug(nw_ifcs)
        LOG.info("Check status of all available network interfaces")
        status = {}
        for nw in nw_ifcs:
            stat_cmd = commands.IP_LINK_SHOW_CMD.format(nw, "DOWN")
            nw_st = self.execute_cmd(stat_cmd, exc=False)
            nw_st = list(filter(None, nw_st.decode("utf-8").split('\n')))
            status[nw] = nw_st

        return status

    def get_current_srvnode(self) -> dict:
        """
        Returns: Bool, Name of current server
        rtype: bool, str
        """
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|:')
        node = []
        h_list = []
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
            -> Tuple[bool, str]:
        """
        Disable given resource using pcs resource command

        :param resource: resource name from pcs resource
        :param wait_time: Wait time in sec after restart
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        LOG.info("Disabling resource : %s", resource)
        cmd = commands.PCS_RESOURCE_DISABLE_CMD.format(resource)

        resp = self.execute_cmd(cmd, read_lines=True)
        time.sleep(wait_time)

        return True

    def enable_pcs_resource(self, resource: str, wait_time: int = 30) \
            -> Tuple[bool, str]:
        """
        Enable given resource using pcs resource command

        :param resource: resource name from pcs resource
        :param wait_time: Wait time in sec after restart
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        LOG.info("Enabling resource : %s", resource)
        cmd = commands.PCS_RESOURCE_ENABLE_CMD.format(resource)

        resp = self.execute_cmd(cmd, read_lines=True)
        time.sleep(wait_time)

        return True
