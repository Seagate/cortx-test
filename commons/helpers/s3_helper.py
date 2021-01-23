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
import configparser

from paramiko.ssh_exception import SSHException
from commons import commands
from commons.helpers.host import Host
from commons.utils import config_utils
from commons.utils.system_utils import run_local_cmd, run_remote_cmd

CM_CFG = config_utils.read_yaml("config/common_config.yaml")[1]
LOGGER = logging.getLogger(__name__)


class S3Helper:

    """S3 Helper class to perform S3 related operations."""

    __instance = None

    def __init__(self) -> None:
        """Virtually private constructor."""
        if S3Helper.__instance:
            raise ImportError(
                "This class is a singleton!, "
                "use S3Helper.get_instance() to access existing object one.")
        S3Helper.__instance = self

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
            access: str,
            secret: str,
            path: str = CM_CFG["s3cfg_path"]) -> bool:
        """
        Function to configure access and secret keys in s3cfg file.
        :param access: aws access key.
        :param secret: aws secret key.
        :param path: path to s3cfg file.
        :return: True if s3cmd configured else False.
        """
        res = False
        if run_local_cmd("s3cmd --version"):
            res1 = config_utils.update_config_ini(
                path, "default", "access_key", access)
            res2 = config_utils.update_config_ini(
                path, "default", "secret_key", secret)
            res = res1 and res2
        else:
            LOGGER.warning(
                "S3cmd is not present, please install it and than run the configuration.")

        return res

    @staticmethod
    def configure_s3fs(
            access: str,
            secret: str,
            path: str = CM_CFG["s3fs_path"]) -> bool:
        """
        Function to configure access and secret keys for s3fs.
        :param access: aws access key.
        :param secret: aws secret key.
        :param path: s3fs config file.
        :return: True if s3fs configured else False.
        """
        res = False
        if run_local_cmd("s3fs --version") and os.path.exists(path):
            with open(path, "w+") as f_write:
                f_write.write(f"{access}:{secret}")
            res = True
        else:
            LOGGER.warning(
                "S3fs is not present, please install it and than run the configuration.")

        return res

    @staticmethod
    def check_s3services_online(host: str = CM_CFG["host"],
                                user: str = CM_CFG["username"],
                                pwd: str = CM_CFG["password"]) -> tuple:
        """
        Check whether all s3server services are online.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: False if no s3server services found or are not Online else True.
        """
        try:
            output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            s3services = []
            for line in output:
                if "s3server" in line:
                    s3services.append(line.strip())
            if not s3services:
                LOGGER.critical("No s3server service found!")
                return False
            for service in s3services:
                if not service.startswith("[started]"):
                    LOGGER.error("S3 service down: %s", s3services)
                    return False, service

            return True, output
        except (SSHException, IOError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.check_s3services_online.__name__,
                str(error))
            return False, error

    @staticmethod
    def get_s3server_service_status(service: str,
                                    host: str = CM_CFG["host"],
                                    user: str = CM_CFG["username"],
                                    pwd: str = CM_CFG["password"]) -> tuple:
        """
        Execute command to get status any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_STATUS_CMD.format(
            service), host, user, pwd, read_lines=True)
        result_ = ''.join(result)
        element = result_.split()
        LOGGER.debug(element)
        if 'active' in element:
            return True, result_

        return False, result_

    def start_s3server_service(self,
                               service: str,
                               host: str = CM_CFG["host"],
                               user: str = CM_CFG["username"],
                               pwd: str = CM_CFG["password"]
                               ) -> tuple:
        """
        Execute command to start any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_START_CMD.format(
            service), host, user, pwd, read_lines=True)
        LOGGER.debug(result)
        status = self.get_s3server_service_status(service, host, user, pwd)

        return status

    def stop_s3server_service(self,
                              service: str,
                              host: str = CM_CFG["host"],
                              user: str = CM_CFG["username"],
                              pwd: str = CM_CFG["password"]
                              ) -> tuple:
        """
        Execute command to stop any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_STOP_CMD.format(
            service), host, user, pwd, read_lines=True)
        LOGGER.debug(result)
        status = self.get_s3server_service_status(service, host, user, pwd)

        return status

    def restart_s3server_service(self,
                                 service: str,
                                 host: str = CM_CFG["host"],
                                 user: str = CM_CFG["username"],
                                 pwd: str = CM_CFG["password"]
                                 ) -> tuple:
        """
        Execute command to restart any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        result = run_remote_cmd(
            commands.SYSTEM_CTL_RESTART_CMD.format(service),
            host,
            user,
            pwd,
            read_lines=True)
        LOGGER.debug(result)
        status = self.get_s3server_service_status(service, host, user, pwd)

        return status

    def restart_s3server_processes(self,
                                   host: str = CM_CFG["host"],
                                   user: str = CM_CFG["username"],
                                   pwd: str = CM_CFG["password"],
                                   wait_time: int = 30
                                   ) -> tuple:
        """
        Restart all s3server processes using hctl command.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after restart.
        :return: True if s3server process restarted else False.
        """
        try:
            fids = self.get_s3server_fids()
            LOGGER.debug(fids)
            for pid in fids:
                LOGGER.info("Restarting fid : %s", str(pid))
                response = run_remote_cmd(
                    commands.SYSTEM_CTL_RESTART_CMD.format(pid),
                    host,
                    user,
                    pwd,
                    read_lines=True)
                LOGGER.debug(response)
                time.sleep(wait_time)
            LOGGER.info("Is motr online.")
            output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOGGER.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, line

            return True, output
        except (SSHException, IOError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.restart_s3server_processes.__name__,
                error)
            return False, error

    @staticmethod
    def get_s3server_resource(host: str = CM_CFG["host"],
                              user: str = CM_CFG["username"],
                              pwd: str = CM_CFG["password"]) -> list:
        """
        Get resources of all s3server instances using pcs command.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response, list of s3 resources.
        """
        output = run_remote_cmd(
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

        return s3_rcs

    def restart_s3server_resources(self,
                                   host: str = CM_CFG["host"],
                                   user: str = CM_CFG["username"],
                                   pwd: str = CM_CFG["password"],
                                   wait_time: int = 30
                                   ) -> tuple:
        """
        Restart all s3server resources using pcs command.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after restart.
        :return: True if services restarted else False.
        """
        try:
            resources = self.get_s3server_resource(
                host=host, user=user, pwd=pwd)
            for resource in resources:
                LOGGER.info("Restarting resource : %s", str(resource))
                response = run_remote_cmd(
                    commands.PCS_RESOURCE_RESTART_CMD.format(resource),
                    host,
                    user,
                    pwd,
                    read_lines=True)
                LOGGER.debug(response)
                time.sleep(wait_time)
            LOGGER.info("Is motr online.")
            output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOGGER.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, line

            return True, output
        except (SSHException, IOError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.restart_s3server_resources.__name__,
                error)
            return False, error

    @staticmethod
    def is_s3_server_path_exists(path: str,
                                 host: str = CM_CFG["host"],
                                 user: str = CM_CFG["username"],
                                 pwd: str = CM_CFG["password"]) -> tuple:
        """
        Check if file exists on s3 server
        :param path: Absolute path of the file
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :return: bool, response
        """
        try:
            response = run_remote_cmd(
                f"stat {path}", host, user, pwd, read_lines=True)
            LOGGER.debug(response)
            LOGGER.info("Path exists: %s", path)

            return True, path
        except (SSHException, IOError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.is_s3_server_path_exists.__name__,
                error)
            return False, error

    @staticmethod
    def get_s3server_fids(host: str = CM_CFG["host"],
                          user: str = CM_CFG["username"],
                          pwd: str = CM_CFG["password"]) -> list:
        """
        Get fid's of all s3server processes.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        output = run_remote_cmd(
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

        return fids

    @staticmethod
    def copy_s3server_file(file_path: str,
                           local_path: str,
                           host: str = CM_CFG["host"],
                           user: str = CM_CFG["username"],
                           pwd: str = CM_CFG["password"]) -> tuple:
        """
        copy file from s3 server to local path.
        :param file_path: Remote path.
        :param local_path: Local path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: True if file copied else False.
        """
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
        except (SSHException, IOError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.copy_s3server_file.__name__,
                error)
            return False, error

    def is_string_in_s3server_file(self,
                                   string: str,
                                   file_path: str,
                                   **kwargs
                                   ) -> tuple:
        """
        find given string in file present on s3 server.
        :param string: String to be check.
        :param file_path: file path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: Boolean.
        """
        host = kwargs.get("host") if kwargs.get("host", None) else CM_CFG["host"]
        user = kwargs.get("user") if kwargs.get("user", None) else CM_CFG["username"]
        pwd = kwargs.get("password") if kwargs.get("password", None) else CM_CFG["password"]
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
        except (SSHException, IOError) as error:
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
                                          **kwargs
                                          ) -> tuple:
        """
        Enable or disable s3server instances using pcs command.
        :param resource_disable: True for disable and False for enable.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after resource action.
        :return: tuple with boolean and response/error.
        """
        try:
            host = kwargs.get("host") if kwargs.get("host", None) else CM_CFG["host"]
            user = kwargs.get("user") if kwargs.get("user", None) else CM_CFG["username"]
            pwd = kwargs.get("password") if kwargs.get("password", None) else CM_CFG["password"]
            resources = self.get_s3server_resource()
            for resource in resources:
                if resource_disable:
                    LOGGER.info("Disabling resource : %s", str(resource))
                    resp = run_remote_cmd(
                        commands.PCS_RESOURCE_DISABLE_CMD.format(resource),
                        host,
                        user,
                        pwd,
                        read_lines=True)
                    LOGGER.debug(resp)
                    time.sleep(wait_time)
                else:
                    LOGGER.info("Enabling resource : %s", resource)
                    resp = run_remote_cmd(
                        commands.PCS_RESOURCE_ENABLE_CMD.format(resource),
                        host,
                        user,
                        pwd,
                        read_lines=True)
                    LOGGER.debug(resp)
                    time.sleep(wait_time)
            LOGGER.info("Is motr online.")
            output = run_remote_cmd(
                commands.MOTR_STATUS_CMD,
                host,
                user,
                pwd,
                read_lines=True)
            LOGGER.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            LOGGER.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False, line
            LOGGER.debug("s3server instances: %s", str(resources))

            return True, output
        except (SSHException, IOError) as error:
            LOGGER.error(
                "Error in %s: %s",
                S3Helper.enable_disable_s3server_instances.__name__,
                error)
            return False, error

    @staticmethod
    def configure_minio(access: str,
                        secret: str,
                        path: str = CM_CFG["minio_path"]) -> bool:
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

        return os.path.isfile(res)

    @staticmethod
    def get_local_keys(
            path: str = CM_CFG["aws_path"],
            section: str = CM_CFG["aws_cred_section"]) -> tuple:
        """
        Get local s3 access and secret keys.
        :param path: credential file path.
        :param section: section name for the profile.
        :return:
        """
        if not os.path.isfile(path):
            raise "{} file is not present. Please configure aws in the system".format(
                path)
        config = configparser.ConfigParser()
        config.read(path)
        access_key = config[section]["aws_access_key_id"]
        secret_key = config[section]["aws_secret_access_key"]
        LOGGER.info("Section %s: fetched access key:%s and secret key: %s.",
                    section, access_key, secret_key)

        return access_key, secret_key

    def is_string_in_file(self,
                          string: str,
                          file_path: str,
                          **kwargs
                          ) -> tuple:
        """
        find given string in file present on s3 server.
        :param string: String to be check.
        :param file_path: file path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: Boolean.
        """
        host = kwargs.get("host") if kwargs.get("host", None) else CM_CFG["host"]
        user = kwargs.get("user") if kwargs.get("user", None) else CM_CFG["username"]
        pwd = kwargs.get("password") if kwargs.get("password", None) else CM_CFG["password"]
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
        except (SSHException, IOError) as error:
            LOGGER.error(
                "An exception occurred in %s: %s",
                S3Helper.is_string_in_file.__name__,
                str(error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        return False, file_path
