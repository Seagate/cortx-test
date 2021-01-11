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

################################################################################
# Standard libraries
################################################################################
import logging
import os
import re
import shutil
import time
import posixpath
import stat
import mdstat

################################################################################
# Local libraries
################################################################################
from commons import commands
from commons.helpers.host import Host
################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"

################################################################################
# Node Helper class
################################################################################
class Node(Host):
    """
    Class to maintain all common functions across component
    """
    def get_authserver_log(self, path, option="-n 3"):
        cmd = "tail {} {}".format(path, option)
        res = self.execute_cmd(cmd)
        return res

    def start_stop_services(self,services,operation,timeout=60):
        """
        This function is responsible to stop all services which are activated by deploy-eos
        :param host: To execute commands on remote host
        :type host: Boolean
        :param timeout: Timeout value
        :type timeout: Integer
        """
        valid_operations = {"start_service", "stop_service"}
        if operation not in valid_operations:
            raise ValueError("Operation parameter must be one of %r." % valid_operations)

        result = {}
        for service in services:
            log.info(f"Stopping service {service}")
            if operation == "start_service":
                cmd = commands.SYSTEMCTL_START
            else:
                cmd = commands.SYSTEM_CTL_STOP
            cmd = cmd.replace("%s", service)
            success, out = self.execute_cmd(cmd, timeout_sec=timeout)
            result['success'] = success
            result['output'] = out
        return result

    def status_service(self, services, expected_status, timeout=2):
        """
        This function display status of services
        :param host: Remote host ip address
        :type host: string
        :param timeout: Timeout value
        :type timeout: Integer
        """
        result = {}
        result["output"] = {}
        status_list = []
        for service in services:
            log.info(f"service status {service}")
            cmd = commands.SYSTEMCTL_STATUS
            cmd = cmd.replace("%s", service)
            _, out = self.execute_cmd(cmd, read_lines=True, timeout_sec=timeout)
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

    def configure_jclient_cloud(self, source, destination, nfs_path):
        """
        Function to configure jclient and cloud jar files
        :param string source: path to the source dir where .jar are present.
        :param string destination: destination path where .jar need to be copied
        :return: True/False
        :rtype: bool
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

    def validate_alert_msg(self, remote_file_path, pattern_lst, shell=True):
        """
        This function checks the list of alerts iteratively in the remote file
        and return boolean value
        :param str remote_file_path: remote file
        :param list pattern_lst: list of err alerts generated
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :return: Boolean, response
        :rtype: tuple
        """

        response = None
        local_path = os.path.join(os.getcwd(), 'temp_file')
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            res = self.copy_file_to_local(file_path=remote_file_path,
                                          local_path=local_path, shell=shell)
            for pattern in pattern_lst:
                if pattern in open(local_path).read():
                    response = pattern
                else:
                    log.info("Match not found : {}".format(pattern))
                    return False, pattern
                log.info("Match found : {}".format(pattern))
            return True, response
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.removedir.__name__, error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)


    ################################################################################
    # remote file operations
    ################################################################################
    def create_file(self, file_name, mb_count):
        """
        Creates a new file, size(count) in MB
        :param str file_name: Name of the file with path
        :param int mb_count: size of the file in MB
        :return: output of remote execution cmd
        :rtype: str:
        """
        cmd = commands.CREATE_FILE.format(file_name, mb_count)
        log.debug(cmd)
        result = self.execute_cmd(cmd, shell=False)
        log.debug("output = {}".format(result))
        return result

    def copy_file_to_remote(self, local_path,remote_file_path, shell=True):
        """
        copy file from local to local remote
        :param str local_path: local path
        :param str remote_file_path: remote path
        :param str host: host ip or domain name
        :param str user: host machine user name
        :param str pwd: host machine password
        :return: boolean, remote_path/error
        :rtype: tuple
        """
        try:
            client = self.connect(shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")
            sftp.put(local_path, remote_file_path)
            log.info("file copied to : {}".format(remote_file_path))
            sftp.close()
            client.close()
            return True, remote_file_path
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.copy_file_to_remote.__name__, error))
            return False, error

    def copy_file_to_local(self,file_path, local_path, shell=True):
        """
        copy file from local to local remote
        :param str local_path: local path
        :param str remote_file_path: remote path
        :param str host: host ip or domain name
        :param str user: host machine user name
        :param str pwd: host machine password
        :return: boolean, remote_path/error
        :rtype: tuple
        """
        try:
            client = self.connect(shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")
            sftp.get(file_path, local_path)
            log.info("file copied to : {}".format(local_path))
            sftp.close()
            client.close()
            return True, local_path
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.copy_file_to_local.__name__, error))
            return False, error

    def write_remote_file_to_local_file(self, file_path, local_path,shell=True):
        """
        Writing remote file content in local file
        :param file_path: Remote path
        :type: str
        :param local_path: Local path
        :return: bool, local path
        :rtype: Boolean, string
        """
        try:
            client = self.connect(shell=shell)
            sftp = client.open_sftp()
            log.debug("sftp connected")
            with sftp.open(file_path, "r") as remote:
                shutil.copyfileobj(remote, open(local_path, "wb"))
            return True, local_path
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.write_remote_file_to_local_file.__name__, error))

            return False, error

    def read_file(self, filename, local_path, shell=True):
        """
        This function reads the given file and returns the file content
        :param filename: Absolute path of the file to be read
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        """
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            resp = self.copy_file_to_local(file_path=filename,
                                           local_path=local_path, shell=shell)
            if resp[0]:
                file = open(local_path, 'r')
                response = file.read()
                return response
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.read_file.__name__, error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def remove_file(self,filename):
        """
        This function removes the unwanted file from the remote host.
        :param filename: Absolute path of the file to be removed
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        """
        try:
            client = self.connect(shell=False)
            log.debug(f"Connected to {self.hostname}")
            sftp = client.open_sftp()
            log.debug("sftp connected")
            try:
                sftp.remove(filename)
            except IOError as err:
                if err[0] == 2:
                    raise err
            sftp.close()
            client.close()
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.remove_file.__name__, error))

    def file_rename(self, old_filename, new_filename, shell=True):
        """
        This function renames file on remote host.
        :param old_filename: Old name of the file(Absolute path)
        :param new_filename: New name of the file(Absolute path)
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        """
        try:
            client = self.connect(shell=shell)
            sftp = client.open_sftp()
            log.debug("sftp connected")
            try:
                sftp.rename(old_filename, new_filename)
            except IOError as err:
                if err[0] == 2:
                    raise err
            sftp.close()
            client.close()
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.file_rename.__name__, error))

    def get_mdstat(self):
        """
        This function retrieves the /proc/mdstat file from remote host and returns the parsed output in json form
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: parsed mdstat output
        :rtype: dict
        """
        mdstat_remote_path = "/proc/mdstat"
        mdstat_local_path = "mdstat"
        try:
            log.debug(
                "Fetching /proc/mdstat file from the host {}".format(self.hostname))
            self.write_remote_file_to_local_file(
                mdstat_remote_path,
                mdstat_local_path)
            log.debug("Parsing mdstat file")
            output = mdstat.parse(mdstat_local_path)
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.get_mdstat.__name__, error))
            return error
        self.remove_file(mdstat_local_path)
        return output

    def is_string_in_remote_file(self,string,file_path, shell=True):
        """
        find given string in file present on s3 server
        :param string: String to be check
        :param file_path: file path
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: Boolean
        """
        local_path = os.path.join(os.getcwd(), "temp_file")
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            response = self.copy_file_to_local(
                file_path, local_path, shell=shell)
            data = open(local_path).read()
            match = re.search(string, data)
            if match:
                log.info("Match found in : {}".format(file_path))
                return True, match
            else:
                return False, "String Not Found"
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.is_string_in_remote_file.__name__, error))
            return False, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    ################################################################################
    # remote directory operations
    ################################################################################
    def path_exists(self, path, shell=True):
        """
        Check if file exists on s3 server
        :param path: Absolute path of the file
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :return: bool, response
        """
        client = self.connect(shell=shell)
        log.info("client connected")
        sftp = client.open_sftp()
        log.info("sftp connected")
        try:
            sftp.stat(path)
        except BaseException:
            return False, path
        sftp.close()
        client.close()
        return True, path

    def validate_is_dir(self, remote_path):
        """
        This function validates if the remote path is directory or not
        :param str remote_path: absolute path on the remote server
        :return: response: Boolean
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :rtype: list
        """
        client = self.connect_pysftp()
        log.info("client connected")
        try:
            resp = client.isdir(remote_path)
            client.close()
            if resp:
                return True, resp
            else:
                return False, resp
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.validate_is_dir.__name__, error))
            return False, error

    def list_dir(self, remote_path, shell=True):
        """
        This function list the files of the remote server
        :param str remote_path: absolute path on the remote server
        :return: response: list of files
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :rtype: list
        """
        try:
            client = self.connect(shell=shell)
            sftp = client.open_sftp()
            try:
                dir_lst = sftp.listdir(remote_path)
            except IOError as err:
                if err[0] == 2:
                    raise err
            return True, dir_lst
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.list_remote_dir.__name__, error))
            return False, error

    def is_dir_exists(self, path, dir_name):
        """
        #TODO: Remove
        This function is use to check directory is exist or not
        :param path: path of directory
        :type path: string
        :param dir_name: directory name
        :type dir_name: string
        :return: boolean True if directory find, False otherwise.
        """
        try:
            out_flag, directories = self.execute_cmd(f"ls {path}")

            # decode utf 8 is to convert bytes to string
            directories = (directories.decode("utf-8")).split("\n")
            directories = (directory.split("\n")[0] for directory in directories)
            if dir_name in directories:
                return True
            else:
                return False
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Node.is_dir_exists.__name__, error))
            return False

    def makedir(self, path, dir_name):
        """
        Make directory
        """
        mkdir_cmd = "mkdir {}"
        try:
            if path is None or dir_name is None:
                raise TypeError("path or dir_name incorrect")
            if not self.is_dir_exists(path, dir_name):
                log.debug(f"Directory '{dir_name}' not exists, creating directory...")
                dpath = os.path.join(path, dir_name)
                self.execute_cmd(mkdir_cmd.format(dpath))
            else:
                log.info(f"Directory '{dir_name}' already exist...")
            return True

        except Exception as error:
            log.error(EXCEPTION_MSG.format(Node.makedir.__name__, error))
            return False

    def removedir(self, path):
        """Remove directory
        """
        cmd = f"rm -rf {path}"
        try:
            if path is None:
                raise TypeError("Requires path to delete directory")
            if not path.startswith("/"):
                raise TypeError("Requires absolute path")
            log.info(f"Removing directory : {path}")
            ret_val = self.execute_cmd(cmd)
            if ret_val:
                log.info("Successfully delete directory")
                return True
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Node.removedir.__name__, error))
            return False

    def deletedir_sftp(self, sftp, remotepath, level=0):
        """
        This function deletes all the remote server files and directory
        recursively of the specified path
        :param object sftp: paramiko.sftp object
        :param str remotepath: Remote directory to be deleted
        :param int level: Level or depth of remote directory
        :return: None
        """
        try:
            for f in sftp.listdir_attr(remotepath):
                rpath = posixpath.join(remotepath, f.filename)
                if stat.S_ISDIR(f.st_mode):
                    self.delete_remote_dir(sftp, rpath, level=(level + 1))
                else:
                    rpath = posixpath.join(remotepath, f.filename)
                    sftp.remove(rpath)
            sftp.rmdir(remotepath)
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Node.removedir.__name__, error))

    def create_dir(self, dir_name, dest_dir, shell=True):
        """
        This function creates directory on the remote server and returns the
        absolute path of the remote server
        :param str dir_name: Name of the directory to be created
        :param str dest_dir: Remote destination path on remote server
        :return: (Boolean, Remotepath)
        """
        remote_path = os.path.join(dest_dir, dir_name)
        try:
            client = self.connect(shell=shell)
            sftp = client.open_sftp()
            log.debug("sftp connected")
            dir_path = str()
            for dir_folder in remote_path.split("/"):
                if dir_folder == "":
                    continue
                dir_path += r"/{0}".format(dir_folder)
                try:
                    sftp.listdir(dir_path)
                except IOError:
                    sftp.mkdir(dir_path)
            sftp.close()
            client.close()
            return True, remote_path
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Node.removedir.__name__, error))
            sftp.close()
            client.close()
            return False, error

    ################################################################################
    # Remote process operations
    ################################################################################
    def kill_remote_process(self, process_name):
        """
        Kill all process matching the process_name at s3 server
        :param process_name: Name of the process to be killed
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return:
        """
        return self.execute_cmd(commands.PKIL_CMD.format(process_name))

    def pgrep(self, process, remote=False):
        """
        Function to get process ID using pgrep cmd.
        :param str process: Name of the process
        :param bool remote: Remote process or local. True/False
        :param str host: IP of the host
        :param str user: user name of the host
        :param str pwd: password for the user
        :return: bool, response/error
        :rtype: tuple
        """
        try:
            response = self.execute_cmd(commands.PGREP_CMD.format(process))
            return True, response
        except Exception as error:
            log.error(EXCEPTION_MSG.format(Node.pgrep.__name__, error))
            return False, error

    ################################################################################
    # Power operations
    ################################################################################
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
            log.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            log.debug(f"Output: {resp}")
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.toggle_apc_node_power.__name__, error))
            return False, error

        log.info(f"Successfully executed cmd {cmd}")
        return resp

    def shutdown_node(self, options=None):
        """
        Function to shutdown any of the node
        :param host:
        :param username:
        :param password:
        :param options:
        :return:
        """
        try:
            cmd = "shutdown {}".format(options if options else "")
            log.info(f"Shutting down {self.hostname} node using cmd: {cmd}.")
            resp = self.execute_cmd(cmd, shell=False)
            log.info(resp)
        except BaseException as error:
            log.error(EXCEPTION_MSG.format(Node.shutdown_node.__name__, error))
            return False, error
        return True, "Node shutdown successfully"