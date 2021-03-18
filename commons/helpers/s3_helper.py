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

"""s3 helper to have s3 services related classes & methods."""

import os
import re
import time
import logging
import subprocess

from configparser import NoSectionError
from paramiko.ssh_exception import SSHException
from commons import commands
from commons import constants
from commons.helpers.host import Host
from commons.utils import config_utils
from commons.utils.system_utils import run_local_cmd, run_remote_cmd
from config import S3_CFG, CMN_CFG

LOGGER = logging.getLogger(__name__)

const = constants

class S3Helper:
    """S3 Helper class to perform S3 related operations."""

    __instance = None
    cm_cfg = CMN_CFG["nodes"][0]

    def __init__(self) -> None:
        """Virtually private constructor."""
        if S3Helper.__instance:
            raise ImportError(
                "S3Helper is a singleton!, "
                "use S3Helper.get_instance() to access existing object.")
        S3Helper.__instance = self
        self.host = self.cm_cfg["host"]
        self.pwd = self.cm_cfg["password"]
        self.user = self.cm_cfg["username"]

    @staticmethod
    def get_instance() -> object:
        """
        Static method to access singleton instance.

        :return: S3Helper object.
        """
        if not S3Helper.__instance:
            S3Helper()
        return S3Helper.__instance

    @staticmethod
    def configure_s3cfg(
            access: str = None,
            secret: str = None,
            path: str = S3_CFG["s3cfg_path"]) -> bool:
        """
        Function to configure access and secret keys in s3cfg file.

        :param access: aws access key.
        :param secret: aws secret key.
        :param path: path to s3cfg file.
        :return: True if s3cmd configured else False.
        """
        status, resp = run_local_cmd("s3cmd --version")
        LOGGER.info(resp)
        if status:
            res1 = config_utils.update_config_ini(
                path, "default", "access_key", access)
            res2 = config_utils.update_config_ini(
                path, "default", "secret_key", secret)
            status = res1 and res2 and status
        else:
            LOGGER.warning(
                "S3cmd is not present, please install it and than run the configuration.")

        return status

    @staticmethod
    def configure_s3fs(
            access: str = None,
            secret: str = None,
            path: str = S3_CFG["s3fs_path"]) -> bool:
        """
        Function to configure access and secret keys for s3fs.

        :param access: aws access key.
        :param secret: aws secret key.
        :param path: s3fs config file.
        :return: True if s3fs configured else False.
        """
        status, resp = run_local_cmd("s3fs --version")
        LOGGER.info(resp)
        if status:
            with open(path, "w+") as f_write:
                f_write.write(f"{access}:{secret}")
        else:
            LOGGER.warning(
                "S3fs is not present, please install it and than run the configuration.")

        return status

    def check_s3services_online(self, host: str = None,
                                user: str = None,
                                pwd: str = None) -> tuple:
        """
        Check whether all s3server services are online.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: False if no s3server services found or are not Online else True.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            if not status:
                return status, output
            s3services = []
            for line in output:
                if "s3server" in line:
                    s3services.append(line.strip())
            if not s3services:
                LOGGER.critical("No s3server service found!")
                return False, s3services
            for service in s3services:
                if not service.startswith("[started]"):
                    LOGGER.error("S3 service down: %s", s3services)
                    return False, service

            return status, output
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.check_s3services_online.__name__,
                str(error))
            return False, error

    def get_s3server_service_status(self, service: str = None,
                                    host: str = None,
                                    user: str = None,
                                    pwd: str = None) -> tuple:
        """
        Execute command to get status any system service at remote s3 server.

        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, result = run_remote_cmd(commands.SYSTEM_CTL_STATUS_CMD.format(
                service), host, user, pwd, read_lines=True)
            if not status:
                return status, result
            result_ = ''.join(result)
            element = result_.split()
            LOGGER.debug(element)
            if 'active' in element:
                return True, result_

            return status, result_
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.get_s3server_service_status.__name__,
                str(error))
            return False, error

    def start_s3server_service(self,
                               service: str = None,
                               host: str = None,
                               user: str = None,
                               pwd: str = None) -> tuple:
        """
        Execute command to start any system service at remote s3 server.

        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, result = run_remote_cmd(commands.SYSTEM_CTL_START_CMD.format(
                service), host, user, pwd, read_lines=True)
            LOGGER.debug(result)
            if not status:
                return status, result
            time.sleep(10)
            response = self.get_s3server_service_status(
                service, host, user, pwd)

            return response
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.start_s3server_service.__name__,
                str(error))
            return False, error

    def stop_s3server_service(self,
                              service: str = None,
                              host: str = None,
                              user: str = None,
                              pwd: str = None) -> tuple:
        """
        Execute command to stop any system service at remote s3 server.

        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, result = run_remote_cmd(commands.SYSTEM_CTL_STOP_CMD.format(
                service), host, user, pwd, read_lines=True)
            LOGGER.debug(result)
            time.sleep(10)
            status, resp = self.get_s3server_service_status(
                service, host, user, pwd)
            # True if service successfully stopped.
            status = bool('inactive' in str(resp))

            return status, resp
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.stop_s3server_service.__name__,
                error)
            return False, error

    def restart_s3server_service(self,
                                 service: str = None,
                                 host: str = None,
                                 user: str = None,
                                 pwd: str = None) -> tuple:
        """
        Execute command to restart any system service at remote s3 server.

        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: bool, response.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, result = run_remote_cmd(
                commands.SYSTEM_CTL_RESTART_CMD.format(service),
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(result)
            if not status:
                return status, result
            time.sleep(10)
            response = self.get_s3server_service_status(
                service, host, user, pwd)

            return response
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.restart_s3server_service.__name__,
                error)
            return False, error

    def restart_s3server_processes(self,
                                   host: str = None,
                                   user: str = None,
                                   pwd: str = None,
                                   wait_time: int = 20) -> tuple:
        """
        Restart all s3server processes using hctl command.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after restart.
        :return: True if s3server process restarted else False.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, fids = self.get_s3server_fids()
            LOGGER.debug(fids)
            if not status:
                return status, fids
            for pid in fids:
                LOGGER.info("Restarting fid : %s", str(pid))
                status, response = run_remote_cmd(
                    commands.SYSTEM_CTL_RESTART_CMD.format(pid),
                    host,
                    user,
                    pwd,
                    read_lines=True)
                LOGGER.debug(response)
                time.sleep(wait_time)
            LOGGER.info("Is motr online.")
            status, output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOGGER.debug(fail_list)
            for line in output:
                if any(
                        fail_str in line for fail_str in fail_list) and "s3server" in line:
                    return False, output

            return status, output
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.restart_s3server_processes.__name__,
                error)
            return False, error

    def get_s3server_resource(self, host: str = None,
                              user: str = None,
                              pwd: str = None) -> tuple:
        """
        Get resources of all s3server instances using pcs command.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response, list of s3 resources.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, output = run_remote_cmd(
                commands.PCS_RESOURCE_SHOW_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.info("Response: %s", str(output))
            s3_rcs = []
            for line in output:
                if "s3server-c" in line:
                    LOGGER.info(line)
                    fid = line.split()[0]
                    s3_rcs.append(fid)
            LOGGER.debug(s3_rcs)

            return status, s3_rcs
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.get_s3server_resource.__name__,
                error)
            return False, error

    def restart_s3server_resources(self,
                                   host: str = None,
                                   user: str = None,
                                   pwd: str = None,
                                   wait_time: int = 20) -> tuple:
        """
        Restart all s3server resources using pcs command.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after restart.
        :return: True if services restarted else False.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, resources = self.get_s3server_resource(
                host=host, user=user, pwd=pwd)
            if not status:
                return status, resources
            for resource in resources:
                LOGGER.info("Restarting resource : %s", str(resource))
                status, response = run_remote_cmd(
                    commands.PCS_RESOURCE_RESTART_CMD.format(resource),
                    host,
                    user,
                    pwd,
                    read_lines=True)
                LOGGER.debug(response)
                time.sleep(wait_time)
            LOGGER.info("Is motr online.")
            status, output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOGGER.debug(fail_list)
            for line in output:
                if any(
                        fail_str in line for fail_str in fail_list) and "s3server" in line:
                    return False, output

            return status, output
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.restart_s3server_resources.__name__,
                error)
            return False, error

    def is_s3_server_path_exists(self, path: str = None,
                                 host: str = None,
                                 user: str = None,
                                 pwd: str = None) -> tuple:
        """
        Check if file exists on s3 server.

        :param path: Absolute path of the file.
        :param host: IP of the host.
        :param user: Username of the host.
        :param pwd: Password for the user.
        :return: bool, response.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, response = run_remote_cmd(
                f"stat {path}", host, user, pwd, read_lines=True)
            LOGGER.debug(response)
            LOGGER.info("Path exists: %s", path)

            return status, path
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.is_s3_server_path_exists.__name__,
                error)
            return False, error

    def get_s3server_fids(self, host: str = None,
                          user: str = None,
                          pwd: str = None) -> tuple:
        """
        Get fid's of all s3server processes.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: bool, response.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            status, output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            fids = []
            for line in output:
                if "s3server" in line:
                    LOGGER.info(line)
                    fid = "{}@{}".format(line.split()[2], line.split()[3])
                    fids.append(fid)
            LOGGER.info("Fids: %s", str(fids))

            return status, fids
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.get_s3server_fids.__name__,
                error)
            return False, error

    def copy_s3server_file(self, file_path: str = None,
                           local_path: str = None,
                           host: str = None,
                           user: str = None,
                           pwd: str = None) -> tuple:
        """
        copy file from s3 server to local path.

        :param file_path: Remote path.
        :param local_path: Local path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: True if file copied else False, error/path.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            hobj = Host(hostname=host, username=user, password=pwd)
            hobj.connect_pysftp()
            sftp = hobj.pysftp_obj
            LOGGER.info("sftp connected")
            sftp.get(file_path, local_path)
            LOGGER.info("file copied to : %s", str(local_path))
            sftp.close()
            hobj.disconnect()

            return os.path.isfile(local_path), local_path
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.copy_s3server_file.__name__,
                error)
            return False, error

    def is_string_in_s3server_file(self,
                                   string: str = None,
                                   file_path: str = None,
                                   **kwargs) -> tuple:
        """
        find given string in file present on s3 server.

        :param string: String to be check.
        :param file_path: file path.
        :keyword host: IP of the host.
        :keyword user: user name of the host.
        :keyword pwd: password for the user.
        :return: bool, response.
        """
        host = kwargs.get("host", self.host)
        user = kwargs.get("user", self.user)
        pwd = kwargs.get("password", self.pwd)
        local_path = os.path.join(os.getcwd(), 'temp_file')
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            self.copy_s3server_file(file_path, local_path, host, user, pwd)
            if string in open(local_path).read():
                LOGGER.info("Match '%s' found in : %s", string, file_path)
                return True, file_path

            num = 1
            while True:
                if os.path.exists(local_path):
                    os.remove(local_path)
                self.copy_s3server_file(
                    file_path + '.' + str(num), local_path, host, user, pwd)
                if string in open(local_path).read():
                    LOGGER.info(
                        "Match '%s' found in : %s",
                        string,
                        file_path + '.' + str(num))
                    return True, file_path
                num = num + 1
                if num > 6:
                    break
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.is_string_in_s3server_file.__name__,
                error)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        return False, file_path

    def enable_disable_s3server_instances(self,
                                          resource_disable: bool = True,
                                          wait_time: int = 10,
                                          **kwargs) -> tuple:
        """
        Enable or disable s3server instances using pcs command.

        :param resource_disable: True for disable and False for enable.
        :param wait_time: Wait time in sec after resource action.
        :keyword host: IP of the host.
        :keyword user: user name of the host.
        :keyword pwd: password for the user.
        :return: boolean and response/error.
        """
        try:
            host = kwargs.get("host", self.host)
            user = kwargs.get("user", self.user)
            pwd = kwargs.get("password", self.pwd)
            status, resources = self.get_s3server_resource()
            if not status:
                return status, resources
            for resource in resources:
                if resource_disable:
                    LOGGER.info("Disabling resource : %s", str(resource))
                    status, resp = run_remote_cmd(
                        commands.PCS_RESOURCE_DISABLE_CMD.format(resource),
                        host,
                        user,
                        pwd,
                        read_lines=True)
                    LOGGER.debug(resp)
                    time.sleep(wait_time)
                else:
                    LOGGER.info("Enabling resource : %s", resource)
                    status, resp = run_remote_cmd(
                        commands.PCS_RESOURCE_ENABLE_CMD.format(resource),
                        host,
                        user,
                        pwd,
                        read_lines=True)
                    LOGGER.debug(resp)
                    time.sleep(wait_time)
            LOGGER.info("Is motr online.")
            status, output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOGGER.debug(fail_list)
            for line in output:
                if resource_disable:
                    if "[started]" in line and "s3server" in line:
                        return False, output
                else:
                    if any(
                            fail_str in line for fail_str in fail_list) and "s3server" in line:
                        return False, output
            LOGGER.debug("s3server instances: %s", str(resources))

            return status, output
        except (SSHException, OSError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.enable_disable_s3server_instances.__name__,
                error)
            return False, error

    @staticmethod
    def configure_minio(access: str = None,
                        secret: str = None,
                        path: str = S3_CFG["minio_path"]) -> bool:
        """
        Function to configure minio creds in config.json file.

        :param access: aws access key.
        :param secret: aws secret key.
        :param path: path to minio cfg file.
        :return: True/False.
        """
        res = False
        if os.path.exists(path):
            data = config_utils.read_content_json(path)
            data["hosts"]["s3"]["accessKey"] = access
            data["hosts"]["s3"]["secretKey"] = secret
            res = config_utils.create_content_json(path=path, data=data)
        else:
            LOGGER.warning(
                "Minio is not installed please install and than run the configuration.")

        return os.path.isfile(path) and res

    @staticmethod
    def get_local_keys(
            path: str = S3_CFG["aws_path"],
            section: str = S3_CFG["aws_cred_section"]) -> tuple:
        """
        Get local s3 access and secret keys.

        :param path: credential file path.
        :param section: section name for the profile.
        :return: access_key, access_secret_key.
        """
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    "{} file is not present. Please configure aws in the system".format(path))
            access_key = config_utils.get_config(
                path, section, "aws_access_key_id")
            secret_key = config_utils.get_config(
                path, section, "aws_secret_access_key")

            return access_key, secret_key
        except (FileNotFoundError, KeyError, NoSectionError) as error:
            LOGGER.error(
                "An exception occurred in %s: %s",
                S3Helper.get_local_keys.__name__,
                str(error))
            return None, None

    def is_string_in_file(self,
                          string: str = None,
                          file_path: str = None,
                          **kwargs) -> tuple:
        """
        find given string in file present on s3 server.

        :param string: String to be check.
        :param file_path: file path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: bool, response..
        """
        host = kwargs.get("host", self.host)
        user = kwargs.get("user", self.user)
        pwd = kwargs.get("password", self.pwd)
        local_path = os.path.join(os.getcwd(), "temp_file")
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            response = self.copy_s3server_file(
                file_path, local_path, host, user, pwd)
            LOGGER.debug(response)
            data = open(local_path).read()
            match = re.search(string, data)
            if match:
                LOGGER.info("Match '%s' found in : %s", string, file_path)
                return True, file_path
        except (SSHException, OSError) as error:
            LOGGER.error(
                "An exception occurred in %s: %s",
                S3Helper.is_string_in_file.__name__,
                str(error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        return False, file_path

    def remote_execution(self, hostname, username, password, cmd):
        """running remote cmd."""
        LOGGER.info("Remote Execution")
        return run_remote_cmd(cmd, hostname, username, password)

    def is_mero_online(self, host, user, passwd):
        """
        Check whether all services are online in mero cluster
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return: bool , response
        """
        try:
            output = self.remote_execution(
                host, user, passwd, const.MERO_STATUS_CMD)
            LOGGER.info(output)
            fail_list = const.FAILED_LIST
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, output
            return True, output
        except BaseException as error:
            LOGGER.error("{} {}: {}".format(
                "Error in", S3Helper.is_mero_online.__name__,
                error))
            return False, error

    @staticmethod
    def run_cmd(cmd):
        """
        Execute any given command
        :param cmd: Command to execute on the node
        :return: response
        """
        LOGGER.info(cmd)
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        result = str(proc.communicate())
        LOGGER.debug("Output:{}".format(result))
        return result
