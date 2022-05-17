#!/usr/bin/python
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
"""Interface module for establishing connections."""

import logging
import os
import posixpath
import re
import shutil
import socket
import stat
import time
from typing import Any
from typing import List
from typing import Tuple
from typing import Union

import mdstat
import paramiko
import pysftp
from paramiko.ssh_exception import SSHException

from commons import commands, const

LOGGER = logging.getLogger(__name__)


class AbsHost:
    """Abstract class for establishing connections."""

    def __init__(self, hostname: str, username: str, password: str) -> None:
        """Initializer for AbsHost."""
        self.hostname = hostname
        self.username = username
        self.password = password
        self.host_obj = None
        self.shell_obj = None
        self.pysftp_obj = None

    def connect(
            self,
            shell: bool = False,
            retry: int = 1,
            timeout: int = 400,
            **kwargs) -> None:
        """
        Connect to remote host using hostname, username and password attribute.
        ref: http://docs.paramiko.org/en/stable/api/client.html#paramiko.client.SSHClient.connect
        :param shell: In case required shell invocation.
        :param timeout: timeout in seconds.
        :param retry: retry to connect.
        :param kwargs: Optional keyword arguments for SSHClient.connect func call.
        """
        try:
            self.host_obj = paramiko.SSHClient()
            self.host_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            LOGGER.debug("Connecting to host: %s", str(self.hostname))
            count = 0
            retry_count = 3
            while count < retry_count:
                try:
                    self.host_obj.connect(hostname=self.hostname,
                                          username=self.username,
                                          password=self.password,
                                          timeout=timeout,
                                          allow_agent=False,
                                          look_for_keys=False,
                                          **kwargs)
                    break
                except SSHException as error:
                    LOGGER.exception("Exception in connecting %s", error)
                    count = count + 1
                    if count == retry_count:
                        raise error
                    LOGGER.debug("Retrying to connect the host")

            if shell:
                self.shell_obj = self.host_obj.invoke_shell()

        except socket.timeout as timeout_exception:
            LOGGER.error("Could not establish connection because of timeout: %s",
                         timeout_exception)
            reconnected = self.reconnect(retry=retry, shell=shell, timeout=timeout, **kwargs)
            if not reconnected:
                raise TimeoutError(f'Connection timed out on {self.hostname}') from None
        except Exception as error:
            LOGGER.error(
                "Exception while connecting to server: Error: %s",
                str(error))
            if self.host_obj:
                self.host_obj.close()
            if shell and self.shell_obj:
                self.shell_obj.close()
            raise RuntimeError('Rethrowing the SSH exception') from error

    def connect_pysftp(
            self,
            private_key: str = None,
            private_key_pass: str = None,
            **kwargs) -> None:
        """
        Connect to remote host using pysftp.
        :param private_key: path to private key file(str) or paramiko.AgentKey
        :param private_key_pass:  password to use, if private_key is encrypted
        """
        LOGGER.debug("Connecting to host: %s", str(self.hostname))
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        self.pysftp_obj = pysftp.Connection(host=self.hostname,
                                            username=self.username,
                                            password=self.password,
                                            private_key=private_key,
                                            private_key_pass=private_key_pass,
                                            cnopts=cnopts,
                                            **kwargs)

    def disconnect(self) -> None:
        """
        Disconnects the host obj.
        """
        if self.host_obj:
            self.host_obj.close()
        if self.shell_obj:
            self.shell_obj.close()
        if self.pysftp_obj:
            self.pysftp_obj.close()
        self.host_obj = None
        self.shell_obj = None
        self.pysftp_obj = None

    def reconnect(
            self,
            retry_count: int,
            wait_time: int = 10,
            **kwargs) -> bool:
        """
        This method re-connect to host machine
        :param wait_time: wait for retry connection.
        :param retry_count: host retry count.
        :return: bool
        """
        while retry_count:
            try:
                self.connect(**kwargs)
                return True
            except Exception as error:
                LOGGER.debug("Attempting to reconnect: %s", str(error))
                retry_count -= 1
                time.sleep(wait_time)
        return False


