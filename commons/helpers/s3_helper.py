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

import os
import re
import time
import logging
import configparser

from commons import commands
from commons.helpers.host import Host
from commons.utils.system_utils import run_local_cmd, run_remote_cmd
from commons.utils.config_utils import read_yaml, update_config_ini, read_content_json, create_content_json
from typing import Any

CM_CFG = read_yaml("config/common_config.yaml")[1]
logger = logging.getLogger(__name__)


class S3Helper:
    __instance = None

    def __init__(self) -> None:
        """ Virtually private constructor. """
        if S3Helper.__instance:
            raise Exception("This class is a singleton!, use S3Helper.get_instance() to access existing object one.")
        else:
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
    def configure_s3cfg(access: str, secret: str, path: str = CM_CFG["s3cfg_path"]) -> bool:
        """
        Function to configure access and secret keys in s3cfg file.
        :param access: aws access key.
        :param secret: aws secret key.
        :param path: path to s3cfg file.
        :return: True if s3cmd configured else False.
        """
        res = False
        if run_local_cmd("s3cmd --version"):
            res1 = update_config_ini(path, "default", "access_key", access)
            res2 = update_config_ini(path, "default", "secret_key", secret)
            res = res1 and res2
        else:
            logger.warning("S3cmd is not present, please install it and than run the configuration.")

        return res

    @staticmethod
    def configure_s3fs(access: str, secret: str, path: str = CM_CFG["s3fs_path"]) -> bool:
        """
        Function to configure access and secret keys for s3fs.
        :param access: aws access key.
        :param secret: aws secret key.
        :param path: s3fs config file.
        :return: True if s3fs configured else False.
        """
        res = False
        if run_local_cmd("s3fs --version") and os.path.exists(path):
            with open(path, "w+") as fd:
                fd.write(f"{access}:{secret}")
            res = True
        else:
            logger.warning("S3fs is not present, please install it and than run the configuration.")

        return res

    def check_s3services_online(self,
                                host: str = CM_CFG["host"],
                                user: str = CM_CFG["username"],
                                pwd: str = CM_CFG["password"]
                                ) -> bool:
        """
        Check whether all s3server services are online.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: False if no s3server services found or are not Online else True.
        """
        try:
            output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd, read_lines=True)
            s3services = []
            for line in output:
                if "s3server" in line:
                    s3services.append(line.strip())
            if not s3services:
                logging.critical("No s3server service found!")
                return False
            for service in s3services:
                if not service.startswith("[started]"):
                    logging.error("S3 service down: %s", s3services)
                    return False

            return True
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.check_s3services_online.__name__, error))
            return False

    def get_s3server_service_status(self,
                                    service: str,
                                    host: str = CM_CFG["host"],
                                    user: str = CM_CFG["username"],
                                    pwd: str = CM_CFG["password"]
                                    ) -> bool:
        """
        Execute command to get status any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_STATUS_CMD.format(service), host, user, pwd, read_lines=True)
        result_ = ''.join(result)
        element = result_.split()
        logging.debug(element)
        if 'active' in element:
            return True

        return False

    def start_s3server_service(self,
                               service: str,
                               host: str = CM_CFG["host"],
                               user: str = CM_CFG["username"],
                               pwd: str = CM_CFG["password"]
                               ) -> Any:
        """
        Execute command to start any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_START_CMD.format(service), host, user, pwd, read_lines=True)
        logging.debug(result)
        status = self.get_s3server_service_status(service, host, user, pwd)
        if status:
            return True

        return False

    def stop_s3server_service(self,
                              service: str,
                              host: str = CM_CFG["host"],
                              user: str = CM_CFG["username"],
                              pwd: str = CM_CFG["password"]
                              ) -> Any:
        """
        Execute command to stop any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_STOP_CMD.format(service), host, user, pwd, read_lines=True)
        logging.debug(result)
        status = self.get_s3server_service_status(service, host, user, pwd)
        if not status:
            return True

        return False

    def restart_s3server_service(self,
                                 service: str,
                                 host: str = CM_CFG["host"],
                                 user: str = CM_CFG["username"],
                                 pwd: str = CM_CFG["password"]
                                 ) -> Any:
        """
        Execute command to restart any system service at remote s3 server.
        :param service: Name of the service.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        result = run_remote_cmd(commands.SYSTEM_CTL_RESTART_CMD.format(service), host, user, pwd, read_lines=True)
        logging.debug(result)
        status = self.get_s3server_service_status(service, host, user, pwd)
        if status:
            return True

        return False

    def restart_s3server_processes(self,
                                   host: str = CM_CFG["host"],
                                   user: str = CM_CFG["username"],
                                   pwd: str = CM_CFG["password"],
                                   wait_time: int = 30
                                   ) -> bool:
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
            logging.debug(fids)
            for pid in fids:
                logger.info("Restarting fid : {}".format(pid))
                response = run_remote_cmd(commands.SYSTEM_CTL_RESTART_CMD.format(pid), host, user, pwd, read_lines=True)
                logging.debug(response)
                time.sleep(wait_time)
            logger.info("Is motr online.")
            output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd, read_lines=True)
            logging.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            logging.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False

            return True
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.restart_s3server_processes.__name__, error))
            return False

    def get_s3server_resource(self,
                              host: str = CM_CFG["host"],
                              user: str = CM_CFG["username"],
                              pwd: str = CM_CFG["password"]
                              ) -> list:
        """
        Get resources of all s3server instances using pcs command.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response, list of s3 resources.
        """
        output = run_remote_cmd(commands.PCS_RESOURCE_SHOW_CMD, host, user, pwd, read_lines=True)
        logger.info(f"Response: {output}")
        s3_rcs = []
        for line in output:
            if "s3server-c" in line:
                logger.info(line)
                fid = line.split()[0]
                s3_rcs.append(fid)
        logging.debug(s3_rcs)

        return s3_rcs

    def restart_s3server_resources(self,
                                   host: str = CM_CFG["host"],
                                   user: str = CM_CFG["username"],
                                   pwd: str = CM_CFG["password"],
                                   wait_time: int = 30
                                   ) -> bool:
        """
        Restart all s3server resources using pcs command.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after restart.
        :return: True if services restarted else False.
        """
        try:
            rcs = self.get_s3server_resource(host=host, user=user, pwd=pwd)
            for rc in rcs:
                logger.info("Restarting resource : {}".format(rc))
                response = run_remote_cmd(commands.PCS_RESOURCE_RESTART_CMD.format(rc), host, user, pwd,
                                          read_lines=True)
                logging.debug(response)
                time.sleep(wait_time)
            logger.info("Is motr online.")
            output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd, read_lines=True)
            logging.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            logging.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False

            return True
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.restart_s3server_resources.__name__, error))
            return False

    def is_s3_server_path_exists(self,
                                 path: str,
                                 host: str = CM_CFG["host"],
                                 user: str = CM_CFG["username"],
                                 pwd: str = CM_CFG["password"]
                                 ) -> bool:
        """
        Check if file exists on s3 server
        :param path: Absolute path of the file
        :param host: IP of the host
        :param user: Username of the host
        :param pwd: Password for the user
        :return: bool, response
        """
        try:
            try:
                response = run_remote_cmd(f"stat {path}", host, user, pwd, read_lines=True)
                logging.debug(response)
                logging.info("Path exists: %s", path)
            except IOError as err:
                if err[0] == 2:
                    raise IOError(err)

            return True
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.is_s3_server_path_exists.__name__, error))
            return False

    def get_s3server_fids(self,
                          host: str = CM_CFG["host"],
                          user: str = CM_CFG["username"],
                          pwd: str = CM_CFG["password"]
                          ) -> list:
        """
        Get fid's of all s3server processes.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: response.
        """
        output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd, read_lines=True)
        fids = []
        for line in output:
            if "s3server" in line:
                logger.info(line)
                fid = "{}@{}".format(line.split()[2], line.split()[3])
                fids.append(fid)
        logger.info(f"Fids: {fids}")

        return fids

    def copy_s3server_file(self,
                           file_path: str,
                           local_path: str,
                           host: str = CM_CFG["host"],
                           user: str = CM_CFG["username"],
                           pwd: str = CM_CFG["password"]
                           ) -> bool:
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
            sftp = hobj.pysftp_obj.open_sftp()
            logger.info("sftp connected")
            sftp.get(file_path, local_path)
            logger.info("file copied to : {}".format(local_path))
            sftp.close()
            hobj.disconnect()

            return os.path.isfile(local_path)
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.copy_s3server_file.__name__, error))
            return False

    def is_string_in_s3server_file(self,
                                   string: str,
                                   file_path: str,
                                   host: str = CM_CFG["host"],
                                   user: str = CM_CFG["username"],
                                   pwd: str = CM_CFG["password"]
                                   ) -> bool:
        """
        find given string in file present on s3 server.
        :param string: String to be check.
        :param file_path: file path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: Boolean.
        """
        local_path = os.path.join(os.getcwd(), 'temp_file')
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            self.copy_s3server_file(file_path, local_path, host, user, pwd)
            if string in open(local_path).read():
                logger.info("Match '{}' found in : {}".format(string, file_path))
                return True
            num = 1
            while True:
                if os.path.exists(local_path):
                    os.remove(local_path)
                self.copy_s3server_file(file_path + '.' + str(num), local_path, host, user, pwd)
                if string in open(local_path).read():
                    logger.info("Match '{}' found in : {}".format(string, file_path + '.' + str(num)))
                    return True
                num = num + 1
                if num > 6:
                    break
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.is_string_in_s3server_file.__name__, error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        return False

    def enable_disable_s3server_instances(self,
                                          resource_disable: bool = True,
                                          host: str = CM_CFG["host"],
                                          user: str = CM_CFG["username"],
                                          pwd: str = CM_CFG["password"],
                                          wait_time: int = 1
                                          ) -> bool:
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
            rcs = self.get_s3server_resource()
            for rc in rcs:
                if resource_disable:
                    logger.info("Disabling resource : {}".format(rc))
                    resp = run_remote_cmd(commands.PCS_RESOURCE_DISABLE_CMD.format(rc), host, user, pwd,
                                          read_lines=True)
                    logging.debug(resp)
                    time.sleep(wait_time)
                else:
                    logger.info("Enabling resource : {}".format(rc))
                    resp = run_remote_cmd(commands.PCS_RESOURCE_ENABLE_CMD.format(rc), host, user, pwd, read_lines=True)
                    logging.debug(resp)
                    time.sleep(wait_time)
            logger.info("Is motr online.")
            output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd, read_lines=True)
            logging.debug(output)
            fail_list = ['failed', 'not running', 'offline']
            logging.debug(fail_list)
            for line in output:
                if any(fail_str in line for fail_str in fail_list):
                    return False
            logging.debug("s3server instances: {}".format(rcs))

            return True
        except BaseException as error:
            logger.error("{} {}: {}".format("Error in", S3Helper.enable_disable_s3server_instances.__name__, error))
            return False

    def configure_minio(self, access: str, secret: str, path: str = CM_CFG["minio_path"]) -> bool:
        """
        Function to configure minio creds in config.json file.
        :param access: aws access key.
        :param secret: aws secret key.
        :param path: path to minio cfg file.
        :return: True/False.
        """
        res = False
        if os.path.exists(path):
            data = read_content_json(path)
            data["hosts"]["s3"]["accessKey"] = access
            data["hosts"]["s3"]["secretKey"] = secret
            res = create_content_json(path=path, data=data)
            res = True if os.path.isfile(res) else False
        else:
            logger.warning("Minio is not installed please install and than run the configuration.")

        return res

    @staticmethod
    def get_local_keys(path: str = CM_CFG["aws_path"], section: str = CM_CFG["aws_cred_section"]) -> tuple:
        """
        Get local s3 access and secret keys.
        :param path: credential file path.
        :param section: section name for the profile.
        :return:
        """
        if not os.path.isfile(path):
            raise "{} file is not present. Please configure aws in the system".format(path)
        config = configparser.ConfigParser()
        config.read(path)
        access_key = config[section]["aws_access_key_id"]
        secret_key = config[section]["aws_secret_access_key"]
        logger.info(f"Section {section}: fetched access key: {access_key} and secret key: {secret_key}.")

        return access_key, secret_key

    def is_string_in_file(self, string: str,
                          file_path: str,
                          host: str = CM_CFG["host"],
                          user: str = CM_CFG["username"],
                          pwd: str = CM_CFG["password"]
                          ) -> bool:
        """
        find given string in file present on s3 server.
        :param string: String to be check.
        :param file_path: file path.
        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: Boolean.
        """
        local_path = os.path.join(os.getcwd(), "temp_file")
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
            response = self.copy_s3server_file(file_path, local_path, host, user, pwd)
            logging.debug(response)
            data = open(local_path).read()
            match = re.search(string, data)
            if match:
                logger.info("Match '{}' found in : {}".format(string, file_path))
                return True
        except BaseException as error:
            logger.error("An exception occurred in ".format(S3Helper.is_string_in_file.__name__, error))
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

        return False
