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
import re
from typing import Tuple, List, Any
from commons.helpers.host import Host
from commons import commands
from commons.utils.system_utils import check_ping

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
        LOG.info("Response of the command %s:\n %s ",
                 hctl_command, result)
        result = json.loads(result)

        return result

    def get_sys_capacity(self):
        """Parse the hctl response to extract used, available and total capacity

        :return [tuple]: total_cap,avail_cap,used_cap
        """
        response = self.hctl_status_json()
        LOG.info("HCTL response : \n%s", response)
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

    def check_node_health(self) -> tuple:
        """
        Check the node health and return True if all services up and running.

        1. Checking online status of node.
        2. Check hax, confd, ioservice, s3server services up and running.
        3. Check corosync, pacemaker, pcsd Daemons up and running.
        4. Check kibana, csm-agent, csm-web  resource groups up and running.
        5. Check s3auth, io_group, sspl-ll, s3backprod resources up and running.
        :return: True or False, response.
        """
        LOG.info("Checking online status of %s node", self.hostname)
        response = check_ping(self.hostname)
        if not response:
            return response, "Node {} is offline.".format(self.hostname)
        LOG.info("Node %s is online.", self.hostname)

        LOG.info("Checking hctl status for %s node", self.hostname)
        response = self.execute_cmd(cmd=commands.MOTR_STATUS_CMD, read_lines=True)
        services = ["hax", "confd", "ioservice", "s3server"]
        LOG.info("Checking status of services: %s", services)
        LOG.info(response)
        for line in response[1]:
            if any([True if service in line else False for service in services]):
                if not line.strip().startswith("[started]"):
                    LOG.error("service down: %s", line)
                    return False, response[0]
        if "Cluster is not running" in ",".join(response[1]) or not response[0]:
            return False, response[1]
        LOG.info("Services: %s up and running", services)

        LOG.info("Checking pcs status for %s node", self.hostname)
        response = self.pcs_resource_cleanup(options="--all")
        if "Cleaned up all resources on all nodes" not in str(response):
            return False, "Failed to clean up all resources on all nodes"
        time.sleep(10)
        response = self.execute_cmd(cmd=commands.PCS_STATUS_CMD, read_lines=True)
        LOG.info(response)
        if "cluster is not currently running on this node" in ",".join(response[1]):
            LOG.info("cluster is not currently running on this node: %s", self.hostname)
            return False, "cluster is not currently running on this node: {}".format(self.hostname)

        daemons = ["corosync", "pacemaker", "pcsd"]
        LOG.info("Checking status of Daemons: %s", daemons)
        for line in response[1]:
            if any([True if daemon in line else False for daemon in daemons]):
                if "active/enabled" not in line:
                    return False, "daemons down: {}".format(line)
        LOG.info("Daemons are active/enabled: %s", daemons)

        resource_group = ["kibana", "csm-agent", "csm-web", "s3backprod"]
        LOG.info("Checking status of resource group: %s", resource_group)
        for line in response[1]:
            if any([True if resource in line else False for resource in resource_group]):
                if "Started" not in line:
                    return False, "resource down: {}".format(line)
        LOG.info("All resource groups are running: %s", resource_group)

        resources = ["s3auth", "io_group", "sspl-ll"]
        LOG.info("Checking status of resources: %s", resources)
        for line in response[1]:
            if any([True if resource in line else False for resource in resources]):
                if "Started" not in response[1][response[1].index(line) + 1]:
                    return False, "resource down: {}".format(
                        " ".join([line, response[1][response[1].index(line) + 1]]))
        LOG.info("All resources are running: %s", resources)

        if "Stopped" in ",".join(response[1]) or not response[0]:
            return False, response[1]

        return True, "cluster {} up and running.".format(self.hostname)

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

    def pcs_resource_cmd(self, command: str, resources: list, srvnode: str = "",
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

    def get_current_srvnode(self) -> Tuple[bool, str]:
        """
        Returns: Bool, Name of current server
        rtype: bool, str
        """
        cmd = commands.CMD_PCS_STATUS_FULL + " | grep 'Current DC:'"
        LOG.info("Running command: %s", cmd)
        resp = self.execute_cmd(cmd)
        resp = (resp.decode("utf-8").split('\n'))[0].split()
        for ele in resp:
            if "srvnode" in ele:
                return True, ele

        return False, "Current srvnode not found"
