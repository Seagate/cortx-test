#!/usr/bin/python # pylint: disable=C0302
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

"""
File test helper lib implements the base functions of ras_lib by inheriting the
class
"""
import logging
import os
import random
import re
import time
from decimal import Decimal
from typing import Tuple, Any, Union

from commons import commands as common_commands
from commons import constants as cmn_cons
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.helpers.node_helper import Node
from commons.utils import system_utils as sys_utils
from commons.utils.config_utils import get_config
from commons.utils.config_utils import update_cfg_based_on_separator
from config import CMN_CFG
from config import RAS_VAL
from libs.ras.ras_core_lib import RASCoreLib

# Global Constants
LOGGER = logging.getLogger(__name__)


class RASTestLib(RASCoreLib):
    """
    Test lib calls for RAS test-cases
    """

    def __init__(
            self,
            host: str = None,
            username: str = None,
            password: str = None) -> None:
        """
        Method initializes members of RASTestLib and its parent class

        :param str host: host
        :param str username: username
        :param str password: password
        """
        nd_cfg = CMN_CFG.get("nodes", None)
        ldap_cfg = CMN_CFG.get("ldap", None)
        self.host = host if host else nd_cfg[0]["host"] if nd_cfg else None
        self.pwd = password if password else nd_cfg[0]["password"] if nd_cfg else None
        self.username = username if username else nd_cfg[0]["username"] if nd_cfg else None
        self.sspl_pass = ldap_cfg["sspl_pass"] if ldap_cfg else None
        self.system_random = random.SystemRandom()

        super().__init__(host, username, password)

    def start_rabbitmq_reader_cmd(self, sspl_exchange: str, sspl_key: str,
                                  **kwargs) -> bool:
        """
        Function will check for the disk space alert for sspl.

        :param str sspl_exchange: sspl exchange string
        :param str sspl_key: sspl key string
        :keyword sspl_pass: sspl_pass
        :return: Command response along with status(True/False)
        :rtype: bool
        """
        sspl_pass = kwargs.get("sspl_pass") if kwargs.get("sspl_pass") else \
            self.sspl_pass
        try:
            LOGGER.info("Start rabbitmq chanel on node %s ", self.host)
            cmd_output = super().start_rabbitmq_reader_cmd(sspl_exchange,
                                                           sspl_key,
                                                           sspl_pass=sspl_pass)
            LOGGER.debug(cmd_output)
            return cmd_output
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.start_rabbitmq_reader_cmd.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

    def start_message_bus_reader_cmd(self) -> bool:
        """
        Function will check for the alerts in message bus.

        :return: Command response along with status(True/False)
        :rtype: bool
        """
        try:
            LOGGER.info("Start to read message bus on node %s ", self.host)
            cmd_output = super().start_message_bus_reader_cmd()
            LOGGER.debug(cmd_output)
            return cmd_output
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.start_rabbitmq_reader_cmd.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

    def check_sspl_event_generated(self) -> Tuple[bool, Any]:
        """
        Check for relevant events are generated on RabbitMQ Channel for the
        specific volumes inside disk group.

        :return: (Boolean, response)
        :rtype: (bool, str)
        """
        cmd = common_commands.SSPL_SERVICE_CMD
        LOGGER.debug(cmd)
        try:
            LOGGER.info("Check ssp events are generated")
            res = self.node_utils.execute_cmd(
                cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
            LOGGER.info(res)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.check_sspl_event_generated.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return res

    def check_status_file(self) -> Tuple[bool, Any]:
        """
        Function checks the state.txt file of sspl service and sets the
        status=active.

        :return: (Boolean, response)
        :rtype: (bool, resp)
        """
        try:
            LOGGER.info("Check sspl status file")
            response = super().check_status_file()
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASCoreLib.check_status_file.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, response

    def put_kv_store(self, username: str, pwd: str, field: str) -> bool:
        """
        Function updates the values in KV store as per the values in
        storage_enclosure.sls.

        :param str username: Username of the enclosure
        :param str pwd: password for the enclosure user
        :param str field: Field in K store to be updated
        :return: Boolean
        :rtype: bool
        """
        try:
            LOGGER.info("Put expected value of %s in KV store", field)
            response = super().put_kv_store(username, pwd, field)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASCoreLib.put_kv_store.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return response

    def retain_config(self, filename: str, restore: bool):
        """
        Function renames the sspl.cong file to sspl_original.cong to retain
        the original config

        :param str filename: Name of the file to be renamed
        :param bool restore: boolean value to specify te operation
        :return: Boolean
        :rtype: bool
        """
        path = RAS_VAL["ras_sspl_alert"]["file"]["sspl_conf_filename"]
        backup_path = filename
        node = Node(hostname=self.host, username=self.username, password=self.pwd)
        if restore:
            res = node.path_exists(path=backup_path)
            if res:
                LOGGER.info("Restoring the sspl.conf file")
                self.node_utils.rename_file(old_filename=backup_path,
                                            new_filename=path)
                LOGGER.info("Removing %s file", backup_path)
                self.node_utils.remove_file(filename=backup_path)
            else:
                LOGGER.info("Removing sspl.conf file")
                self.node_utils.remove_file(filename=path)
        else:
            res = node.path_exists(path=path)
            if res:
                LOGGER.info("Retaining the %s file", path)
                self.cp_file(path, backup_path)

    def validate_alert_log(self, filename: str,
                           string: str) -> Tuple[bool, Any]:
        """
        Function validates if the specific alerts are generated.

        :param filename: Name of the log file in which alerts are stored
        :param string: String of the alert message
        :return: Boolean
        :rtype: bool
        """
        resp = self.node_utils.is_string_in_remote_file(string=string,
                                                        file_path=filename)
        if resp[0]:
            LOGGER.info("Alert %s generated successfully on node", string)
        else:
            LOGGER.info("%s Alert is not generated", string)

        return resp

    def kill_remote_process(self, process_name: str) -> Tuple[bool, str]:
        """
        Function kills the process running on remote server with process
        name (Be careful while using this function as it kills all the processes
        having specified name)

        :param process_name: Name of the process to be killed
        :returns: Response in tuple
        """
        cmd = common_commands.KILL_PROCESS_CMD.format(process_name)
        return self.node_utils.execute_cmd(cmd=cmd,
                                           read_nbytes=cmn_cons.BYTES_TO_READ)

    def update_threshold_values(self, kv_store_path: str, field: str, value,
                                update: bool = True) -> bool:
        """
        Function updates the values in KV store as per the values.

        :param kv_store_path: Path of the field in kv-store
        :param field: Field in KV store to be updated
        :param value: Threshold value to be updated
        :param update: Flag for updating the consul value or not
        :return: True/False
        :rtype: bool
        """
        try:
            LOGGER.info("Updating the consul value %s", field)
            response = super().update_threshold_values(kv_store_path, field,
                                                       value, update=update)
            LOGGER.info(response)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.update_threshold_values.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True

    def reset_log_file(self, file_path: str) -> bool:
        """
        Function takes the backup of the log file and then empties the file.

        :param str file_path: path of the remote file
        :return: True/False
        :rtype: bool
        """
        try:
            # Copy existing log to another file
            LOGGER.info("Creating backup log file")
            remote_dir = "/".join(file_path.split("/")[:-1])
            bck_file_path = f"{remote_dir}/bck.log"
            res = self.cp_file(file_path, bck_file_path)
            LOGGER.info("Copy file resp : %s", res)
            res = self.truncate_file(file_path)
            LOGGER.info("Reset file resp : %s", res)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.reset_log_file.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True

    def get_sspl_state(self) -> Tuple[bool, str]:
        """
        Function reads the sspl text file to get state of sspl on master node.

        :return: Boolean and response
        :rtype: (bool, str)
        """
        try:
            LOGGER.info("Getting the SSPL state")
            response = super().get_sspl_state()
            LOGGER.info(response)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_sspl_state.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return response

    # pylint: disable=too-many-statements
    def generate_disk_full_alert(
            self,
            du_val: int,
            fault: bool = True,
            fault_resolved: bool = False) -> Tuple[bool, float]:
        """
        Function to verify the sspl disk space alert, both positive and negative
        based on the disk usage

        :param int du_val: Value to be added to current disk usage to form new
         disk_usage_threshold
        :param bool fault: True to generate disk full fault alert, default True
        :param bool fault_resolved: True to generate disk full fault_resolved
         alert, default False
        :return: status, current disk usage(bool,int|float)
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            status = False
            LOGGER.info("Retrieve original value of disk_usage_threshold")
            self.node_utils.copy_file_to_local(
                common_cfg["file"]["sspl_conf_filename"],
                common_cfg["file"]["sspl_cfg_temp"])
            default_disk_threshold = get_config(
                common_cfg["file"]["sspl_cfg_temp"],
                common_cfg["sspl_config"]["sspl_section"],
                common_cfg["sspl_config"]["sspl_du_key"])
            LOGGER.info(
                "Original value of %s :%s",
                common_cfg["sspl_config"]["sspl_du_key"],
                default_disk_threshold)

            resp = self.node_utils.disk_usage_python_interpreter_cmd(
                dir_path=common_cfg["sspl_config"]["server_du_path"],
                field_val=0)
            total_disk_size = int(resp[1].strip().decode("utf-8"))
            file_name = common_cfg["file"]["disk_usage_temp_file"]
            file_size = int((total_disk_size * du_val) / (1024 * 1024 * 100)) * 2

            LOGGER.info("Fetching server disk usage")
            resp = self.node_utils.disk_usage_python_interpreter_cmd(
                dir_path=common_cfg["sspl_config"]["server_du_path"])
            current_disk_usage = float(resp[1].strip().decode("utf-8"))
            LOGGER.info("Current disk usage of EES server : %s",
                        current_disk_usage)
            new_disk_threshold = current_disk_usage + du_val

            LOGGER.info(
                "Setting value of disk_usage_threshold to %s",
                new_disk_threshold)
            res = self.update_threshold_values(
                cmn_cons.KV_STORE_DISK_USAGE,
                common_cfg["sspl_config"]["sspl_du_key"],
                new_disk_threshold)
            LOGGER.info("Updated server disk_usage_threshold value")

            LOGGER.info("Restarting sspl services and waiting some time")
            self.health_obj.restart_pcs_resource(
                common_cfg["sspl_resource_id"])
            time.sleep(common_cfg["sleep_val"])
            LOGGER.info(res)

            if fault:
                if self.node_utils.path_exists(file_name):
                    LOGGER.info("Remove temp disk usage file")
                    self.node_utils.remove_file(filename=file_name)
                LOGGER.info(
                    "Creating file %s on host %s to increase the disk "
                    "usage of size %s", file_name, self.host, file_size)
                resp = self.node_utils.create_file(
                    file_name, file_size)
                LOGGER.info(resp)
                time.sleep(common_cfg["one_min_delay"])
                LOGGER.info("Fetching server disk usage")
                resp = self.node_utils.disk_usage_python_interpreter_cmd(
                    dir_path=common_cfg["sspl_config"]["server_du_path"])
                current_disk_usage = float(resp[1].strip().decode("utf-8"))
                LOGGER.info("Current disk usage of EES server :%s",
                            current_disk_usage)
                status = current_disk_usage >= new_disk_threshold
                LOGGER.info("Disk fault generation status: %s", status)

            if fault_resolved:
                LOGGER.info(
                    "Removing file %s to reduce the disk usage on host "
                    "%s", file_name, self.host)
                self.node_utils.remove_file(file_name)
                time.sleep(common_cfg["one_min_delay"])
                LOGGER.info("Fetching server disk usage")
                resp = self.node_utils.disk_usage_python_interpreter_cmd(
                    dir_path=common_cfg["sspl_config"]["server_du_path"])
                current_disk_usage = float(resp[1].strip().decode("utf-8"))
                LOGGER.info("Current disk usage of EES server :%s",
                            current_disk_usage)
                status = current_disk_usage < new_disk_threshold
                LOGGER.info("Disk fault generation status: %s", status)
                time.sleep(common_cfg["one_min_delay"])

        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.generate_disk_full_alert.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return status, current_disk_usage

    def list_alert_validation(self, string_list: list) -> Tuple[bool, Any]:
        """
        Function to verify the alerts generated on specific events.

        :param list string_list: List of expected strings in alert response
        having
        format [resource_type, alert_type, ...]
        :return: response in tuple{bool, resp)
        :rtype: (bool, str)
        """
        common_cfg = RAS_VAL["ras_sspl_alert"]
        try:
            LOGGER.info("Checking status of sspl and kafka services")
            resp = self.s3obj.get_s3server_service_status(
                common_cfg["service"]["sspl_service"], host=self.host,
                user=self.username, pwd=self.pwd)
            if not resp[0]:
                return resp
            resp = self.s3obj.get_s3server_service_status(
                common_cfg["service"]["kafka_service"], host=self.host,
                user=self.username, pwd=self.pwd)
            if not resp[0]:
                return resp
            LOGGER.info(
                "Verified sspl and kafka services are in running state")
            time.sleep(common_cfg["sleep_val"])

            LOGGER.info("Fetching sspl alert response")
            response = self.cp_file(common_cfg["file"]["screen_log"],
                                    common_cfg["file"]["alert_log_file"])
            if not response[0]:
                return response
            LOGGER.info("Successfully fetched the alert response")

            LOGGER.debug("Reading the alert log file")
            read_resp = self.node_utils.read_file(
                common_cfg["file"]["alert_log_file"],
                common_cfg["file"]["local_path"])
            LOGGER.debug(
                "======================================================")
            LOGGER.debug(read_resp)
            LOGGER.debug(
                "======================================================")

            LOGGER.info(
                "Checking if alerts are generated on message bus")
            cmd = common_commands.EXTRACT_LOG_CMD.format(
                common_cfg["file"]["alert_log_file"], string_list[0])
            self.node_utils.execute_cmd(cmd=cmd,
                                        read_nbytes=cmn_cons.BYTES_TO_READ)
            resp = self.validate_alert_msg(
                common_cfg["file"]["extracted_alert_file"], string_list)

            LOGGER.info(resp)
            return resp
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.list_alert_validation.__name__, error)
            return False, error

    def generate_cpu_usage_alert(self, delta_cpu_usage: str, ) -> bool:
        """
        Function to generate cpu usage alert, both positive and negative
        based on the delta_cpu_usage value

        :param delta_cpu_usage: Value to be added or subtracted from current cpu
         usage as per requirement
        :return: True/False
        :rtype: bool
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            LOGGER.info("Fetching cpu usage from server node %s", self.host)
            resp = self.health_obj.get_cpu_usage()

            current_cpu_usage = resp
            LOGGER.info("Current cpu usage of server node %s is %s", self.host, current_cpu_usage)
            new_threshold_cpu_usage = float("{:.1f}".format(sum([resp, delta_cpu_usage])))
            LOGGER.info("Setting new value of cpu_usage_threshold to %s on node %s",
                        new_threshold_cpu_usage, self.host)

            resp = self.update_threshold_values(cmn_cons.KV_STORE_DISK_USAGE,
                                                cmn_cons.CPU_USAGE_KEY, new_threshold_cpu_usage)

            LOGGER.info("Updated server cpu_usage_threshold to %s", new_threshold_cpu_usage)

            LOGGER.info("Restarting sspl service on node %s", self.host)
            self.health_obj.restart_pcs_resource(common_cfg["sspl_resource_id"])
            LOGGER.info("Sleeping for %s seconds after restarting sspl service",
                        common_cfg["sleep_val"])
            time.sleep(common_cfg["sleep_val"])

        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.generate_cpu_usage_alert.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return resp

    def generate_memory_usage_alert(
            self,
            delta_mem_usage: str,
            host: str = None) -> bool:
        """
        Function to generate memory usage alert, both positive and negative
        based on the delta_mem_usage value

        :param host: host machine ip
        :param delta_mem_usage: Value to be added or subtracted from current
        memory usage as per requirement
        :return: True/False
        :rtype: bool
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            host = host if host else self.host
            LOGGER.info("Fetching memory usage from server node %s", host)
            resp = self.health_obj.get_memory_usage()

            current_mem_usage = resp
            LOGGER.info("Current memory usage of server node %s is %s", host, current_mem_usage)
            new_threshold_mem_usage = float("{:.1f}".format(sum([resp, delta_mem_usage])))
            LOGGER.info("Setting new value of host_memory_usage_threshold to %s on node %s",
                        new_threshold_mem_usage, host)

            resp = self.update_threshold_values(cmn_cons.KV_STORE_DISK_USAGE,
                                                cmn_cons.MEM_USAGE_KEY, new_threshold_mem_usage)

            LOGGER.info("Updated server host_memory_usage_threshold to %s", new_threshold_mem_usage)

            LOGGER.info("Restarting sspl service on node %s", host)
            self.health_obj.restart_pcs_resource(common_cfg["sspl_resource_id"])
            LOGGER.info("Sleeping for %s seconds after restarting sspl service",
                        common_cfg["sleep_val"])
            time.sleep(common_cfg["sleep_val"])

        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.generate_cpu_usage_alert.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return resp

    def update_mdadm_config(self) -> str:
        """
        Method updates the current MDRAID devices details into mdadm config.

        :return: content of mdadm config
        :rtype: str
        """
        LOGGER.info(
            "Updating the mdadm config %s", RAS_VAL["mdadm_conf_path"])
        try:
            update_conf_arg = common_commands.MDADM_UPDATE_CONFIG
            mdadm_conf_path = RAS_VAL["mdadm_conf_path"]
            local_path = RAS_VAL["mdadm_conf_local_path"]
            mdadm_args = [update_conf_arg, mdadm_conf_path]
            super().run_mdadm_cmd(mdadm_args)
            self.node_utils.write_remote_file_to_local_file(
                mdadm_conf_path,
                local_path)
            with open(local_path, "r", encoding="utf-8") as f_pointer:
                mdadm_conf = f_pointer.read()
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.update_mdadm_config.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return mdadm_conf

    def create_mdraid_disk_array(
            self,
            md_device: str,
            *disks: Any) -> Tuple[bool, Union[str, dict]]:
        """
        Method creates a MDRAID array device with the given list of disks.

        :param str md_device: MDRAID device to be created
        :param disks: Disks to be added in the MDRAID array
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info(
            "Creating a MDRAID device %s with disks %s on the host %s",
            md_device, disks, self.host)
        if not md_device:
            return False, "Please provide RAID device name e.g., /dev/md?"
        if not disks:
            return False, "Please provide disk from RAID device e.g., /dev/sd??"
        try:
            create_mdraid_cmd = common_commands.MDADM_CREATE_ARRAY.format(md_device, len(disks))
            mdadm_args = [create_mdraid_cmd]
            for disk in disks:
                mdadm_args.append(disk)
            super().run_mdadm_cmd(mdadm_args)
            mdadm_conf = self.update_mdadm_config()
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(
                    md_device) in md_stat["devices"] and md_device in mdadm_conf:
                md_stat_disks = md_stat["devices"][os.path.basename(md_device)]["disks"]
                disk_flag = [True for disk in disks if os.path.basename(disk) in md_stat_disks]
                if all(disk_flag):
                    return True, md_stat
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.create_mdraid_disk_array.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return False, md_stat

    def assemble_mdraid_device(self, md_device: str) -> Tuple[bool, Union[str, dict]]:
        """
        Method re-assembles/restarts the given MDRAID device on the given host.

        :param str md_device: MDRAID device to be assemble
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info("Assembling the MDRAID device %s on the host %s", md_device, self.host)
        try:
            assemble_arg = common_commands.MDADM_ASSEMBLE
            mdadm_args = [assemble_arg, md_device]
            super().run_mdadm_cmd(mdadm_args)
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(md_device) in md_stat["devices"]:
                return True, md_stat
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.assemble_mdraid_device.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return False, md_stat

    def stop_mdraid_device(self, md_device: str) -> Tuple[bool, Union[str, dict]]:
        """
        Method stops the given MDRAID device on the given host.

        :param str md_device: MDRAID device to be stopped
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info("Stopping the MDRAID device %s on the host %s", md_device, self.host)
        try:
            stop_arg = common_commands.MDADM_STOP
            mdadm_args = [stop_arg, md_device]
            super().run_mdadm_cmd(mdadm_args)
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(md_device) in md_stat["devices"]:
                return False, md_stat
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.stop_mdraid_device.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, md_stat

    def fail_disk_mdraid(self, md_device: str, disk: str) -> Tuple[bool, Union[str, dict]]:
        """
        Method simulates disk failure from a given MRAID device.

        :param str md_device: MDRAID device
        :param str disk: Disk from MDRAID device which is to be declare as
        faulty
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info("Declaring Disk %s from RAID device %s as faulty", disk, md_device)
        try:
            manage_arg = common_commands.MDADM_MANAGE
            fail_arg = common_commands.MDADM_FAIL
            mdadm_args = [manage_arg, md_device, fail_arg, disk]
            super().run_mdadm_cmd(mdadm_args)
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if md_stat["devices"][os.path.basename(
                    md_device)]["disks"][os.path.basename(disk)]["faulty"]:
                return True, md_stat
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.fail_disk_mdraid.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return False, md_stat

    def remove_faulty_disk(self, md_device: str, disk: str) -> Tuple[bool, Union[str, dict]]:
        """
        Method removes given faulty disk from the given MRAID device.

        :param str md_device: MDRAID device
        :param str disk: Faulty Disk which is to be removed from MDRAID device
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info("Removing Disk %s from RAID device %s", disk, md_device)
        try:
            manage_arg = common_commands.MDADM_MANAGE
            remove_arg = common_commands.MDADM_REMOVE
            mdadm_args = [manage_arg, md_device, remove_arg, disk]
            super().run_mdadm_cmd(mdadm_args)
            self.update_mdadm_config()
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(
                    disk) in md_stat["devices"][os.path.basename(md_device)]["disks"]:
                return False, md_stat
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.remove_faulty_disk.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, md_stat

    def add_disk_mdraid(self, md_device: str, disk: str) -> Tuple[bool, dict]:
        """
        Method adds new disk to the given MRAID device.

        :param str md_device: MDRAID device
        :param str disk: Disk to be added to MDRAID device
        :return: True/False and mdstat response
        :rtype: bool, dict
        """
        LOGGER.info("Adding Disk %s to the RAID device %s", disk, md_device)
        try:
            manage_arg = common_commands.MDADM_MANAGE
            add_arg = common_commands.MDADM_ADD
            mdadm_args = [manage_arg, md_device, add_arg, disk]
            super().run_mdadm_cmd(mdadm_args)
            self.update_mdadm_config()
            md_stat = self.node_utils.get_mdstat()
            LOGGER.info(md_stat)
            if os.path.basename(
                    disk) in md_stat["devices"][os.path.basename(md_device)]["disks"]:
                return True, md_stat
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.add_disk_mdraid.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return False, md_stat

    def remove_mdraid_disk_array(self, md_device: str) -> Tuple[bool, Union[str, dict]]:
        """
        Method removes given MDRAID array device anc cleanup all the disks
         from array

        :param str md_device: MDRAID device to be created
        :return: True/False and content of mdadm config
        :rtype: bool, str
        """
        if not md_device:
            return False, "Please provide RAID device name e.g., /dev/md?"
        try:
            md_stat = self.node_utils.get_mdstat()
            if os.path.basename(md_device) not in md_stat["devices"]:
                return False, f"{md_device} device not found: {md_stat}"

            disks = md_stat["devices"][os.path.basename(md_device)]["disks"].keys()
            LOGGER.info("Removing MDRAID array device %s with disks %s on the host %s",
                        md_device, disks, self.host)
            stop_device = self.stop_mdraid_device(md_device)
            if not stop_device[0]:
                return stop_device
            mdadm_conf = self.update_mdadm_config()

            LOGGER.info("Performing cleanup and deleting superblock from disks %s on the host %s",
                        disks, self.host)
            for disk in disks:
                disk_path = f"/dev/{disk}"
                LOGGER.info("Deleting superblock from disk %s", disk_path)
                zero_superblock_arg = common_commands.MDADM_ZERO_SUPERBLOCK
                mdadm_args = [zero_superblock_arg, disk_path]
                super().run_mdadm_cmd(mdadm_args)

                LOGGER.info("Performing cleanup on disk %s", disk_path)
                wipe_disk_cmd = common_commands.WIPE_DISK_CMD.format(disk_path)
                self.node_utils.execute_cmd(
                    cmd=wipe_disk_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
                time.sleep(RAS_VAL["ras_sspl_alert"]["disk_clean_time"])
                self.node_utils.kill_remote_process(
                    common_commands.KILL_WIPE_DISK_PROCESS)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.remove_mdraid_disk_array.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, mdadm_conf

    def get_sspl_state_pcs(self) -> dict:
        """
        Function reads the sspl text file to get state of sspl on master node.

        :return: Boolean and response
        :rtype: dict
        """
        try:
            LOGGER.info("Getting the SSPL state")
            response = super().get_sspl_state_pcs()
            LOGGER.info(response)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_sspl_state.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return response

    def get_string_from_file(self) -> Tuple[bool, str]:
        """
        Function to get the status string of SELinux.

        :return: (Boolean, status).
        """
        try:
            status = False
            status_file = RAS_VAL["ras_sspl_alert"]["file"]["selinux_status"]
            local_path = status_file
            cmd = common_commands.SELINUX_STATUS_CMD.format(status_file)
            resp = self.node_utils.execute_cmd(cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
            LOGGER.info(resp)
            self.node_utils.copy_file_to_local(remote_path=status_file, local_path=local_path)
            LOGGER.info(resp)

            f_pointer = open(local_path, "r", encoding="utf-8")
            string = ""
            for line in f_pointer:
                if "SELinux status" in line:
                    string = line.split()[-1]
                    if string == "enabled":
                        status = True
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_string_from_file.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return status, string

    def modify_selinux_file(self) -> Tuple[bool, str]:
        """
        Function to modify SELinux config file on remote.

        :return: (Boolean, string)
        :rtype: tuple
        """
        try:
            common_cfg = RAS_VAL["ras_sspl_alert"]
            local_path = common_cfg["local_selinux_path"]
            selinux_key = common_cfg["selinux_key"]
            old_value = common_cfg["selinux_disabled"]
            new_value = common_cfg["selinux_enforced"]
            LOGGER.info("Copy Selinux file for romote to local.")
            self.node_utils.copy_file_to_local(
                remote_path=cmn_cons.SELINUX_FILE_PATH, local_path=local_path)
            LOGGER.info("Updating config file.")
            update_cfg_based_on_separator(
                local_path, selinux_key, old_value, new_value)
            LOGGER.info("Copy modified Selinux file to remote.")
            self.node_utils.copy_file_to_remote(
                local_path=local_path, remote_path=cmn_cons.SELINUX_FILE_PATH)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.modify_selinux_file.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, "Modified file successfully"

    def get_fan_name(self) -> Union[str, None]:
        """
        Function returns the list of fans connected to infrastructure system.

        :return: fan name
        """
        try:
            return super().get_fan_name()
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_fan_name.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

    def check_sspl_log(self, exp_string: str, filepath: str) -> bool:
        """
        Function to verify the alerts generated on specific events.

        :param str exp_string: Expected string in sspl log file
        :param str filepath: Path of the file to be parsed
        """
        common_cfg = RAS_VAL["ras_sspl_alert"]

        LOGGER.info("Fetching sspl log file")
        time.sleep(common_cfg["sleep_val"])
        LOGGER.debug("Reading the sspl log file")
        read_resp = self.node_utils.read_file(filepath, "/tmp/local_sspl.log")
        LOGGER.debug(read_resp)
        LOGGER.info("Checking expected strings are in sspl log file")
        resp = self.validate_alert_log(filepath, exp_string)
        LOGGER.debug("%s : %s", resp[1], exp_string)
        LOGGER.info("Fetched sspl disk space alert")
        LOGGER.info("Removing sspl log file from the Node")
        self.node_utils.remove_file(filename=filepath)

        return resp[0]

    def verify_alert(
            self,
            sspl_file_path: dict,
            sspl_conf: dict,
            du_val,
            alert=True,
    ) -> bool:
        """
        Function to verify the sspl disk space alert, both positive and negative
        based on the disk usage

        :param sspl_file_path: sspl config path
        :param sspl_conf: temp local sspl path
        :param du_val: disk usage value
        :param alert: if alert true it checks for expected alert response
        """
        LOGGER.info("Step 1: Fetching server disk usage")
        resp = self.node_utils.disk_usage_python_interpreter_cmd(
            dir_path=sspl_conf.get("server_du_path"))
        if not resp[0]:
            return resp[0]
        LOGGER.info("Step 1: Fetched server disk usage")
        original_disk_usage = float(resp[1].strip().decode("utf-8"))
        LOGGER.info(
            "Current disk usage of EES server :%f",
            original_disk_usage)

        # Converting value of disk usage to int to update it in sspl.conf
        if alert:
            disk_usage = int(Decimal(original_disk_usage)) - du_val
        else:
            disk_usage = float(resp[1][0])

        LOGGER.info(
            "Step 2: Retrieve original value of disk_usage_threshold")

        self.node_utils.copy_file_to_local(
            sspl_file_path["sspl_conf_filename"],
            sspl_file_path["sspl_cfg_temp"])

        orig_key_val = get_config(sspl_file_path["sspl_cfg_temp"],
                                  sspl_conf["sspl_section"],
                                  sspl_conf["sspl_du_key"])

        LOGGER.info("Step 2: Original value of %s :%s",
                    sspl_conf["sspl_du_key"], orig_key_val)

        LOGGER.info("Step 3: Setting value of disk_usage_threshold to value"
                    " less/greater than EES server disk usage")

        res = self.update_threshold_values(cmn_cons.KV_STORE_DISK_USAGE,
                                           sspl_conf["sspl_du_key"],
                                           disk_usage)
        LOGGER.info("Step 3: Updated server disk_usage_threshold value")

        return res

    def verify_the_logs(self, file_path: str, pattern_lst: str) -> list:
        """
        Function generated warning message on server and download the
        remote file and verifies the log

        :param str file_path: remote file path
        :param list pattern_lst: pattern need to search in file
        :return: True/False
        :rtype: Boolean
        """
        # Generate Warning alert
        resp_lst = []
        common_cfg = RAS_VAL["ras_sspl_alert"]
        self.verify_alert(
            common_cfg["file"],
            common_cfg["sspl_config"],
            common_cfg["disk_usage_val"])
        time.sleep(common_cfg["max_wait_time"])
        file_name = file_path.split("/")[-1]
        local_file_path = os.path.join(os.getcwd(),
                                       file_name)
        time.sleep(10)
        self.health_obj.restart_pcs_resource(common_cfg["sspl_resource_id"])
        LOGGER.info("Sleeping for 120 seconds after restarting sspl services")
        time.sleep(common_cfg["sleep_val"])
        self.node_utils.copy_file_to_local(file_path, local_file_path)
        LOGGER.info("Downloaded remote file %s", local_file_path)
        if not os.path.exists(local_file_path):
            resp_lst.append(False)
            return resp_lst
        # Read the remote file contents
        with open(local_file_path, "r", encoding="utf-8") as f_pointer:
            for line in f_pointer:
                if any(x in line for x in pattern_lst):
                    resp_lst.append(True)
                else:
                    resp_lst.append(False)
        LOGGER.info("Removing sspl log file from the Node")
        self.node_utils.remove_file(filename=file_path)

        os.remove(local_file_path)

        return resp_lst

    def sspl_log_collect(self) -> Tuple[bool, tuple]:
        """
        Function starts the collection of SSPl logs.

        :return: (boolean, stdout)
        """
        common_cfg = RAS_VAL["ras_sspl_alert"]
        try:
            LOGGER.info("Starting collection of sspl.log")
            cmd = common_commands.CHECK_SSPL_LOG_FILE.format(
                common_cfg["file"]["sspl_log_file"])
            response = sys_utils.run_remote_cmd(cmd=cmd, hostname=self.host,
                                                username=self.username,
                                                password=self.pwd,
                                                read_lines=True, shell=False)
            LOGGER.info("Started collection of sspl logs")
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_fan_name.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, response

    def update_enclosure_values(self, enclosure_vals: dict) -> Tuple[bool, dict]:
        """
        This will update values for enclosure in yaml/json file using conf store
        :param enclosure_vals: dict of {field: value}
        :return: True/False, values
        :rtype: bool, dict
        """
        try:
            url = cmn_cons.SSPL_GLOBAL_CONF_URL
            LOGGER.info("Update correct values of enclosure using conf")
            enclosure_vals['CONF_PRIMARY_IP'] = CMN_CFG["enclosure"]["primary_enclosure_ip"]
            enclosure_vals['CONF_PRIMARY_PORT'] = 80
            enclosure_vals['CONF_SECONDARY_IP'] = CMN_CFG["enclosure"]["secondary_enclosure_ip"]
            enclosure_vals['CONF_SECONDARY_PORT'] = 80
            enclosure_vals['CONF_ENCL_USER'] = CMN_CFG["enclosure"]["enclosure_user"]
            secret_key = self.encrypt_password_secret(CMN_CFG["enclosure"]["enclosure_pwd"])[1]
            enclosure_vals['CONF_ENCL_SECRET'] = secret_key

            self.set_conf_store_vals(url=url, encl_vals=enclosure_vals)
            controller_vals = self.get_conf_store_enclosure_vals(field='controller')
            LOGGER.info("Updated values are : %s", controller_vals)
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.update_enclosure_values.__name__, error)
            raise CTException(err.RAS_ERROR, error.args[0]) from error

        return True, controller_vals

    # pylint: disable-msg=too-many-locals
    def create_obj_for_nodes(self, **kwargs) -> dict:
        """
        Function to get/create all server node related information/objects.
        Inputs expected in kwargs:
        ras_c=RAS class object
        node_c=Node class object
        hlt_c=Health class object
        ctrl_c=ControllerLib class object
        Example response dict:
        {'srvnode-1': {'nd_num': 'srvnode-1.data.private',
        'hostname': 'ssc-vm-5592', 'ip': '10.230.248.33',
        'pu_data_ip': '192.168.56.53', 'pr_data_ip': '192.168.91.69',
        'ras_obj': <libs.ras.ras_test_lib.RASTestLib object at 0x7fc676045fd0>,
        'nd_obj': <commons.helpers.node_helper.Node object at 0x7fc676045e90>,
        'hlt_obj': <commons.helpers.health_helper.Health object at 0x7fc66852fd50>,
        'ctrl_obj': <commons.helpers.controller_helper.ControllerLib object at 0x7fc66852b310>},
        'srvnode-2': {...}}
        """
        num_nodes = len(CMN_CFG["nodes"])
        c_dict = {}
        node_d = self.health_obj.get_current_srvnode()
        ras_c = kwargs.get("ras_c", None)
        nd_c = kwargs.get("node_c", None)
        hlt_c = kwargs.get("hlt_c", None)
        ctrl_c = kwargs.get("ctrl_c", None)
        bmc_c = kwargs.get("bmc_c", None)
        for n_n in range(1, num_nodes + 1):
            c_dict[f"srvnode-{n_n}"] = {}
            for k_k, v_v in node_d.items():
                if f"srvnode-{n_n}" in v_v:
                    c_dict[f"srvnode-{n_n}"]["nd_num"] = v_v
                    c_dict[f"srvnode-{n_n}"]["hostname"] = k_k
                    db_n = n_n - 1
                    if CMN_CFG["nodes"][db_n]["hostname"].split('.')[0] == k_k:
                        c_dict[f"srvnode-{n_n}"]["ip"] = CMN_CFG["nodes"][db_n]["ip"]
                        c_dict[f"srvnode-{n_n}"]["pu_data_ip"] = \
                            CMN_CFG["nodes"][db_n]["public_data_ip"]
                        c_dict[f"srvnode-{n_n}"]["pr_data_ip"] = \
                            CMN_CFG["nodes"][db_n]["private_data_ip"]

                    host = CMN_CFG["nodes"][db_n]["hostname"]
                    uname = CMN_CFG["nodes"][db_n]["username"]
                    passwd = CMN_CFG["nodes"][db_n]["password"]
                    ras_obj = ras_c(
                        host=host,
                        username=uname,
                        password=passwd) if ras_c is not None else None
                    c_dict[f"srvnode-{n_n}"]["ras_obj"] = ras_obj
                    nd_obj = nd_c(
                        hostname=host,
                        username=uname,
                        password=passwd) if nd_c is not None else None
                    c_dict[f"srvnode-{n_n}"]["nd_obj"] = nd_obj
                    bmc_obj = bmc_c(hostname=host, username=uname,
                                    password=passwd) if bmc_c is not None else None
                    c_dict[f"srvnode-{n_n}"]["bmc_obj"] = bmc_obj

                    hlt_obj = hlt_c(hostname=host, username=uname,
                                    password=passwd) if hlt_c is not None else None
                    c_dict[f"srvnode-{n_n}"]["hlt_obj"] = hlt_obj
                    ctrl_obj = ctrl_c(
                        host=host, h_user=uname, h_pwd=passwd,
                        enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
                        enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
                        enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])
                    c_dict[f"srvnode-{n_n}"]["ctrl_obj"] = ctrl_obj

        return c_dict

    # pylint: disable=too-many-return-statements
    def get_node_drive_details(self, check_drive_count: bool = False):
        """
        Function to get details of the drives connected to node
        :return: True/False, drive_name, host_num, drive_count
        (e.g. '/dev/sda', 2, 4)
        """
        try:
            filepath = localpath = RAS_VAL["ras_sspl_alert"]["file"]["lsscsi_file"]
            tempfile = RAS_VAL["ras_sspl_alert"]["file"]["temp_txt_file"]

            cmd = common_commands.LSSCSI_CMD.format(filepath)
            LOGGER.info("Running command %s", cmd)
            response = sys_utils.run_remote_cmd(cmd=cmd, hostname=self.host,
                                                username=self.username,
                                                password=self.pwd,
                                                read_lines=True, shell=False)
            if not response[0]:
                return response

            LOGGER.info("Copying file from remote to local")
            resp = self.node_utils.copy_file_to_local(remote_path=filepath,
                                                      local_path=localpath)
            if not resp[0]:
                return resp

            LOGGER.info("Getting drive information")
            cmd = common_commands.LINUX_STRING_CMD.format(
                "ATA", filepath, tempfile)
            resp = sys_utils.run_local_cmd(cmd=cmd)
            if not resp[0]:
                return resp

            LOGGER.info("Checking OS drive count")
            cmd = common_commands.LINE_COUNT_CMD.format(tempfile)
            resp = sys_utils.run_local_cmd(cmd=cmd)

            drive_count = int(re.findall(r'\d+', resp[1])[0])
            if not resp[0]:
                return resp

            LOGGER.info("%s number of drives are connected to nodes %s", drive_count, self.host)

            if check_drive_count:
                return resp[0], drive_count

            line_num = self.system_random.randint(1, drive_count)
            LOGGER.info("Getting LUN number of OS drive")
            cmd = f"sed -n '{line_num}p' {tempfile} | awk '{{print $1}}'"
            LOGGER.info("Running command: %s", cmd)
            resp = os.popen(cmd=cmd).read()

            numeric_filter = filter(str.isdigit, resp.split(':')[0])
            host_num = "".join(numeric_filter)

            LOGGER.info("Getting name of OS drive")
            cmd = f"sed -n '{line_num}p' {tempfile} | awk '{{print $NF}}'"
            LOGGER.info("Running command: %s", cmd)
            resp = os.popen(cmd=cmd).read()
            drive_name = resp.strip()
            return True, drive_name, host_num, drive_count
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_node_drive_details.__name__, error)
            return False, error
        finally:
            if os.path.exists(localpath):
                os.remove(localpath)
            if os.path.exists(tempfile):
                os.remove(tempfile)
            self.node_utils.remove_file(filename=filepath)

    def get_ipmi_sensor_list(self, sensor_type: str = None) -> tuple:
        """
        Function returns the list of sensors connected to infrastructure system.
        :param sensor_type: Type of sensor e.g., Power Supply, FAN
        :return: List of sensors of given sensor_type if provided else all available sensors
        """
        try:
            LOGGER.info("Fetching all sensor types")
            output = super().get_ipmi_sensor_list()
            all_types = list()
            for line in output:
                if "(0x" in line:
                    all_types.append(re.split('[()]', line)[0].strip().lower())
                    all_types.append(re.split('[()]', line)[2].strip().lower())

            if sensor_type:
                if sensor_type.lower() in all_types:
                    sensor_type = f"'{sensor_type}'"
                    LOGGER.info(
                        "Fetching all sensors for sensor type %s",
                        sensor_type)
                    output = super().get_ipmi_sensor_list(sensor_type)
                    sensor_list = [line.split("|")[0].strip()
                                   for line in output if "ok" in line.split("|")[2]]

                    return True, sensor_list

                return False, "Invalid Sensor Type"

            return True, all_types
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_ipmi_sensor_list.__name__, error)
            return False, error

    def get_ipmi_sensor_states(self, sensor_name: str) -> list:
        """
        Function returns the list of states available for a given sensor.
        :param sensor_name: Name of sensor e.g., PS2 Status, FAN1
        :return: List of states for given sensor
        """
        try:
            LOGGER.info("Fetching all sensor states for sensor %s", sensor_name)
            sensor_name = f"'{sensor_name}'"
            output = super().get_ipmi_sensor_states(sensor_name)
            sensor_states = [state.strip().lower() for state in output[2:]]
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_ipmi_sensor_states.__name__, error)
            return False, error

        return sensor_states

    def assert_deassert_sensor_state(
            self,
            sensor_name: str,
            sensor_state: str,
            deassert: bool = False) -> tuple:
        """
        Function to assert or deassert the given state of a given sensor.
        :param sensor_name: Name of sensor e.g., PS2 Status, FAN1
        :param sensor_state: state of sensor to assert or deassert
        :param deassert: deasserts the state if set True
        :return: response of assert or deassert sensor state
        """
        try:
            LOGGER.info("Fetching all sensor states for sensor %s", sensor_name)
            sensor_name = f"'{sensor_name}'"
            sensor_state = f"'{sensor_state}'"
            output = super().assert_deassert_sensor_state(
                sensor_name, sensor_state, deassert)
            event_details = [val.strip() for val in output[-1].split("|")]
            if not deassert and "Asserted" in event_details:
                return True, event_details
            if deassert and "Deasserted" in event_details:
                return True, event_details

            return False, output
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.assert_deassert_sensor_state.__name__, error)
            return False, error

    def get_nw_infc_names(self, node_num):
        """
        Function to get names of the network interfaces
        :return: True/False, dict
        (e.g. (True, {'MGMT': 'eno1', 'PUBLIC_DATA': 'enp175s0f0',
        'PRIVATE_DATA': 'enp216s0f0'}))
        :rtype: Boolean, dict
        """
        ips = [CMN_CFG["nodes"][node_num]["ip"],
               CMN_CFG["nodes"][node_num]["public_data_ip"],
               CMN_CFG["nodes"][node_num]["private_data_ip"]]

        network_interfaces = {"MGMT": None, "PUBLIC_DATA": None,
                              "PRIVATE_DATA": None}
        try:
            for i_p in ips:
                cmd = common_commands.GET_INFCS_NAME_CMD.format(i_p)
                resp = self.node_utils.execute_cmd(cmd=cmd, read_lines=True)
                infc_name = resp[0].strip()
                network_interfaces[list(network_interfaces.keys())[ips.index(
                    i_p)]] = infc_name

            return True, network_interfaces
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_nw_infc_names.__name__, error)
            return False, error

    def get_raid_arrays(self) -> Tuple[bool, list]:
        """
        Function to get names of the raid arrays of node
        Returns: status, list (e.g. ['md2', 'md0', 'md1'])
        """
        try:
            cmd = common_commands.GET_RAID_ARRAYS_CMD
            resp = self.node_utils.execute_cmd(cmd=cmd)
            resp = resp.decode("utf-8").split('\n')
            arrays = list(filter(None, resp))
            LOGGER.debug("Response: %s", resp)
            return True, arrays
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_raid_arrays.__name__, error)
            return False, error

    # pylint: disable=too-many-nested-blocks
    def get_raid_array_details(self) -> Tuple[bool, dict]:
        """
        Function to get details of the raid arrays of node
        Returns: status, dict (e.g. {'md2': {'state': 'Degraded', 'drives': [
        'sdbo']},
        'md0': {'state': 'Active', 'drives': ['sda1', 'sdb1']},
        'md1': {'state': 'Active', 'drives': ['sda3', 'sdb3']}})
        """
        try:
            LOGGER.info("Checking state of arrays")
            resp = self.check_raid_array_state()
            if not resp[0]:
                return resp
            md_arrays = resp[1]
            cmd = common_commands.GET_RAID_ARRAY_DETAILS_CMD
            resp = self.node_utils.execute_cmd(cmd=cmd, read_lines=True)
            for key, _ in md_arrays.items():
                for i in resp:
                    x_x = i.replace("\n", "")
                    k_k = (x_x.split(":")[0]).strip()
                    if key == k_k:
                        v_lst = ((x_x.split(":")[1]).strip()).split()
                        lst = []
                        for v_v in v_lst:
                            if (re.match("^sd[a-z0-9]*", v_v)) is not None:
                                lst.append(re.match("^sd[a-z0-9]*", v_v).group())
                        md_arrays[k_k]["drives"] = lst
                    else:
                        continue
            return True, md_arrays
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_raid_array_details.__name__, error)
            return False, error

    def check_raid_array_state(self) -> Tuple[bool, dict]:
        """
        Function to get states of the raid arrays of node
        Returns: status, dict
        (e.g. {'md0': {'state': 'Active'}, 'md1': {'state':
        'Active'}, 'md2': {'state': 'Degraded'}})
        """
        try:
            md_arrays = dict()
            LOGGER.info("Getting raid array names")
            resp = self.get_raid_arrays()
            if not resp[0]:
                return resp
            arrays = resp[1]
            for m_ar in arrays:
                md_arrays[m_ar] = {}
                cmd = common_commands.RAID_ARRAY_STATE_CMD.format(m_ar)
                resp = self.node_utils.execute_cmd(cmd=cmd)
                state = resp.decode('utf-8').split('\n')[0]
                if state != '0':
                    LOGGER.info("Array %s is in degraded state", m_ar)
                    md_arrays[m_ar]["state"] = "Degraded"
                else:
                    md_arrays[m_ar]["state"] = "Active"
            return True, md_arrays
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.check_raid_array_state.__name__, error)
            return False, error

    def get_drive_partition_details(self, filepath: str, drive: str) -> \
            Tuple[bool, list]:
        """
        Function to get raid drive partitions of drive
        Returns: status, list (e.g. ['/dev/sda1', '/dev/sda3'])
        """
        try:
            local_path = filepath
            cmd = common_commands.FDISK_RAID_PARTITION_CMD.format(drive,
                                                                  filepath)
            LOGGER.info("Running command %s", cmd)
            self.node_utils.execute_cmd(cmd=cmd)
            if os.path.exists(local_path):
                os.remove(local_path)
            self.node_utils.copy_file_to_local(filepath, local_path)
            LOGGER.info("Extract Linux RAID partitions of drive %s", drive)
            f_p = open(local_path, 'r', encoding="utf-8")
            resp = (f_p.read()).split('\n')
            resp = list(filter(None, resp))
            raid_parts = []
            for i in resp:
                if re.search("^[0-9]", i) is not None:
                    d_name = drive + i
                    raid_parts.append(d_name)
                else:
                    raid_parts = resp
                    break

            LOGGER.debug("Response: %s", raid_parts)
            return True, raid_parts
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_drive_partition_details.__name__, error)
            return False, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
            self.node_utils.remove_file(filename=filepath)

    def get_drive_by_hostnum(self, hostnum: str) -> Tuple[bool, str]:
        """
        Function to get drive name by its host number
        Returns: status, str (e.g. '/dev/sda1')
        """
        try:
            cmd = common_commands.GET_DRIVE_HOST_NUM_CMD.format(hostnum)
            resp = self.node_utils.execute_cmd(cmd=cmd)
            drive_name = resp.decode('utf-8').replace('\n', '')
            return True, drive_name
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.get_drive_by_hostnum.__name__, error)
            return False, error

    # pylint: disable=too-many-nested-blocks
    def add_raid_partitions(self, alert_lib_obj, alert_type, raid_parts: list,
                            md_arrays: dict) -> Tuple[bool, dict]:
        """
        Function to add partitions of drive in raid array
        Returns: status, dict (e.g.
        {'md2': {'state': 'Degraded', 'drives': ['sdbo']},
        'md0': {'state': 'Active', 'drives': ['sda1', 'sdb1']},
        'md1': {'state': 'Active', 'drives': ['sda3', 'sdb3']}})
        """
        try:
            for part in raid_parts:
                for key, value in md_arrays.items():
                    if part.split("/")[-1] in value["drives"]:
                        resp = alert_lib_obj.generate_alert(
                            alert_type.RAID_ADD_DISK_ALERT,
                            input_parameters={
                                "operation": "add_disk",
                                "md_device": f"/dev/{key}",
                                "disk": part})
                    else:
                        for drv in value["drives"]:
                            if re.search("[0-9]*$",
                                         drv).group() == re.search("[0-9]*$",
                                                                   part.split("/")[-1]).group():
                                resp = alert_lib_obj.generate_alert(
                                    alert_type.RAID_ADD_DISK_ALERT,
                                    input_parameters={
                                        "operation": "add_disk",
                                        "md_device": f"/dev/{key}",
                                        "disk": part})
            LOGGER.info("Getting new RAID array details of node %s",
                        self.host)
            resp = self.get_raid_array_details()
            if not resp[0]:
                return resp
            new_md_arrays = resp[1]
            return True, new_md_arrays
        except (OSError, IOError) as error:
            LOGGER.exception("%s %s: %s", cmn_cons.EXCEPTION_ERROR,
                             RASTestLib.add_raid_partitions.__name__, error)
            return False, error
