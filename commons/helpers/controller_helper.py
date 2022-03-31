#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""Controller helper lib implements the base functions for controller operations."""
import os
import logging
from typing import Tuple
import requests
from commons.helpers.node_helper import Node
from commons import constants as cons
from commons import commands as common_cmd
from commons import errorcodes as cterr
from commons.exceptions import CTException
from commons.utils import config_utils as conf_util
from config import CMN_CFG, RAS_VAL, CMN_DESTRUCTIVE_CFG

LOGGER = logging.getLogger(__name__)


class ControllerLib:
    """Controller helper functions."""

    def __init__(self, host: str = None, h_user: str = None, h_pwd: str = None,
                 enclosure_ip: str = None, enclosure_user: str = None,
                 enclosure_pwd: str = None) -> None:
        """
        Method to initialize members of ControllerLib class.
        :param host: IP of the remote host
        :type: str
        :param h_user: User of the remote host
        :type: str
        :param h_pwd: Password of the remote user
        :type: str
        :param enclosure_ip: IP of the enclosure
        :type enclosure_ip: str
        :param enclosure_user: username of the enclosure
        :type enclosure_user: str
        :param enclosure_pwd: password of the enclosure
        :type enclosure_pwd: str
        """
        nd_cfg = CMN_CFG.get("nodes", None)
        ctrl_cfg = CMN_CFG.get("enclosure", None)
        self.host = host if host else nd_cfg[0]["host"] if nd_cfg else None
        self.h_pwd = h_pwd if h_pwd else nd_cfg[0]["password"] if nd_cfg else None
        self.h_user = h_user if h_user else nd_cfg[0]["username"] if nd_cfg else None

        self.enclosure_ip = enclosure_ip if enclosure_ip else ctrl_cfg[
            "primary_enclosure_ip"] if ctrl_cfg else None
        self.enclosure_user = enclosure_user if enclosure_user else ctrl_cfg[
            "enclosure_user"] if ctrl_cfg else None
        self.enclosure_pwd = enclosure_pwd if enclosure_pwd else ctrl_cfg[
            "enclosure_pwd"] if ctrl_cfg else None

        self.node_obj = Node(hostname=self.host, username=self.h_user,
                             password=self.h_pwd)

        self.copy = False

    def copy_telnet_operations_file(self):
        """
        Function to copy telnet operations file
        """
        runner_path = cons.REMOTE_TELNET_PATH
        local_path = cons.TELNET_OP_PATH
        LOGGER.info("Copying file %s to %s", local_path, runner_path)
        self.node_obj.copy_file_to_remote(local_path=local_path,
                                          remote_path=runner_path)

        runner_path = cons.REMOTE_DAEMON_PATH
        local_path = cons.DAEMON_OP_PATH
        LOGGER.info("Copying file %s to %s", local_path, runner_path)
        self.node_obj.copy_file_to_remote(local_path=local_path,
                                          remote_path=runner_path)

        runner_path = cons.REMOTE_RECEIVER_PATH
        local_path = cons.RECEIVER_OP_PATH
        LOGGER.info("Copying file %s to %s", local_path, runner_path)
        self.node_obj.copy_file_to_remote(local_path=local_path,
                                          remote_path=runner_path)
        if self.node_obj.path_exists(path=runner_path):
            self.copy = True

    def get_mc_ver_sr(self) -> Tuple[str, str, str]:
        """
        Function to get the version and serial number of the management controller.
        :return: version and serial number of the management controller
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.SET_DEBUG_CMD

                command = f"python3 /root/telnet_operations.py " \
                          f"--telnet_op='get_mc_ver_sr(" \
                          f"enclosure_ip=\"{self.enclosure_ip}\", " \
                          f"enclosure_user=\"{self.enclosure_user}\", " \
                          f"enclosure_pwd=\"{self.enclosure_pwd}\", " \
                          f"cmd=\"{cmd}\")'"

                LOGGER.info("Running command %s", command)
                response = self.node_obj.execute_cmd(cmd=command, read_lines=True)
                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
                mc_ver = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[1])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
                mc_sr = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[2])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.get_mc_ver_sr.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return status, mc_ver, mc_sr

        return "False", "File not found :", "telnet_operations.py"

    @staticmethod
    def get_mc_debug_pswd(mc_ver: str, mc_sr: str) -> str:
        """
        Function to get the password for management controller debug console.
        :param mc_ver: Management controller version
        :type: str
        :param mc_sr: Management controller serial number
        :type: str
        :return: Password string
        :rtype: String
        """
        header_data = {'mc_version': mc_ver, 'serial_number': mc_sr}
        headers = cons.HEADERS_STREAM_UTILITIES
        url = cons.URL_STREAM_UTILITIES
        try:
            response = requests.post(url, data=header_data, headers=headers)
            mc_password = str(response.text)
            mc_password = (mc_password.split(',')[1]).split('=')[1]
        except BaseException as error:
            LOGGER.exception("Error in %s: %s", ControllerLib.get_mc_debug_pswd.__name__, error)
            raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

        LOGGER.info("MC debug password: %s", mc_password)
        return mc_password

    def simulate_fault_ctrl(self, mc_deb_password: str, enclid: str, pos: str,
                            fru: str, type_fault: str, ctrl_name: str) -> \
            Tuple[str, str]:
        """
        Function to simulate faults on the controller.
        :param mc_deb_password: Password of Management controller debug console
        :type: str
        :param enclid: Enclosure ID
        :type: str
        :param pos: Position of fru
        :type: str
        :param fru: Fru type for which fault is to be simulated
        :type: str
        :param type_fault: Type of fault to be simulated
        :type: str
        :param ctrl_name: Name of the controller to be used
        :type: str
        :return: Boolean, Response
        :rtype: Tuple of (bool, String)
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                ras_sspl_cfg = RAS_VAL["ras_sspl_alert"]
                cmd = common_cmd.SIMULATE_FAULT_CTRL_CMD. \
                    format(enclid, pos, fru, type_fault, ctrl_name)
                telnet_port = ras_sspl_cfg["mc_debug_port"]
                timeout = ras_sspl_cfg["one_min_delay"]

                command = f"python3 /root/telnet_operations.py " \
                          f"--telnet_op='simulate_fault_ctrl(" \
                          f"mc_deb_password=\"{mc_deb_password}\", " \
                          f"enclosure_ip=\"{self.enclosure_ip}\", " \
                          f"telnet_port=\"{telnet_port}\", " \
                          f"timeout=\"{timeout}\", cmd=\"{cmd}\")'"

                LOGGER.info("Running command %s", command)
                response = self.node_obj.execute_cmd(cmd=command,
                                                     read_lines=True)
                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
                password_str = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[1]))
                    .replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.simulate_fault_ctrl.__name__,
                                 error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return status, password_str

        return "False", "File not found : telnet_operations.py"

    def show_disks(self, telnet_file: str) -> Tuple[str, str]:
        """
        Show disk.
        :param telnet_file: File path to save response of telnet command
        :type: str
        :return: Boolean, file path
        :rtype: Tuple of (bool, String)
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                LOGGER.info("Show disks for %s enclosure.", self.enclosure_ip)
                cmd = common_cmd.SHOW_DISKS_CMD

                command = f"python3 /root/telnet_operations.py " \
                          f"--telnet_op='show_disks(" \
                          f"enclosure_ip=\"{self.enclosure_ip}\", " \
                          f"enclosure_user=\"{self.enclosure_user}\", " \
                          f"enclosure_pwd=\"{self.enclosure_pwd}\", " \
                          f"telnet_filepath=\"{telnet_file}\", " \
                          f"cmd=\"{cmd}\")'"

                LOGGER.info("Running command : %s", command)
                response = self.node_obj.execute_cmd(cmd=command,
                                                     read_lines=True)

                LOGGER.info(response)
                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
                path = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[1])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.show_disks.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])
            return status, path

        return "False", "File not found : telnet_operations.py"

    def get_total_drive_count(self, telnet_file: str) -> Tuple[str, int or str]:
        """
        Get total number of drives mapped.
        :param telnet_file: File path to save response of telnet command
        :type: str
        :return: (Boolean, Number of drives)
        :rtype: Boolean, Integer
        """
        self.copy_telnet_operations_file()
        if self.copy:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            try:
                resp = self.show_disks(telnet_file=telnet_file)

                LOGGER.info("Copying telnet file from node to client")
                self.node_obj.write_remote_file_to_local_file(
                    file_path=telnet_file, local_path=telnet_file)

                LOGGER.info("Copy completed")

                os.system("sed -i '1d; $d' {}".format(
                    common_cfg["file"]["telnet_xml"]))

                if resp[0]:
                    resp = conf_util.parse_xml_controller(
                        filepath=telnet_file, field_list=['location'])
                else:
                    return resp

                drive_dict = resp[1]
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.get_total_drive_count.__name__,
                                 error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return resp[0], len(drive_dict)

        return "False", "File not found : telnet_operations.py"

    def check_phy_health(self, phy_num: str, telnet_file: str) -> Tuple[bool,
                                                                        str]:
        """
        Check health of the phy.
        :param phy_num: number of the phy to be disabled
        :type: int
        :param telnet_file: File path to save response of telnet command
        :type: str
        :return: (Boolean, status of the phy)
        :rtype: Boolean, String
        """
        self.copy_telnet_operations_file()
        if self.copy:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            try:
                resp = self.show_disks(telnet_file=telnet_file)

                LOGGER.info("Copying telnet file from node to client")
                self.node_obj.write_remote_file_to_local_file(
                    file_path=telnet_file, local_path=telnet_file)

                LOGGER.info("Copy completed")

                os.system("sed -i '1d; $d' {}".format(
                    common_cfg["file"]["telnet_xml"]))

                if resp[0]:
                    resp = conf_util.parse_xml_controller(
                        filepath=telnet_file, field_list=['location', 'health'])
                else:
                    return resp

                drive_dict = resp[1]

                for k, v in drive_dict.items():
                    if v['location'] == '0.{}'.format(phy_num):
                        status = v['health']
                        break
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.check_phy_health.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return resp[0], status

        return False, "File not found : telnet_operations.py"

    def set_drive_status_telnet(self, enclosure_id: str, controller_name: str,
                                drive_number: str, status: str) -> Tuple[str,
                                                                         str]:
        """
        Enable or Disable drive status from disk group.
        :param enclosure_id: Enclosure ID of the machine
        :type: str
        :param controller_name: Server controller name
        :type: str
        :param drive_number: Drive number
        :type: str
        :param status: Status of the drive. Value will be enabled or disabled
        :type: str
        :return: None
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.SET_DRIVE_STATUS_CMD.format(
                    enclosure_id, controller_name, drive_number, status)

                command = f"python3 /root/telnet_operations.py " \
                          f"--telnet_op='set_drive_status_telnet(" \
                          f"enclosure_ip=\"{self.enclosure_ip}\", " \
                          f"username=\"{self.enclosure_user}\", " \
                          f"pwd=\"{self.enclosure_pwd}\", " \
                          f"status=\"{status}\", cmd=\"{cmd}\")'"

                LOGGER.info("Running command %s", command)
                response = self.node_obj.execute_cmd(cmd=command, read_lines=True)

                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
                drive_status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[1]))
                    .replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.set_drive_status_telnet.__name__,
                                 error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return status, drive_status

        return "False", "File not found : telnet_operations.py"

    def get_show_volumes(self, output_file_path: str = cons.CTRL_LOG_PATH) ->\
            Tuple[bool, dict or str]:
        """
        Execute "show volumes" command on primary enclosure.
        Parse output file.
        Return response dict: {key: disk-group, {Values: key: volume,
        {values: "storage-pool-name", "volume-name",
                            "total-size", "allocated-size", "storage-type",
                            "health", "health-reason",
                            "health-recommendation"}}}
        :param output_file_path: File path to save response of telnet
        common_cmd.
        :type: str
        :return: (Boolean, disk volume dict).
        :rtype: tuple
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.CMD_SHOW_VOLUMES
                LOGGER.debug(cmd)
                volumes_param = CMN_DESTRUCTIVE_CFG.get("show_volumes")
                LOGGER.debug(volumes_param)
                if not isinstance(volumes_param, dict):
                    raise Exception(f"Failed to get show_volumes: {volumes_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res:
                    raise Exception(f"telnet_operations.py path '{runner_path}'"
                                    f" not exists on primary node.")
                # Run show volumes command on primary controller.
                command = f"python3 {runner_path} " \
                          f"--telnet_op=" \
                          f"'execute_cmd_on_enclosure(enclosure_ip=\"" \
                          f"{self.enclosure_ip}\", " \
                          f"enclosure_user=\"{self.enclosure_user}\", " \
                          f"enclosure_pwd=\"{self.enclosure_pwd}\", " \
                          f"file_path=\"{output_file_path}\", cmd=\"{cmd}\")'"
                LOGGER.info("Running command : %s", command)
                resp = self.node_obj.execute_cmd(cmd=command,
                                                 read_lines=True)
                LOGGER.info("Show volumes response log: %s", resp)
                # Copy remote log file to local path.
                LOGGER.info("Copying log file from node to client")
                self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info("copy file log: %s", output_file_path)
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} not exists.")
                status, disk_volumes_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(volumes_param.values()))
                LOGGER.debug("Show volumes dict: %s", disk_volumes_dict)
                if not status:
                    raise Exception(f"failed to parse output file: {disk_volumes_dict}")
                # Cleanup dict.
                if isinstance(disk_volumes_dict, dict):
                    d = {}
                    keys = disk_volumes_dict.keys()
                    for k in keys:
                        if disk_volumes_dict[k].get(
                                "storage-pool-name") not in d:
                            d[disk_volumes_dict[k]["storage-pool-name"]] = {
                                disk_volumes_dict[k]["volume-name"]:
                                    dict([(ik, disk_volumes_dict[k][iv])
                                          for ik, iv in volumes_param.items()
                                          if disk_volumes_dict[k].get(iv)])
                            }
                        else:
                            d[disk_volumes_dict[k]["storage-pool-name"]].update(
                                {
                                    disk_volumes_dict[k]["volume-name"]:
                                        dict([(ik, disk_volumes_dict[k][iv])
                                              for ik, iv in
                                              volumes_param.items()
                                              if disk_volumes_dict[k].get(iv)])
                                })
                    disk_volumes_dict = d
                # Remove local log file.
                if os.path.exists(output_file_path):
                    os.remove(output_file_path)
                if not disk_volumes_dict:
                    return False, disk_volumes_dict
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.get_show_volumes.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return True, disk_volumes_dict

        return False, "File not found : telnet_operations.py"

    def get_show_expander_status(self,
                                 output_file_path: str = cons.CTRL_LOG_PATH) \
            -> Tuple[bool, dict or str]:
        """
        Get "show expander-status" output from enclosure.
        Parse the output files.
        Return response dict: {key: controller, {Values: key: wide-port-index,
         {values: "enclosure-id", "controller",
                            "wide-port-index", "type", "elem-status",
                             "elem-disabled", "status", "elem-reason"}}}
        :param output_file_path: File path to save response of telnet command
        :type: str
        :return: (Boolean, controller dict).
        :rtype: tuple
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.CMD_SHOW_XP_STATUS
                LOGGER.debug(cmd)
                expander_param = CMN_DESTRUCTIVE_CFG.get("show_expander_status")
                LOGGER.debug(expander_param)
                if not isinstance(expander_param, dict):
                    raise Exception(f"Failed to get show_expander_status: {expander_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res:
                    raise Exception(f"telnet_operations.py path '{runner_path}'"
                                    f" not exists on primary node.")
                # Run 'show expander-status' command on primary controller.
                command = f"python3 {runner_path} " \
                          f"--telnet_op=" \
                          f"'execute_cmd_on_enclosure(enclosure_ip=\"" \
                          f"{self.enclosure_ip}\", enclosure_user=\"" \
                          f"{self.enclosure_user}\", enclosure_pwd=\"" \
                          f"{self.enclosure_pwd}\", " \
                          f"file_path=\"{output_file_path}\", cmd=\"{cmd}\")'"
                LOGGER.info("Running command : %s", command)
                resp = self.node_obj.execute_cmd(cmd=command,
                                                 read_lines=True)
                LOGGER.info("Show show expander-status response log: %s", resp)
                LOGGER.info("Copying log file from node to client")
                self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info("copy file log: %s", output_file_path)
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} not exists.")
                status, expander_status_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(expander_param.values()))
                LOGGER.debug("Show expander-status dict: %s",
                             expander_status_dict)
                if not status:
                    raise Exception(f"failed to parse output file: {expander_status_dict}")
                # Cleanup dict.
                if isinstance(expander_status_dict, dict):
                    d = {}
                    keys = expander_status_dict.keys()
                    for k in keys:
                        if expander_status_dict[k].get("type") == "Drive":
                            if expander_status_dict[k].get('controller') \
                                    not in d:
                                d[expander_status_dict[k].get('controller')] = {
                                    int(expander_status_dict[k]
                                        ["wide-port-index"]):
                                        dict([(ik, expander_status_dict[k][iv])
                                              for ik, iv in
                                              expander_param.items()
                                              if
                                              expander_status_dict[k].get(iv)])
                                }
                            else:
                                d[expander_status_dict[k].get(
                                    'controller')].update({
                                        int(expander_status_dict[k]
                                            ["wide-port-index"]):
                                        dict([(ik, expander_status_dict[k][iv])
                                              for ik, iv in
                                              expander_param.items()
                                              if
                                              expander_status_dict[k].get(iv)])
                                        })
                    expander_status_dict = d
                # Remove local log file.
                if os.path.exists(output_file_path):
                    os.remove(output_file_path)
                if not expander_status_dict:
                    return False, expander_status_dict
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.get_show_expander_status.__name__,
                                 error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return True, expander_status_dict

        return False, "File not found : telnet_operations.py"

    def get_show_disk_group(self, output_file_path: str = cons.CTRL_LOG_PATH)\
            -> Tuple[bool, dict or str]:
        """
        Execute "show disk-groups" command on primary controller.
        Parse output xml.
        Get response dict: key-"disk group" and values dict of "name, size,
        health, health-reason, health-recommendation".
        :param output_file_path: File path to save response of telnet
        common_cmd.
        :type: str
        :return: (Boolean, disk group dict).
        :rtype: tuple
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.CMD_SHOW_DISK_GROUP
                LOGGER.debug(cmd)
                diskgroup_param = CMN_DESTRUCTIVE_CFG.get("show_disk_groups")
                LOGGER.debug(diskgroup_param)
                if not isinstance(diskgroup_param, dict):
                    raise Exception(f"Failed to get show_disk_group: {diskgroup_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res:
                    raise Exception(f"telnet_operations.py path '{runner_path}'"
                                    f" does not exist on primary node.")
                # Run 'show disk-group' command on primary controller.
                command = f"python3 {runner_path} " \
                          f"--telnet_op=" \
                          f"'execute_cmd_on_enclosure(enclosure_ip=\"" \
                          f"{self.enclosure_ip}\", " \
                          f"enclosure_user=\"{self.enclosure_user}\", " \
                          f"enclosure_pwd=\"{self.enclosure_pwd}\", " \
                          f"file_path=\"{output_file_path}\", cmd=\"{cmd}\")'"
                LOGGER.info("Running command : %s", command)
                resp = self.node_obj.execute_cmd(cmd=command,
                                                 read_lines=True)
                LOGGER.info("Show disk group response log: %s", resp)
                # Copy remote log file to local path.
                LOGGER.info("Copying log file from node to client")
                self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info("copy file log: %s", output_file_path)
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} not exists.")
                status, disk_group_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(diskgroup_param.values()))
                LOGGER.debug("Show disk-group dict: %s", disk_group_dict)
                if not status:
                    raise Exception(f"failed to parse output file: {disk_group_dict}")
                # Cleanup dict.
                if isinstance(disk_group_dict, dict):
                    disk_group_dict = dict([(disk_group_dict[k]['name'],
                                             dict([(ik, v[iv])
                                                   for ik, iv in
                                                   diskgroup_param.items()
                                                   if v.get(iv)]))
                                            for k, v in
                                            disk_group_dict.items()])
                # Remove local log file.
                if os.path.exists(output_file_path):
                    os.remove(output_file_path)
                if not disk_group_dict:
                    return False, disk_group_dict
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.get_show_disk_group.__name__,
                                 error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return True, disk_group_dict

        return False, "File not found : telnet_operations.py"

    def get_show_disks(self, output_file_path: str = cons.CTRL_LOG_PATH) -> \
            Tuple[bool, dict or str]:
        """
        Execute "show disks" command on primary controller.
        Parse output xml.
        Get response dict: key-"disks" and values dict of "durable-id",
        "location", "serial-number", "vendor",
                    "revision", "description", "interface", "usage", "size",
                    "disk-group", "storage-pool-name", "storage-tier",
                    "health", "health-reason", "health-recommendation".
        :param output_file_path: File path to save response of telnet
        common_cmd.
        :type: str
        :return: (Boolean, disks dict).
        :rtype: tuple
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.SHOW_DISKS_CMD
                LOGGER.debug(cmd)
                disks_param = CMN_DESTRUCTIVE_CFG.get("show_disks")
                LOGGER.debug(disks_param)
                if not isinstance(disks_param, dict):
                    raise Exception(f"Failed to get shows_disks: {disks_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res:
                    raise Exception(f"telnet_operations.py path '{runner_path}'"
                                    f" does not exist on primary node.")
                # Run 'show disks' command on primary controller.
                command = f"python3 {runner_path} " \
                          f"--telnet_op=" \
                          f"'execute_cmd_on_enclosure(enclosure_ip=\"" \
                          f"{self.enclosure_ip}\", enclosure_user=\"" \
                          f"{self.enclosure_user}\", enclosure_pwd=\"" \
                          f"{self.enclosure_pwd}\", " \
                          f"file_path=\"{output_file_path}\", cmd=\"{cmd}\")'"
                LOGGER.info("Running command : %s", command)
                resp = self.node_obj.execute_cmd(cmd=command,
                                                 read_lines=True)
                LOGGER.info("Show disk group response log: %s", resp)
                # Copy remote log file to local path.
                LOGGER.info("Copying log file from node to client")
                self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info("copy file log: %s", output_file_path)
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} not exists.")
                status, disks_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(disks_param.values()))
                LOGGER.debug("Show disks dict: %s", disks_dict)
                if not status:
                    raise Exception(f"failed to parse output file: {disks_dict}")
                # Cleanup dict.
                if isinstance(disks_dict, dict):
                    disks_dict = dict([(disks_dict[k]['durable-id'],
                                        dict([(ik, v[iv])
                                              for ik, iv in disks_param.items()
                                              if v.get(iv)]))
                                       for k, v in disks_dict.items()])
                # Remove local log file.
                if os.path.exists(output_file_path):
                    os.remove(output_file_path)
                if not disks_dict:
                    return False, disks_dict
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.get_show_disks.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return True, disks_dict

        return False, "File not found : telnet_operations.py"

    def clear_drive_metadata(self, drive_num: str) -> str:
        """
        Execute "clear metadata" command on primary controller.
        :param drive_num: Drive of which metadata is to be cleared
        :type: str
        :return: (Boolean, disks dict).
        :rtype: tuple
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                cmd = common_cmd.CMD_CLEAR_METADATA.format(drive_num)
                LOGGER.debug("Running command: %s", cmd)
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res:
                    raise Exception(f"telnet_operations.py path '{runner_path}'"
                                    f" does not exist on primary node.")
                # Run 'show disks' command on primary controller.
                command = f"python3 {runner_path} " \
                          f"--telnet_op=" \
                          f"'clear_metadata(enclosure_ip=\"" \
                          f"{self.enclosure_ip}\", enclosure_user=\"" \
                          f"{self.enclosure_user}\", enclosure_pwd=\"" \
                          f"{self.enclosure_pwd}\", cmd=\"{cmd}\")'"
                LOGGER.info("Running command : %s", command)
                resp = self.node_obj.execute_cmd(cmd=command,
                                                 read_lines=True)

                LOGGER.debug(resp)
                response = resp[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                    replace('\n', ' ').replace('\\n', ' ')).read()
            except Exception as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.clear_drive_metadata.__name__,
                                 error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return status

        return "False"

    def remove_add_drive(self, enclosure_id: str, controller_name: list,
                         drive_number: list, operation: str) -> Tuple[str, str]:
        """
        Enable or Disable drive status from disk group.
        :param enclosure_id: Enclosure ID of the machine
        :type: str
        :param controller_name: Server controller name
        :type: list
        :param drive_number: Drive number
        :type: list
        :param operation: Status of the drive. Value will be enabled or disabled
        :type: str
        :return: None
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                for drv in drive_number:
                    drv = drv.split(".")[-1]
                    for cnt in controller_name:
                        cmd = common_cmd.SET_DRIVE_STATUS_CMD.format(
                            enclosure_id, cnt, drv, operation)

                        command = f"python3 /root/telnet_operations.py " \
                                  f"--telnet_op='set_drive_status_telnet(" \
                                  f"enclosure_ip=\"{self.enclosure_ip}\", " \
                                  f"username=\"{self.enclosure_user}\", " \
                                  f"pwd=\"{self.enclosure_pwd}\", " \
                                  f"status=\"{operation}\", cmd=\"{cmd}\")'"

                        LOGGER.info("Running command %s", command)
                        response = self.node_obj.execute_cmd(cmd=command,
                                                             read_lines=True)

                        response = response[0].split()

                        status = os.popen(
                            (common_cmd.STRING_MANIPULATION.format(response[0]))
                            .replace('\n', ' ').replace('\\n', ' ')).read()
                        drive_status = os.popen(
                            (common_cmd.STRING_MANIPULATION.format(response[1]))
                            .replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.remove_add_drive.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return status, drive_status

        return "False", "File not found : telnet_operations.py"

    def add_spares_dg(self, drives: list, disk_group: str) -> Tuple[bool, str]:
        """
        Function to add spare drives in disk group
        :param drives: List of drives to be added
        :type: list
        :param disk_group: Disk group in which drives to be added
        :type: str
        :return: status, message
        :rtype: bool, str
        """
        self.copy_telnet_operations_file()
        if self.copy:
            try:
                LOGGER.info("Adding available drives to disk group %s", disk_group)
                LOGGER.info("Check usage of drives %s", drives)
                status, drive_usage_dict = self.get_drive_usage(phy_num=drives)
                if not status:
                    return status, f"Failed to get drive usages for drives {drives}"

                LOGGER.info("Drive usages: %s", drive_usage_dict)

                for key, value in drive_usage_dict.items():
                    if value == "LINEAR POOL":
                        return True, "Drive is already part of disk group"
                    elif value == "AVAIL":
                        LOGGER.info("Drive is already available")
                    elif value != "AVAIL" and value != "LINEAR POOL":
                        LOGGER.info("Running clear metadata")
                        resp = self.clear_drive_metadata(drive_num=key)
                        if not resp[0]:
                            return resp[0], resp[1]

                        LOGGER.info("Successfully cleared drive metadata of %s", key)

                    LOGGER.info("Adding spare drive %s to disk group %s", key, disk_group)
                    cmd = common_cmd.ADD_SPARES_CMD.format(key, disk_group)
                    command = f"python3 /root/telnet_operations.py " \
                              f"--telnet_op='set_drive_status_telnet(" \
                              f"enclosure_ip=\"{self.enclosure_ip}\", " \
                              f"username=\"{self.enclosure_user}\", " \
                              f"pwd=\"{self.enclosure_pwd}\", " \
                              f"status=\"{status}\", cmd=\"{cmd}\")'"

                    LOGGER.info("Running command %s", command)
                    response = self.node_obj.execute_cmd(cmd=command, read_lines=True)

                    LOGGER.info("Response: %s", response)
                    response = response[0].split()

                    status = os.popen(
                        (common_cmd.STRING_MANIPULATION.format(response[0]))
                        .replace('\n', ' ').replace('\\n', ' ')).read()
                    resp = os.popen(
                        (common_cmd.STRING_MANIPULATION.format(response[1]))
                        .replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.exception("Error in %s: %s", ControllerLib.add_spares_dg.__name__, error)
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return True, f"Successfully added drives {drives} to disk group {disk_group}"

    def get_dg_drive_list(self, disk_group: str) -> Tuple[bool, any]:
        """
        Function to get drives in disk group
        :param disk_group: Disk group name
        :type: str
        :return: status, drive_list
        :rtype: bool, list
        """
        drive_list = []
        status, drive_dict = self.get_show_disks()
        if status:
            LOGGER.info("Collecting drives under same disk group")
            for key, value in drive_dict.items():
                try:
                    if value['disk_group'] == disk_group:
                        drive_list.append(value['location'])
                except KeyError:
                    LOGGER.exception("No disk group found for %s", key)
                    continue

            return True, drive_list
        else:
            LOGGER.error("Failed to get drive details")
            return status, drive_dict

    def get_drive_usage(self, phy_num: list) -> Tuple[bool, dict]:
        """
        Function to get usage of drives
        :param phy_num: List of drives
        :type: list
        :return: status, dict of usages
        :rtype: bool, dict
        """
        drive_usage_dict = {}
        status, drive_dict = self.get_show_disks()
        if status:
            LOGGER.info("Getting drive usage")
            for d in phy_num:
                for key, value in drive_dict.items():
                    try:
                        if value['location'] == d:
                            drive_usage_dict[d] = value['usage']
                    except KeyError:
                        LOGGER.exception("No disk found of phy number %s", d)
                        continue

            return True, drive_usage_dict
        else:
            LOGGER.error("Failed to get drive details")
            return status, drive_dict

    def poll_dg_recon_status(self, disk_group: str, percent: int = 100) \
            -> Tuple[str, str, int]:
        """
        Function to poll disk group reconstruction progress
        :param disk_group: Disk group in which drives to be added
        :type: str
        :param percent: Upto which percent status shpuld be polled
        :type: int
        :return: status, progress percent
        :rtype: bool, int
        """
        LOGGER.info("Polling disk group reconstruction percent")
        recon_percent = 0
        while True:
            status, disk_group_dict = self.get_show_disk_group()
            LOGGER.info("Reconstruction percent: %s", recon_percent)
            recon_percent = disk_group_dict[disk_group].get('job_percent',
                                                            '100%')
            recon_percent = int(recon_percent.split("%")[0])
            if recon_percent >= percent:
                LOGGER.info("Checking if recon_percent >= percent")
                LOGGER.info("Reconstruction percent went beyond expected "
                            "percent. Reconstruction percent: %s%",
                            recon_percent)
                health = disk_group_dict[disk_group]['health']
                job = disk_group_dict[disk_group].get('job', 'No job running')
                final_percent = recon_percent
                break
            elif disk_group_dict[disk_group]['health'] == "OK":
                LOGGER.info("Reconstruction of disk group %s completed. Disk "
                            "group is in healthy state", disk_group)
                health = disk_group_dict[disk_group]['health']
                job = disk_group_dict[disk_group].get('job', 'No job running')
                final_percent = recon_percent
                break
            elif disk_group_dict[disk_group].get('job') is None:
                LOGGER.info("No job is running", disk_group)
                health = disk_group_dict[disk_group]['health']
                job = disk_group_dict[disk_group].get('job', 'No job running')
                final_percent = recon_percent
                break

        return health, job, final_percent
