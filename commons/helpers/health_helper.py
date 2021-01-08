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


################################################################################
# Local libraries
################################################################################
from commons.host import Host

################################################################################
# Constants
################################################################################
logger = logging.getLogger(__name__)

class HealthHelper(Host):

    ############################################################################
    # Mero services
    ############################################################################
    def is_mero_online(self, host=CM_CFG["host"],
                       user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Check whether all services are online in mero cluster
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: bool , response
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.MERO_STATUS_CMD)
            log.info(output)
            fail_list = cons.FAILED_LIST
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, output
            return True, output
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.is_mero_online.__name__,
                error))
            return False, error
    ############################################################################
    # Get Ports
    ############################################################################
    def get_ports_of_service(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Find all TCP ports for given running service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: (boolean, response)
        :return:
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.NETSAT_CMD.format(service))
            ports = []
            for line in output:
                out_list = line.split()
                ports.append(out_list[3].split(':')[-1])
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_ports_of_service.__name__,
                error))
            return False, error
    # Provisioner
    def get_ports_for_firewall_cmd(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Find all ports exposed through firewall permanent service for given component
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: service component
        :return: (boolean, response)
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.FIREWALL_CMD.format(service))
            ports = []
            for word in output:
                ports.append(word.split())
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_ports_for_firewall_cmd.__name__,
                    error))
            return False, error
    ############################################################################
    # Resource usage
    ############################################################################
    def get_disk_usage(self, path, remote=False, host=CM_CFG["host"],
                       user=CM_CFG["username"],
                       pwd=CM_CFG["password"]):
        """
        This function will return disk usage associated with given path.
        :param path: Path to retrieve disk usage
        :param remote: for getting remote disk usgae True/False
        :param host: IP of the remort host
        :param user: User of the remote host
        :param pwd: Password of the remote user
        :return: Disk usage of given path or error in case of failure
        :type: (Boolean, float/str)
        """
        try:
            if not remote:
                log.info("Running local disk usage cmd.")
                stats = os.statvfs(path)
                f_blocks, f_frsize, f_bfree = stats.f_blocks, stats.f_frsize, stats.f_bfree

            else:
                log.info("Running remote disk usage cmd.")
                cmd = "stat --file-system / --format %b,%S,%f"
                log.debug(f"Running cmd: {cmd} on host:{host}")
                res = self.remote_execution(host, user, pwd, cmd)
                f_res = res[0].replace("\n", "").split(",")
                f_blocks, f_frsize, f_bfree = int(
                    f_res[0]), int(
                    f_res[1]), int(
                    f_res[2])
            total = (f_blocks * f_frsize)
            used = (f_blocks - f_bfree) * f_frsize
            result = format((float(used) / total) * 100, ".1f")
        except ZeroDivisionError as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_disk_usage.__name__,
                error))
            return False, error
        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_disk_usage.__name__,
                error))
            return False, error
        return True, result

    def disk_usage_python_interpreter_cmd(self,
                                          dir_path,
                                          field_val=3,
                                          host=CM_CFG["host"],
                                          user=CM_CFG["username"],
                                          pwd=CM_CFG["password"]):
        """
        This function will return disk usage associated with given path.
        :param dir_path: Directory path of which size is to be calculated
        :type: str
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and percent used space respectively
        :type: int
        :param host: IP of the remote host
        :type: str
        :param user: User of the remote host
        :type: str
        :param pwd: Password of the remote user
        :type: str
        :return: Output of the python interpreter command
        :rtype: (int/float/str)
        """
        try:
            cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'" \
                .format(a=str(dir_path), b=int(field_val))
            log.info(f"Running python command {cmd}")
            resp = self.execute_command(command=cmd, host=host, username=user,
                                        password=pwd)
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.disk_usage_python_interpreter_cmd.__name__,
                    error))
            return False, error

        return resp

    def get_system_cpu_usage(
            self,
            host=CM_CFG["host"],
            username=CM_CFG["username"],
            password=CM_CFG["password"]):
        """
        This function with fetch the system cpu usage percentage from remote host
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: system cpu usage
        :rtype: (bool, float)
        """
        try:
            log.info("Fetching system cpu usage from node {}".format(host))
            log.info(ras_cons.CPU_USAGE_CMD)
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=ras_cons.CPU_USAGE_CMD)
            log.info(resp)
            cpu_usage = float(resp[0])
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_system_cpu_usage.__name__,
                    error))
            return False, error

        return True, cpu_usage

    def get_system_memory_usage(
            self,
            host=CM_CFG["host"],
            username=CM_CFG["username"],
            password=CM_CFG["password"]):
        """
        This function with fetch the system memory usage percentage from remote host
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: system memory usage in percent
        :rtype: (bool, float)
        """
        try:
            log.info(
                "Fetching system memory usage from node {}".format(host))
            log.info(ras_cons.MEM_USAGE_CMD)
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=ras_cons.MEM_USAGE_CMD)
            log.info(resp)
            mem_usage = float(resp[0])
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_system_memory_usage.__name__,
                    error))
            return False, error

        return True, mem_usage


    ############################################################################
    # PCS command functions
    ############################################################################
    def get_pcs_service_systemd(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Function to return pcs service systemd service name.
        This function will be usefull when service is not under systemctl
        :param str service: Name of the pcs resource service
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :return: (True, name of the service mentioned in systemd)
        :type: tuple
        """
        cmd = ha_cons.GREP_PCS_SERVICE_CMD.format(service)
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
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
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_pcs_service_systemd.__name__,
                    error))
            return False, error
    def pcs_cluster_start_stop(self, node, stopFlag):
        """
        This function Gracefully shutdown the given node
        using pcs cluster stop command
        :param str node: Node to be shutdown
        :param bool stopFlag: Shutdown if flag is True else Start
                          the node
        :return: True/False
        :rtype: Boolean
        """
        user = CM_CFG["username"]
        pwd = CM_CFG["password"]
        server = node
        prefix = node.split(CM_CFG["NodeNamePattern"])
        node_prefix = prefix[1]
        nodeName = "{}{}".format(CM_CFG["ServerNamePattern"], node_prefix)

        if stopFlag:
            cmd = ha_cons.PCS_CLUSTER_STOP.format(nodeName)
        else:
            cmd = ha_cons.PCS_CLUSTER_START.format(nodeName)

        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=server,
                user=user,
                password=pwd,
                cmd=cmd,
                read_lines=False)
            log.info(resp)
            if not resp:
                return False, None

            return True, resp[1]

        except Exception as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_cluster_start_stop.__name__,
                    error))

            return False, error



    def pcs_status_grep(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Function to return grepped pcs status services.
        :param str service: Name of the pcs resource service
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :return: (True, pcs staus str response)
        :type: tuple
        """
        cmd = ha_cons.GREP_PCS_SERVICE_CMD.format(service)
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return None
        except Exception as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_status_grep.__name__,
                    error))

            return error

        return resp
    def pcs_resource_cleanup(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"],
            options=None):
        """
        Perform pcs resource cleanup
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :param str options: option supported in resource cleanup eg: [<resource id>] [--node <node>]
        :return: (True, pcs str response)
        :type: tuple
        """
        if options:
            cmd = ha_cons.PCS_RESOURCES_CLEANUP.format(options)
        else:
            options = " "
            cmd = ha_cons.PCS_RESOURCES_CLEANUP.format(options)
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return False, None
        except Exception as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_resource_cleanup.__name__,
                    error))

            return False, error

        return True, resp
    ############################################################################
    # HCTL command functions
    ############################################################################
        def is_machine_already_configured(self):
        """
        This method checks that machine is already configured or not.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = constants.STATUS_MERO
        log.info(f"command : {mero_status_cmd}")
        cmd_output = self.execute_command(command=mero_status_cmd)
        if not cmd_output[0] or "command not found" in str(cmd_output[1]):
            log.info("Machine is not configured..!")
            return False
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            if ('[' and ']') in output:
                log.info(output)
        log.info("Machine is already configured..!")
        return True

    def all_cluster_services_online(self, host=None, timeout=400):
        """
        This function will verify hctl status commands output. Check for
        all cluster services are online using hctl mero status command.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = constants.STATUS_MERO
        log.info(f"command : {mero_status_cmd}")
        cmd_output = self.execute_command(command=mero_status_cmd,
                                          host=host, timeout_sec=timeout)
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
                return False, f"{constants.STATUS_MERO} command not found"
        else:
            log.info("All other services are online")
            return True, "Server is Online"
