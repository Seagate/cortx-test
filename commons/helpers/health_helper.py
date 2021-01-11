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

################################################################################
# Standard libraries
################################################################################
import logging

################################################################################
# Local libraries
################################################################################
from commons.helpers.host import Host
from commons import commands
################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"

################################################################################
# Health Helper class
################################################################################
class Health(Host):
    ############################################################################
    # Get Ports
    ############################################################################
    def get_ports_of_service(self, service):
        """
        Find all TCP ports for given running service
        :param service: (boolean, response)
        :return:
        """
        try:
            flag, output = self.execute_cmd(commands.NETSAT_CMD.format(service), read_lines=True)
            ports = []
            for line in output:
                out_list = line.split()
                ports.append(out_list[3].split(':')[-1])
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Health.get_ports_of_service.__name__, error))
            return False, error
    # Provisioner
    def get_ports_for_firewall_cmd(self,service):
        """
        Find all ports exposed through firewall permanent service for given component
        :param service: service component
        :return: (boolean, response)
        """
        try:
            flag, output = self.execute_cmd(commands.FIREWALL_CMD.format(service), read_lines=True)
            ports = []
            for word in output:
                ports.append(word.split())
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Health.get_ports_for_firewall_cmd.__name__, error))
            return False, error

    ############################################################################
    # Resource usage
    ############################################################################
    def get_disk_usage(self):
        """
        #TODO: REMOVE
        This function will return disk usage associated with given path.
        :param path: Path to retrieve disk usage
        :return: Disk usage of given path or error in case of failure
        :type: (Boolean, float/str)
        """
        try:

            log.info("Running remote disk usage cmd.")
            cmd = "stat --file-system / --format %b,%S,%f"
            log.debug(f"Running cmd: {cmd} on host:{self.hostname}")
            flag, res = self.execute_cmd(cmd)
            res = res.decode("utf-8")
            f_res = res.replace("\n", "").split(",")
            f_blocks, f_frsize, f_bfree = int(
                f_res[0]), int(
                f_res[1]), int(
                f_res[2])
            total = (f_blocks * f_frsize)
            used = (f_blocks - f_bfree) * f_frsize
            result = format((float(used) / total) * 100, ".1f")
        except (Exception ,ZeroDivisionError) as error:
            log.error(EXCEPTION_MSG.format(Health.get_disk_usage.__name__, error))
            return False, error
        return True, result

    def disk_usage_python_interpreter_cmd(self,dir_path,field_val=3):
        """
        This function will return disk usage associated with given path.
        :param dir_path: Directory path of which size is to be calculated
        :type: str
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and percent used space respectively
        :type: int
        :return: Output of the python interpreter command
        :rtype: (int/float/str)
        """
        try:
            cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'" \
                .format(a=str(dir_path), b=int(field_val))
            log.info(f"Running python command {cmd}")
            flag, res = self.execute_cmd(cmd)
            res = res.decode("utf-8")
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Health.disk_usage_python_interpreter_cmd.__name__, error))
            return False, error
        return res

    def get_system_cpu_usage(self):
        """
        This function with fetch the system cpu usage percentage from remote host
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: system cpu usage
        :rtype: (bool, float)
        """
        try:
            log.info("Fetching system cpu usage from node {}".format(self.hostname))
            log.info(commands.CPU_USAGE_CMD)
            flag, resp = self.execute_cmd(commands.CPU_USAGE_CMD)
            log.info(resp)
            cpu_usage = float(resp[0])
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Health.get_system_cpu_usage.__name__, error))
            return False, error

        return True, cpu_usage

    def get_system_memory_usage(self):
        """
        This function with fetch the system memory usage percentage from remote host
        :return: system memory usage in percent
        :rtype: (bool, float)
        """
        try:
            log.info(
                "Fetching system memory usage from node {}".format(self.hostname))
            log.info(commands.MEM_USAGE_CMD)
            flag, resp = self.execute_cmd(commands.MEM_USAGE_CMD, read_lines=True)
            log.info(resp)
            mem_usage = float(resp[0])
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Health.get_system_memory_usage.__name__, error))
            return False, error
        return True, mem_usage

    ############################################################################
    # PCS command functions
    ############################################################################
    def get_pcs_service_systemd(self,service):
        """
        Function to return pcs service systemd service name.
        This function will be usefull when service is not under systemctl
        :param str service: Name of the pcs resource service
        :return: (True, name of the service mentioned in systemd)
        :type: tuple
        """
        cmd = commands.GREP_PCS_SERVICE_CMD.format(service)
        log.info(f"Executing cmd: {cmd}")
        try:
            flag, resp = self.execute_cmd(cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return False, None

            resp = resp.decode().strip().replace("\t", "")
            resp1 = resp.split("):")
            for element in resp1:
                if "systemd:" in element:
                    res = element.split("(systemd:")
                    log.info(res)
                    return True, res[1]
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Health.get_disk_usage.__name__, error))
            return False, error
    
    def pcs_cluster_start_stop(self, node_name, stop_flag):
        """
        This function Gracefully shutdown the given node
        using pcs cluster stop command
        :param bool stopFlag: Shutdown if flag is True else Start
                          the node
        :return: True/False
        :rtype: Boolean
        """
        if stop_flag:
            cmd = commands.PCS_CLUSTER_STOP.format(node_name)
        else:
            cmd = commands.PCS_CLUSTER_START.format(node_name)

        log.info(f"Executing cmd: {cmd}")
        try:
            flag, resp = self.execute_cmd(cmd, read_lines=False)
            log.info(resp)
            if not resp:
                return False, None
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Health.pcs_cluster_start_stop.__name__, error))

            return False, error
        return True, resp[1]

    def pcs_status_grep(self, service):
        """
        Function to return grepped pcs status services.
        :param str service: Name of the pcs resource service
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :return: (True, pcs staus str response)
        :type: tuple
        """
        cmd = commands.GREP_PCS_SERVICE_CMD.format(service)
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.execute_cmd(cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return None
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Health.get_disk_usage.__name__, error))
            return error
        return resp

    def pcs_resource_cleanup(self, options=None):
        """
        Perform pcs resource cleanup
        :param str options: option supported in resource cleanup eg: [<resource id>] [--node <node>]
        :return: (True, pcs str response)
        :type: tuple
        """
        if options:
            cmd = commands.PCS_RESOURCES_CLEANUP.format(options)
        else:
            options = " "
            cmd = commands.PCS_RESOURCES_CLEANUP.format(options)
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.execute_cmd(cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return False, None
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Health.pcs_resource_cleanup.__name__, error))
            return False, error
        return True, resp

    ############################################################################
    # Mero services / HTCL commands
    ############################################################################
    def is_mero_online(self):
        """
        Check whether all services are online in mero cluster
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: bool , response
        """
        try:
            flag, output = self.execute_cmd(commands.MERO_STATUS_CMD, read_lines=True)
            log.info(output)
            fail_list = ['failed', 'not running', 'offline']
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, output
            return True, output
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Health.is_mero_online.__name__, error))
            return False, error

    def is_machine_already_configured(self):
        """
        This method checks that machine is already configured or not.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = commands.MERO_STATUS_CMD
        log.info(f"command : {mero_status_cmd}")
        flag, cmd_output = self.execute_cmd(mero_status_cmd, read_lines=True)
        if not cmd_output[0] or "command not found" in str(cmd_output[1]):
            log.info("Machine is not configured..!")
            return False
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            if ('[' and ']') in output:
                log.info(output)
        log.info("Machine is already configured..!")
        return True

    def all_cluster_services_online(self, timeout=400):
        """
        This function will verify hctl status commands output. Check for
        all cluster services are online using hctl mero status command.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = commands.MERO_STATUS_CMD
        log.info(f"command : {mero_status_cmd}")
        flag, cmd_output = self.execute_cmd(mero_status_cmd, timeout_sec=timeout, read_lines=True)
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
                log.info("Machine is not configured..!")
                return False, f"{commands.MERO_STATUS_CMD} command not found"
            else:
                log.info("All other services are online")
                return True, "Server is Online"
