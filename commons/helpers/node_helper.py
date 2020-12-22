#!/usr/bin/python
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
import json
import yaml
import mdstat
from hashlib import md5
from subprocess import Popen, PIPE
import xml.etree.ElementTree
from eos_test.provisioner import constants
from eos_test.s3 import constants as cons
from eos_test.ha import constants as ha_cons
from eos_test.ras import constants as ras_cons
from ctp.utils import ctpyaml
from configparser import ConfigParser
CM_CFG = ctpyaml.read_yaml("config/common_config.yaml")
PRVSNR_CFG = ctpyaml.read_yaml("config/provisioner/provisioner_config.yaml")
RAS_CFG = ctpyaml.read_yaml("config/ras/ras_config.yaml")
logger = logging.getLogger(__name__)
PROV_DICT_OBJ = constants.PROV_BUILD_VER[CM_CFG["BUILD_VER_TYPE"]]

from configparser import ConfigParser
logger = logging.getLogger(__name__)


class Utility:
    """
    Class to maintain all common functions across component
    """

    @staticmethod
    def connect(host, username, password, shell=True):
        """
        Connect to remote host.
        :param host: host ip address
        :type host: str
        :param username: host username
        :type username: str
        :param password: host password
        :type password: str
        :param shell: In case required shell invocation
        :return: Boolean, Whether ssh connection establish or not
        """
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            logger.debug(f"Connecting to host: {host}")
            client.connect(hostname=host, username=username, password=password)
            if shell:
                shell = client.invoke_shell()
        except paramiko.AuthenticationException:
            logger.error(constants.SERVER_AUTH_FAIL)
            result = False
        except paramiko.SSHException as ssh_exception:
            logger.error(
                "Could not establish ssh connection: %s",
                ssh_exception)
            result = False
        except socket.timeout as timeout_exception:
            logger.error(
                "Could not establish connection because of timeout: %s",
                timeout_exception)
            result = False
        except Exception as error:
            logger.error(constants.SERVER_CONNECT_ERR)
            logger.error("Error message: ", error)
            result = False
            if shell:
                client.close()
            if not isinstance(shell, bool):
                shell.close()
        else:
            result = client
        return result

    @staticmethod
    def connect_pysftp(
            host,
            username,
            pwd,
            private_key=None,
            private_key_pass=None):
        """
        Connect to remote host using pysftp
        :param str host: The Hostname or IP of the remote machine
        :param str username: Your username at the remote machine
        :param str pwd: Your password at the remote machine
        :param str private_key: path to private key file(str) or paramiko.AgentKey
        :param str private_key_pass:  password to use, if private_key is encrypted
        :return: connection object based on the success
        :rtype: pysftp.Connection
        """
        try:
            logger.debug(f"Connecting to host: {host}")
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            result = pysftp.Connection(
                host=host,
                username=username,
                password=pwd,
                private_key=private_key,
                private_key_pass=private_key_pass,
                cnopts=cnopts)
        except socket.timeout as timeout_exception:
            logger.error(
                "Could not establish connection because of timeout: %s",
                timeout_exception)
            result = False
        except Exception as error:
            logger.error(constants.SERVER_CONNECT_ERR)
            logger.error("Error message: ", error)
            result = False
        return result

    @staticmethod
    def get_local_keys(
            path=CM_CFG["aws_path"],
            section=CM_CFG["aws_cred_section"]):
        """
        Get local s3 access and secret keys
        :param path: credential file path
        :param section: section name for the profile
        :return:
        """
        if not os.path.exists(path) and os.path.isfile(path):
            raise cons.FILE_NOT_PRESENT_MSG.format(path)
        config = configparser.ConfigParser()
        config.read(path)
        access_key = config[section]["aws_access_key_id"]
        secret_key = config[section]["aws_secret_access_key"]
        logger.info(f"fetched {access_key} access and {secret_key} secret key")
        return access_key, secret_key

    @staticmethod
    def cal_percent(num1, num2):
        """
        percentage calculator to track progress
        :param num1: First number
        :param num2: second number
        :return: calculated percentage
        """
        return float(num1) / float(num2) * 100.0

    def remote_execution(self, host, user, password, cmd, read_lines=True,
                         shell=True):
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
            client = self.connect(host, username=user, password=password,
                                  shell=shell)
            stdin, stdout, stderr = client.exec_command(cmd)
            if read_lines:
                result = stdout.readlines()
            else:
                result = stdout.read()
            client.close()
            logger.info(f"Response: {result}, Error: {stderr.readlines()}")
            return result
        except BaseException as error:
            logger.error(error)
            return error

    @staticmethod
    def _format_dict(el):
        """
        Format the data in dict format
        :param el: list of string element
        :return: dict
        """
        resp_dict = {}
        list_tup = []
        for i in el:
            list_tup.append(i.split(" = "))
        for i in list_tup:
            resp_dict[i[0]] = i[1]
        return resp_dict

    def format_iam_resp(self, res_msg):
        """
        Function to format IAM response which comes in string format.
        :param res_msg: bytes string of tuple
        :return: list of dict
        """
        resp = []
        res = res_msg.split("b'")[1].replace("\\n',", "").split("\\n")
        for i in res:
            new_result = i.split(',')
            result = self._format_dict(new_result)
            resp.append(result)
        return resp

    @staticmethod
    def run_cmd(cmd):
        """
        Execute any given command
        :param cmd: Command to execute on the node
        :return: response
        """
        logger.info(cmd)
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        result = str(proc.communicate())
        logger.debug("Output:{}".format(result))
        return result

    def create_file(self, file_name, count, remote=False, host=CM_CFG["host"],
                    username=CM_CFG["username"],
                    password=CM_CFG["password"]):
        """
        Creates a new file, size(count) in MB
        :param str file_name: Name of the file with path
        :param int count: size of the file in MB
        :param bool remote: True for creating file on remote host, False for creating locally
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: output of remote execution cmd
        :rtype: str:
        """
        cmd = "dd if=/dev/zero of={} bs=1M count={}".format(file_name, count)
        logger.info(cmd)
        if remote:
            result = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=cmd,
                shell=False)
        else:
            result = self.run_cmd(cmd)
        logger.debug("output = {}".format(result))
        return result

    def execute_cmd(self, command):
        """
        This function executes  jcloud and jlient commands on the local machine
        :param str command: Command to be executed
        :return: tuple (boolean, output): includes boolean value and return output
        of the cli command
        """
        logger.info("Command : {}".format(command))
        proc = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            encoding="utf-8")
        output = proc.communicate()
        logger.debug("Output of command execution : {}".format(output))
        if proc.returncode != 0:
            return False, str(output)
        elif output[1]:
            return False, output[1].strip()
        else:
            return True, output[0].strip()

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

    def restart_s3server_service(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        Execute command to restart any system service at remote s3 server
        :param service: Name of the service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        return self.remote_execution(
            host, user, pwd, cons.SYSTEM_CTL_RESTART_CMD.format(service),
            shell=shell)

    def start_s3server_service(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Execute command to start any system service at remote s3 server
        :param service: Name of the service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        return self.remote_execution(host, user, pwd,
                                     cons.SYSTEM_CTL_START_CMD.format(service))

    def stop_s3server_service(self, service, host=CM_CFG["host"],
                              user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Execute command to stop any system service at remote s3 server
        :param service: Name of the service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        return self.remote_execution(host, user, pwd,
                                     cons.SYSTEM_CTL_STOP_CMD.format(service))

    def get_s3server_service_status(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], shell=True):
        """
        Execute command to get status any system service at remote s3 server
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: Name of the service
        :return: response
        """
        result = self.remote_execution(
            host, user, pwd, cons.SYSTEM_CTL_STATUS_CMD.format(service),
            shell=shell)
        result_ = ''.join(result)
        logger.info(result_.split())
        element = result_.split()
        if 'active' in element:
            return True, element
        else:
            return False, element

    @staticmethod
    def is_path_exists(path):
        """
        Check if file exists locally
        :param path: Absolute path
        :return: response
        """
        return os.path.exists(path)

    def is_s3_server_path_exists(
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
        try:
            client = self.connect(host, username=user, password=pwd,
                                  shell=shell)
            logger.info("client connected")
            sftp = client.open_sftp()
            logger.info("sftp connected")
            try:
                sftp.stat(path)
            except IOError as err:
                if err[0] == 2:
                    raise err
            sftp.close()
            client.close()
            return True, path
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.is_s3_server_path_exists.__name__,
                    error))
            return False, error

    def create_multiple_size_files(
            self,
            start_range,
            stop_range,
            file_count,
            folder_path=CM_CFG["test_folder_path"]):
        """
        Creating multiple random size files in a folder
        :param start_range: Start range of the file
        :param stop_range: Stop range of the file
        :param file_count: No of files
        :param folder_path: folder path at which file will be created
        :return: folder list
        """
        if not os.path.exists(folder_path):
            logger.warning(f"{folder_path} doesnt exist creating new one")
            os.mkdir(folder_path)
        try:
            os.chdir(folder_path)
            logger.info(f"Creating {file_count} file at path {os.getcwd()}")
            for i in range(file_count):
                file_name = "{}{}".format(
                    os.path.join(
                        folder_path,
                        CM_CFG["test_file_name"]),
                    i)
                self.create_file(
                    file_name, random.randint(
                        start_range, stop_range))
            list_dir = os.listdir(folder_path)
            return True, list_dir
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.create_multiple_size_files.__name__,
                    error))
            return False, error

    def get_s3server_fids(self, host=CM_CFG["host"],
                          user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Get fid's of all s3server processes
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: response
        """
        output = self.remote_execution(host, user, pwd, cons.MERO_STATUS_CMD)
        logger.info(f"Response: {output}")
        fids = []
        for line in output:
            if "s3server" in line:
                logger.info(line)
                fid = "{}@{}".format(line.split()[2], line.split()[3])
                fids.append(fid)
        return fids

    def restart_s3server_processes(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=30):
        """
        Restart all s3server processes using hctl command
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after restart
        :return:
        """
        try:
            fids = self.get_s3server_fids(host, user, pwd)
            for pid in fids:
                logger.info("Restarting fid : {}".format(pid))
                self.remote_execution(host, user, pwd,
                                      cons.SYSTEM_CTL_RESTART_CMD.format(pid))
                time.sleep(wait_time)
            logger.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, fids
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.restart_s3server_processes.__name__,
                    error))
            return False, error

    def is_mero_online(self, host=CM_CFG["host"],
                       user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Check whether all services are online in mero cluster
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: bool , response
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.MERO_STATUS_CMD)
            logger.info(output)
            fail_list = cons.FAILED_LIST
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, output
            return True, output
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.is_mero_online.__name__,
                error))
            return False, error

    @staticmethod
    def backup_or_restore_files(action,
                                backup_path,
                                backup_list):
        """Used to take backup or restore mentioned files at the required path"""
        try:
            if action == "backup":
                logger.info('Starting the backup')
                if not os.path.exists(backup_path):
                    os.mkdir(backup_path)
                for files in backup_list:
                    shutil.copy(files, backup_path)
                    logger.info(
                        "Files :{} copied successfully at path {}".format(
                            files, backup_path))
                return True, backup_list
            elif action == "restore":
                logger.info('Starting the restore')
                if not os.path.exists(backup_path):
                    logger.info(
                        "Backup path :{}, does not exist".format(backup_path))
                else:
                    os.chdir(backup_path)
                    for files in backup_list:
                        file = os.path.basename(files)
                        file_path = os.path.dirname(files)
                        shutil.copy(file, file_path)
                        logger.info(
                            "File :{} got copied successfully at path {}".format(
                                file, file_path))
                    return True, backup_path
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.backup_or_restore_files.__name__,
                error))
            return False, error

    def copy_s3server_file(
            self,
            file_path,
            local_path,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"],
            shell=True):
        """
        copy file from s3 server to local path
        :param file_path: Remote path
        :param local_path: Local path
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: bool, local path
        """
        try:
            client = self.connect(
                host, username=user, password=pwd, shell=shell)
            logger.info("client connected")
            sftp = client.open_sftp()
            logger.info("sftp connected")
            sftp.get(file_path, local_path)
            logger.info("file copied to : {}".format(local_path))
            sftp.close()
            client.close()
            return True, local_path
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.copy_s3server_file.__name__,
                error))
            return False, error

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
            logger.info("client connected")
            sftp = client.open_sftp()
            logger.info("sftp connected")
            sftp.put(local_path, remote_file_path)
            logger.info("file copied to : {}".format(remote_file_path))
            sftp.close()
            client.close()
            return True, remote_file_path
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.copy_file_to_remote.__name__,
                error))
            return False, error

    def is_string_in_s3server_file(self, string, file_path):
        """
        find given string in file present on s3 server
        :param string: String to be check
        :param file_path: file path
        :return: Boolean
        """
        local_path = os.path.join(os.getcwd(), 'temp_file')
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            local_path = self.copy_s3server_file(file_path, local_path)[0]
            if string in open(local_path).read():
                logger.info("Match found in : {}".format(file_path))
                return True, "Success"
            num = 1
            while True:
                if os.path.exists(local_path):
                    os.remove(local_path)
                local_path = self.copy_s3server_file(
                    file_path + '.' + str(num), local_path)[0]
                if string in open(local_path).read():
                    logger.info(
                        "Match found in : {}".format(
                            file_path + '.' + str(num)))
                    return True, "Success"
                num = num + 1
                if num > 6:
                    break
            return False, "Not found"
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.is_string_in_s3server_file.__name__,
                    error))
            return None, error
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def get_ports_of_service(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Find all TCP ports for given running service
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: (boolean, response)
        :return:
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.NETSAT_CMD.format(service))
            ports = []
            for line in output:
                out_list = line.split()
                ports.append(out_list[3].split(':')[-1])
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_ports_of_service.__name__,
                error))
            return False, error

    def check_s3services_online(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Check whether all s3server services are online
        :return: False, if no s3server services found or are not Online
        :return: True, if all the s3server services are online
        :return: None, if any exception
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.MERO_STATUS_CMD)
            s3services = []
            for line in output:
                if "s3server" in line:
                    s3services.append(line.strip())
            if s3services == []:
                return False, "No s3server service found!"
            for service in s3services:
                if not service.startswith("[started]"):
                    return False, s3services
            return True, s3services
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.check_s3services_online.__name__,
                error))
            return False, error

    # RAS
    def remote_machine_cmd(self,
                           cmd,
                           host,
                           nbytes,
                           user_name=CM_CFG["username"],
                           user_password=CM_CFG["password"],
                           shell=True):
        """
        This function will execute the command on remote host.
        :param cmd: Command to be executed
        :type cmd: str
        :param host: Host name of remote machine
        :type host: str
        :param nbytes: Number of bytes to read from command response
        :type nbytes: int, buffer size to be read at once
        :param user_name: Username of remote machine
        :type user_name: str
        :param user_password: User password of remote machine
        :type user_password: str
        :return: Command response or error in case of failure and status(True/False)
        :type: tuple
        """
        logger.info("Executing command = ", cmd)
        client = self.connect(
            host,
            username=user_name,
            password=user_password,
            shell=shell)
        try:
            _, stdout, stderr = client.exec_command(cmd)
            # Reading nbytes bytes of response data from remote machine.
            result = stdout.read(nbytes)
            stdout.flush()
            status = True
        except Exception as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.remote_machine_cmd.__name__,
                error))
            result = error
            status = False
        finally:
            client.close()
        return status, result

    def get_disk_usage(self, path, remote=False, host=CM_CFG["host"],
                       user=CM_CFG["username"],
                       pwd=CM_CFG["password"]):
        """
        This function will return disk usage associated with given path.
        :param path: Path to retrieve disk usage
        :param remote: for getting remote disk usgae True/False
        :param host: IP of the remort host
        :param user: User of the remote host
        :param pwd: Password of the remote user
        :return: Disk usage of given path or error in case of failure
        :type: (Boolean, float/str)
        """
        try:
            if not remote:
                logger.info("Running local disk usage cmd.")
                stats = os.statvfs(path)
                f_blocks, f_frsize, f_bfree = stats.f_blocks, stats.f_frsize, stats.f_bfree

            else:
                logger.info("Running remote disk usage cmd.")
                cmd = "stat --file-system / --format %b,%S,%f"
                logger.debug(f"Running cmd: {cmd} on host:{host}")
                res = self.remote_execution(host, user, pwd, cmd)
                f_res = res[0].replace("\n", "").split(",")
                f_blocks, f_frsize, f_bfree = int(
                    f_res[0]), int(
                    f_res[1]), int(
                    f_res[2])
            total = (f_blocks * f_frsize)
            used = (f_blocks - f_bfree) * f_frsize
            result = format((float(used) / total) * 100, ".1f")
        except ZeroDivisionError as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_disk_usage.__name__,
                error))
            return False, error
        except Exception as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_disk_usage.__name__,
                error))
            return False, error
        return True, result

    @staticmethod
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

    def execute_command(
            self,
            command,
            timeout_sec=400,
            host=None,
            username=None,
            password=None,
            inputs=None,
            nbytes=None,
            read_sls=False):
        """
        Execute command on remote machine.
        :param command: A command to execute
        :type command: str
        :param timeout_sec: Timeout value
        :type timeout_sec: integer
        :param host: Remote machine IP address to connect
        :type host: str
        :param username: Remote machine user name
        :type username: str
        :param password: Remote machine password
        :type password: str
        :param inputs: used to pass yes argument to commands.
        :type inputs: str
        :param nbytes: nbytes returns string buffer.
        :type nbytes: bool
        :param read_sls: use only if we want to read sls file data
        :type read_sls: bool
        :return: Return a tuple containing
        an boolean status and output string which
        can contain command execution output or error
        """
        conf_val = ctpyaml.read_yaml(
            'config/provisioner/provisioner_config.yaml')
        if not host:
            host = conf_val['server_ip']
        if not username:
            username = conf_val['server_username']
        if not password:
            password = conf_val['server_password']
        output = None
        result_flag = True
        client = self.connect(host, username, password)
        if client:
            logger.info("Server_IP: {}".format(host))
            logger.info("Executing command: {}".format(command))
            stdin, stdout, stderr = client.exec_command(
                command, timeout=timeout_sec)
            exit_status = stdout.channel.recv_exit_status()
            if inputs:
                stdin.write('\n'.join(inputs))
                stdin.write('\n')
            stdin.flush()
            stdin.channel.shutdown_write()
            client.close()
            if nbytes:
                ssh_output = stdout.read(nbytes)
            # below elif is only applicable in configure-eos Lib
            elif read_sls:
                ssh_output = stdout.read()
                if ssh_output == b'':
                    ssh_error = stderr.read()
                    return False, ssh_error
                return True, ssh_output
            else:
                ssh_output = stdout.readlines()
            ssh_error = stderr.read()
            if ssh_error == b'':
                output = ssh_output
            else:
                output = ssh_error
                result_flag = False
        else:
            output = constants.SSH_CONNECT_ERR
            result_flag = False
            # client.close()
        return result_flag, output

    def is_eos_utility_present(self, utility_name, filepath):
        """
        This function will check utility file
        is present on specific location or not
        :return: Status(True/False) of command execution
        """
        cmd = f"ls {filepath}"
        try:
            values = self.execute_command(cmd)
            logger.info(values)
            if values[0]:
                for val in values[1]:
                    if utility_name == val.split("\n")[0]:
                        return True
            return False
        except BaseException as error:
            logger.info(
                "is_eos_utility_present failed with error : {}".format(error))
            return False

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
            logger.error("{} {}: {}".format(
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
                logger.info(
                    f"Directory '{dir_name}' not exists, creating directory...")
                if remote_host:
                    self.execute_command(
                        command=f"mkdir {path}{dir_name}",
                        host=PRVSNR_CFG['machine1'])
                else:
                    self.execute_command(command=f"mkdir {path}{dir_name}")
            else:
                logger.info(f"Directory '{dir_name}' already exist...")
            return True

        except Exception as error:
            logger.error("{} {}: {}".format(
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
            logger.info(f"Removing directory : {path}")
            cmd = f"rm -rf {path}"
            if remote_host:
                ret_val = self.execute_command(
                    command=cmd, host=PRVSNR_CFG['machine1'])
            else:
                ret_val = self.execute_command(command=cmd)
            if ret_val:
                logger.info("Successfully delete directory")
                return True
        except Exception as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.rem_directory.__name__,
                error))
            return False

    def remove_file(self, file_path=None):
        """
        This function is used to remove file at specified path
        :param file_path: Path of file to be deleted
        :return: (Boolean, Response)
        """
        try:
            os.remove(file_path)
            return True, "Success"
        except Exception as error:
            logger.error("Error while deleting file".format(error))
            return False, error

    def split_file(self, file_name, size, split_count, random_part_size=False):
        """
        Creates a new file of size(count) in MB and split based on split count
        :param file_name: File name with absolute path
        :param size: Size of the file
        :param split_count: No. of parts the file needs to be split into
        :param random_part_size: True for random size parts, False for equal size parts
        :return: [{"Output":partname, "Size":partsize}]
        """

        if os.path.exists(file_name):
            logger.debug("Deleting existing file: {}".format(file_name))
            self.remove_file(file_name)
        self.create_file(file_name, size)
        logger.debug(
            "Created new file {} with size {} MB".format(
                file_name, size))
        dir_path = os.path.dirname(file_name)
        random.seed(1048576)
        res_d = []
        with open(file_name, "rb") as fin:
            for el in range(split_count):
                fop = "{}/{}_out{}".format(dir_path,
                                           os.path.basename(file_name), str(el))
                if random_part_size:
                    read_bytes = random.randint(
                        1048576 * size // 10, 1048576 * size)
                else:
                    read_bytes = (1048576 * size // split_count)
                with open(fop, 'wb') as split_fin:
                    split_fin.write(fin.read(read_bytes))
                    res_d.append({"Output": fop, "Size": os.stat(fop).st_size})
        logger.debug(res_d)
        return res_d

    def install_new_cli_rpm(self, rpm_link=None, host=None):
        cmd_output = []
        try:
            # cmd = f"yum install -y {rpm_link}"
            cmd = constants.RPM_INSTALL_CMD.format(rpm_link)
            logger.info(f"command : {cmd}")
            cmd_flag, cmd_output = self.execute_command(command=cmd, host=host)
            if cmd_flag and cmd_output != []:
                logger.info(constants.RPM_INSTALLATION_SUCCESS)
            return cmd_flag, cmd_output
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                constants.RPM_INSTALLATION_FAILED,
                self.install_new_cli_rpm.__name__,
                error))
            return False, cmd_output

    @staticmethod
    def read_config():
        config = ConfigParser()
        return config

    def get_config(self, path, section=None, key=None):
        """
        Get config file value as per the section and key
        :param path: File path
        :param section: Section name
        :param key: Section key name
        :return: key value else all items else None
        """
        try:
            config = self.read_config()
            config.read(path)
            if section and key:
                return config.get(section, key)
            else:
                return config.items(section)
        except configparser.MissingSectionHeaderError:
            keystr = "{}=".format(key)
            with open(path, "r") as fp:
                for line in fp:
                    if keystr in line and "#" not in line:
                        return line[len(keystr):].strip()
            return None

    def update_config(self, path, section, key, value):
        """
        Update config file value as per the section and key
        :param path: File path
        :param section: Section name
        :param key: Section key name
        :param value: new value
        :return: boolean
        """
        config = self.read_config()
        config.read(path)
        try:
            config.set(section, key, value)
            with open(path, "w") as configfile:
                config.write(configfile)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.update_config.__name__,
                error))
            return False
        return True

    def is_rpm_installed(self, expected_rpm=PRVSNR_CFG['rpm_name'], host=None):
        """
        This function checks that expected rpm is currenty installed or not
        :param expected_rpm: rpm to check
        :type expected_rpm: string
        :return: True if rpm is installed, false otherwise
        :param host: Remote machine IP to connect
        :type host: str
        """
        rpm_installed = False
        cmd = PROV_DICT_OBJ["LST_RPM_CMD"]
        logger.info(f"command : {cmd}")
        cmd_output = self.execute_command(command=cmd, host=host)
        if cmd_output[1] == []:
            logger.info("RPM not found")
            rpm_installed = False
            return rpm_installed, "RPM not found"
        else:
            logger.info(cmd_output[1])
            rpm_list = [rpm.split("\n")[0] for rpm in cmd_output[1]]
            logger.info(f"Installed RPM: {rpm_list}")
            for rpm in rpm_list:
                if rpm in expected_rpm:
                    rpm_installed = True
                    logger.info(f"RPM {expected_rpm} already installed")
                    break
            return rpm_installed, "Expected RPM installed"

    def is_machine_clean(self):
        """
        This function checks that any rpm is installed on machine and
        will check for eos-prvsnr binaries present at /opt/seagate/ path
        ex -
        rpm_cmd = "rpm -qa | grep eos-prvsnr"
        bin_cmd = "ls /opt/seagate/"
        :return: boolean values for both scenarioes
        """
        rpm_installed = False
        eos_prvsnr_present = False

        # Check any RPM is being installed on machine
        rpm_cmd = PROV_DICT_OBJ["LST_RPM_CMD"]
        prvsn_dir = constants.LST_PRVSN_DIR
        logger.info(f"command : {rpm_cmd}")
        cmd_output = self.execute_command(command=rpm_cmd)
        if cmd_output[1] != []:
            rpm_installed = True

        # Now check eos-prvsn binaries present at path
        logger.info(f"command : {prvsn_dir}")
        cmd_output_1 = self.execute_command(command=prvsn_dir)
        if cmd_output_1[1] != []:
            eos_prvsnr_present = True
        return rpm_installed, eos_prvsnr_present

    def is_machine_already_configured(self):
        """
        This method checks that machine is already configured or not.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = constants.STATUS_MERO
        logger.info(f"command : {mero_status_cmd}")
        cmd_output = self.execute_command(command=mero_status_cmd)
        if not cmd_output[0] or "command not found" in str(cmd_output[1]):
            logger.info("Machine is not configured..!")
            return False
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            if ('[' and ']') in output:
                logger.info(output)
        logger.info("Machine is already configured..!")
        return True

    def all_cluster_services_online(self, host=None, timeout=400):
        """
        This function will verify hctl status commands output. Check for
        all cluster services are online using hctl mero status command.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = constants.STATUS_MERO
        logger.info(f"command : {mero_status_cmd}")
        cmd_output = self.execute_command(command=mero_status_cmd,
                                          host=host, timeout_sec=timeout)
        if not cmd_output[0]:
            logger.error(f"Command {mero_status_cmd} failed..!")
            return False, cmd_output[1]
        # removing \n character from each line of output
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            # fetching all services status
            if ']' in output:
                service_status = output.split(']')[0].split('[')[1].strip()
                if 'started' not in service_status:
                    logger.error("services not starts successfully")
                    return False, "Services are not online"
            elif ("command not found" in output) or \
                    ("Cluster is not running." in output):
                logger.info("Machine is not configured..!")
                return False, f"{constants.STATUS_MERO} command not found"
        else:
            logger.info("All other services are online")
            return True, "Server is Online"

    def get_authserver_log(self, path, option="-n 3", host=CM_CFG["host"],
                           user=CM_CFG["username"],
                           pwd=CM_CFG["password"]):
        cmd = "tail {} {}".format(path, option)
        res = self.remote_execution(host, user, pwd, cmd)
        return res

    def validate_output(self, output, expected_keywords):
        logger.info("actual output", output)
        output = [i.strip() for i in output]
        logger.info("output after strip %s", output)
        validation_steps = dict()
        for ele in expected_keywords:
            validation_steps[ele] = False
        for line in output:
            for out in validation_steps:
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if out in line:
                    validation_steps[out] = True
        retval = (
            False not in list(
                validation_steps.values()),
            'validation failed')
        return retval

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
        logger.info("Stop all services individually")
        result = {}
        for service in services:
            logger.info(f"stopping service {service}")
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
            logger.info(f"service status {service}")
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

    def open_empty_file(self,
                        fpath,
                        ):
        """
        Create empty file specified in path.
        :param fpath: Non-existing file path.
        :type fpath: str.
        :return: True/err.
        :rtype: bool.
        """
        try:
            with open(fpath, "w") as f_write:
                pass
        except OSError as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.open_empty_file.__name__,
                error))
            return False
        return True

    def create_symlink(self,
                       fpath,
                       spath,
                       ):
        """
        Create symlink using os.symlink specified in fpath.
        :param fpath: Existing file path.
        :type fpath: str.
        :param spath: Non-existing file path.
        :type spath: str.
        :return: True/err.
        :rtype: bool.
        """
        try:
            os.symlink(fpath, spath)
        except OSError as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.create_symlink.__name__,
                error))
            return False

        return True

    def cleanup_directory(self,
                          dpath,
                          ):
        """
        Remove all files, links, directory recursively inside dpath.
        :param dpath: Absolute directory path.
        :type dpath: str.
        :return: True/False, "Success"/err
        :rtype: tuple.
        """
        for filename in os.listdir(dpath):
            file_path = os.path.join(dpath, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except OSError as error:
                logger.error("{0} {1}: {2}".format(
                    constants.EXCEPTION_ERROR,
                    Utility.cleanup_directory.__name__,
                    error))
                return False

        return True

    def listdir(self,
                dpath,
                ):
        """
        List directory from dpath.
        :param dpath: Directory path.
        :type dpath: str.
        :return: flist.
        :rtype: list.
        """
        try:
            flist = os.listdir(dpath)
            logging.debug("List: {}".format(flist))
        except IOError as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.listdir.__name__,
                error))
            return []

        return flist

    def makedir(self,
                dpath,
                mode=None,
                ):
        """
        Create directory path.
        :param dpath: Directory path.
        :type dpath: str.
        :return: dpath.
        :rtype: tuple.
        """
        try:
            if mode:
                os.mkdir(path=dpath, mode=mode)
            else:
                os.mkdir(dpath)
        except IOError as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.update_config.__name__,
                error))
            return str(error)

        return dpath

    def makedirs(self,
                 dpath,
                 mode=None,
                 ):
        """
        Create directory path recursively.
        :param dpath: Directory path.
        :type dpath: str.
        :return: dpath.
        :rtype: path.
        """
        try:
            if mode:
                os.makedirs(dpath, mode)
            else:
                os.makedirs(dpath)
        except IOError as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.makedirs.__name__,
                error))
            return str(error)

        return dpath

    def removedir(self,
                  dpath,
                  ):
        """
        remove empty directory.
        :param dpath: Directory path.
        :type dpath: str.
        :return: dpath
        :rtype: path.
        """
        try:
            os.rmdir(dpath)
        except IOError as error:
            logger.error("{0} {1}: {2}".format(
                constants.EXCEPTION_ERROR,
                Utility.removedir.__name__,
                error))
            return str(error)

        return dpath

    def update_config_helper(
            self,
            filename,
            key,
            old_value,
            new_value,
            delimiter):
        """
        helper method for update_config2
        :param filename: file to update
        :param key: key in file
        :param old_value: old value of key
        :param new_value: new value of key
        :param delimiter: delimiter used in file
        :return: bool, string
        """
        if os.path.exists(filename):
            shutil.copy(filename, filename + '_bkp')
            nw_value = list(new_value)
            ol_value = list(old_value)
            with open(filename, 'r+') as f_in:
                for line in f_in.readlines():
                    if delimiter in line:
                        if key in line:
                            f_in.seek(0, 0)
                            data = f_in.read()
                            if delimiter == ':':
                                if '"' in data:
                                    old_pattern = '{}{}{}"{}"'.format(
                                        key, ":", " ", old_value)
                                    new_pattern = '{}{}{}"{}"'.format(
                                        key, ":", " ", new_value)
                                else:
                                    old_pattern = '{}{}{}{}'.format(
                                        key, ":", " ", old_value)
                                    new_pattern = '{}{}{}{}'.format(
                                        key, ":", " ", new_value)
                                logger.debug("old_pattern: {}".format(old_pattern))
                                logger.debug("new_pattern: {}".format(new_pattern))
                            else:
                                old_pattern = key + "=" + old_value
                                new_pattern = key + "=" + new_value
                            if len(ol_value) > len(nw_value):
                                count = len(ol_value) - len(nw_value)
                                new_pattern = new_pattern + " " * count
                                match = re.search(old_pattern, data)
                                span_ = match.span()
                                f_in.seek(span_[0])
                                f_in.write(new_pattern)
                                logger.debug(
                                    "Old pattern {} got replaced by new pattern {}".format(
                                        old_pattern, new_pattern))
                                f_in.seek(0, 0)
                                new_data = f_in.read()
                                return True, new_data
                            else:
                                match = re.search(old_pattern, data)
                                span_ = match.span()
                                f_in.seek(span_[0])
                                f_in.write(new_pattern)
                                logger.debug(
                                    "Old pattern {} got replaced by new pattern {}".format(
                                        old_pattern, new_pattern))
                                f_in.seek(0, 0)
                                new_data = f_in.read()
                                return True, new_data

    def update_config2(self, filename, key, old_value, new_value):
        """
        Editing a file provided with : or = separator
        :param filename: file to update
        :param key: key in file
        :param old_value: old value of key
        :param new_value: new value of key
        :return: bool
        """
        try:
            with open(filename, 'r+') as f_in:
                for line in f_in.readlines():
                    if "=" in line:
                        self.update_config_helper(
                            filename, key, old_value, new_value, "=")
                    elif ":" in line:
                        self.update_config_helper(
                            filename, key, old_value, new_value, ":")
                    return True, new_value
        except AttributeError as error:
            logger.debug(
                'Old value : {} is incorrect, please correct it and try again'.format(old_value))
            return False, error
        except Exception as error:
            os.remove(filename)
            os.rename(filename + '_bkp', filename)
            logger.debug(
                "Removed original corrupted file and Backup file has been restored ")
            logger.debug(
                "*ERROR* An exception occurred in upload_config : {}".format(error))
            return False, error

    def get_file_checksum(self, file_name):
        """
        This function will return checksum of file content present on the
        local server
        :param str file_name: Name of the file
        :return: (Boolean, response)
        """
        logger.info("Calculating checksum of file content")
        try:
            result = md5(open(file_name, "rb").read()).hexdigest()
            return True, result
        except BaseException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_file_checksum.__name__,
                    error))
            return False, error

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
            logger.error(error)

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
            logger.debug("sftp connected")
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
            logger.error(error)
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
            logger.debug(f"Connected to {host}")
            sftp = client.open_sftp()
            logger.debug("sftp connected")
            try:
                sftp.rename(old_filename, new_filename)
            except IOError as err:
                if err[0] == 2:
                    raise err
            sftp.close()
            client.close()
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.file_rename_remote.__name__,
                    error))

    def get_s3server_resource(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Get resources of all s3server instances using pcs command.
        :param str host: IP of the host
        :param str user: user name of the host
        :param str pwd: password for the user
        :return: response, list of s3 resources
        :rtype: list
        """
        output = self.remote_execution(
            host, user, pwd, cons.PCS_RESOURCE_SHOW_CMD)
        logger.info(f"Response: {output}")
        s3_rcs = []
        for line in output:
            if "s3server-c" in line:
                logger.info(line)
                fid = line.split()[0]
                s3_rcs.append(fid)
        return s3_rcs

    def restart_s3server_resources(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=30, shell=True):
        """
        Restart all s3server resources using pcs command
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after restart
        :param shell: for interactive shell True/False
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        try:
            rcs = self.get_s3server_resource(host, user, pwd)
            for rc in rcs:
                logger.info("Restarting resource : {}".format(rc))
                self.remote_execution(
                    host,
                    user,
                    pwd,
                    cons.PCS_RESOURCE_RESTART_CMD.format(rc),
                    shell=shell)
                time.sleep(wait_time)
            logger.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, rcs
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.restart_s3server_resources.__name__,
                    error))
            return False, error

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
            logger.debug(f"Connected to {host}")
            sftp = client.open_sftp()
            logger.debug("sftp connected")
            try:
                sftp.remove(filename)
            except IOError as err:
                if err[0] == 2:
                    raise err
            sftp.close()
            client.close()
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.remove_file_remote.__name__,
                    error))

    # Provisioner
    def get_ports_for_firewall_cmd(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Find all ports exposed through firewall permanent service for given component
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: service component
        :return: (boolean, response)
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.FIREWALL_CMD.format(service))
            ports = []
            for word in output:
                ports.append(word.split())
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_ports_for_firewall_cmd.__name__,
                    error))
            return False, error

    def enable_disable_s3server_instances(
            self,
            resource_disable=True,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=1):
        """
        Enable or disable s3server instances using pcs command
        :param resource_disable: True for disable and False for enable
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after resource action
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        try:
            rcs = self.get_s3server_resource()
            for rc in rcs:
                if resource_disable:
                    logger.info("Disabling resource : {}".format(rc))
                    self.remote_execution(
                        host, user, pwd, cons.PCS_RESOURCE_DISABLE_CMD.format(rc))
                    time.sleep(wait_time)
                else:
                    logger.info("Enabling resource : {}".format(rc))
                    self.remote_execution(
                        host, user, pwd, cons.PCS_RESOURCE_ENABLE_CMD.format(rc))
                    time.sleep(wait_time)
            logger.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, rcs
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.enable_disable_s3server_instances.__name__,
                    error))
            return False, error

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
            logger.error(
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
                logger.info("Match found in : {}".format(file_path))
                return True, match
            else:
                return False, "String Not Found"
        except BaseException as error:
            logger.error(
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
        logger.info("client connected")
        sftp = client.open_sftp()
        logger.info("sftp connected")
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

    def configure_s3fs(self, access, secret, path=CM_CFG["s3fs_path"]):
        """
        Function to configure access and secret keys for s3fs.
        :param access: aws access key
        :param secret: aws secret key
        :param path: s3fs config file
        :return: True
        """
        if self.execute_cmd("s3fs --version") and os.path.exists(path):
            with open(path, "w+") as fd:
                fd.write(f"{access}:{secret}")
            res = True
        else:
            msg = "S3fs is not present, please install it and than run the " \
                  "configuration."
            logger.info(msg)
            res = False

        return res

    def configure_s3cfg(self, access, secret, path=CM_CFG["s3cfg_path"]):
        """
        Function to configure access and secret keys in s3cfg file.
        :param access: aws access key
        :param secret: aws secret key
        :param path: path to s3cfg file
        :return: True
        """
        if self.execute_cmd("s3cmd --version"):
            res1 = self.update_config(path, "default", "access_key", access)
            res2 = self.update_config(path, "default", "secret_key", secret)
            res = res1 and res2
        else:
            msg = "S3cmd is not present, please install it and than run the " \
                  "configuration."
            logger.warning(msg)
            res = False

        return res

    def get_json(self, file_path):
        """
        Function to get json data from a file.
        :param string file_path: Path of the file
        :return: True
        """
        try:
            with open(file_path, "r") as jsFile:
                data = json.load(jsFile)
            return data
        except Exception as error:
            logger.error(error)
            raise error

    def update_json(self, file_path, data):
        """
        Function to update json data in file
        :param string file_path: path of the file.
        :param dict data: updated json data to be updated in file
        :return: True
        """
        try:
            with open(file_path, "w") as jsonFile:
                json.dump(data, jsonFile)
            return True
        except Exception as error:
            logger.error(error)
            raise error

    def configure_minio(self, access, secret, path=CM_CFG["minio_path"]):
        """
        Function to configure minio creds in config.json file.
        :param access: aws access key
        :param secret: aws secret key
        :param path: path to minio cfg file
        :return: True/False
        """

        if os.path.exists(path):
            data = self.get_json(path)
            data["hosts"]["s3"]["accessKey"] = access
            data["hosts"]["s3"]["secretKey"] = secret
            res = self.update_json(path, data)
        else:
            msg = "Minio is not installed please install and than run the " \
                  "configuration"
            logger.warning(msg)
            res = False

        return res

    # Provisioner
    def get_ports_for_firewall_cmd(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Find all ports exposed through firewall permanent service for given component
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param service: service component
        :return: (boolean, response)
        """
        try:
            output = self.remote_execution(
                host, user, pwd, cons.FIREWALL_CMD.format(service))
            ports = []
            for word in output:
                ports.append(word.split())
            if not ports:
                return None, "Does Not Found Running Service '{}'".format(
                    service)
            return True, ports
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_ports_for_firewall_cmd.__name__,
                    error))
            return False, error

    def enable_disable_s3server_instances(
            self,
            resource_disable=True,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"], wait_time=1):
        """
        Enable or disable s3server instances using pcs command
        :param resource_disable: True for disable and False for enable
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :param wait_time: Wait time in sec after resource action
        :return: tuple with boolean and response/error
        :rtype: tuple
        """
        try:
            rcs = self.get_s3server_resource()
            for rc in rcs:
                if resource_disable:
                    logger.info("Disabling resource : {}".format(rc))
                    self.remote_execution(
                        host, user, pwd, cons.PCS_RESOURCE_DISABLE_CMD.format(rc))
                    time.sleep(wait_time)
                else:
                    logger.info("Enabling resource : {}".format(rc))
                    self.remote_execution(
                        host, user, pwd, cons.PCS_RESOURCE_ENABLE_CMD.format(rc))
                    time.sleep(wait_time)
            logger.info(
                "Is mero online : {}".format(
                    self.is_mero_online(
                        host, user, pwd)))
            return True, rcs
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.enable_disable_s3server_instances.__name__,
                    error))
            return False, error

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
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pgrep.__name__,
                    error))
            return False, error

    def parse_xml_controller(self, filepath, field_list, xml_tag="PROPERTY"):
        """
        This function parses xml file and converts it into nested dictionary.
        :param filepath: File path of the xml file to be parsed
        :type: str
        :param field_list: List of the required fields
        :type: list of the strings
        :param xml_tag: Tag in the xml file
        :type: str
        :return: Nested dictionary having values of the fields mentioned in
        field list
        :rtype: Nested dict
        """
        try:
            e = xml.etree.ElementTree.parse(filepath).getroot()

            d = {}
            new_d = {}
            listkeys = []
            i = 0

            fields = field_list
            for child in e.iter(xml_tag):
                d['dict_{}'.format(i)] = {}
                for field in fields:
                    if (child.attrib['name']) == field:
                        new_d[field] = child.text
                        listkeys.append('True')
                        d['dict_{}'.format(i)] = new_d
                if listkeys.count('True') == len(fields):
                    i += 1
                    new_d = {}
                    listkeys = []

            logger.info("Removing empty dictionaries")
            i = 0
            while True:
                if d['dict_{}'.format(i)] == {}:
                    del (d['dict_{}'.format(i)])
                    break
                i += 1

            logger.debug(d)
            return True, d
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.parse_xml_controller.__name__,
                    error))

    def get_pcs_service_systemd(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Function to return pcs service systemd service name.
        This function will be usefull when service is not under systemctl
        :param str service: Name of the pcs resource service
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :return: (True, name of the service mentioned in systemd)
        :type: tuple
        """
        cmd = ha_cons.GREP_PCS_SERVICE_CMD.format(service)
        logger.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            logger.debug(resp)
            if not resp:
                return False, None

            resp = resp.decode().strip().replace("\t", "")
            resp1 = resp.split("):")
            for element in resp1:
                if "systemd:" in element:
                    res = element.split("(systemd:")
                    logger.info(res)
                    return True, res[1]
        except Exception as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_pcs_service_systemd.__name__,
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
            logger.error(
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
                    logger.info("Match not found : {}".format(pattern))
                    return False, pattern
                logger.info("Match found : {}".format(pattern))
            return True, response
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.validate_alert_msg.__name__,
                    error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def pcs_cluster_start_stop(self, node, stopFlag):
        """
        This function Gracefully shutdown the given node
        using pcs cluster stop command
        :param str node: Node to be shutdown
        :param bool stopFlag: Shutdown if flag is True else Start
                          the node
        :return: True/False
        :rtype: Boolean
        """
        user = CM_CFG["username"]
        pwd = CM_CFG["password"]
        server = node
        prefix = node.split(CM_CFG["NodeNamePattern"])
        node_prefix = prefix[1]
        nodeName = "{}{}".format(CM_CFG["ServerNamePattern"], node_prefix)

        if stopFlag:
            cmd = ha_cons.PCS_CLUSTER_STOP.format(nodeName)
        else:
            cmd = ha_cons.PCS_CLUSTER_START.format(nodeName)

        logger.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=server,
                user=user,
                password=pwd,
                cmd=cmd,
                read_lines=False)
            logger.info(resp)
            if not resp:
                return False, None

            return True, resp[1]

        except Exception as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_cluster_start_stop.__name__,
                    error))

            return False, error

    def write_yaml(self, fpath, write_data, backup=True):
        """
        This functions overwrites the content of given yaml file with given data
        :param str fpath: yaml file path to be overwritten
        :param dict/list write_data: data to be written in yaml file
        :param bool backup: if set False, backup will not be taken before overwriting
        :return: True/False, yaml file path
        :rtype: boolean, str
        """
        try:
            if backup:
                bkup_path = f'{fpath}.bkp'
                shutil.copy2(fpath, bkup_path)
                logger.info("Backup file {} at {}".format(fpath, bkup_path))
            with open(fpath, 'w') as fobj:
                yaml.safe_dump(write_data, fobj)
            logger.info("Updated yaml file at {}".format(fpath))
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.write_yaml.__name__,
                    error))
            return False, error
        return True, fpath

    def list_rpms(self, filter_str="", host=CM_CFG["host"],
                  user=CM_CFG["username"],
                  passwd=CM_CFG["password"]):
        """
        This function lists the rpms installed on a given host and filters by given string
        :param str filter_str: string to search in rpm names for filtering results, default lists all the rpms
        :param str host: hostname or IP of the host
        :param str user: username of host
        :param str passwd: password of host
        :return: True/False, list of rpms
        :rtype: boolean, list
        """
        rpm_grep_cmd = "rpm -qa | grep {}".format(filter_str)
        resp = self.remote_execution(
            host=host,
            user=user,
            password=passwd,
            cmd=rpm_grep_cmd)
        if isinstance(resp, list):
            rpm_list = [rpm.strip("\n") for rpm in resp]
            if not rpm_list:
                return False, rpm_list
            return True, rpm_list
        else:
            return False, resp

    def pcs_status_grep(
            self,
            service,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"]):
        """
        Function to return grepped pcs status services.
        :param str service: Name of the pcs resource service
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :return: (True, pcs staus str response)
        :type: tuple
        """
        cmd = ha_cons.GREP_PCS_SERVICE_CMD.format(service)
        logger.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            logger.debug(resp)
            if not resp:
                return None
        except Exception as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_status_grep.__name__,
                    error))

            return error

        return resp

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
        logger.info("client connected")
        try:
            resp = client.isdir(remote_path)
            client.close()
            if resp:
                return True, resp
            else:
                return False, resp
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.validate_is_dir.__name__,
                    error))
            return False, error

    def pcs_resource_cleanup(
            self,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"],
            options=None):
        """
        Perform pcs resource cleanup
        :param str host: Machine host name or IP
        :param str user: Machine login user name
        :param str pwd: Machine login user passsword
        :param str options: option supported in resource cleanup eg: [<resource id>] [--node <node>]
        :return: (True, pcs str response)
        :type: tuple
        """
        if options:
            cmd = ha_cons.PCS_RESOURCES_CLEANUP.format(options)
        else:
            options = " "
            cmd = ha_cons.PCS_RESOURCES_CLEANUP.format(options)
        logger.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            logger.debug(resp)
            if not resp:
                return False, None
        except Exception as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_resource_cleanup.__name__,
                    error))

            return False, error

        return True, resp

    def disk_usage_python_interpreter_cmd(self,
                                          dir_path,
                                          field_val=3,
                                          host=CM_CFG["host"],
                                          user=CM_CFG["username"],
                                          pwd=CM_CFG["password"]):
        """
        This function will return disk usage associated with given path.
        :param dir_path: Directory path of which size is to be calculated
        :type: str
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and percent used space respectively
        :type: int
        :param host: IP of the remote host
        :type: str
        :param user: User of the remote host
        :type: str
        :param pwd: Password of the remote user
        :type: str
        :return: Output of the python interpreter command
        :rtype: (int/float/str)
        """
        try:
            cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'" \
                .format(a=str(dir_path), b=int(field_val))
            logger.info(f"Running python command {cmd}")
            resp = self.execute_command(command=cmd, host=host, username=user,
                                        password=pwd)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.disk_usage_python_interpreter_cmd.__name__,
                    error))
            return False, error

        return resp

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
            logger.error(error)
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
            logger.info("client connected")
            sftp = client.open_sftp()
            logger.info("sftp connected")

            with sftp.open(file_path, "r") as remote:
                shutil.copyfileobj(remote, open(local_path, "wb"))

            return True, local_path
        except BaseException as error:
            logger.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR,
                Utility.write_remote_file_to_local_file.__name__, error))

            return False, error

    def get_system_cpu_usage(
            self,
            host=CM_CFG["host"],
            username=CM_CFG["username"],
            password=CM_CFG["password"]):
        """
        This function with fetch the system cpu usage percentage from remote host
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: system cpu usage
        :rtype: (bool, float)
        """
        try:
            logger.info("Fetching system cpu usage from node {}".format(host))
            logger.info(ras_cons.CPU_USAGE_CMD)
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=ras_cons.CPU_USAGE_CMD)
            logger.info(resp)
            cpu_usage = float(resp[0])
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_system_cpu_usage.__name__,
                    error))
            return False, error

        return True, cpu_usage

    def get_system_memory_usage(
            self,
            host=CM_CFG["host"],
            username=CM_CFG["username"],
            password=CM_CFG["password"]):
        """
        This function with fetch the system memory usage percentage from remote host
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: system memory usage in percent
        :rtype: (bool, float)
        """
        try:
            logger.info(
                "Fetching system memory usage from node {}".format(host))
            logger.info(ras_cons.MEM_USAGE_CMD)
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=ras_cons.MEM_USAGE_CMD)
            logger.info(resp)
            mem_usage = float(resp[0])
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_system_memory_usage.__name__,
                    error))
            return False, error

        return True, mem_usage

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
            logger.info(
                "Fetching /proc/mdstat file from the host {}".format(host))
            self.write_remote_file_to_local_file(
                RAS_CFG["mdstat_remote_path"],
                RAS_CFG["mdstat_local_path"],
                host=host,
                user=username,
                pwd=password)
            logger.info("Parsing mdstat file")
            output = mdstat.parse(RAS_CFG["mdstat_local_path"])
        except BaseException as error:
            logger.error(
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
            logger.info(
                f"Shutting down {host} node using cmd: {cmd}.")
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=cmd,
                shell=False)
            logger.info(resp)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.shutdown_node.__name__,
                    error))
            return False, error

        return True, f"Node shutdown successfully"

    def calculate_checksum(self, file_path, binary_bz64=True, options=""):
        """
        Calculate MD5 checksum with/without binary coversion for a file.
        :param file_name: Name of the file with path
        :param binary_bz64: Calulate binary base64 checksum for file,
        if False it will return MD5 checksum digest
        :return: string or MD5 object
        :rtype: str
        """
        if not os.path.exists(file_path):
            return False, "Please pass proper file path"
        if binary_bz64:
            cmd = "openssl md5 -binary {} | base64".format(file_path)
        else:
            cmd = "md5sum {} {}".format(options, file_path)
        logger.info(f"Executing cmd: {cmd}")
        result = self.execute_cmd(cmd)
        logger.debug("Output: {}".format(result))
        return result

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
            logger.debug("Installing expect package")
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
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.toggle_apc_node_power.__name__,
                    error))
            return False, error

        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def bmc_node_power_status(self, bmc_ip, bmc_user, bmc_pwd):
        """
        Function to check node power states using BMC
        :param bmc_ip: Node BMC IP
        :param bmc_user: Node BMC user name
        :param bmc_pwd: Node BMC user pwd
        :return: bool, resp
        :rtype: tuple
        """
        if not self.execute_cmd("rpm  -qa | grep ipmitool")[0]:
            logger.debug("Installing ipmitool")
            self.execute_cmd("yum install ipmitool")
        try:
            cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pwd} chassis power status"
            if not cmd:
                return False, "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.bmc_node_power_status.__name__,
                    error))
            return False, error

        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def bmc_node_power_on_off(self, bmc_ip, bmc_user, bmc_pwd, status="on"):
        """
        Function to on and off node power using BMC IP
        :param bmc_ip:
        :param bmc_user:
        :param bmc_pwd:
        :param status:
        :return:
        """
        if not self.execute_cmd("rpm  -qa | grep ipmitool")[0]:
            logger.debug("Installing ipmitool")
            self.execute_cmd("yum install ipmitool")
        cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pwd} chassis power {status.lower()}"
        try:
            if not cmd:
                return False, "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.bmc_node_power_on_off.__name__,
                    error))
            return False, error

        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def get_pillar_values(
            self,
            component,
            keys,
            decrypt=False,
            host=CM_CFG["host"],
            username=CM_CFG["username"],
            password=CM_CFG["password"]):
        """
        Fetch pillar values for given keys from given component
        :param str component: name of pillar component to fetch value from
        :param list keys: list of level wise nested keys e.g., [0th level, 1st level,..]
        :param bool decrypt: True for decrypted output
        :param str host: hostname or IP of remote host
        :param str username: username of the host
        :param str password: password of the host
        :return: True/False and pillar output value
        :rtype: bool, str
        """
        pillar_key = ":".join([component, *keys])
        get_pillar_cmd = "salt-call pillar.get {} --output=newline_values_only".format(
            pillar_key)
        logger.info(
            "Fetching pillar value with cmd: {}".format(get_pillar_cmd))
        output = self.remote_execution(
            host=host,
            user=username,
            password=password,
            cmd=get_pillar_cmd,
            shell=False)
        if not output:
            err_msg = "Pillar value not found for {}".format(pillar_key)
            return False, err_msg

        pillar_value = output[0].strip("\n")
        logger.info(
            "Pillar value for {} is {}".format(
                pillar_key, pillar_value))
        if decrypt:
            if len(pillar_value) != 100:
                err_msg = "Invalid Token passed for decryption: {}".format(
                    pillar_value)
                return False, err_msg
            decrypt_cmd = "salt-call lyveutil.decrypt {} {} --output=newline_values_only".format(
                component, pillar_value)
            output = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=decrypt_cmd,
                shell=False)
            pillar_value = output[0].strip("\n")
            logger.info(
                "Decrypted Pillar value for {} is {}".format(
                    pillar_key, pillar_value))

        return True, pillar_value
