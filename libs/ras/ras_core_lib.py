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

"""
Python library which will perform ras component related and system level operations.
"""
import os
import logging
import time
from typing import Tuple, Any
from commons.helpers import node_helper
from commons import constants as cmn_cons
from commons import commands as common_commands

BYTES_TO_READ = cmn_cons.BYTES_TO_READ

LOGGER = logging.getLogger(__name__)


class RASCoreLib:
    """
    A class including functions for ras component related operations.
    """

    def __init__(self, host: str, username: str, password: str) -> None:
        """
        This method initializes members of RASCoreLib
        :param str host: node hostname
        :param str username: node username
        :param str password: node password
        """
        self.host = host
        self.username = username
        self.pwd = password
        self.node_utils = node_helper.Node(
            hostname=self.host, username=self.username, password=self.pwd)

    def create_remote_dir_recursive(self, file_path: str) -> bool:
        """
        Creates the remote directory structure
        :param str file_path: Path of the file having complete directory structure
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
                if not (self.node_utils.path_exists(new_path)):
                    resp = self.node_utils.create_dir_sftp(
                        dpath=os.path.join(directory, old_path))
                    if not resp:
                        return False

        return True

    def truncate_file(self, file_path: str) -> Tuple[bool, Any]:
        """
        Empty remote file content using truncate cmd
        :param file_path: path of the file to be truncated
        :return: response in tuple
        """
        reset_file_cmd = common_commands.EMPTY_FILE_CMD.format(file_path)
        res = self.node_utils.execute_cmd(
            cmd=reset_file_cmd, read_nbytes=BYTES_TO_READ, shell=False)
        return res

    def cp_file(self, path: str, backup_path: str) -> Tuple[bool, Any]:
        """
        copy file with remote machine cp cmd
        :param path: source path
        :param backup_path: destination path
        :return: response in tuple
        """
        cmd = common_commands.COPY_FILE_CMD.format(path, backup_path)
        resp = self.node_utils.execute_cmd(
            cmd=cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return resp

    def install_screen_on_machine(self) -> Tuple[bool, bytes]:
        """
        Install screen utility on remote machine
        :return: installation cmd response
        """
        LOGGER.info("Installing screen utility")
        cmd = common_commands.INSTALL_SCREEN_CMD
        LOGGER.info(f"Running command {cmd}")
        response = self.node_utils.execute_cmd(
            cmd=cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return response

    def run_cmd_on_screen(self, cmd: str) -> Tuple[bool, bytes]:
        """
        Start screen on remote machine and run specified command within screen.
        :param cmd: command to be executed on screen
        :return: screen response
        """
        if not self.node_utils.execute_cmd("rpm  -qa | grep screen")[0]:
            self.install_screen_on_machine()
        time.sleep(5)
        LOGGER.debug(f"RabbitMQ command: {cmd}")
        screen_cmd = common_commands.SCREEN_CMD.format(cmd)
        LOGGER.info(f"Running command {screen_cmd}")
        response = self.node_utils.execute_cmd(
            cmd=screen_cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return response

    def start_rabbitmq_reader_cmd(self, sspl_exchange: str, sspl_key: str, sspl_pass: str) -> bool:
        """
        This function will check for the disk space alert for sspl.
        :param str sspl_exchange: sspl exchange string
        :param str sspl_key: sspl key string
        :return: Command response along with status(True/False)
        :rtype: bool
        """
        file_path = cmn_cons.RABBIT_MQ_FILE
        local_path_rabittmq = cmn_cons.RABBIT_MQ_LOCAL_PATH
        resp = self.create_remote_dir_recursive(file_path)
        if resp:
            LOGGER.debug(f'Copying file to {self.host}')
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
        LOGGER.debug(f"RabbitMQ command: {cmd}")
        response = self.run_cmd_on_screen(cmd=cmd)

        return response[0]

    def check_status_file(self) -> Tuple[bool, Any]:
        """
        This function checks the state.txt file of sspl service and sets the
        status=active.
        :return: (Boolean, response)
        """
        LOGGER.info("Creating/Updating sspl status file")
        stat_cmd = common_commands.UPDATE_STAT_FILE_CMD.format(
            cmn_cons.SERVICE_STATUS_PATH)
        LOGGER.debug(f"Running cmd: {stat_cmd} on host:{self.host}")
        response = self.node_utils.execute_cmd(
            cmd=stat_cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)

        return response

    def change_file_mode(self, path: str) -> Tuple[bool, bytes]:
        """
        Function to change file mode using cmd chmod on remote machine
        :param str path: remote file path.
        :return: response in tuple
        """
        cmd = common_commands.FILE_MODE_CHANGE_CMD.format(path)
        LOGGER.debug(f"Executing cmd : {cmd} on {self.host} node.")
        res = self.node_utils.execute_cmd(
            cmd=cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return res

    def get_cluster_id(self) -> Tuple[bool, bytes]:
        """
        Function to get cluster ID.
        :return: get cluster id cmd console resp in str
        """
        cmd = common_commands.GET_CLUSTER_ID_CMD
        LOGGER.debug(f"Running cmd: {cmd} on host: {self.host}")
        cluster_id = self.node_utils.execute_cmd(
            cmd=cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return cluster_id

    def encrypt_pwd(self, password: str, cluster_id: str) -> Tuple[bool, bytes]:
        """
        Encrypt password for the cluster ID
        :param password: password to be encrypted
        :param cluster_id: node cluster id
        :return: response
        """
        cmd = common_commands.ENCRYPT_PASSWORD_CMD.format(password, cluster_id)
        LOGGER.debug(f"Running cmd: {cmd} on host:{self.host}")
        res = self.node_utils.execute_cmd(
            cmd=cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return res

    def kv_put(self, field: str, val: str, kv_path: str) -> Tuple[bool, bytes]:
        """
        Store KV using consule KV put for specified path.
        :param str field: service field to be updated
        :param str val: value to be updated on key
        :param str kv_path: path to the KV store for consul
        :return: response in tupple
        """
        LOGGER.info(
            f"Putting value {val} of {field} from {kv_path}")
        put_cmd = "{} kv put {}/{} {}" \
            .format(cmn_cons.CONSUL_PATH,
                    kv_path, field, val)
        resp = self.node_utils.execute_cmd(
            cmd=put_cmd,
            read_nbytes=cmn_cons.ONE_BYTE_TO_READ,
            shell=False)
        return resp

    def kv_get(self, field: str, kv_path: str) -> Tuple[bool, bytes]:
        """
        To get KV from specified KV store path.
        :param field: field to be fetched
        :param kv_path: path to the KV store for consul
        :return:
        """
        get_cmd = "{} kv get {}/{}" \
            .format(cmn_cons.CONSUL_PATH,
                    kv_path, field)
        response = self.node_utils.execute_cmd(
            cmd=get_cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
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
            elif field == "password":
                password = pwd

                if not (self.node_utils.path_exists(path=path)):
                    self.node_utils.copy_file_to_remote(local_path=local_path, remote_path=path)
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
                    f"Getting value of {field} from storage_enclosure.sls")
                if field.split('_')[0] == 'primary':
                    lin = 2
                elif field.split('_')[0] == 'secondary':
                    lin = 1
                else:
                    LOGGER.debug(f"Unexpected field entered")
                    return False

                str_f = field.split('_')[-1]
                cmd = "sed '/{}:/!d' {} | sed '{}d' | awk '{{print $2}}'".format(
                    str_f, cmn_cons.STORAGE_ENCLOSURE_PATH, lin)
                val = self.node_utils.execute_cmd(
                    cmd=cmd,
                    read_nbytes=BYTES_TO_READ,
                    shell=False)
                val = val[1].decode("utf-8")
                val = " ".join(val.split())

            LOGGER.info(
                f"Putting value {val} of {field} from storage_enclosure.sls")
            self.kv_put(field, val, cmn_cons.KV_STORE_PATH)
            LOGGER.info(f"Validating the value")
            response = self.kv_get(field, cmn_cons.KV_STORE_PATH)
            response = response[1].decode("utf-8")
            response = " ".join(response.split())
            if val == response:
                LOGGER.debug(f"Successfully written data for {field}")
                return True
            else:
                LOGGER.debug(f"Failed to write data for {field}")
                return False
        else:
            LOGGER.info("Please check path of storage_enclosure.sls")
            return False

    def update_threshold_values(self, kv_store_path: str, field: str, value,
                                update: bool = True) -> bool:
        """
        This function updates the values in KV store as per the values.
        :param str kv_store_path: Path of the field in kv-store
        :param str field: Field in KV store to be updated
        :param value: Threshold value to be updated
        :param bool update: Flag for updating the consul value or not
        :return: Boolean
        :rtype: bool
        """
        if update:
            LOGGER.info(f"Putting value {value} of {field} on {kv_store_path}")
            self.kv_put(field, value, kv_store_path)
            LOGGER.info(f"Validating the value")
        LOGGER.info(f"Getting value {value} of {field} from {kv_store_path}")
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
            LOGGER.debug(f"Successfully written data for {field}")
            return True
        else:
            LOGGER.debug(f"Failed to write data for {field}")
            return False

    def run_mdadm_cmd(self, args: list) -> Tuple[bool, Any]:
        """
        This function runs mdadm utility commands on host and returns their output
        :param list args: list of args passed to the mdadm command
        :param str host: Hostname of IP of system to run mdadm commands
        :param str username: Username of the host
        :param str password: Password of the host
        :return: output response
        :rtype: str
        """
        arguments = " ".join(args)
        mdadm_cmd = common_commands.MDADM_CMD.format(arguments)
        LOGGER.info("Executing {} cmd on host {}".format(mdadm_cmd, self.host))
        output = self.node_utils.execute_cmd(
            cmd=mdadm_cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        return output

    def get_sspl_state(self) -> Tuple[bool, str]:
        """
        This function reads the sspl text file to get the state of
        sspl on master node
        :return: Boolean and response
        :rtype: (bool, str)
        """
        sspl_state_cmd = cmn_cons.SSPL_STATE_CMD
        response = self.node_utils.execute_cmd(
            cmd=sspl_state_cmd,
            read_nbytes=BYTES_TO_READ,
            shell=False)
        response = response[1].decode("utf-8")
        response = response.strip().split("=")[-1]
        LOGGER.debug("SSPL state resp : {}".format(response))
        if response == "active":
            flag = True
        else:
            flag = False

        return flag, response

    def get_sspl_state_pcs(self) -> dict:
        """
        This function checks the sspl state on nodes using pcs status
        :return: sspl state on all the nodes
        :rtype: dict
        """
        pcs_status_cmd = common_commands.PCS_STATUS_CMD
        pcs_status = self.node_utils.execute_cmd(
            cmd=pcs_status_cmd, read_lines=True, shell=False)
        sspl_section = pcs_status.index(common_commands.PCS_SSPL_SECTION)
        masters = pcs_status[sspl_section + 1].strip()[11:20]
        slaves = pcs_status[sspl_section + 2].strip()[10:19]
        state = {'masters': masters, 'slaves': slaves}
        return state
