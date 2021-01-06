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
import subprocess
import time
import random
import socket
import configparser
import paramiko
import pysftp
import posixpath
import stat
import mdstat
from hashlib import md5
from subprocess import Popen, PIPE

################################################################################
# Local libraries
################################################################################
from eos_test.provisioner import constants
from eos_test.s3 import constants as cons
from eos_test.ha import constants as ha_cons
from eos_test.ras import constants as ras_cons
from ctp.utils import ctpyaml


################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)

class NodeHelper(Host):
    """
    Class to maintain all common functions across component
    """
    def command_formatter(cmd_options, utility_path=None):
        """
        Creating command fronm dictonary cmd_options
        :param cmd_options: input dictonary contains command option/general_options
        :type cmd_options: dict
        :param utility_path: cli utility path for which command is being created
        :type utility_path: str
        :return: actual command that is going to execute for utility
        """
        cmd_elements = []
        # utility path only for cli utilities
        if utility_path:
            cmd_elements.append(utility_path)
        # Positional argument is mandatory
        if 'positional_argument' in cmd_options:
            cmd_elements.append(cmd_options['positional_argument'])
        if 'options' in cmd_options:
            for argument in cmd_options['options']:
                arg_val = cmd_options['options'][argument]
                if arg_val is None:
                    arg_str = argument
                else:
                    arg_str = argument + " " + arg_val
                cmd_elements.append(arg_str)
        if 'general_options' in cmd_options:
            for argument in cmd_options['general_options']:
                arg_val = cmd_options['general_options'][argument]
                if arg_val is None:
                    arg_str = argument
                else:
                    arg_str = argument + " " + arg_val
                cmd_elements.append(arg_str)
        if 'teardown' in cmd_options:
            cmd_elements.append("salt")
            if '--local' in cmd_options['teardown']:
                cmd_elements.append("--local")
            else:
                cmd_elements.append("'*'")
            # "all-at-time" is to execute teardown services all at a time
            if 'all-at-time' in cmd_options['teardown']['services']:
                cmd_elements.append("state.apply components.teardown")
            # "one-by-one" is to execute teardown services individually
            elif 'one-by-one' in cmd_options['teardown']['services']:
                cmd_elements.append("state.apply components.%s.teardown")

        cmd = " ".join(cmd_elements)
        return cmd

    def is_directory_exists(self, path, dir_name, remote_machine=False):
        """
        This function is use to check directory is exist or not
        :param path: path of directory
        :type path: string
        :param dir_name: directory name
        :type dir_name: string
        :return: boolean True if directory find, False otherwise.
        """
        try:
            if remote_machine:
                out_flag, directories = self.execute_command(
                    command=f"ls {path}", host=PRVSNR_CFG['machine1'])
            else:
                out_flag, directories = self.execute_command(
                    command=f"ls {path}")
            # decode utf 8 is to convert bytes to string
            # directories = (directories.decode("utf-8")).split("\n")
            directories = (directory.split("\n")[0]
                           for directory in directories)
            if dir_name in directories:
                return True
            else:
                return False
        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.is_directory_exists.__name__,
                error))
            return False

    def make_directory(self, path=None, dir_name=None, remote_host=False):
        """
        Make directory
        """
        try:
            if path is None or dir_name is None:
                raise TypeError("path or dir_name incorrect")

            if not self.is_directory_exists(
                    path, dir_name, remote_machine=remote_host):
                log.info(
                    f"Directory '{dir_name}' not exists, creating directory...")
                if remote_host:
                    self.execute_command(
                        command=f"mkdir {path}{dir_name}",
                        host=PRVSNR_CFG['machine1'])
                else:
                    self.execute_command(command=f"mkdir {path}{dir_name}")
            else:
                log.info(f"Directory '{dir_name}' already exist...")
            return True

        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.make_directory.__name__,
                error))
            return False

    def rem_directory(self, path=None, remote_host=False):
        """Remove directory
        """
        try:
            if path is None:
                raise TypeError("Requires path to delete directory")
            if not path.startswith("/"):
                raise TypeError("Requires absolute path")
            log.info(f"Removing directory : {path}")
            cmd = f"rm -rf {path}"
            if remote_host:
                ret_val = self.execute_command(
                    command=cmd, host=PRVSNR_CFG['machine1'])
            else:
                ret_val = self.execute_command(command=cmd)
            if ret_val:
                log.info("Successfully delete directory")
                return True
        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.rem_directory.__name__,
                error))
            return False

    def get_authserver_log(self, path, option="-n 3", host=CM_CFG["host"],
                           user=CM_CFG["username"],
                           pwd=CM_CFG["password"]):
        cmd = "tail {} {}".format(path, option)
        res = self.remote_execution(host, user, pwd, cmd)
        return res

    def start_stop_services(
            self,
            services,
            operation=constants.SERVICE_START,
            host=None,
            timeout=60):
        """
        This function is responsible to stop all services which are activated by deploy-eos
        :param host: To execute commands on remote host
        :type host: Boolean
        :param timeout: Timeout value
        :type timeout: Integer
        """
        log.info("Stop all services individually")
        result = {}
        for service in services:
            log.info(f"stopping service {service}")
            if operation == constants.SERVICE_START:
                cmd = constants.SYSTEMCTL_START
            else:
                cmd = constants.SYSTEM_CTL_STOP
            cmd = cmd.replace("%s", service)
            if not host:
                host = PRVSNR_CFG['server_ip']
            success, out = self.execute_command(
                cmd, host=host, timeout_sec=timeout)
            result['success'] = success
            result['output'] = out
        return result

    def status_service(self, services,
                       expected_status=constants.SERVICE_ACTIVE,
                       host=None, timeout=2):
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
            cmd = constants.SYSTEMCTL_STATUS
            cmd = cmd.replace("%s", service)
            if not host:
                host = PRVSNR_CFG["server_ip"]
            _, out = self.execute_command(
                cmd, host=host, timeout_sec=timeout)
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

    def check_server_connectivity(self, host=PRVSNR_CFG["server_ip"],
                                  username=PRVSNR_CFG['server_username'],
                                  password=PRVSNR_CFG['server_password'],
                                  retry_count=constants.RETRY_COUNT
                                  ):
        """
        This method re-connect to host machine
        :param host: host machine ip
        :param username: host machine username
        :param password: host machine password
        :param retry_count: host retry count
        :return: string
        """
        while retry_count:
            retval = self.connect(
                host=host,
                username=username,
                password=password)
            if retval is False:
                retry_count -= 1
                time.sleep(1)
                continue
            break



    def delete_remote_dir(self, sftp, remotepath, level=0):
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
            log.error(error)

    def create_remote_dir(
            self,
            dir_name,
            dest_dir,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        This function creates directory on the remote server and returns the
        absolute path of the remote server
        :param str dir_name: Name of the directory to be created
        :param str dest_dir: Remote destination path on remote server
        :param host: host machine ip
        :param user: host machine username
        :param pwd: host machine password
        :return: (Boolean, Remotepath)
        """
        remote_path = os.path.join(dest_dir, dir_name)
        try:
            client = self.connect(
                host, username=user, password=pwd, shell=shell)
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
            log.error(error)
            sftp.close()
            client.close()
            return False, error

    def file_rename_remote(
            self,
            old_filename,
            new_filename,
            host=RAS_CFG["host"],
            user=RAS_CFG["username"],
            pwd=RAS_CFG["password"], shell=True):
        """
        This function renames file on remote host.
        :param old_filename: Old name of the file(Absolute path)
        :param new_filename: New name of the file(Absolute path)
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        """
        try:
            client = self.connect(host, username=user, password=pwd,
                                  shell=shell)
            log.debug(f"Connected to {host}")
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
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.file_rename_remote.__name__,
                    error))




    def remove_file_remote(
            self,
            filename,
            host=RAS_CFG["host"],
            user=RAS_CFG["username"],
            pwd=RAS_CFG["password"]):
        """
        This function removes the unwanted file from the remote host.
        :param filename: Absolute path of the file to be removed
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        """
        try:
            client = self.connect(host, username=user, password=pwd,
                                  shell=False)
            log.debug(f"Connected to {host}")
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
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.remove_file_remote.__name__,
                    error))




    def read_file_remote(self,
                         filename,
                         host=CM_CFG["host"],
                         user=CM_CFG["username"],
                         pwd=CM_CFG["password"],
                         shell=True):
        """
        This function reads the given file and returns the file content
        :param filename: Absolute path of the file to be read
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        """
        local_path = '/tmp/rabbitmq_alert.log'
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            resp = self.copy_s3server_file(file_path=filename,
                                           local_path=local_path, host=host,
                                           user=user, pwd=pwd, shell=shell)
            if resp[0]:
                f = open(local_path, 'r')
                response = f.read()
                return response
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.read_file_remote.__name__,
                    error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def is_string_in_remote_file(self,
                                 string,
                                 file_path,
                                 host=CM_CFG["host"],
                                 user=CM_CFG["username"],
                                 pwd=CM_CFG["password"], shell=True):
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
            response = self.copy_s3server_file(
                file_path, local_path, host=host, shell=shell)
            data = open(local_path).read()
            match = re.search(string, data)
            if match:
                log.info("Match found in : {}".format(file_path))
                return True, match
            else:
                return False, "String Not Found"
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.is_string_in_remote_file.__name__,
                    error))
            return False, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def is_remote_path_exists(
            self,
            path,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        Check if file exists on s3 server
        :param path: Absolute path of the file
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :return: bool, response
        """
        client = self.connect(host, username=user, password=pwd, shell=shell)
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

    def configure_jclient_cloud(
            self, source=CM_CFG["jClientCloud_path"]["source"],
            destination=CM_CFG["jClientCloud_path"]["dest"],
            nfs_path=CM_CFG["nfs_path"]):
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












    def pgrep(self, process, remote=False,
              host=CM_CFG["host"],
              user=CM_CFG["username"],
              pwd=CM_CFG["password"]):
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
            if remote:
                response = self.remote_execution(
                    host, user, pwd, cons.PGREP_CMD.format(process))
                return True, response
            else:
                response = self.execute_cmd(cons.PGREP_CMD.format(process))
                return response
        except Exception as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pgrep.__name__,
                    error))
            return False, error




    def check_ping(self, host):
        """
        This function will send ping to the given host
        :param str host: Host to whom ping to be sent
        :return: True/ False
        :rtype: Boolean
        """
        response = os.system("ping -c 1 {}".format(host))
        if response == 0:
            pingstatus = True
        else:
            pingstatus = False

        return pingstatus

    def list_remote_dir(self, remote_path,
                        host=CM_CFG["host"],
                        user=CM_CFG["username"],
                        pwd=CM_CFG["password"], shell=True):
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
            client = self.connect(
                host, username=user, password=pwd, shell=shell)
            sftp = client.open_sftp()
            try:
                dir_lst = sftp.listdir(remote_path)
            except IOError as err:
                if err[0] == 2:
                    raise err
            return True, dir_lst
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.list_remote_dir.__name__,
                    error))
            return False, error

    def validate_alert_msg(self, remote_file_path, pattern_lst,
                           host=CM_CFG["host"], user=CM_CFG["username"],
                           pwd=CM_CFG["password"], shell=True):
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
            res = self.copy_s3server_file(file_path=remote_file_path,
                                          local_path=local_path, host=host,
                                          user=user, pwd=pwd, shell=shell)
            for pattern in pattern_lst:
                if pattern in open(local_path).read():
                    response = pattern
                else:
                    log.info("Match not found : {}".format(pattern))
                    return False, pattern
                log.info("Match found : {}".format(pattern))
            return True, response
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.validate_alert_msg.__name__,
                    error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)


    def validate_is_dir(self, remote_path,
                        host=CM_CFG["host"],
                        user=CM_CFG["username"],
                        pwd=CM_CFG["password"]
                        ):
        """
        This function validates if the remote path is directory or not
        :param str remote_path: absolute path on the remote server
        :return: response: Boolean
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :rtype: list
        """
        client = self.connect_pysftp(host, user, pwd)
        log.info("client connected")
        try:
            resp = client.isdir(remote_path)
            client.close()
            if resp:
                return True, resp
            else:
                return False, resp
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.validate_is_dir.__name__,
                    error))
            return False, error





    def command_execution(self, host, user, password, cmd):
        """
        Execute any command on remote machine/VM do not evaluate
        stderr,stdout or stdin
        :param str host: Host IP
        :param str user: Host user name
        :param ste password: Host password
        :param str cmd: command user wants to execute on host
        :return Bool True/False: True if command executed successfully
        :rtype Boolean:
        """
        try:
            client = self.connect(host, username=user, password=password)
            stdin, stdout, stderr = client.exec_command(cmd)
            client.close()
            return True
        except BaseException as error:
            log.error(error)
            return False

    def write_remote_file_to_local_file(self, file_path, local_path,
                                        host=CM_CFG["host"],
                                        user=CM_CFG["username"],
                                        pwd=CM_CFG["password"], shell=True):
        """
        Writing remote file content in local file
        :param file_path: Remote path
        :type: str
        :param local_path: Local path
        :type: str
        :param host: IP of the host
        :type: str
        :param user: user name of the host
        :type: str
        :param pwd: password for the user
        :type: str
        :return: bool, local path
        :rtype: Boolean, string
        """
        try:
            client = self.connect(host, username=user, password=pwd,
                                  shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")

            with sftp.open(file_path, "r") as remote:
                shutil.copyfileobj(remote, open(local_path, "wb"))

            return True, local_path
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR,
                Utility.write_remote_file_to_local_file.__name__, error))

            return False, error
    def get_mdstat(self, host=CM_CFG["host"],
                   username=CM_CFG["username"],
                   password=CM_CFG["password"]):
        """
        This function retrieves the /proc/mdstat file from remote host and returns the parsed output in json form
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: parsed mdstat output
        :rtype: dict
        """
        try:
            log.info(
                "Fetching /proc/mdstat file from the host {}".format(host))
            self.write_remote_file_to_local_file(
                RAS_CFG["mdstat_remote_path"],
                RAS_CFG["mdstat_local_path"],
                host=host,
                user=username,
                pwd=password)
            log.info("Parsing mdstat file")
            output = mdstat.parse(RAS_CFG["mdstat_local_path"])
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_mdstat.__name__,
                    error))
            return error
        self.remove_file(RAS_CFG["mdstat_local_path"])
        return output

    def shutdown_node(self, host=CM_CFG["host"],
                      username=CM_CFG["username"],
                      password=CM_CFG["password"], options=None):
        """
        Function to shutdown any of the node
        :param host:
        :param username:
        :param password:
        :param options:
        :return:
        """
        try:
            cmd = ha_cons.SHUTDOWN_NODE_CMD.format(
                options if options else "")
            log.info(
                f"Shutting down {host} node using cmd: {cmd}.")
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=cmd,
                shell=False)
            log.info(resp)
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.shutdown_node.__name__,
                    error))
            return False, error

        return True, f"Node shutdown successfully"



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
            log.debug("Output:", resp)
        except BaseException as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.toggle_apc_node_power.__name__,
                    error))
            return False, error

        log.info(f"Successfully executed cmd {cmd}")
        return resp

    ################################################################################
    # remote execution
    ################################################################################
    def execute_cmd(self, cmd, read_lines=True, read_nbytes=-1):
        """
        Execute any command on remote machine/VM
        :param host: Host IP
        :param user: Host user name
        :param password: Host password
        :param cmd: command user wants to execute on host
        :param read_lines: Response will be return using readlines() else using read()
        :return: response
        """
        try:
            stdin, stdout, stderr = self.host_obj.exec_command(cmd)
            if read_lines:
                result = stdout.readlines()
            else:
                result = stdout.read(read_nbytes)
            return result
        except BaseException as error:
            log.error(error)
            return error

    ################################################################################
    # remote file operations
    ################################################################################
    def create_file(self, file_name, count):
        """
        Creates a new file, size(count) in MB
        :param str file_name: Name of the file with path
        :param int count: size of the file in MB
        :return: output of remote execution cmd
        :rtype: str:
        """
        cmd = "dd if=/dev/zero of={} bs=1M count={}".format(file_name, count)
        log.debug(cmd)
        if remote:
            result = self.execute_cmd(
                host=self.hostname,
                user=self.username,
                password=self.password,
                cmd=cmd,
                shell=False)
        else:
            result = self.run_cmd(cmd)
        log.debug("output = {}".format(result))
        return result


    def copy_file_to_remote(
            self,
            local_path,
            remote_file_path,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"],
            shell=True):
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
            client = self.connect(
                host, username=user, password=pwd, shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")
            sftp.put(local_path, remote_file_path)
            log.info("file copied to : {}".format(remote_file_path))
            sftp.close()
            client.close()
            return True, remote_file_path
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.copy_file_to_remote.__name__,
                error))
            return False, error

    ################################################################################
    # remote directory operations
    ################################################################################
    def is_directory_exists(self, path, dir_name, remote_machine=False):
        """
        This function is use to check directory is exist or not
        :param path: path of directory
        :type path: string
        :param dir_name: directory name
        :type dir_name: string
        :return: boolean True if directory find, False otherwise.
        """
        try:
            if remote_machine:
                out_flag, directories = self.execute_command(
                    command=f"ls {path}", host=PRVSNR_CFG['machine1'])
            else:
                out_flag, directories = self.execute_command(
                    command=f"ls {path}")
            # decode utf 8 is to convert bytes to string
            # directories = (directories.decode("utf-8")).split("\n")
            directories = (directory.split("\n")[0]
                           for directory in directories)
            if dir_name in directories:
                return True
            else:
                return False
        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.is_directory_exists.__name__,
                error))
            return False

    ################################################################################
    # Remote process operations
    ################################################################################
    def kill_remote_process(self, process_name, host=CM_CFG["host"],
                            user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Kill all process matching the process_name at s3 server
        :param process_name: Name of the process to be killed
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return:
        """
        return self.remote_execution(
            host, user, pwd, cons.PKIL_CMD.format(process_name))



