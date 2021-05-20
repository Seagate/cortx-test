#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
This file contains the wrapper functions used by Alert Simulation API.
"""
import logging
import time
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.host import Host
from commons import constants as cons
from commons.helpers.controller_helper import ControllerLib
from commons.utils.system_utils import run_remote_cmd
from commons import commands

LOGGER = logging.getLogger(__name__)


class GenerateAlertWrapper:
    """
    Class contains the wrappers for simulating alerts using different tools.
    """
    @staticmethod
    def simulatefault(encl_ip, encl_user, encl_pwd, host, h_user, h_pwd,
                      input_parameters):
        """
        Wrapper for simulating HW alerts of modules like psu and ctrl
        using simulatefrufault on controller.

        :param encl_ip: IP of the enclosure
        :type: str
        :param encl_user: Username of the enclosure
        :type: str
        :param encl_pwd: Password of the enclosure
        :type: str
        :param host: IP of the remote host
        :type: str
        :param h_user: User of the remote host
        :type: str
        :param h_pwd: Password of the remote user
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        enclid = input_parameters["enclid"]
        pos = input_parameters["pos"]
        fru = input_parameters["fru"]
        type_fault = input_parameters["type_fault"]
        ctrl_name = input_parameters["ctrl_name"]
        controller_obj = ControllerLib(host=host, h_user=h_user, h_pwd=h_pwd,
                                       enclosure_ip=encl_ip,
                                       enclosure_user=encl_user,
                                       enclosure_pwd=encl_pwd)

        try:
            resp = controller_obj.get_mc_ver_sr()
            if resp[1] is None:
                return False, f"{resp[1]} is returned for MC Version"
            if resp[2] is None:
                return False, f"{resp[2]} is returned for MC Version"

            LOGGER.info("MC version : %s Serial Number : %s", resp[1], resp[2])

            mc_debug_pswd = controller_obj.get_mc_debug_pswd(resp[1], resp[2])
            if mc_debug_pswd is None:
                return False, f"{mc_debug_pswd} is returned for MC debug " \
                              f"password"

            resp = controller_obj.simulate_fault_ctrl(
                mc_deb_password=mc_debug_pswd, enclid=enclid, pos=pos, fru=fru,
                type_fault=type_fault, ctrl_name=ctrl_name)
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.simulatefault.__name__, error)

            return False, error

        return resp

    @staticmethod
    def disk_faults(encl_ip, encl_user, encl_pwd, host, h_user, h_pwd,
                    input_parameters):
        """
        Wrapper for simulating disk disable and enable faults.

        :param encl_ip: IP of the enclosure
        :type: str
        :param encl_user: Username of the enclosure
        :type: str
        :param encl_pwd: Password of the enclosure
        :type: str
        :param host: IP of the remote host
        :type: str
        :param h_user: User of the remote host
        :type: str
        :param h_pwd: Password of the remote user
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        enclid = input_parameters["enclid"]
        ctrl_name = input_parameters["ctrl_name"]
        phy_num = input_parameters["phy_num"]
        operation = input_parameters["operation"]
        exp_status = input_parameters["exp_status"]
        telnet_file = input_parameters["telnet_file"]
        controller_obj = ControllerLib(host=host, h_user=h_user, h_pwd=h_pwd,
                                       enclosure_ip=encl_ip,
                                       enclosure_user=encl_user,
                                       enclosure_pwd=encl_pwd)

        try:
            LOGGER.info("Changing status of phy num %s to %s",
                        phy_num, operation)
            controller_obj.set_drive_status_telnet(
                enclosure_id=enclid, controller_name=ctrl_name,
                drive_number=phy_num, status=operation)
            resp = None
            timeout, starttime = 120, time.time()
            while time.time() <= starttime + timeout:  # Added to avoid hardcoded wait.
                _, resp = controller_obj.check_phy_health(
                    phy_num=phy_num, telnet_file=telnet_file)
                if isinstance(exp_status, list):
                    if resp in (exp_status[0], exp_status[1]):
                        break
                else:
                    if resp == exp_status:
                        break
                time.sleep(20)  # Added 20s delay to repeat check_phy_health.
            LOGGER.info("check phy response: %s", resp)
            if isinstance(exp_status, list):
                if resp not in (exp_status[0], exp_status[1]):
                    return False, f"Failed to put drive in {exp_status} " \
                                  f"state, response: {resp}"
            else:
                if resp != exp_status:
                    return False, f"Failed to put drive in {exp_status} " \
                                  f"state, response: {resp}"

            LOGGER.info("Successfully put phy in %s state", exp_status)
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.disk_faults.__name__, error)

            return False, error

        return True, exp_status

    @staticmethod
    def disk_full_fault(host, h_user, h_pwd, input_parameters):
        """
        Wrapper for generating disk alerts on node.

        :param host: IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        du_val = input_parameters["du_val"]
        fault = input_parameters["fault"]
        fault_resolved = input_parameters["fault_resolved"]
        ras_test_obj = RASTestLib(host=host, username=h_user, password=h_pwd)
        try:
            resp = ras_test_obj.generate_disk_full_alert(du_val=du_val,
                                                         fault=fault,
                                                         fault_resolved=fault_resolved)

            return resp
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.disk_full_fault.__name__, error)
            return False, error

    @staticmethod
    def cpu_usage_fault(host, h_user, h_pwd, input_parameters):
        """
        Wrapper for generating cpu usage alerts on the given host.

        :param host: hostname or IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        delta_cpu_usage = input_parameters["delta_cpu_usage"]
        ras_test_obj = RASTestLib(host=host, username=h_user, password=h_pwd)
        LOGGER.info("Generating CPU usage alert")
        try:
            resp = ras_test_obj.generate_cpu_usage_alert(
                delta_cpu_usage=delta_cpu_usage)
            return resp, "Completed CPU usage Fault Generation"
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.cpu_usage_fault.__name__, error)
            return False, error

    @staticmethod
    def memory_usage_fault(host, h_user, h_pwd, input_parameters):
        """
        Wrapper for generating memory usage alerts on the given host.

        :param host: IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to simulate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        delta_mem_usage = input_parameters["delta_mem_usage"]
        ras_test_obj = RASTestLib(host=host, username=h_user, password=h_pwd)
        LOGGER.info("Generating memory usage alert")
        try:
            resp = ras_test_obj.generate_memory_usage_alert(
                delta_mem_usage=delta_mem_usage)
            return resp, "Completed Memory Usage Fault Generation"
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.memory_usage_fault.__name__,
                         error)
            return False, error

    @staticmethod
    def raid_faults(host, h_user, h_pwd, input_parameters):
        """
        Wrapper for generating raid faults on the given host.

        :param host: hostname or IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: Returns response tuple
        :rtype: (Boolean, string)
        """
        ras_test_obj = RASTestLib(host=host, username=h_user, password=h_pwd)
        operation = input_parameters["operation"]
        md_device = input_parameters["md_device"]
        disk = input_parameters["disk"]
        LOGGER.info("Device provided for raid operations %s", md_device)
        LOGGER.info("Disks provided for raid operations %s", disk)
        if not md_device:
            return False, "Please provide RAID device name e.g., /dev/md?"

        try:
            if operation == "assemble":
                resp = ras_test_obj.assemble_mdraid_device(md_device=md_device)
            elif operation == "stop":
                resp = ras_test_obj.stop_mdraid_device(md_device=md_device)
            elif operation == "fail_disk" and disk:
                resp = ras_test_obj.fail_disk_mdraid(
                    md_device=md_device, disk=disk)
            elif operation == "remove_disk" and disk:
                resp = ras_test_obj.remove_faulty_disk(
                    md_device=md_device, disk=disk)
            elif operation == "add_disk" and disk:
                resp = ras_test_obj.add_disk_mdraid(
                    md_device=md_device, disk=disk)
            else:
                resp = False, None

            return resp
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.raid_faults.__name__, error)
            return False, error

    @staticmethod
    def iem_alerts(host, h_user, h_pwd, input_parameters):
        """
        Wrapper for generating iem faults on the given host.

        :param host: hostname or IP of the host
        :type: str
        :param h_user: Username of the host
        :type: str
        :param h_pwd: Password of the host
        :type: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: Returns stdout response
        :rtype: (string)
        """
        try:
            logger_alert_cmd = input_parameters['cmd']
            LOGGER.info("Logger cmd : %s", logger_alert_cmd)
            host_connect = Host(hostname=host, username=h_user, password=h_pwd)
            resp = host_connect.execute_cmd(cmd=logger_alert_cmd, read_lines=True,
                                            shell=False)
            return True, resp
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.iem_alerts.__name__, error)
            return False, error

    @staticmethod
    def create_mgmt_network_fault(host, h_user, h_pwd, input_parameters):
        """
        Function to generate the management network fault on node
        :param host: host
        :type host: str
        :param h_user: username
        :type h_user: str
        :param h_pwd: password
        :type h_pwd: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: True/False
        :rtype: Boolean
        """
        try:
            device = input_parameters['device']
            status = input_parameters['status']
            LOGGER.info(f"Creating management fault on resource {device} on "
                        f"{host}")
            LOGGER.info(f"Making {device} {status} on {host}")
            ras_test_obj = RASTestLib(host=host, username=h_user, password=h_pwd)
            resp = ras_test_obj.toggle_nw_status(device=device, status=status)
            return resp, "Created Mgmt NW Port Fault"
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.create_mgmt_network_fault.__name__, error)
            return False, error

    @staticmethod
    def resolve_mgmt_network_fault(host, h_user, h_pwd, input_parameters):
        """
        Function to resolve the management network fault on node
        :param host: host from which command is to be run
        :type host: str
        :param h_user: username
        :type h_user: str
        :param h_pwd: password
        :type h_pwd: str
        :param input_parameters: This contains the input parameters required
        to generate the fault
        :type: Dict
        :return: True/False, Response
        :rtype: Boolean, str
        """
        try:
            device = input_parameters['device']
            status = input_parameters['status']
            host_data_ip = input_parameters['host_data_ip']
            LOGGER.info(f"Resolving management fault on resource {device} on "
                        f"{host}")
            LOGGER.info(f"Making {device} {status} from {host} using Data IP "
                        f"{host_data_ip}")
            ip_link_cmd = commands.IP_LINK_CMD.format(device, status)
            LOGGER.info(f"Running command {ip_link_cmd} on {host} through "
                        f"data ip {host_data_ip}")
            resp = run_remote_cmd(hostname=host_data_ip, username=h_user,
                                  password=h_pwd, cmd=ip_link_cmd,
                                  read_lines=True)
            LOGGER.info(resp)
            return resp
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.resolve_mgmt_network_fault.__name__,
                         error)
            return False, error
