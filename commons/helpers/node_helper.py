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
logger = logging.getLogger(__name__)


CM_CFG = ctpyaml.read_yaml("config/common_config.yaml")
PRVSNR_CFG = ctpyaml.read_yaml("config/provisioner/provisioner_config.yaml")
RAS_CFG = ctpyaml.read_yaml("config/ras/ras_config.yaml")
PROV_DICT_OBJ = constants.PROV_BUILD_VER[CM_CFG["BUILD_VER_TYPE"]]


class Node_Helper(Host):
    """
    Class to maintain all common functions across component
    """

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
            log.info(f"Response: {result}, Error: {stderr.readlines()}")
            return result
        except BaseException as error:
            log.error(error)
            return error



    def execute_command(cmd, remote=False)
        if remote:
            self.remote_execution(cmd)
        else:
            system_util.run_cmd(cmd)

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
            log.info(output)
            fail_list = cons.FAILED_LIST
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, output
            return True, output
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.is_mero_online.__name__,
                error))
            return False, error

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
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_ports_of_service.__name__,
                error))
            return False, error


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
                log.info("Running local disk usage cmd.")
                stats = os.statvfs(path)
                f_blocks, f_frsize, f_bfree = stats.f_blocks, stats.f_frsize, stats.f_bfree

            else:
                log.info("Running remote disk usage cmd.")
                cmd = "stat --file-system / --format %b,%S,%f"
                log.debug(f"Running cmd: {cmd} on host:{host}")
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
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_disk_usage.__name__,
                error))
            return False, error
        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.get_disk_usage.__name__,
                error))
            return False, error
        return True, result


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
            log.info("Server_IP: {}".format(host))
            log.info("Executing command: {}".format(command))
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








    def is_machine_already_configured(self):
        """
        This method checks that machine is already configured or not.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = constants.STATUS_MERO
        log.info(f"command : {mero_status_cmd}")
        cmd_output = self.execute_command(command=mero_status_cmd)
        if not cmd_output[0] or "command not found" in str(cmd_output[1]):
            log.info("Machine is not configured..!")
            return False
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            if ('[' and ']') in output:
                log.info(output)
        log.info("Machine is already configured..!")
        return True

    def all_cluster_services_online(self, host=None, timeout=400):
        """
        This function will verify hctl status commands output. Check for
        all cluster services are online using hctl mero status command.
        ex - mero_status_cmd = "hctl status"
        :return: boolean
        """
        mero_status_cmd = constants.STATUS_MERO
        log.info(f"command : {mero_status_cmd}")
        cmd_output = self.execute_command(command=mero_status_cmd,
                                          host=host, timeout_sec=timeout)
        if not cmd_output[0]:
            log.error(f"Command {mero_status_cmd} failed..!")
            return False, cmd_output[1]
        # removing \n character from each line of output
        cmd_output = [line.split("\n")[0] for line in cmd_output[1]]
        for output in cmd_output:
            # fetching all services status
            if ']' in output:
                service_status = output.split(']')[0].split('[')[1].strip()
                if 'started' not in service_status:
                    log.error("services not starts successfully")
                    return False, "Services are not online"
            elif ("command not found" in output) or \
                    ("Cluster is not running." in output):
                log.info("Machine is not configured..!")
                return False, f"{constants.STATUS_MERO} command not found"
        else:
            log.info("All other services are online")
            return True, "Server is Online"

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
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_ports_for_firewall_cmd.__name__,
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
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.get_ports_for_firewall_cmd.__name__,
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
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pgrep.__name__,
                    error))
            return False, error


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
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return False, None

            resp = resp.decode().strip().replace("\t", "")
            resp1 = resp.split("):")
            for element in resp1:
                if "systemd:" in element:
                    res = element.split("(systemd:")
                    log.info(res)
                    return True, res[1]
        except Exception as error:
            log.error(
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

        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=server,
                user=user,
                password=pwd,
                cmd=cmd,
                read_lines=False)
            log.info(resp)
            if not resp:
                return False, None

            return True, resp[1]

        except Exception as error:
            log.error(
                "{} {}: {}".format(
                    cons.EXCEPTION_ERROR,
                    Utility.pcs_cluster_start_stop.__name__,
                    error))

            return False, error



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
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return None
        except Exception as error:
            log.error(
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
        log.info(f"Executing cmd: {cmd}")
        try:
            resp = self.remote_execution(
                host=host, user=user, password=pwd, cmd=cmd, read_lines=False)
            log.debug(resp)
            if not resp:
                return False, None
        except Exception as error:
            log.error(
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
            log.info(f"Running python command {cmd}")
            resp = self.execute_command(command=cmd, host=host, username=user,
                                        password=pwd)
        except BaseException as error:
            log.error(
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
            log.info("Fetching system cpu usage from node {}".format(host))
            log.info(ras_cons.CPU_USAGE_CMD)
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=ras_cons.CPU_USAGE_CMD)
            log.info(resp)
            cpu_usage = float(resp[0])
        except BaseException as error:
            log.error(
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
            log.info(
                "Fetching system memory usage from node {}".format(host))
            log.info(ras_cons.MEM_USAGE_CMD)
            resp = self.remote_execution(
                host=host,
                user=username,
                password=password,
                cmd=ras_cons.MEM_USAGE_CMD)
            log.info(resp)
            mem_usage = float(resp[0])
        except BaseException as error:
            log.error(
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



