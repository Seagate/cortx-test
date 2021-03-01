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
import time
import re
from typing import Tuple, List, Any
from commons.helpers.host import Host
from commons import commands

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
        output = self.execute_cmd(
            commands.FIREWALL_CMD.format(service), read_lines=True)
        ports = []
        for word in output:
            ports.append(word.split())
        if not ports:
            LOG.error("Does Not Found Running Service %s", service)
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
