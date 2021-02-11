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
#

"""Python library which will perform ras component related and system level operations."""
import os
import logging
import time
from typing import Tuple, Any, Union, List
from commons.helpers import node_helper
from commons import constants as cmn_cons
from commons import commands as common_commands
from commons.helpers.health_helper import Health
from commons.helpers.s3_helper import S3Helper
from config import RAS_VAL

BYTES_TO_READ = cmn_cons.BYTES_TO_READ

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
        try:
            self.s3obj = S3Helper()
        except ImportError as err:
            LOGGER.info(str(err))
            self.s3obj = S3Helper.get_instance()

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
            cmd=reset_file_cmd, read_nbytes=BYTES_TO_READ)
        return res

    def cp_file(self, path: str, backup_path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        copy file with remote machine cp cmd.

        :param path: source path
        :param backup_path: destination path
        :return: response in tuple
        """
        cmd = common_commands.COPY_FILE_CMD.format(path, backup_path)
        resp = self.node_utils.execute_cmd(cmd=cmd, read_nbytes=BYTES_TO_READ)
        return resp

    def install_screen_on_machine(self) -> Tuple[Union[List[str], str, bytes]]:
        """
        Install screen utility on remote machine.

        :return: installation cmd response
        """
        LOGGER.info("Installing screen utility")
        cmd = common_commands.INSTALL_SCREEN_CMD
        LOGGER.info("Running command %s", cmd)
        response = self.node_utils.execute_cmd(cmd=cmd,
                                               read_nbytes=BYTES_TO_READ)
        return response

    def run_cmd_on_screen(self, cmd: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Start screen on remote machine and run specified command within screen.

        :param cmd: command to be executed on screen
        :return: screen response
        """
        if not self.node_utils.execute_cmd("rpm  -qa | grep screen")[0]:
            self.install_screen_on_machine()
        time.sleep(5)
        LOGGER.debug("RabbitMQ command: %s", cmd)
        screen_cmd = common_commands.SCREEN_CMD.format(cmd)
        LOGGER.info("Running command %s", screen_cmd)
        response = self.node_utils.execute_cmd(cmd=screen_cmd,
                                               read_nbytes=BYTES_TO_READ)
        return response

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
        response = self.node_utils.execute_cmd(cmd=stat_cmd,
                                               read_nbytes=BYTES_TO_READ)

        return response

    def change_file_mode(self, path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Function to change file mode using cmd chmod on remote machine.

        :param str path: remote file path.
        :return: response in tuple
        """
        cmd = common_commands.FILE_MODE_CHANGE_CMD.format(path)
        LOGGER.debug("Executing cmd : %s on %s node.", cmd, self.host)
        res = self.node_utils.execute_cmd(cmd=cmd, read_nbytes=BYTES_TO_READ)
        return res

    def get_cluster_id(self) -> Tuple[Union[List[str], str, bytes]]:
        """
        Function to get cluster ID.

        :return: get cluster id cmd console resp in str
        """
        cmd = common_commands.GET_CLUSTER_ID_CMD
        LOGGER.debug("Running cmd: %s on host: %s", cmd, self.host)
        cluster_id = self.node_utils.execute_cmd(cmd=cmd,
                                                 read_nbytes=BYTES_TO_READ)
        return cluster_id

    def encrypt_pwd(self, password: str, cluster_id: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Encrypt password for the cluster ID.

        :param password: password to be encrypted
        :param cluster_id: node cluster id
        :return: response
        """
        cmd = common_commands.ENCRYPT_PASSWORD_CMD.format(password, cluster_id)
        LOGGER.debug("Running cmd: %s on host: %s", cmd, self.host)
        res = self.node_utils.execute_cmd(cmd=cmd, read_nbytes=BYTES_TO_READ)
        return res

    def kv_put(self, field: str, val: str, kv_path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Store KV using consul KV put for specified path.

        :param str field: service field to be updated
        :param str val: value to be updated on key
        :param str kv_path: path to the KV store for consul
        :return: response in tupple
        """
        LOGGER.info(
            "Putting value %s of %s from %s", val, field, kv_path)
        put_cmd = "{} kv put {}/{} {}" \
            .format(cmn_cons.CONSUL_PATH,
                    kv_path, field, val)
        LOGGER.info("Running command: %s", put_cmd)
        resp = self.node_utils.execute_cmd(cmd=put_cmd,
                                           read_nbytes=cmn_cons.ONE_BYTE_TO_READ)
        return resp

    def kv_get(self, field: str, kv_path: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        To get KV from specified KV store path.

        :param field: field to be fetched
        :param kv_path: path to the KV store for consul
        :return:
        """
        get_cmd = "{} kv get {}/{}" \
            .format(cmn_cons.CONSUL_PATH,
                    kv_path, field)
        LOGGER.info("Running command: %s", get_cmd)
        response = self.node_utils.execute_cmd(cmd=get_cmd,
                                               read_nbytes=BYTES_TO_READ)
        return response

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
        path = "/root/encryptor_updated.py"
        res = self.node_utils.path_exists(
            path=cmn_cons.STORAGE_ENCLOSURE_PATH)
        if res:
            if field == "user":
                val = username
            elif field in ("password", "secret"):
                password = pwd

                if not self.node_utils.path_exists(path=path):
                    self.node_utils.copy_file_to_remote(local_path=local_path,
                                                        remote_path=path)
                    if not self.node_utils.path_exists(path=path):
                        LOGGER.debug('Failed to copy the file')
                        return False
                    self.change_file_mode(path=path)
                LOGGER.info("Getting cluster id")
                cluster_id = self.get_cluster_id()
                cluster_id = cluster_id.decode("utf-8")
                cluster_id = " ".join(cluster_id.split())
                cluster_id = cluster_id.split(' ')[-1]

                LOGGER.info("Encrypting the password")
                val = self.encrypt_pwd(password, cluster_id)
                val = val.split()[-1]
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
                cmd = "sed '/{}:/!d' {} | sed '{}d' | awk '{{print $2}}'".format(
                    str_f, cmn_cons.STORAGE_ENCLOSURE_PATH, lin)
                val = self.node_utils.execute_cmd(cmd=cmd,
                                                  read_nbytes=BYTES_TO_READ)
                val = val.decode("utf-8")
                val = " ".join(val.split())

            LOGGER.info(
                "Putting value %s of %s from storage_enclosure.sls", val, field)
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
            response = response.decode("utf-8")
            response = " ".join(response.split())
            if val == response:
                LOGGER.debug("Successfully written data for %s", field)
                return True
            else:
                LOGGER.debug("Failed to write data for %s", field)
                return False
        else:
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
        else:
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
        output = self.node_utils.execute_cmd(cmd=mdadm_cmd,
                                             read_nbytes=BYTES_TO_READ)
        return output

    def get_sspl_state(self) -> Tuple[bool, str]:
        """
        Function reads the sspl text file to get the state of sspl on master node.

        :return: Boolean and response
        :rtype: (bool, str)
        """
        flag = False
        sspl_state_cmd = cmn_cons.SSPL_STATE_CMD
        response = self.node_utils.execute_cmd(cmd=sspl_state_cmd,
                                               read_nbytes=BYTES_TO_READ)
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
        if not res[0]:
            return 0
        alert_cache_data = res[1]
        use_percent_lst = [k for k in alert_cache_data if "Percent Used" in k]
        percent_use = use_percent_lst[0].split(":")[-1].strip().rstrip("%")

        return int(percent_use)

    def generate_log_err_alert(self, logger_alert_cmd: str) -> \
            Tuple[Union[List[str], str, bytes]]:
        """
        Function generate err log on the using logger command on the
        rabbitmq channel.

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
        if not componets_lst[0]:
            return None
        fan_list = [i for i in componets_lst[1] if "FAN" in i]
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
        else:

            return False, time_str

    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """
        Function start and stop s3services using the systemctl command.

        :param str service_name: Name of the service to be restarted
        :return: bool
        """
        LOGGER.info("Service to be restarted is: %s", service_name)
        self.health_obj.restart_pcs_resource(service_name)
        time.sleep(60)
        status = S3Helper.get_s3server_service_status(service=service_name,
                                                      host=self.host,
                                                      user=self.username,
                                                      pwd=self.pwd)
        return status

    def enable_disable_service(self, operation: str, service: str) -> \
            Tuple[bool, str]:
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
        resp = S3Helper.get_s3server_service_status(service=service,
                                                    host=self.host,
                                                    user=self.username,
                                                    pwd=self.pwd)
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
            self.health_obj.restart_pcs_resource(common_cfg["sspl_resource_id"])

            LOGGER.info("Sleeping for 120 seconds after restarting sspl "
                        "services")
            time.sleep(common_cfg["sleep_val"])

        LOGGER.info("Checking status of sspl and rabbitmq services")
        resp = S3Helper.get_s3server_service_status(
            service=common_cfg["service"]["sspl_service"],
            host=self.host, user=self.username, pwd=self.pwd)
        if not resp[0]:
            return resp
        resp = S3Helper.get_s3server_service_status(
            service=common_cfg["service"]["rabitmq_service"],
            host=self.host, user=self.username, pwd=self.pwd)
        if not resp[0]:
            return resp
        LOGGER.info(
            "Verified sspl and rabbitmq services are in running state")
        time.sleep(common_cfg["sleep_val"])

        LOGGER.info("Fetching sspl alert response")
        cmd = common_commands.COPY_FILE_CMD.format(
            common_cfg["file"]["screen_log"],
            common_cfg["file"]["alert_log_file"])

        response = self.node_utils.execute_cmd(cmd=cmd,
                                               read_nbytes=BYTES_TO_READ)
        if not response[0]:
            return response
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
            "Checking if alerts are generated on rabbitmq channel")
        cmd = common_commands.EXTRACT_LOG_CMD.format(
            common_cfg["file"]["alert_log_file"], string_list[0],
            common_cfg["file"]["extracted_alert_file"])
        response = self.node_utils.execute_cmd(cmd=cmd,
                                               read_nbytes=BYTES_TO_READ)
        if not response[0]:
            return response

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
        _ = S3Helper.copy_s3server_file(file_path=remote_file_path,
                                        local_path=local_path,
                                        host=self.host,
                                        user=self.username, pwd=self.pwd)
        for pattern in pattern_lst:
            if pattern in open(local_path).read():
                response = pattern
            else:
                LOGGER.info("Match not found : %s", pattern)
                os.remove(local_path)
                return False, pattern
            LOGGER.info("Match found : %s", pattern)

        os.remove(local_path)
        return True, response
