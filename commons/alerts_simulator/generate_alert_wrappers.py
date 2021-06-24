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
import random
import os
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.host import Host
from commons import constants as cons
from commons.helpers.controller_helper import ControllerLib
from commons.utils.system_utils import toggle_nw_status, make_dirs, open_empty_file
from commons import commands
from commons.helpers.node_helper import Node

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
    def create_disk_group_failures(encl_ip, encl_user, encl_pwd, host, h_user,
                                   h_pwd, input_parameters):
        """
        Wrapper for generating disk group failure.

        :param encl_ip: IP of the enclosure
        :type: str
        :param encl_user: Username of the enclosure
        :type: str
        :param encl_pwd: Password of the enclosure
        :type: str
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
        :rtype: bool, str
        """
        enclid = input_parameters["enclid"]
        ctrl_name = input_parameters["ctrl_name"]
        operation = input_parameters["operation"]
        disk_group = input_parameters["disk_group"]
        controller_obj = ControllerLib(host=host, h_user=h_user, h_pwd=h_pwd,
                                       enclosure_ip=encl_ip,
                                       enclosure_user=encl_user,
                                       enclosure_pwd=encl_pwd)

        try:
            LOGGER.info("Check state of disk group")
            status, disk_group_dict = controller_obj.get_show_disk_group()
            LOGGER.info("Disk group info: %s", disk_group_dict)
            if not status:
                return status, "Failed to get information about disk groups"
            elif disk_group_dict[disk_group]['health'] != 'OK':
                LOGGER.info("Provided disk group is not in healthy state.")
                return False, disk_group_dict[disk_group]['health']

            LOGGER.info("Getting list of drives in disk group %s", disk_group)

            status, drive_list = controller_obj.get_dg_drive_list(disk_group=disk_group)
            if not status:
                return status, "Failed to get drive list"

            LOGGER.info("Picking two random drives from disk group %s", disk_group)
            drives = random.sample(drive_list, 2)
            if disk_group_dict[disk_group]['raidtype'] == "ADAPT":
                drives = [drives[-1]]
            LOGGER.info("Removing drive : %s", drives)
            resp = controller_obj.remove_add_drive(enclosure_id=enclid,
                                                   controller_name=ctrl_name,
                                                   drive_number=drives,
                                                   operation=operation)

            if not resp[0]:
                return resp[0], "Failed to remove drives"

            LOGGER.info("Check if drives are completely removed")
            status, drive_list = controller_obj.get_dg_drive_list(
                                 disk_group=disk_group)
            if not status:
                return status, "Failed to get drive list"

            for d in drives:
                if d in drive_list:
                    return False, f"Drive {d} is not removed"

            return True, drives
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.create_disk_group_failures.__name__, error)
            return False, error

    @staticmethod
    def resolve_disk_group_failures(encl_ip, encl_user, encl_pwd, host, h_user,
                                    h_pwd, input_parameters):
        """
        Wrapper for resolving disk group failure.

        :param encl_ip: IP of the enclosure
        :type: str
        :param encl_user: Username of the enclosure
        :type: str
        :param encl_pwd: Password of the enclosure
        :type: str
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
        :rtype: bool, str
        """
        enclid = input_parameters["enclid"]
        ctrl_name = input_parameters["ctrl_name"]
        phy_num = input_parameters["phy_num"]
        operation = input_parameters["operation"]
        disk_group = input_parameters["disk_group"]
        poll = input_parameters["poll"]
        controller_obj = ControllerLib(host=host, h_user=h_user, h_pwd=h_pwd,
                                       enclosure_ip=encl_ip,
                                       enclosure_user=encl_user,
                                       enclosure_pwd=encl_pwd)

        try:
            LOGGER.info("Check state of disk group")
            status, disk_group_dict = controller_obj.get_show_disk_group()
            LOGGER.info("Disk group info: %s", disk_group_dict)
            if not status:
                return status, "Failed to get information about disk groups"
            elif disk_group_dict[disk_group]['health'] == 'OK':
                LOGGER.info("Provided disk group is already in healthy state.")
                return status, disk_group_dict[disk_group]['health']

            LOGGER.info("RAID type of disk group %s is %s", disk_group,
                        disk_group_dict[disk_group]['raidtype'])

            if disk_group_dict[disk_group]['raidtype'] == "ADAPT" and \
                    disk_group_dict[disk_group].get('job') is None:
                LOGGER.info("No intermediate job is running")
            elif disk_group_dict[disk_group]['raidtype'] == "ADAPT":
                LOGGER.info("Wait for %s job to complete.",
                            disk_group_dict[disk_group]['job'])
                dg_health, job, poll_percent = controller_obj.poll_dg_recon_status(
                        disk_group=disk_group)
                if poll_percent == 100:
                    LOGGER.info("Completed job %s", job)
                else:
                    LOGGER.error("Job %s failed", job)
                    return False, f"Job progress: {poll_percent}"

            LOGGER.info("Adding drives %s", phy_num)
            resp = controller_obj.remove_add_drive(enclosure_id=enclid,
                                                   controller_name=ctrl_name,
                                                   drive_number=phy_num,
                                                   operation=operation)

            if not resp[0]:
                return resp[0], f"Failed to add drives {phy_num} to disk " \
                                f"group {disk_group}"
            time.sleep(15)
            LOGGER.info("Adding drives to the disk group %s", disk_group)
            if disk_group_dict[disk_group]['raidtype'] == "ADAPT":
                LOGGER.info("Check usage of drives %s", phy_num)
                status, drive_usage_dict = controller_obj.get_drive_usage(
                    phy_num=phy_num)
                if not status:
                    return status, f"Failed to get drive usages for drives" \
                                   f" {phy_num}"

                LOGGER.info("Drive usages: %s", drive_usage_dict)

                for key, value in drive_usage_dict.items():
                    if value != "AVAIL" and value != "LINEAR POOL":
                        LOGGER.info("Running clear metadata")
                        resp = controller_obj.clear_drive_metadata(
                            drive_num=key)
                        if not resp[0]:
                            return resp[0], resp[1]

                    LOGGER.info("Successfully cleared drive metadata of %s", key)
            else:
                LOGGER.info("Adding available/spare drives to disk group %s",
                            disk_group)
                resp = controller_obj.add_spares_dg(drives=phy_num,
                                                    disk_group=disk_group)
                if not resp[0]:
                    return resp[0], f"Failed to add drives {phy_num} to disk " \
                                    f"group {disk_group}"

            LOGGER.info("Check if reconstruction of disk group is started")
            status, disk_group_dict = controller_obj.get_show_disk_group()
            if disk_group_dict[disk_group]['job'] == 'RCON' or \
                    disk_group_dict[disk_group]['job'] == 'RBAL' or \
                    disk_group_dict[disk_group]['job'] == 'EXPD':
                LOGGER.info("Successfully started recovery of disk "
                            "group %s", disk_group)
            else:
                return False, "Failed to start Disk Group reconstruction"

            if poll:
                dg_health, job, poll_percent = controller_obj.poll_dg_recon_status(
                    disk_group=disk_group)
                if poll_percent == 100 or dg_health == "OK":
                    LOGGER.info("Successfully recovered disk group %s \n "
                                "Reconstruction percent: %s", disk_group,
                                poll_percent)
                    LOGGER.info("Disk group health state is: %s", dg_health)
                    return True, f"Reconstruction progress: {poll_percent}"
                else:
                    LOGGER.error("Failed to recover disk group %s \n "
                                 "Reconstruction percent: %s", disk_group,
                                 poll_percent)
                    LOGGER.info("Disk group health state is: %s", dg_health)
                    return False, f"Reconstruction progress: {poll_percent}"
            return True, "Reconstruction started"
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.resolve_disk_group_failures.__name__,
                         error)
            return False, error

    @staticmethod
    def create_network_port_fault(host, h_user, h_pwd, input_parameters):
        """
        Function to generate the network port fault on node
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
            status = "down"
            LOGGER.info(f"Creating nw fault for resource {device} on "
                        f"{host}")
            LOGGER.info(f"Making {device} {status} on {host}")
            resp = toggle_nw_status(device=device, status=status, host=host,
                                    username=h_user, pwd=h_pwd)
            return resp, f"Created NW Port Fault of {device}"
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.create_network_port_fault
                         .__name__, error)
            return False, error

    @staticmethod
    def resolve_network_port_fault(host, h_user, h_pwd, input_parameters):
        """
        Function to resolve the network port fault on node
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
            status = "up"
            LOGGER.info(f"Resolving network fault for resource {device} on "
                        f"{host}")
            resp = toggle_nw_status(device=device, status=status, host=host,
                                    username=h_user, pwd=h_pwd)
            LOGGER.info(resp)
            return resp, f"Resolved NW fault of {device}"
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.resolve_network_port_fault
                         .__name__, error)
            return False, error

    @staticmethod
    def create_resolve_network_cable_faults(host, h_user, h_pwd,
                                            input_parameters):
        """
        Function to create and resolve the network cable fault on node
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
        device = input_parameters['device']
        action = input_parameters['action']
        ras_test_obj = RASTestLib(host=host, username=h_user, password=h_pwd)
        node_connect = Node(hostname=host, username=h_user, password=h_pwd)

        LOGGER.info("Simulating network cable fault using sysfs")
        try:
            carrier_file_path = f"/tmp/sys/class/net/{device}/carrier"
            LOGGER.info(f"Make network cable of {device} on {host} {action}")
            LOGGER.info("Creating dummy network path")
            if not node_connect.path_exists(carrier_file_path):
                node_connect.make_dir(dpath=os.path.dirname(carrier_file_path))
                node_connect.open_empty_file(fpath=carrier_file_path)

            LOGGER.info("Update sysfs_base_path in sspl.conf file")
            ras_test_obj.set_conf_store_vals(
                url=cons.SSPL_CFG_URL,
                encl_vals={'CONF_SYSFS_BASE_PATH': "/tmp/sys/"})

            res = ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                   field=cons.CONF_SYSFS_BASE_PATH)
            LOGGER.debug("Response: %s", res)

            LOGGER.info("Update network cable status in carrier file")
            cmd = commands.CMD_UPDATE_FILE.format(action, carrier_file_path)
            resp = node_connect.execute_cmd(cmd=cmd, read_lines=True)
            LOGGER.debug("Response: %s", resp)

            return True, action
        except BaseException as error:
            LOGGER.error("%s %s: %s", cons.EXCEPTION_ERROR,
                         GenerateAlertWrapper.create_resolve_network_cable_faults
                         .__name__, error)
            return False, error