class Host(AbsHost):
    """Class for performing system file operation on Host"""

    def execute_cmd(self,
                    cmd: str,
                    inputs: str = None,
                    read_lines: bool = False,
                    read_nbytes: int = -1,
                    **kwargs) -> Tuple[Union[List[str],
                                             str,
                                             bytes]]:
        """
        If connection is not established,  it will establish the connection and
        Execute any command on remote machine/VM. Timeout is set for SSL handshake.
        As per request by CFT Deployment team raising the TimeoutError if the timeout is
        exceeded and the command is still running. This addition of `TimeoutError` has a
        little performance overhead which might be more for fast commands and can consumes
        more cpu cycles for larger timeouts.
        :param cmd: command user wants to execute on host.
        :param read_lines: Response will be return using readlines() else using read().
        :param inputs: used to pass yes argument to commands.
        :param timeout: command and connect timeout.
        :param exc: Flag to disable/enable exception raising
        :param read_nbytes: maximum number of bytes to read.
        :return: stdout/strerr.
        """
        timer = time.time()
        timeout = kwargs.get('timeout', 400)
        check_recv_ready = kwargs.get('recv_ready', False)
        if 'recv_ready' in kwargs.keys():
            kwargs.pop('recv_ready')
        exc = kwargs.get('exc', True)
        if 'exc' in kwargs.keys():
            kwargs.pop('exc')
        LOGGER.debug("Executing %s", cmd)
        self.connect(**kwargs)  # fn will raise an exception
        stdin, stdout, stderr = self.host_obj.exec_command(cmd, timeout=timeout)  # nosec
        # above is non blocking call and timeout is set for SSL handshake and command
        if check_recv_ready:
            while time.time() - timer < timeout and not stdout.channel.exit_status_ready():
                time.sleep(1)  # to avoid perf impact on other commands
            if time.time() - timer >= timeout:  # as per request by CFT Deployment team
                raise TimeoutError('The script or command was not completed within estimated time')
        exit_status = stdout.channel.recv_exit_status()
        LOGGER.debug(exit_status)
        if exit_status != 0:
            err = stderr.readlines()
            err = [r.strip().strip("\n").strip() for r in err]
            LOGGER.debug("Error: %s", str(err))
            if exc:
                if err:
                    raise IOError(err)
                else:
                    raise IOError(stdout.readlines())
            else:
                if err:
                    return stdout.read(read_nbytes), err
                else:
                    return stdout.read(read_nbytes)
        if inputs:
            stdin.write('\n'.join(inputs))
            stdin.write('\n')
            stdin.flush()
        if read_lines:
            return stdout.readlines()

        return stdout.read(read_nbytes)

    def path_exists(self, path: str) -> bool:
        """
        Check if file exists.

        :param path: Absolute path of the file
        """
        self.connect_pysftp()
        LOGGER.debug("client connected")
        try:
            self.pysftp_obj.stat(path)
        except BaseException as error:
            LOGGER.error(error)
            return False
        finally:
            self.disconnect()

        return True

    def create_file(
            self,
            filename: str,
            mb_count: int,
            dev="/dev/zero",
            b_size="1M") -> Tuple:
        """
        Create a new file, size(count) in MB.

        :param b_size:
        :param dev:
        :param filename: Name of the file with path
        :param mb_count: size of the file in MB
        :return: output of remote execution cmd
        """
        cmd = commands.CREATE_FILE.format(dev, filename, b_size, mb_count)
        LOGGER.debug(cmd)
        result = self.execute_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return self.path_exists(filename), result

    def rename_file(self, old_filename: str, new_filename: str):
        """
        Function renames file on remote host.

        :param old_filename: Old name of the file(Absolute path)
        :param new_filename: New name of the file(Absolute path)
        """
        self.connect_pysftp()
        LOGGER.debug("sftp connected")
        try:
            self.pysftp_obj.rename(old_filename, new_filename)
        except IOError as error:
            if error.args[0] == 2:
                raise error
        self.disconnect()

    def remove_file(self, filename: str):
        """
        Function removes the unwanted file from the remote host.

        :param filename: Absolute path of the file to be removed.
        """
        self.connect_pysftp()
        LOGGER.debug("Connected to %s", self.hostname)
        try:
            self.pysftp_obj.remove(filename)
        except IOError as error:
            if error.args[0] == 2:
                raise error
        self.disconnect()

        return not self.path_exists(filename)

    def read_file(self, filename: str, local_path: str = None):
        """
        Function reads the given file and returns the file content.

        :param local_path:
        :param filename: Absolute path of the file to be read
        """
        if local_path is None:
            local_path = os.path.join(os.getcwd(), filename)
        if os.path.exists(local_path):
            os.remove(local_path)
        self.copy_file_to_local(remote_path=filename, local_path=local_path)
        with open(local_path, "r") as file:
            response = file.read()
        if os.path.exists(local_path):
            os.remove(local_path)

        return response

    def write_file(self, fpath: str, content: str = None):
        """
        This function writes the given file
        :param fpath: file path with name
        :param content: content to be written.
        """
        self.connect_pysftp()
        LOGGER.debug("sftp connected")
        with self.pysftp_obj.open(fpath, "w") as remote:
            remote.write(content)
        self.disconnect()

    def copy_file_to_remote(self, local_path: str, remote_path: str) -> tuple:
        """
        Copy local file to remote path.

        :param str local_path: local file path.
        :param str remote_path: remote file path.
        """
        try:
            self.connect_pysftp()
            LOGGER.debug("sftp connected")
            resp = self.pysftp_obj.put(local_path, remote_path)
            LOGGER.debug("file copied to : %s", str(remote_path))
            self.disconnect()

            return self.path_exists(remote_path), resp
        except Exception as error:
            LOGGER.error(
                "%s %s: %s", const.EXCEPTION_ERROR,
                self.copy_file_to_remote.__name__, error)
            return False, error

    def copy_file_to_local(self, remote_path: str, local_path: str) -> tuple:
        """
        Copy remote file path to local file path.

        :param str local_path: local file path.
        :param str remote_path: remote local path.
        :return: True/False, response.
        """
        try:
            self.connect_pysftp()
            LOGGER.debug("sftp connected")
            resp = self.pysftp_obj.get(remote_path, local_path)
            LOGGER.debug("file copied to : %s", str(local_path))
            self.disconnect()

            return os.path.exists(local_path), resp
        except Exception as error:
            LOGGER.error(
                "%s %s: %s", const.EXCEPTION_ERROR,
                self.copy_file_to_local.__name__, error)
            return False, error

    def write_remote_file_to_local_file(
            self, file_path: str, local_path: str) -> None:
        """
        Writing remote file content in local file.

        :param file_path: Remote path
        :param local_path: Local path
        """
        self.connect_pysftp()
        LOGGER.debug("sftp connected")
        with self.pysftp_obj.open(file_path, "r") as remote:
            shutil.copyfileobj(remote, open(local_path, "wb"))

    def get_mdstat(self):
        """
        Get file stat.

        Function retrieves the /proc/mdstat file from remote host and
        returns the parsed output in json form.
        :return: parsed mdstat output
        :rtype: dict
        """
        mdstat_remote_path = "/proc/mdstat"
        mdstat_local_path = "mdstat"
        LOGGER.debug(
            "Fetching /proc/mdstat file from the host %s", self.hostname)
        self.write_remote_file_to_local_file(
            mdstat_remote_path, mdstat_local_path)
        LOGGER.debug("Parsing mdstat file")
        output = mdstat.parse(mdstat_local_path)
        os.remove(mdstat_local_path)

        return output

    def is_string_in_remote_file(
            self, string: str, file_path: str) -> Tuple[bool, Any]:
        """
        find given string in file present on s3 server.

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
                LOGGER.debug("Match found in : %s", str(file_path))
                return True, match

            return False, "String Not Found"
        except BaseException as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Host.is_string_in_remote_file.__name__, error)
            return False, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def validate_is_dir(self, remote_path: str) -> tuple:
        """
        Function validates if the remote path is directory or not.

        :param str remote_path: absolute path on the remote server
        :return: response: Boolean
        :rtype: list
        """
        self.connect_pysftp()
        LOGGER.debug("client connected")
        try:
            resp = self.pysftp_obj.isdir(remote_path)
            self.pysftp_obj.close()
            if resp:
                return True, resp

            return False, resp
        except BaseException as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Host.validate_is_dir.__name__, error)
            return False, error

    def list_dir(self, remote_path: str) -> list:
        """
        Function list the files of the remote server.

        :param str remote_path: absolute path on the remote server
        :return: response: list of files
        :rtype: list
        """
        dir_lst = list()
        self.connect_pysftp()
        try:
            dir_lst = self.pysftp_obj.listdir(remote_path)
        except IOError as error:
            if error.args[0] == 2:
                raise error

        return dir_lst

    def make_dir(self, dpath: str) -> bool:
        """Make multiple directories with hierarchy."""
        if dpath is None:
            raise TypeError("path or dir_name incorrect")
        if not self.path_exists(dpath):
            LOGGER.debug(
                "Directory '%s' not exists, creating directory...",
                dpath)
            self.execute_cmd(commands.CMD_MKDIR.format(dpath))

        return self.path_exists(dpath)

    def remove_dir(self, dpath: str):
        """Remove directory."""
        cmd = f"rm -rf {dpath}"
        if dpath is None:
            raise TypeError("Requires path to delete directory")
        if not dpath.startswith("/"):
            raise TypeError("Requires absolute path")
        LOGGER.debug("Removing directory : %s", dpath)
        ret_val = self.execute_cmd(cmd)
        if ret_val:
            LOGGER.debug("Successfully delete directory")

        return not self.path_exists(dpath)

    def create_dir_sftp(self, dpath: str) -> bool:
        """
        Create remote directory.

        This function creates directory on the remote server and returns the
        absolute path of the remote server
        :param str dpath: Remote destination path on remote server
        :return: (Boolean, Remotepath)
        """
        self.connect_pysftp()
        LOGGER.debug("sftp connected")
        dir_path = str()
        for dir_folder in dpath.split("/"):
            if dir_folder == "":
                continue
            dir_path += r"/{0}".format(dir_folder)
            try:
                self.pysftp_obj.listdir(dir_path)
            except IOError:
                self.pysftp_obj.mkdir(dir_path)
        self.disconnect()

        return self.path_exists(dpath)

    def delete_dir_sftp(self, dpath: str, level: int = 0) -> bool:
        """
        Delete remote directory.

        Function deletes all the remote server files and directory
        recursively of the specified path.
        :param str dpath: Remote directory to be deleted
        :param int level: Level or depth of remote directory
        :return: None
        """
        self.connect_pysftp()
        LOGGER.debug("sftp connected")
        for fpath in self.pysftp_obj.listdir_attr(dpath):
            rpath = posixpath.join(dpath, fpath.filename)
            if stat.S_ISDIR(fpath.st_mode):
                self.delete_dir_sftp(rpath, level=(level + 1))
            else:
                rpath = posixpath.join(dpath, fpath.filename)
                self.pysftp_obj.remove(rpath)
        self.pysftp_obj.rmdir(dpath)
        self.disconnect()

        return not self.path_exists(dpath)

    def kill_remote_process(self, process_name: str):
        """
        Kill all process matching the process_name at s3 server.

        :param process_name: Name of the process to be killed
        """
        return self.execute_cmd(commands.KILL_PROCESS_CMD.format(process_name))

    def pgrep(self, process: str):
        """
        Function to get process ID using pgrep cmd.

        :param str process: Name of the process
        :return: bool, response/error
        :rtype: tuple
        """
        return self.execute_cmd(commands.PGREP_CMD.format(process))

    def shutdown_node(self, options=None):
        """Function to shutdown any of the node."""
        try:
            cmd = "shutdown {}".format(options if options else "")
            LOGGER.debug(
                "Shutting down %s node using cmd: %s.",
                self.hostname,
                cmd)
            resp = self.execute_cmd(cmd, shell=False)
            LOGGER.debug(resp)
        except Exception as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Host.shutdown_node.__name__, error)
            return False, error

        return True, "Node shutdown successfully"

    def get_file_size(self, path):
        """
        Check if file exists and the size of the file on s3 server of extracted file.

        :param path: Absolute path of the file
        :return: bool, response
        """
        flag = False
        self.connect_pysftp()
        LOGGER.debug("Client connected")
        try:
            resp = self.pysftp_obj.stat(path)
            resp_val = resp.st_size
            flag = bool(resp.st_size > 0)
        except Exception as error:
            LOGGER.error(
                "%s %s: %s", const.EXCEPTION_ERROR,
                self.get_file_size.__name__, error)
            resp_val = error
        return flag, resp_val

    def open_empty_file(self, fpath: str) -> bool:
        """
        Create empty file specified in path.
        :param fpath: Non-existing file path.
        :return: True/False
        """
        try:
            if not self.path_exists(fpath):
                LOGGER.debug("File '%s' not exists, creating file...", fpath)
                self.execute_cmd(commands.CMD_TOUCH_FILE.format(fpath))
            return self.path_exists(fpath)
        except Exception as error:
            LOGGER.error(
                "%s %s: %s", const.EXCEPTION_ERROR,
                self.open_empty_file.__name__, error)
            return False

    def remove_remote_file(self, filename: str):
        """
        Function removes the unwanted file from the remote host.

        :param filename: Absolute path of the file to be removed.
        """
        self.connect_pysftp()
        LOGGER.debug("Connected to %s", self.hostname)
        try:
            self.pysftp_obj.remove(filename)
        except IOError as error:
            if error.args[0] == 2:
                LOGGER.error(error)
        self.disconnect()

        return not self.path_exists(filename)


if __name__ == '__main__':
    hostobj = Host(hostname='<>',  # nosec
                   username='<>',  # nosec
                   password='<>')  # nosec
    # Test 1
    print(hostobj.execute_cmd(cmd='ls', read_lines=True))
    # Test 2 -- term capturing API's are not supported.
    hostobj.execute_cmd(cmd='top', read_lines=True)
