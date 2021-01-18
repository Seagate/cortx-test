#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This test helper lib implements the base functions for controller operations
"""
import logging
import requests
import os
from typing import Tuple
from commons.helpers.host import Host
from commons.helpers.node_helper import Node
from commons import constants as cons
from commons import commands as common_cmd
from commons import errorcodes as cterr
from commons.exceptions import CTException
from commons.utils import config_utils as conf_util

LOGGER = logging.getLogger(__name__)

COMMON_CONF = conf_util.read_yaml(cons.COMMON_CONFIG_PATH)[1]
COMMON_DESTRUCTIVE_VAL = conf_util.read_yaml(cons.COMMON_CONFIG_PATH)[1]
RAS_VAL = conf_util.read_yaml(cons.RAS_CONFIG_PATH)[1]

BYTES_TO_READ = cons.BYTES_TO_READ


class ControllerLib:
    """
    RAS helper functions which for Test-cases
    """

    def __init__(self, host=COMMON_CONF["host"], h_user=COMMON_CONF["username"],
                 h_pwd=COMMON_CONF["password"],
                 enclosure_ip=COMMON_CONF["primary_enclosure_ip"],
                 enclosure_user=COMMON_CONF["enclosure_user"],
                 enclosure_pwd=COMMON_CONF["enclosure_pwd"]):
        """This method initializes members of ControllerLib class
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
        self.host = host
        self.h_user = h_user
        self.h_pwd = h_pwd
        self.enclosure_ip = enclosure_ip
        self.enclosure_user = enclosure_user
        self.enclosure_pwd = enclosure_pwd
        self.host_connect = Host(hostname=self.host, username=self.h_user,
                                 password=self.h_pwd)
        self.node_obj = Node(hostname=self.host, username=self.h_user,
                             password=self.h_pwd)

        self.copy = True
        runner_path = cons.REMOTE_TELNET_PATH
        local_path = cons.TELNET_OP_PATH
        LOGGER.info(f"Copying file {local_path} to {runner_path}")
        self.node_obj.copy_file_to_remote(local_path=local_path,
                                          remote_path=runner_path)

        if not self.node_obj.path_exists(path=runner_path):
            self.copy = False

    def get_mc_ver_sr(self) -> Tuple[str, str, str]:
        """
        Function to get the version and serial number of the management
        controller
        :return: version and serial number of the management controller
        :rtype: String
        """
        if self.copy:
            try:
                cmd = common_cmd.SET_DEBUG_CMD

                command = f"python3 /root/telnet_operations.py " \
                          f"--telnet_op=" \
                          f"'get_mc_ver_sr(enclosure_ip=\"{self.enclosure_ip}\", " \
                          f"enclosure_user=\"{self.enclosure_user}\", " \
                          f"enclosure_pwd=\"{self.enclosure_pwd}\", cmd=\"{cmd}\")'"

                LOGGER.info(f"Running command {command}")
                response = self.host_connect.execute_cmd(cmd=command,
                                                         read_lines=True,
                                                         shell=False)
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

                return status, mc_ver, mc_sr
            except BaseException as error:
                LOGGER.error(f"Error in {ControllerLib.get_mc_ver_sr.__name__}:"
                             f" {error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def get_mc_debug_pswd(self, mc_ver: str, mc_sr: str) -> str:
        """
        Function to get the password for management controller debug console
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
            LOGGER.error(f"Error in {ControllerLib.get_mc_debug_pswd.__name__}:"
                         f" {error}")
            raise CTException(cterr.RAS_ERROR, error.args[0])

        LOGGER.info(f"MC debug password: {mc_password}")
        return mc_password

    def simulate_fault_ctrl(self, mc_deb_password: str, enclid: str, pos: str,
                            fru: str, type_fault: str, ctrl_name: str) -> \
            Tuple[str, str]:
        """
        Function to simulate faults on the controller
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
                          f"telnet_port=\"{telnet_port}\", timeout=\"{timeout}\", " \
                          f"cmd=\"{cmd}\")'"

                LOGGER.info(f"Running command {command}")
                response = self.host_connect.execute_cmd(cmd=command,
                                                         read_lines=True,
                                                         shell=False)
                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                        replace('\n', ' ').replace('\\n', ' ')).read()
                password_str = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(
                        response[1])).replace(
                        '\n', ' ').replace(
                        '\\n', ' ')).read()

                return status, password_str
            except BaseException as error:
                LOGGER.error(f"Error in "
                             f"{ControllerLib.simulate_fault_ctrl.__name__}:"
                             f" {error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def show_disks(self, telnet_file: str) -> Tuple[str, str]:
        """
        Show disk.
        :param telnet_file: File path to save response of telnet command
        :type: str
        :return: Boolean, file path
        :rtype: Tuple of (bool, String)
        """
        if self.copy:
            try:
                common_cfg = RAS_VAL["ras_sspl_alert"]
                LOGGER.info(f"Show disks for {self.enclosure_ip} enclosure.")
                cmd = common_cmd.SHOW_DISKS_CMD

                command = f"python3 /root/telnet_operations.py " \
                          f"--telnet_op=" \
                          f"'show_disks(enclosure_ip=\"{self.enclosure_ip}\", " \
                          f"enclosure_user=\"{self.enclosure_user}\", " \
                          f"enclosure_pwd=\"{self.enclosure_pwd}\", " \
                          f"telnet_filepath=\"{telnet_file}\", " \
                          f"cmd=\"{cmd}\")'"

                LOGGER.info(f"Running command : {command}")
                response = self.host_connect.execute_cmd(cmd=command,
                                                         read_lines=True,
                                                         shell=False)

                LOGGER.info(response)
                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                        replace('\n', ' ').replace('\\n', ' ')).read()
                path = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[1])).
                        replace('\n', ' ').replace('\\n', ' ')).read()
            except BaseException as error:
                LOGGER.error(
                    f"Error in {ControllerLib.show_disks.__name__}: {error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])
            return status, path

    def get_total_drive_count(self, telnet_file: str) -> Tuple[str, int]:
        """
        Get total number of drives mapped.
        :param telnet_file: File path to save response of telnet command
        :type: str
        :return: (Boolean, Number of drives)
        :rtype: Boolean, Integer
        """
        if self.copy:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            try:
                resp = self.show_disks(telnet_file=telnet_file)

                LOGGER.info("Copying telnet file from node to client")
                resp = self.node_obj.write_remote_file_to_local_file(
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

                return resp[0], len(drive_dict)
            except BaseException as error:
                LOGGER.error(
                    f"Error on {ControllerLib.get_total_drive_count.__name__}:"
                    f" {error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

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
        if self.copy:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            try:
                resp = self.show_disks(telnet_file=telnet_file)

                LOGGER.info("Copying telnet file from node to client")
                resp = self.node_obj.write_remote_file_to_local_file(
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

                return resp[0], status
            except BaseException as error:
                LOGGER.error(
                    f"Error in {ControllerLib.check_phy_health.__name__}: "
                    f"{error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

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

                LOGGER.info(f"Running command {command}")
                response = self.host_connect.execute_cmd(cmd=command,
                                                         read_lines=True,
                                                         shell=False)

                response = response[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[0])).
                        replace('\n', ' ').replace('\\n', ' ')).read()
                drive_status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(
                        response[1])).replace(
                        '\n', ' ').replace(
                        '\\n', ' ')).read()

                return status, drive_status
            except BaseException as error:
                LOGGER.error(f"Error in"
                             f" {ControllerLib.set_drive_status_telnet.__name__}:"
                             f" {error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def get_show_volumes(self, output_file_path: str = cons.CTRL_LOG_PATH) ->\
            Tuple[bool, dict]:
        """
        Execute "show volumes" command on primary enclosure.
        Parse output file.
        Return response dict: {key: disk-group, {Values: key: volume,
        {values: "storage-pool-name", "volume-name",
                            "total-size", "allocated-size", "storage-type",
                            "health", "health-reason",
                            "health-recommendation"}}}
        :param output_file_path: File path to save response of telnet common_cmd.
        :type: str
        :return: (Boolean, disk volume dict).
        :rtype: tuple
        """
        if self.copy:
            try:
                cmd = common_cmd.CMD_SHOW_VOLUMES
                LOGGER.debug(cmd)
                volumes_param = COMMON_DESTRUCTIVE_VAL.get("show_volumes")
                LOGGER.debug(volumes_param)
                if not isinstance(volumes_param, dict):
                    raise Exception(f"Failed to get show_volumes: "
                                    f"{volumes_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res[0]:
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
                LOGGER.info(f"Running command : {command}")
                resp = self.host_connect.execute_cmd(cmd=command,
                                                     read_lines=True,
                                                     shell=False)
                LOGGER.info(f"Show volumes response log: {resp}")
                # Copy remote log file to local path.
                LOGGER.info("Copying log file from node to client")
                status, res_path = self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info(f"copy file log: {status, resp}")
                if not status:
                    raise Exception(f"Failed to copy file: {output_file_path}. "
                                    f"response: {res_path}")
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} "
                                    f"not exists.")
                status, disk_volumes_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(volumes_param.values()))
                LOGGER.debug(f'Show volumes dict: {disk_volumes_dict}')
                if not status:
                    raise Exception(f"failed to parse output file: "
                                    f"{disk_volumes_dict}")
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

                return True, disk_volumes_dict
            except BaseException as error:
                LOGGER.error(
                    f"Error in {ControllerLib.get_show_volumes.__name__}: "
                    f"{error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def get_show_expander_status(self, output_file_path: str = cons.CTRL_LOG_PATH) \
            -> Tuple[bool, dict]:
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
        if self.copy:
            try:
                cmd = common_cmd.CMD_SHOW_XP_STATUS
                LOGGER.debug(cmd)
                expander_param = COMMON_DESTRUCTIVE_VAL.get("show_expander_"
                                                            "status")
                LOGGER.debug(expander_param)
                if not isinstance(expander_param, dict):
                    raise Exception(f"Failed to get show_expander_status: "
                                    f"{expander_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res[0]:
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
                LOGGER.info(f"Running command : {command}")
                resp = self.host_connect.execute_cmd(cmd=command,
                                                     read_lines=True,
                                                     shell=False)
                LOGGER.info(f"Show show expander-status response log: {resp}")
                LOGGER.info("Copying log file from node to client")
                status, res_path = self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info(f"copy file log: {status, resp}")
                if not status:
                    raise Exception(f"Failed to copy log. response: {res_path}")
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} "
                                    f"not exists.")
                status, expander_status_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(expander_param.values()))
                LOGGER.debug(f'Show expander-status dict: '
                             f'{expander_status_dict}')
                if not status:
                    raise Exception(f"failed to parse output file: "
                                    f"{expander_status_dict}")
                # Cleanup dict.
                if isinstance(expander_status_dict, dict):
                    d = {}
                    keys = expander_status_dict.keys()
                    for k in keys:
                        if expander_status_dict[k].get("type") == "Drive":
                            if expander_status_dict[k].get(
                                    'controller') not in d:
                                d[expander_status_dict[k].get('controller')] = {
                                    int(expander_status_dict[k][
                                            "wide-port-index"]):
                                        dict([(ik, expander_status_dict[k][iv])
                                              for ik, iv in
                                              expander_param.items()
                                              if
                                              expander_status_dict[k].get(iv)])
                                }
                            else:
                                d[expander_status_dict[k].get(
                                    'controller')].update({
                                    int(expander_status_dict[k][
                                            "wide-port-index"]):
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

                return True, expander_status_dict
            except BaseException as error:
                LOGGER.error(
                    f"Error in "
                    f"{ControllerLib.get_show_expander_status.__name__}:"
                    f" {error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def get_show_disk_group(self, output_file_path: str = cons.CTRL_LOG_PATH)\
            -> Tuple[bool, dict]:
        """
        Execute "show disk-groups" command on primary controller.
        Parse output xml.
        Get response dict: key-"disk group" and values dict of "name, size,
        health, health-reason, health-recommendation".
        :param output_file_path: File path to save response of telnet common_cmd.
        :type: str
        :return: (Boolean, disk group dict).
        :rtype: tuple
        """
        if self.copy:
            try:
                cmd = common_cmd.CMD_SHOW_DISK_GROUP
                LOGGER.debug(cmd)
                diskgroup_param = COMMON_DESTRUCTIVE_VAL.get("show_disk_groups")
                LOGGER.debug(diskgroup_param)
                if not isinstance(diskgroup_param, dict):
                    raise Exception(f"Failed to get show_disk_group: "
                                    f"{diskgroup_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res[0]:
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
                LOGGER.info(f"Running command : {command}")
                resp = self.host_connect.execute_cmd(cmd=command,
                                                     read_lines=True,
                                                     shell=False)
                LOGGER.info(f"Show disk group response log: {resp}")
                # Copy remote log file to local path.
                LOGGER.info("Copying log file from node to client")
                status, res_path = self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info(f"copy file log: {status, resp}")
                if not status:
                    raise Exception(f"Failed to copy file: {output_file_path}. "
                                    f"response: {res_path}")
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} "
                                    f"not exists.")
                status, disk_group_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(diskgroup_param.values()))
                LOGGER.debug(f'Show disk-group dict: {disk_group_dict}')
                if not status:
                    raise Exception(f"failed to parse output file: "
                                    f"{disk_group_dict}")
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

                return True, disk_group_dict
            except BaseException as error:
                LOGGER.error(
                    f"Error in {ControllerLib.get_show_disk_group.__name__}: "
                    f"{error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def get_show_disks(self, output_file_path: str = cons.CTRL_LOG_PATH) -> \
            Tuple[bool, dict]:
        """
        Execute "show disks" command on primary controller.
        Parse output xml.
        Get response dict: key-"disks" and values dict of "durable-id",
        "location", "serial-number", "vendor",
                    "revision", "description", "interface", "usage", "size",
                    "disk-group", "storage-pool-name", "storage-tier",
                    "health", "health-reason", "health-recommendation".
        :param output_file_path: File path to save response of telnet common_cmd.
        :type: str
        :return: (Boolean, disks dict).
        :rtype: tuple
        """
        if self.copy:
            try:
                cmd = common_cmd.SHOW_DISKS_CMD
                LOGGER.debug(cmd)
                disks_param = COMMON_DESTRUCTIVE_VAL.get("show_disks")
                LOGGER.debug(disks_param)
                if not isinstance(disks_param, dict):
                    raise Exception(f"Failed to get shows_disks: {disks_param}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res[0]:
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
                LOGGER.info(f"Running command : {command}")
                resp = self.host_connect.execute_cmd(cmd=command,
                                                     read_lines=True,
                                                     shell=False)
                LOGGER.info(f"Show disk group response log: {resp}")
                # Copy remote log file to local path.
                LOGGER.info("Copying log file from node to client")
                status, res_path = self.node_obj.write_remote_file_to_local_file(
                    file_path=output_file_path, local_path=output_file_path)
                LOGGER.info(f"copy file log: {status, resp}")
                if not status:
                    raise Exception(f"Failed to copy file: {output_file_path}. "
                                    f"response: {res_path}")
                # Parse output xml.
                if not os.path.exists(output_file_path):
                    raise Exception(f"Local copy for {output_file_path} "
                                    f"not exists.")
                status, disks_dict = conf_util.parse_xml_controller(
                    filepath=output_file_path,
                    field_list=list(disks_param.values()))
                LOGGER.debug(f'Show disks dict: {disks_dict}')
                if not status:
                    raise Exception(f"failed to parse output file: "
                                    f"{disks_dict}")
                # Cleanup dict.
                if isinstance(disks_dict, dict):
                    disks_dict = dict([(disks_dict[k]['durable-id'],
                                        dict([(ik, v[iv])
                                              for ik, iv in disks_param.items()
                                              if v.get(iv)])
                                        ) for k, v in disks_dict.items()])
                # Remove local log file.
                if os.path.exists(output_file_path):
                    os.remove(output_file_path)
                if not disks_dict:
                    return False, disks_dict

                return True, disks_dict
            except BaseException as error:
                LOGGER.error(
                    f"Error in {ControllerLib.get_show_disks.__name__}: "
                    f"{error}")
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

    def clear_drive_metadata(self, drive_num: str) -> str:
        """
        Execute "clear metadata" command on primary controller.
        :param drive_num: Drive of which metadata is to be cleared
        :type: str
        :return: (Boolean, disks dict).
        :rtype: tuple
        """
        if self.copy:
            try:
                cmd = common_cmd.CMD_CLEAR_METADATA.format(drive_num)
                LOGGER.debug(f"Running command: {cmd}")
                # Check telnet_operations.py present on primary node.
                runner_path = cons.REMOTE_TELNET_PATH
                res = self.node_obj.path_exists(path=runner_path)
                if not res[0]:
                    raise Exception(f"telnet_operations.py path '{runner_path}'"
                                    f" does not exist on primary node.")
                # Run 'show disks' command on primary controller.
                command = f"python3 {runner_path} " \
                          f"--telnet_op=" \
                          f"'clear_metadata(enclosure_ip=\"" \
                          f"{self.enclosure_ip}\", enclosure_user=\"" \
                          f"{self.enclosure_user}\", enclosure_pwd=\"" \
                          f"{self.enclosure_pwd}\", cmd=\"{cmd}\")'"
                LOGGER.info(f"Running command : {command}")
                resp = self.host_connect.execute_cmd(cmd=command,
                                                     read_lines=True,
                                                     shell=False)

                LOGGER.debug(resp)
                response = resp[0].split()

                status = os.popen(
                    (common_cmd.STRING_MANIPULATION.format(response[
                                                               0])).
                        replace('\n', ' ').replace('\\n', ' ')).read()

            except Exception as error:
                LOGGER.error("Error in {0}: {1}".format(
                    ControllerLib.clear_drive_metadata.__name__, error))
                raise CTException(cterr.CONTROLLER_ERROR, error.args[0])

            return status
