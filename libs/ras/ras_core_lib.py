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
#

"""Python library which will perform ras component related and system level operations."""
import ast
import json
import logging
import os
import time
from typing import Tuple, Any, Union, List

from commons import commands as common_commands
from commons import constants as cmn_cons
from commons.helpers import node_helper
from commons.helpers.controller_helper import ControllerLib
from commons.helpers.health_helper import Health
from commons.utils.system_utils import run_remote_cmd
from config import CMN_CFG
from config import RAS_VAL
from libs.s3 import S3H_OBJ

LOGGER = logging.getLogger(__name__)


class RASCoreLib:
    """A class including functions for ras component related operations."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """
        Method which initializes members of RASCoreLib.

        :param str host: node hostname
        :param str username: node username
        :param str password: node password
        """
        self.host = host
        self.username = username
        self.pwd = password
        self.node_utils = node_helper.Node(
            hostname=self.host, username=self.username, password=self.pwd)
        self.health_obj = Health(hostname=self.host, username=self.username,
                                 password=self.pwd)
        self.controller_obj = ControllerLib(
            host=self.host, h_user=self.username, h_pwd=self.pwd,
            enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
            enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
            enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])

        self.s3obj = S3H_OBJ

    def create_remote_dir_recursive(self, file_path: str) -> bool:
        """
        Create the remote directory structure.

        :param str file_path: Path of the file having complete directory
        structure
        :return: Boolean status
        :rtype: bool
        """
        new_path = "/"
        res = self.node_utils.path_exists(path=file_path)
        if not res:
            remote_path_lst = file_path.split("/")[:-1]
            for directory in remote_path_lst[1:]:
                old_path = new_path
                new_path = os.path.join(new_path, directory)
                if not self.node_utils.path_exists(new_path):
                    resp = self.node_utils.create_dir_sftp(
                        dpath=os.path.join(directory, old_path))
                    if not resp:
                        return False

        return True

    def truncate_file(self, file_path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Empty remote file content using truncate cmd.

        :param file_path: path of the file to be truncated
        :return: response in tuple
        """
        reset_file_cmd = common_commands.EMPTY_FILE_CMD.format(file_path)
        res = self.node_utils.execute_cmd(
            cmd=reset_file_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        return res

    def cp_file(self, path: str, backup_path: str) -> \
            Tuple[bool, Union[List[str], str, bytes]]:
        """
        copy file with remote machine cp cmd.

        :param path: source path
        :param backup_path: destination path
        :return: response in tuple
        """
        cmd = common_commands.COPY_FILE_CMD.format(path, backup_path)
        resp = self.node_utils.execute_cmd(cmd=cmd,
                                           read_nbytes=cmn_cons.BYTES_TO_READ)
        return True, resp

    def install_screen_on_machine(self) -> Tuple[Union[List[str], str, bytes]]:
        """
        Install screen utility on remote machine.

        :return: installation cmd response
        """
        LOGGER.info("Installing screen utility")
        cmd = common_commands.INSTALL_SCREEN_CMD
        LOGGER.info("Running command %s", cmd)
        response = self.node_utils.execute_cmd(
            cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        return response

    def run_cmd_on_screen(self, cmd: str) -> \
            Tuple[bool, Union[List[str], str, bytes]]:
        """
        Start screen on remote machine and run specified command within screen.

        :param cmd: command to be executed on screen
        :return: screen response
        """
        self.install_screen_on_machine()
        time.sleep(5)
        LOGGER.debug("Command to be run: %s", cmd)
        screen_cmd = common_commands.SCREEN_CMD.format(cmd)
        LOGGER.info("Running command %s", screen_cmd)
        response = self.node_utils.execute_cmd(
            cmd=screen_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        return True, response

    def start_rabbitmq_reader_cmd(self, sspl_exchange: str, sspl_key: str,
                                  **kwargs) -> bool:
        """
        Function will check for the disk space alert for sspl.

        :param str sspl_exchange: sspl exchange string
        :param str sspl_key: sspl key string
        :return: Command response along with status(True/False)
        :rtype: bool
        """
        file_path = cmn_cons.RABBIT_MQ_FILE
        local_path_rabittmq = cmn_cons.RABBIT_MQ_LOCAL_PATH
        resp = self.create_remote_dir_recursive(file_path)
        sspl_pass = kwargs.get("sspl_pass")
        if resp:
            LOGGER.debug("Copying file to %s", self.host)
            self.node_utils.copy_file_to_remote(
                local_path=local_path_rabittmq, remote_path=file_path)
            copy_res = self.node_utils.path_exists(file_path)
            if not copy_res:
                LOGGER.debug('Failed to copy the file')
                return copy_res
            self.change_file_mode(path=file_path)
        else:
            return False

        cmd = common_commands.START_RABBITMQ_READER_CMD.format(
            sspl_exchange, sspl_key, sspl_pass)
        LOGGER.debug("RabbitMQ command: %s", cmd)
        response = self.run_cmd_on_screen(cmd=cmd)

        return response

    def start_message_bus_reader_cmd(self) -> bool:
        """
        Function will check for the alerts in message bus.

        :return: Command response along with status(True/False)
        :rtype: bool
        """
        file_path = cmn_cons.MSG_BUS_READER_PATH
        local_path_msg_bus = cmn_cons.MSG_BUS_READER_LOCAL_PATH
        LOGGER.debug("Copying file to %s", self.host)
        self.node_utils.copy_file_to_remote(
            local_path=local_path_msg_bus, remote_path=file_path)
        copy_res = self.node_utils.path_exists(file_path)
        if not copy_res:
            LOGGER.debug('Failed to copy the file')
            return copy_res
        self.change_file_mode(path=file_path)

        cmd = common_commands.START_MSG_BUS_READER_CMD
        LOGGER.debug("MSG Bus Reader command: %s", cmd)
        response = self.run_cmd_on_screen(cmd=cmd)

        return response[0]

    def check_status_file(self) -> Tuple[Union[List[str], str, bytes]]:
        """
        Function checks the state.txt file of sspl service and sets the
        status=active.

        :return: (Boolean, response)
        """
        LOGGER.info("Creating/Updating sspl status file")
        stat_cmd = common_commands.UPDATE_STAT_FILE_CMD.format(
            cmn_cons.SERVICE_STATUS_PATH)
        LOGGER.debug("Running cmd: %s on host: %s", stat_cmd, self.host)
        response = self.node_utils.execute_cmd(
            cmd=stat_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)

        return True, response

    def change_file_mode(self, path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Function to change file mode using cmd chmod on remote machine.

        :param str path: remote file path.
        :return: response in tuple
        """
        cmd = common_commands.FILE_MODE_CHANGE_CMD.format(path)
        LOGGER.debug("Executing cmd : %s on %s node.", cmd, self.host)
        res = self.node_utils.execute_cmd(cmd=cmd,
                                          read_nbytes=cmn_cons.BYTES_TO_READ)
        return res

    def get_cluster_id(self) -> Tuple[bool, Union[List[str], str, bytes]]:
        """
        Function to get cluster ID.

        :return: get cluster id cmd console resp in str
        """
        cmd = common_commands.GET_CLUSTER_ID_CMD
        LOGGER.debug("Running cmd: %s on host: %s", cmd, self.host)
        cluster_id = self.node_utils.execute_cmd(
            cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        return True, cluster_id

    def encrypt_pwd(self, password: str, cluster_id: str) -> \
            Tuple[bool, Union[List[str], str, bytes]]:
        """
        Encrypt password for the cluster ID.

        :param password: password to be encrypted
        :param cluster_id: node cluster id
        :return: response
        """
        cmd = common_commands.ENCRYPT_PASSWORD_CMD.format(password, cluster_id)
        LOGGER.debug("Running cmd: %s on host: %s", cmd, self.host)
        res = self.node_utils.execute_cmd(cmd=cmd,
                                          read_nbytes=cmn_cons.BYTES_TO_READ)
        return True, res

    def kv_put(self, field: str, val: str, kv_path: str) -> \
            Tuple[bool, Union[List[str], str, bytes]]:
        """
        Store KV using consul KV put for specified path.

        :param str field: service field to be updated
        :param str val: value to be updated on key
        :param str kv_path: path to the KV store for consul
        :return: response in tupple
        """
        LOGGER.info("Putting value %s of %s from %s", val, field, kv_path)
        put_cmd = f"{cmn_cons.CONSUL_PATH} kv put {kv_path}/{field} {val}"
        LOGGER.info("Running command: %s", put_cmd)
        resp = self.node_utils.execute_cmd(cmd=put_cmd, read_nbytes=cmn_cons.ONE_BYTE_TO_READ)
        return True, resp

    def kv_get(self, field: str, kv_path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        To get KV from specified KV store path.

        :param field: field to be fetched
        :param kv_path: path to the KV store for consul
        :return:
        """
        get_cmd = f"{cmn_cons.CONSUL_PATH} kv get {kv_path}/{field}"
        LOGGER.info("Running command: %s", get_cmd)
        response = self.node_utils.execute_cmd(
            cmd=get_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        return True, response

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-branches
    def put_kv_store(self, username: str, pwd: str, field: str) -> bool:
        """
        This function updates the values in KV store as per the values in
        storage_enclosure.sls.

        :param str username: Username of the enclosure
        :param str pwd: password for the enclosure user
        :param str field: Field in KV store to be updated
        :return: Boolean
        :rtype: bool
        """
        local_path = cmn_cons.ENCRYPTOR_FILE_PATH
        path = "/root/encryptor.py"
        res = self.node_utils.path_exists(
            path=cmn_cons.STORAGE_ENCLOSURE_PATH)
        if res:
            if field == "user":
                val = username
            elif field in ("password", "secret"):
                password = pwd

                self.node_utils.copy_file_to_remote(local_path=local_path,
                                                    remote_path=path)
                if not self.node_utils.path_exists(path=path):
                    LOGGER.debug('Failed to copy the file')
                    return False
                self.change_file_mode(path=path)
                LOGGER.info("Getting cluster id")
                cluster_id = self.get_cluster_id()
                cluster_id = cluster_id[1].decode("utf-8")
                cluster_id = " ".join(cluster_id.split())
                cluster_id = cluster_id.split(' ')[-1]

                LOGGER.info("Encrypting the password")
                val = self.encrypt_pwd(password, cluster_id)
                val = val[1].split()[-1]
                val = val.decode("utf-8")
                val = (repr(val)[2:-1]).replace('\'', '')
            else:
                LOGGER.info(
                    "Getting value of %s from storage_enclosure.sls", field)
                if field.split('_')[0] == 'primary':
                    lin = 2
                elif field.split('_')[0] == 'secondary':
                    lin = 1
                else:
                    LOGGER.debug("Unexpected field entered")
                    return False

                str_f = field.split('_')[-1]
                cmd = f"sed '/{str_f}:/!d' {cmn_cons.STORAGE_ENCLOSURE_PATH} | sed '{lin}d' | " \
                      f"awk '{{print $2}}'"
                val = self.node_utils.execute_cmd(cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
                val = val.decode("utf-8")
                val = " ".join(val.split())

            LOGGER.info(
                "Putting value %s of %s from storage_enclosure.sls",
                val,
                field)
            if field == "secret":
                self.kv_put(cmn_cons.SECRET_KEY, val, cmn_cons.KV_STORE_PATH)
            else:
                self.kv_put(field, val, cmn_cons.KV_STORE_PATH)
            LOGGER.info("Validating the value")
            if field == "secret":
                response = self.kv_get(cmn_cons.SECRET_KEY,
                                       cmn_cons.KV_STORE_PATH)
            else:
                response = self.kv_get(field, cmn_cons.KV_STORE_PATH)
            response = response[1].decode("utf-8")
            response = " ".join(response.split())
            if val == response:
                LOGGER.debug("Successfully written data for %s", field)
                return True

            LOGGER.debug("Failed to write data for %s", field)
            return False

        LOGGER.info("Please check path of storage_enclosure.sls")
        return False

    def update_threshold_values(self, kv_store_path: str, field: str, value,
                                update: bool = True) -> bool:
        """
        Function updates the values in KV store as per the values.

        :param str kv_store_path: Path of the field in kv-store
        :param str field: Field in KV store to be updated
        :param value: Threshold value to be updated
        :param bool update: Flag for updating the consul value or not
        :return: Boolean
        :rtype: bool
        """
        if update:
            LOGGER.info("Putting value %s of %s on %s", value, field,
                        kv_store_path)
            self.kv_put(field, value, kv_store_path)
            LOGGER.info("Validating the value")
        LOGGER.info("Getting value %s of %s from %s", value, field,
                    kv_store_path)
        response = self.kv_get(field, kv_store_path)
        response = response[1].decode("utf-8")
        if isinstance(value, int):
            response = int(response)
        elif isinstance(value, float):
            response = float(response)
        else:
            value = value.strip()
            response = response.strip()

        if value == response:
            LOGGER.debug("Successfully written data for %s", field)
            return True

        LOGGER.debug("Failed to write data for %s", field)
        return False

    def run_mdadm_cmd(self, args: list) -> Tuple[Union[List[str], str, bytes]]:
        """
        Function runs mdadm utility commands on host and returns their
        output.

        :param list args: list of args passed to the mdadm command
        :return: output response
        :rtype: str
        """
        arguments = " ".join(args)
        mdadm_cmd = common_commands.MDADM_CMD.format(arguments)
        LOGGER.info("Executing %s cmd on host %s", mdadm_cmd, self.host)
        output = self.node_utils.execute_cmd(
            cmd=mdadm_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        return output

    def get_sspl_state(self) -> Tuple[bool, str]:
        """
        Function reads the sspl text file to get the state of sspl on master node.

        :return: Boolean and response
        :rtype: (bool, str)
        """
        flag = False
        sspl_state_cmd = cmn_cons.SSPL_STATE_CMD
        response = self.node_utils.execute_cmd(
            cmd=sspl_state_cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        response = response.decode("utf-8")
        response = response.strip().split("=")[-1]
        LOGGER.debug("SSPL state resp : %s", response)
        if response == "active":
            flag = True

        return flag, response

    def get_sspl_state_pcs(self) -> dict:
        """
        Function checks the sspl state on nodes using pcs status.

        :return: sspl state on all the nodes
        :rtype: dict
        """
        pcs_status_cmd = common_commands.PCS_STATUS_CMD
        pcs_status = self.node_utils.execute_cmd(
            cmd=pcs_status_cmd, read_lines=True)
        sspl_section = pcs_status.index(cmn_cons.PCS_SSPL_SECTION)
        masters = pcs_status[sspl_section + 1].strip()[11:20]
        slaves = pcs_status[sspl_section + 2].strip()[10:19]
        state = {'masters': masters, 'slaves': slaves}

        return state

    def cal_sel_space(self) -> int:
        """
        Method returns the percentage use of sel cache size.

        :return: percent_use: total percentage of cache used
        :rtype int
        """
        sel_info_cmd = common_commands.SEL_INFO_CMD
        res = self.node_utils.execute_cmd(sel_info_cmd)
        alert_cache_data = res.decode("utf-8").split('\n')
        use_percent_lst = [k for k in alert_cache_data if "Percent Used" in k]
        percent_use = use_percent_lst[0].split(":")[-1].strip().rstrip("%")

        return int(percent_use)

    def generate_log_err_alert(self, logger_alert_cmd: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Function generate err log on the using logger command on the
        message bus channel.

        :param str logger_alert_cmd: command to be executed
        :return: response in tuple
        """
        LOGGER.info("Logger cmd : %s", logger_alert_cmd)
        resp = self.node_utils.execute_cmd(logger_alert_cmd)

        return resp

    def get_fan_name(self) -> Union[str, None]:
        """
        Function returns the list of fans connected to infrastructure system.

        :return: fan name
        """
        ipmi_tool_lst_cmd = common_commands.IPMI_SDR_LIST_CMD
        componets_lst = self.node_utils.execute_cmd(ipmi_tool_lst_cmd)
        componets_lst = componets_lst.decode("utf-8").split('\n')
        fan_list = [i for i in componets_lst if "FAN" in i]
        return fan_list[0].split("|")[0].strip()

    @staticmethod
    def validate_exec_time(time_str: str) -> Tuple[bool, Any]:
        """
        Function verifies the time taken to execute command.

        :param str time_str: time to be validate
        :return: Response in tuple (boolean and time in string)
        """
        time_lst = time_str.split()
        LOGGER.debug("Time taken to restart sspl-ll is %s ", time_lst)
        if len(time_lst) < 3:
            return True, time_str
        elif int(time_lst[0][0]) < 3:
            return True, time_str

        return False, time_str

    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Function start and stop s3services using the systemctl command.

        :param str service_name: Name of the service to be restarted
        :return: bool
        """
        LOGGER.info("Service to be restarted is: %s", service_name)
        resp = self.health_obj.restart_pcs_resource(service_name)
        time.sleep(60)
        return resp

    def enable_disable_service(self, operation: str = None,
                               service: str = None) -> Tuple[bool, str]:
        """
        Function start and stop s3services using the pcs resource command.

        :param str operation: Operation to disable or enable the resource
        :param service: Service to be enabled/disabled
        :return: status of the service
        """
        command = common_commands.PCS_RESOURCE_DISABLE_ENABLE\
            .format(operation, service)
        self.node_utils.execute_cmd(cmd=command, read_lines=True)
        time.sleep(30)
        resp = self.health_obj.pcs_service_status(service)
        return resp

    def alert_validation(self, string_list: list, restart: bool = True) -> \
            Tuple[bool, str]:
        """
        Function to verify the alerts generated on specific events.

        :param string_list: List of expected strings in alert response having
        format [resource_type, alert_type, ...]
        :type: list
        :param restart: Flag to specify whether to restart the service or not
        :type: Boolean
        :return: True/False, Response
        :rtype: Boolean, String
        """
        common_cfg = RAS_VAL["ras_sspl_alert"]
        if restart:
            LOGGER.info("Restarting sspl services and waiting some time")
            self.health_obj.restart_pcs_resource(
                common_cfg["sspl_resource_id"])

            LOGGER.info("Sleeping for 120 seconds after restarting sspl "
                        "services")
            time.sleep(common_cfg["sleep_val"])

        LOGGER.info("Checking status of sspl and kafka services")
        resp = self.s3obj.get_s3server_service_status(
            service=common_cfg["service"]["sspl_service"],
            host=self.host, user=self.username, pwd=self.pwd)
        if not resp[0]:
            return resp
        resp = self.s3obj.get_s3server_service_status(
            service=common_cfg["service"]["kafka_service"],
            host=self.host, user=self.username, pwd=self.pwd)
        if not resp[0]:
            return resp
        LOGGER.info(
            "Verified sspl and kafka services are in running state")
        time.sleep(common_cfg["sleep_val"])

        LOGGER.info("Fetching sspl alert response")
        cmd = common_commands.COPY_FILE_CMD.format(
            common_cfg["file"]["screen_log"],
            common_cfg["file"]["alert_log_file"])

        self.node_utils.execute_cmd(
            cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)
        LOGGER.info("Successfully fetched the alert response")

        LOGGER.debug("Reading the alert log file")
        read_resp = self.node_utils.read_file(
            filename=common_cfg["file"]["alert_log_file"],
            local_path=common_cfg["file"]["temp_txt_file"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")
        LOGGER.info(
            "Checking if alerts are generated on message bus")
        cmd = common_commands.EXTRACT_LOG_CMD.format(
            common_cfg["file"]["alert_log_file"], string_list[0],
            common_cfg["file"]["extracted_alert_file"])
        LOGGER.debug(cmd)
        self.node_utils.execute_cmd(cmd=cmd, read_nbytes=cmn_cons.BYTES_TO_READ)

        resp = self.validate_alert_msg(
            remote_file_path=common_cfg["file"]["extracted_alert_file"],
            pattern_lst=string_list)
        if not resp[0]:
            return resp

        LOGGER.info("Fetched sspl alerts")
        return True, "Fetched alerts successfully"

    def validate_alert_msg(self, remote_file_path: str, pattern_lst: list) ->\
            Tuple[bool, str]:
        """
        Function checks the list of alerts iteratively in the remote file
        and return boolean value.

        :param str remote_file_path: remote file
        :param list pattern_lst: list of err alerts generated
        :return: Boolean, response
        :rtype: tuple
        """
        response = None
        local_path = os.path.join(os.getcwd(), 'temp_file')

        if os.path.exists(local_path):
            os.remove(local_path)
        _ = self.node_utils.copy_file_to_local(remote_path=remote_file_path,
                                               local_path=local_path)
        for pattern in pattern_lst:
            if pattern in open(local_path, encoding="utf-8").read():
                response = pattern
            else:
                LOGGER.info("Match not found : %s", pattern)
                os.remove(local_path)
                return False, pattern
            LOGGER.info("Match found : %s", pattern)

        os.remove(local_path)
        return True, response

    def check_service_recovery(self, service, delay=40):
        """
        This function kills the service and checks if its recovered
        :param service: Service to kill and recovery to be checked for
        :param node: Server/Node on which to be killed
        :param delay: wait time after killing for recovery
        :return: True/False
        :rtype: Boolean
        """
        cluster_msg = cmn_cons.CLUSTER_STATUS_MSG
        LOGGER.info("Killing %s service on %s", service, self.host)
        old_pid = self.kill_services(service)
        resp = self.get_pcs_status(cluster_msg)
        LOGGER.info("Successfully killed %s service on %s host", service,
                    self.host)
        LOGGER.info("Verify if the services stops")
        time.sleep(10)
        resp = self.s3obj.get_s3server_service_status(service, host=self.host,
                                                      user=self.username,
                                                      pwd=self.pwd)
        if not resp[0]:
            LOGGER.debug("Verified %s services stops", service)
        else:
            LOGGER.debug("Error: %s services did not stop", service)

        # wait for some time for the service to come back
        time.sleep(delay)
        # verify service is restarted, we expect new PID for restarted service
        new_pid = self.get_service_pid(service)

        if old_pid != new_pid:
            LOGGER.info("Service %s recovery successful:Old PID:%s, New PID:%s", service, old_pid,
                        new_pid)
            return True

        LOGGER.error("ERROR : Service %s recovery failed: Old PID:%s, New PID: %s", service,
                     old_pid, new_pid)
        return False

    def kill_services(self, service_name):
        """
        This function find the process id and kill the services on the remote
        machine without generating dump of the process
        :param str service_name: name of the service
        :return: pid
        :rtype: int
        """
        p_id = self.get_service_pid(service_name)
        LOGGER.info("Service PID %s", p_id)
        resp = self.kill_pid(p_id)
        if not resp:
            LOGGER.error("Failure while killing Service:%s - PID:%s",
                         service_name, p_id)
        return p_id

    def get_service_pid(self, service):
        """
        This functions fetches PID for the service from given Node
        :param service: Service name for which service PID to be fetched
        :return: PID
        :rtype: str
        """
        p_id = None
        service_pid_cmd = common_commands.GET_PID_CMD.format(service)
        LOGGER.info("Get process id, command is : %s", service_pid_cmd)
        resp = self.node_utils.execute_cmd(cmd=service_pid_cmd, read_lines=True)
        for res_str in resp:
            if "Main PID" in resp[0].strip():
                p_id = resp[0].split()[2]
        if p_id is None:
            LOGGER.info("Error : Could not find PID for the service %s", service)
            return p_id

        LOGGER.info("For Service : %s  PID is :%s", service, p_id)
        return p_id

    def kill_pid(self, p_id):
        """
        This function kills the service for given PID
        :param p_id: PID if service
        :return True/False: True if operation is successful
        :rtype: Boolean
        """
        if p_id is not None:
            kill_cmd = common_commands.KILL_CMD.format(p_id)
            LOGGER.info("Kill command using process id, command is : %s",
                        kill_cmd)
            self.node_utils.execute_cmd(cmd=kill_cmd, read_lines=True)
            return True

        return False

    def get_pcs_status(self, cluster_msg):
        """
        This will Check Node status and returns the response for given cluster message
        :param str cluster_msg: string message for validation
        :return: True/False, hostname and result
        :rtype: tupple
        """
        for node in range(cmn_cons.NODE_RANGE_START, cmn_cons.NODE_RANGE_END):
            host_name = f"{cmn_cons.NODE_PREFIX}{node}"
            result = run_remote_cmd(hostname=host_name, username=self.username,
                                    password=self.pwd,
                                    cmd=common_commands.PCS_STATUS_CMD)
            result = result[1].decode('utf-8').strip().split('\n')
            for value in result[1]:
                LOGGER.info(value)
                if cluster_msg in value:
                    LOGGER.info("Failure Seen for Node : %s", host_name)
                    return False, f"{host_name} : {result[1]}"

        return True, f"{host_name} : {result[1]}"

    def get_conf_store_vals(self, url: str, field: str) -> dict:
        """
        This will get the values from any yaml/json file using conf store
        :param url: url of the yaml/json file
        :param field: field whose value needs to be extracted
        :return: field value
        :rtype: str
        """
        cmd = common_commands.CONF_GET_CMD.format(url, field)
        LOGGER.info("Running command: %s", cmd)
        result = run_remote_cmd(hostname=self.host, username=self.username,
                                password=self.pwd, cmd=cmd)
        result = result[1].decode('utf-8').strip().split('\n')
        LOGGER.debug("Response: %s", result)
        res = json.loads(result[0])
        return res[0]

    def get_conf_store_enclosure_vals(self, field: str) -> Tuple[bool, str]:
        """
        This will get the values for storage_enclosure
        :param field: field whose value needs to be extracted (
        storage_enclosure)
        :return: True/False, field value
        :rtype: bool, str
        """
        url = cmn_cons.SSPL_GLOBAL_CONF_URL
        e_field = 'storage_enclosure'
        result = self.get_conf_store_vals(url=url, field=e_field)
        for key, value in result.items():
            if isinstance(value, dict):
                for r_key, r_val in self.recursive_items(value, field):
                    if r_key == field:
                        return True, r_val
            else:
                if key == field:
                    vals = value
                    return True, vals
        return False, "No value found"

    def recursive_items(self, dictionary: dict, field: str):
        """
        This will recursively traverse the yaml/json file
        :param dictionary: dictionary from yaml/json file
        :param field: field whose value needs to be extracted
        :return: key, value generator
        :rtype: generator
        """
        for key, value in dictionary.items():
            if isinstance(value, dict):
                if key == field:
                    yield key, value
                else:
                    yield from self.recursive_items(value, field)
            else:
                yield key, value

    def set_conf_store_vals(self, url: str, encl_vals: dict):
        """
        This will set values in yaml/json file using conf store
        :param url: url of yaml/json file
        :param encl_vals: dict of {field: value}
        :return: None
        """
        for key, value in encl_vals.items():
            k = ast.literal_eval(f"cmn_cons.{key}")
            cmd = common_commands.CONF_SET_CMD.format(url, f"{k}={value}")
            LOGGER.info("Running command: %s", cmd)
            result = run_remote_cmd(hostname=self.host,
                                    username=self.username,
                                    password=self.pwd, cmd=cmd)
            result = result[0]
            LOGGER.debug("Response: %s", result)

    def encrypt_password_secret(self, string: str) -> Tuple[bool, str]:
        """
        This will encrypt the password/secret key
        :param string: string to be encrypted
        :return: True/False, encrypted string
        :rtype: bool, str
        """
        local_path = cmn_cons.ENCRYPTOR_FILE_PATH
        path = "/root/encryptor.py"
        password = string

        self.node_utils.copy_file_to_remote(local_path=local_path,
                                            remote_path=path)
        if not self.node_utils.path_exists(path=path):
            return False, "Failed to copy the file"
        self.change_file_mode(path=path)
        LOGGER.info("Getting cluster id")
        cluster_id = self.get_cluster_id()
        cluster_id = cluster_id[1].decode("utf-8")
        cluster_id = " ".join(cluster_id.split())
        cluster_id = cluster_id.split(' ')[-1]

        LOGGER.info("Encrypting the password")
        val = self.encrypt_pwd(password, cluster_id)
        val = (val[1].split()[-1]).decode("utf-8")
        val = (repr(val)[2:-1]).replace('\'', '')
        return True, val

    def get_ipmi_sensor_list(self, sensor_type: str = None) -> list:
        """
        Function returns the list of sensors connected to infrastructure system.
        :param sensor_type: Type of sensor e.g., Power Supply, FAN
        :return: List of sensors of given sensor_type if provided else all available sensors
        """
        ipmi_sdr_type_cmd = common_commands.IPMI_SDR_TYPE_CMD
        if sensor_type:
            ipmi_sdr_type_cmd = " ".join([ipmi_sdr_type_cmd, sensor_type])

        output = self.node_utils.execute_cmd(
            ipmi_sdr_type_cmd, read_lines=True)

        return output

    def get_ipmi_sensor_states(self, sensor_name: str) -> list:
        """
        Function returns the list of states available for a given sensor.
        :param sensor_name: Name of sensor e.g., PS2 Status, FAN1
        :return: List of states for given sensor
        """
        sensor_states_cmd = " ".join(
            [common_commands.IPMI_EVENT_CMD, sensor_name])
        output = self.node_utils.execute_cmd(
            sensor_states_cmd, read_lines=True)

        return output

    def assert_deassert_sensor_state(
            self,
            sensor_name: str,
            sensor_state: str,
            deassert: bool = False) -> list:
        """
        Function to assert or deassert the given state of a given sensor.
        :param sensor_name: Name of sensor e.g., PS2 Status, FAN1
        :param sensor_state: state of sensor to assert or deassert
        :param deassert: deasserts the state if set True
        :return: response of assert or deassert sensor state
        """
        event_cmd = " ".join(
            [common_commands.IPMI_EVENT_CMD, sensor_name, sensor_state])
        if deassert:
            event_cmd = " ".join([event_cmd, "deassert"])
        output = self.node_utils.execute_cmd(event_cmd, read_lines=True)

        return output
