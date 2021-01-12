#!/usr/bin/python
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
#

import logging
from typing import Union, Tuple, List
from commons.helpers.host import Host
from commons import commands

log = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"

class Health(Host):

    def get_ports_of_service(self, service:str)->List[str]:
        """
        Find all TCP ports for given running service
        """
        flag, output = self.execute_cmd(commands.NETSAT_CMD.format(service), read_lines=True)
        ports = []
        for line in output:
            out_list = line.split()
            ports.append(out_list[3].split(':')[-1])
        if not ports:
            return None, "Does Not Found Running Service '{}'".format(
                service)
        return ports

    def get_ports_for_firewall_cmd(self,service:str)->List[str]:
        """
        Find all ports exposed through firewall permanent service for given component
        """
        flag, output = self.execute_cmd(commands.FIREWALL_CMD.format(service), read_lines=True)
        ports = []
        for word in output:
            ports.append(word.split())
        if not ports:
            return None, "Does Not Found Running Service '{}'".format(
                service)
        return ports

    def get_disk_usage(self, dir_path:str , field_val:int=3)->float:
        """
        This function will return disk usage associated with given path.
        :param dir_path: Directory path of which size is to be calculated
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and percent used space respectively
        :return: float value of the disk usage
        """

        cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'" \
            .format(a=str(dir_path), b=int(field_val))
        log.debug(f"Running python command {cmd}")
        flag, res = self.execute_cmd(cmd)
        log.debug(res)
        res = res.decode("utf-8")
        return float(res.replace('\n',''))

    def get_cpu_usage(self)->float:
        """
        This function with fetch the system cpu usage percentage from remote host
        :return: system cpu usage
        """
        log.debug("Fetching system cpu usage from node {}".format(self.hostname))
        log.debug(commands.CPU_USAGE_CMD)
        flag, res = self.execute_cmd(commands.CPU_USAGE_CMD)
        log.debug(res)
        res = res.decode("utf-8")
        cpu_usage = float(res.replace('\n',''))
        return cpu_usage

    def get_memory_usage(self):
        """
        This function with fetch the system memory usage percentage from remote host
        :return: system memory usage in percent
        """
        log.debug("Fetching system memory usage from node {}".format(self.hostname))
        log.debug(commands.MEM_USAGE_CMD)
        flag, res = self.execute_cmd(commands.MEM_USAGE_CMD)
        log.debug(res)
        res = res.decode("utf-8")
        mem_usage = float(res.replace('\n',''))
        return mem_usage

    def get_pcs_service_systemd(self,service:str)->str:
        """
        Function to return pcs service systemd service name.
        This function will be usefull when service is not under systemctl
        :param service: Name of the pcs resource service
        :return: name of the service mentioned in systemd
        """
        cmd = commands.GREP_PCS_SERVICE_CMD.format(service)
        log.debug(f"Executing cmd: {cmd}")
        flag, resp = self.execute_cmd(cmd, read_lines=False)
        log.debug(resp)
        if not resp:
            return None

        resp = resp.decode().strip().replace("\t", "")
        resp1 = resp.split("):")
        for element in resp1:
            if "systemd:" in element:
                res = element.split("(systemd:")
                log.debug(res)
                return res[1]

    def pcs_cluster_start_stop(self, node_name:str, stop_flag:bool)->str:
        """
        This function Gracefully shutdown the given node using pcs cluster 
        stop command
        :param stopFlag: Shutdown if flag is True else Start the node
        """
        if stop_flag:
            cmd = commands.PCS_CLUSTER_STOP.format(node_name)
        else:
            cmd = commands.PCS_CLUSTER_START.format(node_name)

        log.debug(f"Executing cmd: {cmd}")
        flag, resp = self.execute_cmd(cmd, read_lines=False)
        log.debug(resp)
        if not resp:
            return None
        return resp[1]

    def pcs_status_grep(self, service:str)->str:
        """
        Function to return grepped pcs status services.
        :param str service: Name of the pcs resource service
        :return: pcs staus str response)
        """
        cmd = commands.GREP_PCS_SERVICE_CMD.format(service)
        log.debug(f"Executing cmd: {cmd}")
        resp = self.execute_cmd(cmd, read_lines=False)
        log.debug(resp)
        if not resp:
            return None
        return resp

    def pcs_resource_cleanup(self, options:str=None)->str:
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
        log.debug(f"Executing cmd: {cmd}")
        resp = self.execute_cmd(cmd, read_lines=False)
        log.debug(resp)
        if not resp:
            return None
        return resp

    def is_mero_online(self)->str:
        """
        Check whether all services are online in mero cluster
        :return: hctl reponse
        """
        flag, output = self.execute_cmd(commands.MOTR_STATUS_CMD, read_lines=True)
        log.debug(output)
        fail_list = ['failed', 'not running', 'offline']
        for line in output:
            if any(fail_str in line for fail_str in fail_list):
                return False, output
        return output

    def is_machine_already_configured(self)->bool:
        """
        This method checks that machine is already configured or not.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = commands.MOTR_STATUS_CMD
        log.debug(f"command : {mero_status_cmd}")
        flag, cmd_output = self.execute_cmd(mero_status_cmd, read_lines=True)
        if not cmd_output[0] or "command not found" in str(cmd_output[1]):
            log.debug("Machine is not configured..!")
            return False
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            if ('[' and ']') in output:
                log.debug(output)
        log.debug("Machine is already configured..!")
        return True

    def all_cluster_services_online(self, timeout=400)->Tuple[bool,str]:
        """
        This function will verify hctl status commands output. Check for
        all cluster services are online using hctl mero status command.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = commands.MOTR_STATUS_CMD
        log.debug(f"command : {mero_status_cmd}")
        flag, cmd_output = self.execute_cmd(mero_status_cmd, timeout=timeout, read_lines=True)
        if not cmd_output[0]:
            log.error(f"Command {mero_status_cmd} failed..!")
            return False, cmd_output[1]
        # removing \n character from each line of output
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            # fetching all services status
            if ']' in output:
                service_status = output.split(']')[0].split('[')[1].strip()
                if 'started' not in service_status:
                    log.error("services not starts successfully")
                    return False, "Services are not online"
            elif ("command not found" in output) or \
                    ("Cluster is not running." in output):
                log.debug("Machine is not configured..!")
                return False, f"{commands.MOTR_STATUS_CMD} command not found"
            else:
                log.debug("All other services are online")
                return True, "Server is Online"
