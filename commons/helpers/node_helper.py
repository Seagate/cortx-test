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

import logging
import os
import re
import shutil
import time
import posixpath
import stat
from typing import Tuple
import mdstat
from commons import commands
from commons.helpers.host import Host

log = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"


class Node(Host):
    """
    Class to maintain all common functions across component
    """

    def get_authserver_log(self, path: str, option: str = "-n 3") -> str:
        cmd = "tail {} {}".format(path, option)
        res = self.execute_cmd(cmd)
        return res

    def send_systemctl_cmd(self, command: str, services: list, timeout: int = 60) -> list:
        valid_commands = {"start", "stop",
                          "reload", "enable", "disable", "status"}
        if command not in valid_commands:
            raise ValueError(
                "command parameter must be one of %r." % valid_commands)
        out = []
        for service in services:
            log.debug("Performing {} on service {}...".format(command, service))
            cmd = commands.SYSTEM_CTL_CMD.format(command, service)
            out.append(self.execute_cmd(cmd, timeout=timeout))
        return out

    def status_service(self, services: str, expected_status: str, timeout: int = 2) -> str:
        """
        This function display status of services
        """
        result = {}
        result["output"] = {}
        status_list = []
        for service in services:
            log.debug(f"service status {service}")
            cmd = commands.SYSTEMCTL_STATUS
            cmd = cmd.format(service)
            out = self.execute_cmd(cmd, read_lines=True, timeout=timeout)
            found = False
            for line in out:
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if expected_status in line:
                    found = True
            time.sleep(1)
            status_list.append(found)
            result["output"][service] = out
        result["success"] = False not in status_list
        return result

    def configure_jclient_cloud(self, source: str, destination: str, nfs_path: str) -> bool:
        """
        Function to configure jclient and cloud jar files
        :param source: path to the source dir where .jar are present.
        :param destination: destination path where .jar need to be copied
        """
        if not os.path.exists(source):
            os.mkdir(source)

        dir_list = os.listdir(source)
        if "jcloudclient.jar" not in dir_list or "jclient.jar" not in dir_list:
            temp_dir = "/home/jjarfiles"
            os.mkdir(temp_dir)
            mount_cmd = f"mount.nfs -v {nfs_path} {temp_dir}"
            umount_cmd = f"umount -v {temp_dir}"
            self.execute_cmd(mount_cmd)
            self.execute_cmd(f"yes | cp -rf {temp_dir}*.jar {source}")
            self.execute_cmd(umount_cmd)
            os.remove(temp_dir)

        self.execute_cmd(f"yes | cp -rf {source}*.jar {destination}")
        res_ls = self.execute_cmd(f"ls {destination}")[1]
        res = True if ".jar" in res_ls else False
        return res

    def path_exists(self, path: str) -> bool:
        """
        Check if file exists
        :param path: Absolute path of the file
        """
        self.connect_pysftp()
        log.debug("client connected")
        try:
            self.host_obj.stat(path)
        except BaseException:
            return False
        self.disconnect()
        return True

    def create_file(self, filename: str, mb_count: int, dev="/dev/zero", bs="1M") -> str:
        """
        Creates a new file, size(count) in MB
        :param filename: Name of the file with path
        :param mb_count: size of the file in MB
        :return: output of remote execution cmd
        """
        cmd = commands.CREATE_FILE.format(dev, filename, bs, mb_count)
        log.debug(cmd)
        result = self.execute_cmd(cmd)
        log.debug("output = {}".format(result))
        return self.path_exists(filename), result

    def rename_file(self, old_filename: str, new_filename: str):
        """
        This function renames file on remote host.
        :param old_filename: Old name of the file(Absolute path)
        :param new_filename: New name of the file(Absolute path)
        """
        self.connect_pysftp()
        log.debug("sftp connected")
        try:
            self.host_obj.rename(old_filename, new_filename)
        except IOError as error:
            if error.args[0] == 2:
                raise error
        self.disconnect()

    def remove_file(self, filename: str):
        """
        This function removes the unwanted file from the remote host.
        :param filename: Absolute path of the file to be removed
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        """
        self.connect_pysftp()
        log.debug(f"Connected to {self.hostname}")
        try:
            self.host_obj.remove(filename)
        except IOError as error:
            if error.args[0] == 2:
                raise error
        self.disconnect()
        return not self.path_exists(filename)

    def read_file(self, filename: str, local_path: str):
        """
        This function reads the given file and returns the file content
        :param filename: Absolute path of the file to be read
        """
        if os.path.exists(local_path):
            os.remove(local_path)
        self.copy_file_to_local(remote_path=filename, local_path=local_path)
        file = open(local_path, 'r')
        response = file.read()
        if os.path.exists(local_path):
            os.remove(local_path)
        return response

    def copy_file_to_remote(self, local_path: str, remote_path: str) -> None:
        """
        copy file from local to local remote
        :param str local_path: local path
        :param str remote_file_path: remote path
        """
        self.connect_pysftp()
        log.debug("sftp connected")
        self.host_obj.put(local_path, remote_path)
        log.debug("file copied to : {}".format(remote_path))
        self.disconnect()

    def copy_file_to_local(self, remote_path: str, local_path: str) -> None:
        """
        copy file from local to local remote
        :param str local_path: local path
        :param str remote_file_path: remote path
        """
        self.connect_pysftp()
        log.debug("sftp connected")
        self.host_obj.get(remote_path, local_path)
        log.debug("file copied to : {}".format(local_path))
        self.disconnect()

    def write_remote_file_to_local_file(self, file_path: str, local_path: str) -> None:
        """
        Writing remote file content in local file
        :param file_path: Remote path
        :param local_path: Local path
        """
        self.connect_pysftp()
        log.debug("sftp connected")
        with self.host_obj.open(file_path, "r") as remote:
            shutil.copyfileobj(remote, open(local_path, "wb"))

    def get_mdstat(self):
        """
        This function retrieves the /proc/mdstat file from remote host and returns the parsed output in json form
        :return: parsed mdstat output
        :rtype: dict
        """
        mdstat_remote_path = "/proc/mdstat"
        mdstat_local_path = "mdstat"
        log.debug(
            "Fetching /proc/mdstat file from the host {}".format(self.hostname))
        self.write_remote_file_to_local_file(
            mdstat_remote_path, mdstat_local_path)
        log.debug("Parsing mdstat file")
        output = mdstat.parse(mdstat_local_path)
        self.remove_file(mdstat_local_path)
        return output

    def is_string_in_remote_file(self, string: str, file_path: str) -> bool:
        """
        find given string in file present on s3 server
        :param string: String to be check
        :param file_path: absolute file path
        """
        local_path = os.path.join(os.getcwd(), "temp_file")
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            self.copy_file_to_local(file_path, local_path)
            data = open(local_path).read()
            match = re.search(string, data)
            if match:
                log.debug("Match found in : {}".format(file_path))
                return True, match
            else:
                return False, "String Not Found"
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(
                Node.is_string_in_remote_file.__name__, error))
            return False, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def validate_is_dir(self, remote_path: str) -> Tuple[bool, str]:
        """
        This function validates if the remote path is directory or not
        :param str remote_path: absolute path on the remote server
        :return: response: Boolean
        :rtype: list
        """
        self.connect_pysftp()
        log.debug("client connected")
        try:
            resp = self.host_obj.isdir(remote_path)
            self.host_obj.close()
            if resp:
                return True, resp
            else:
                return False, resp
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(
                Node.validate_is_dir.__name__, error))
            return False, error

    def list_dir(self, remote_path: str) -> list:
        """
        This function list the files of the remote server
        :param str remote_path: absolute path on the remote server
        :return: response: list of files
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :rtype: list
        """
        self.connect_pysftp()
        try:
            dir_lst = self.host_obj.listdir(remote_path)
        except IOError as error:
            if error.args[0] == 2:
                raise error
        return dir_lst

    def make_dir(self, dpath: str) -> bool:
        """
        Make directory
        """
        mkdir_cmd = "mkdir {}"
        if dpath is None:
            raise TypeError("path or dir_name incorrect")
        if not self.path_exists(dpath):
            log.debug(f"Directory '{dpath}' not exists, creating directory...")
            self.execute_cmd(mkdir_cmd.format(dpath))
        return self.path_exists(dpath)

    def remove_dir(self, dpath: str):
        """Remove directory
        """
        cmd = f"rm -rf {dpath}"
        if dpath is None:
            raise TypeError("Requires path to delete directory")
        if not dpath.startswith("/"):
            raise TypeError("Requires absolute path")
        log.debug(f"Removing directory : {dpath}")
        ret_val = self.execute_cmd(cmd)
        if ret_val:
            log.debug("Successfully delete directory")
        return not self.path_exists(dpath)

    def create_dir_sftp(self, dpath: str) -> bool:
        """
        This function creates directory on the remote server and returns the
        absolute path of the remote server
        :param str dir_name: Name of the directory to be created
        :param str dest_dir: Remote destination path on remote server
        :return: (Boolean, Remotepath)
        """
        self.connect_pysftp()
        log.debug("sftp connected")
        dir_path = str()
        for dir_folder in dpath.split("/"):
            if dir_folder == "":
                continue
            dir_path += r"/{0}".format(dir_folder)
            try:
                self.host_obj.listdir(dir_path)
            except IOError:
                self.host_obj.mkdir(dir_path)
        self.disconnect()
        return self.path_exists(dpath)

    def delete_dir_sftp(self, dpath: str, level: int = 0) -> bool:
        """
        This function deletes all the remote server files and directory
        recursively of the specified path
        :param str dpath: Remote directory to be deleted
        :param int level: Level or depth of remote directory
        :return: None
        """
        self.connect_pysftp()
        log.debug("sftp connected")
        for f in self.host_obj.listdir_attr(dpath):
            rpath = posixpath.join(dpath, f.filename)
            if stat.S_ISDIR(f.st_mode):
                self.delete_dir_sftp(rpath, level=(level + 1))
            else:
                rpath = posixpath.join(dpath, f.filename)
                self.host_obj.remove(rpath)
        self.host_obj.rmdir(dpath)
        self.disconnect()
        return not self.path_exists(dpath)

    def kill_remote_process(self, process_name: str):
        """
        Kill all process matching the process_name at s3 server
        :param process_name: Name of the process to be killed
        """
        return self.execute_cmd(commands.PKIL_CMD.format(process_name))

    def pgrep(self, process: str):
        """
        Function to get process ID using pgrep cmd.
        :param str process: Name of the process
        :return: bool, response/error
        :rtype: tuple
        """
        return self.execute_cmd(commands.PGREP_CMD.format(process))

    def toggle_apc_node_power(self, pdu_ip, pdu_user, pdu_pwd, node_slot, timeout=120, status=None):
        """
        Functon to toggle node power status usng APC PDU switch.
        :param string pdu_ip: IP or end pont for the PDU
        :param string pdu_user: PDU login user
        :param string pdu_pwd: PDU logn user password
        :param string node_slot: Node blank sort or port
        :param int timeout: In case rebot node with time interval in sec
        :param string status: In case user want to up or down specific node on/off
        :return: [bool, response]
        :rtype: tuple
        """
        if not self.execute_cmd("rpm  -qa | grep expect")[0]:
            log.debug("Installing expect package")
            self.execute_cmd("yum install expect")

        if status.lower() == "on":
            cmd = f"./scripts/expect_utils/expect_power_on {pdu_ip} {pdu_user} {pdu_pwd} {node_slot} on"
        elif status.lower() == "off":
            cmd = f"./scripts/expect_utils/expect_power_off {pdu_ip} {pdu_user} {pdu_pwd} {node_slot} off"
        else:
            cmd = f"./scripts/expect_utils/expect_power_cycle {pdu_ip} {pdu_user} {pdu_pwd} {node_slot} {timeout}"

        try:
            if not cmd:
                return False, "Command not found"
            log.debug(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            log.debug(f"Output: {resp}")
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(
                Node.toggle_apc_node_power.__name__, error))
            return False, error

        log.debug(f"Successfully executed cmd {cmd}")
        return resp

    def shutdown_node(self, options=None):
        """
        Function to shutdown any of the node
        """
        try:
            cmd = "shutdown {}".format(options if options else "")
            log.debug(f"Shutting down {self.hostname} node using cmd: {cmd}.")
            resp = self.execute_cmd(cmd, shell=False)
            log.debug(resp)
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.shutdown_node.__name__, error))
            return False, error
        return True, "Node shutdown successfully"
