#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
s3 helper to have s3 services related classes & methods.

Note: S3 helper is singleton so please import its object from libs.s3 __init__
as 'from libs.s3 import S3H_OBJ'.
"""

import logging
import os
import time
from configparser import NoSectionError
from paramiko.ssh_exception import SSHException

from commons import commands
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import config_utils
from commons.utils.system_utils import run_remote_cmd


LOGGER = logging.getLogger(__name__)


class S3Helper:
    """S3 Helper class to perform S3 related operations."""

    __instance = None

    def __init__(self, cmn_cfg, s3_cfg) -> None:
        """Virtually private constructor."""
        if S3Helper.__instance:
            raise ImportError(
                "S3Helper is a singleton!, use S3Helper.get_instance() to access existing object.")
        S3Helper.__instance = self
        self.cmn_cfg = cmn_cfg
        self.s3_cfg = s3_cfg
        cm_cfg = self.cmn_cfg.get("nodes", None)
        self.host = cm_cfg[0]["hostname"] if cm_cfg else None
        self.pwd = cm_cfg[0]["password"] if cm_cfg else None
        self.user = cm_cfg[0]["username"] if cm_cfg else None

    @staticmethod
    def get_instance(cmn_cfg, s3_cfg) -> object:
        """
        Static method to access singleton instance.

        :return: S3Helper object.
        """
        if not S3Helper.__instance:
            S3Helper(cmn_cfg, s3_cfg)
        return S3Helper.__instance

    def check_s3services_online(self, host: str = None,
                                user: str = None,
                                pwd: str = None) -> tuple:
        """
        Check whether all s3server services are online using hctl status.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: False if no s3server services found or are not Online else True
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        response = False, "Failed to check s3 service online."
        try:
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd,
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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                health = Health(hostname=host, username=user, password=pwd)
                response = health.hctl_status_service_status(service_name="s3server")

            return response
        except (SSHException, OSError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.check_s3services_online.__name__, str(error))
            return False, error

    def get_s3server_service_status(self, service: str = None,
                                    host: str = None,
                                    user: str = None,
                                    pwd: str = None) -> tuple:
        """
        Execute command to get status any system service at remote s3 server using systemctl status.

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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, result = run_remote_cmd(commands.SYSTEM_CTL_STATUS_CMD.format(service),
                                                host, user, pwd, read_lines=True)
                if not status:
                    return status, result
                result_ = ''.join(result)
                element = result_.split()
                LOGGER.debug(element)
                if 'active' in element:
                    return True, result_

                return status, result_
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to get s3server service status."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.get_s3server_service_status.__name__,
                         str(error))
            return False, error

    def start_s3server_service(self,
                               service: str = None,
                               host: str = None,
                               user: str = None,
                               pwd: str = None) -> tuple:
        """
        Execute command to start any system service at remote s3 server using systemctl command.

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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, result = run_remote_cmd(
                    commands.SYSTEM_CTL_START_CMD.format(service), host, user,
                    pwd, read_lines=True)
                LOGGER.debug(result)
                if not status:
                    return status, result
                time.sleep(10)
                response = self.get_s3server_service_status(
                    service, host, user, pwd)

                return response
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to start s3server service."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.start_s3server_service.__name__, str(error))
            return False, error

    def stop_s3server_service(self,
                              service: str = None,
                              host: str = None,
                              user: str = None,
                              pwd: str = None) -> tuple:
        """
        Execute command to stop any system service at remote s3 server using systemctl command.

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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, result = run_remote_cmd(
                    commands.SYSTEM_CTL_STOP_CMD.format(service), host, user, pwd, read_lines=True)
                LOGGER.debug(result)
                time.sleep(10)
                status, resp = self.get_s3server_service_status(service, host, user, pwd)
                # True if service successfully stopped.
                status = bool('inactive' in str(resp))
                return status, resp
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to stop s3server service."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.stop_s3server_service.__name__, error)
            return False, error

    def restart_s3server_service(self,
                                 service: str = None,
                                 host: str = None,
                                 user: str = None,
                                 pwd: str = None) -> tuple:
        """
        Execute command to restart any system service at remote s3 server using systemctl command.

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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, result = run_remote_cmd(
                    commands.SYSTEM_CTL_RESTART_CMD.format(service), host, user,
                    pwd, read_lines=True)
                LOGGER.debug(result)
                if not status:
                    return status, result
                time.sleep(10)
                response = self.get_s3server_service_status(service, host, user, pwd)
                return response
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to restart s3server service."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.restart_s3server_service.__name__, error)
            return False, error

    def restart_s3server_processes(self,
                                   host: str = None,
                                   user: str = None,
                                   pwd: str = None,
                                   wait_time: int = 20) -> tuple:
        """
        Restart all s3server processes using systemctl restart command.

        :param host: IP of the host.
        :param user: username of the host.
        :param pwd: password for the user.
        :param wait_time: Wait time in sec after restart.
        :return: True if s3server process restarted else False.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, fids = self.get_s3server_fids()
                LOGGER.debug(fids)
                if not status:
                    return status, fids
                for pid in fids:
                    LOGGER.info("Restarting fid : %s", str(pid))
                    status, response = run_remote_cmd(
                        commands.SYSTEM_CTL_RESTART_CMD.format(pid), host, user,
                        pwd, read_lines=True)
                    LOGGER.debug(response)
                    time.sleep(wait_time)
                LOGGER.info("Is motr online.")
                status, output = run_remote_cmd(commands.MOTR_STATUS_CMD, host, user, pwd,
                                                read_lines=True)
                LOGGER.debug(output)
                fail_list = ['failed', 'not running', 'offline']
                LOGGER.debug(fail_list)
                for line in output:
                    if any(
                            fail_str in line for fail_str in fail_list) and "s3server" in line:
                        return False, output
                return status, output
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to restart s3server processes."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.restart_s3server_processes.__name__, error)
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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, output = run_remote_cmd(commands.PCS_RESOURCE_SHOW_CMD, host, user, pwd,
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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to get s3server resources."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.get_s3server_resource.__name__, error)
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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, resources = self.get_s3server_resource(host=host, user=user, pwd=pwd)
                if not status:
                    return status, resources
                for resource in resources:
                    LOGGER.info("Restarting resource : %s", str(resource))
                    status, response = run_remote_cmd(
                        commands.PCS_RESOURCE_RESTART_CMD.format(resource),
                        host, user, pwd, read_lines=True)
                    LOGGER.debug(response)
                    time.sleep(wait_time)
                LOGGER.info("Is motr online.")
                status, output = run_remote_cmd(commands.MOTR_STATUS_CMD, host,
                                                user, pwd, read_lines=True)
                LOGGER.debug(output)
                fail_list = ['failed', 'not running', 'offline']
                LOGGER.debug(fail_list)
                for line in output:
                    if any(
                            fail_str in line for fail_str in fail_list) and "s3server" in line:
                        return False, output

                return status, output
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to restart all s3server resources using pcs command."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.restart_s3server_resources.__name__, error)
            return False, error

    def get_s3server_fids(self, host: str = None,
                          user: str = None,
                          pwd: str = None) -> tuple:
        """
        Get fid's of all s3server processes using hctl command.

        :param host: IP of the host.
        :param user: user name of the host.
        :param pwd: password for the user.
        :return: bool, response.
        """
        host = host if host else self.host
        user = user if user else self.user
        pwd = pwd if pwd else self.pwd
        try:
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, output = run_remote_cmd(commands.MOTR_STATUS_CMD, host,
                                                user, pwd, read_lines=True)
                fids = []
                for line in output:
                    if "s3server" in line:
                        LOGGER.info(line.split())
                        fid = f"{line.split()[1]}@{line.split()[2]}"
                        fids.append(fid)
                LOGGER.info("Fids: %s", str(fids))
                return status, fids
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                health = Health(hostname=host, username=user, password=pwd)
                status, fids = health.hctl_status_get_svc_fids()
                if status:
                    return True, fids['rgw_s3']

            return False, "Failed to get s3server fids"
        except (SSHException, OSError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.get_s3server_fids.__name__, error)
            return False, error

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
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                    self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
                status, resources = self.get_s3server_resource()
                if not status:
                    return status, resources
                for resource in resources:
                    if resource_disable:
                        LOGGER.info("Disabling resource : %s", str(resource))
                        status, resp = run_remote_cmd(
                            commands.PCS_RESOURCE_DISABLE_CMD.format(resource),
                            host, user, pwd, read_lines=True)
                        LOGGER.debug(resp)
                        time.sleep(wait_time)
                    else:
                        LOGGER.info("Enabling resource : %s", resource)
                        status, resp = run_remote_cmd(
                            commands.PCS_RESOURCE_ENABLE_CMD.format(resource),
                            host, user, pwd, read_lines=True)
                        LOGGER.debug(resp)
                        time.sleep(wait_time)
                LOGGER.info("Is motr online.")
                status, output = run_remote_cmd(commands.MOTR_STATUS_CMD, host,
                                                user, pwd, read_lines=True)
                LOGGER.debug(output)
                fail_list = ['failed', 'not running', 'offline']
                LOGGER.debug(fail_list)
                for line in output:
                    if resource_disable:
                        if "[started]" in line and "s3server" in line:
                            return False, output
                    else:
                        if any(
                                fail_str in line for fail_str in fail_list) \
                                and "s3server" in line:
                            return False, output

                LOGGER.debug("s3server instances: %s", str(resources))

                return status, output
            if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
                LOGGER.critical("Product family: LC")
                # TODO: Add LC related calls
                raise NotImplementedError("TODO: Add LC related calls")

            return False, "Failed to enable/disable s3server instances."
        except (SSHException, OSError, NotImplementedError) as error:
            LOGGER.error("Error in %s: %s", S3Helper.enable_disable_s3server_instances.__name__,
                         error)
            return False, error

    def get_local_keys(
            self,
            path: str = None,
            section: str = None) -> tuple:
        """
        Get local s3 access and secret keys.

        :param path: credential file path.
        :param section: section name for the profile.
        :return: access_key, access_secret_key.
        """
        path = path if path else self.s3_cfg["aws_path"]
        section = section if section else self.s3_cfg["aws_cred_section"]
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"{path} file is not present. Please "
                                        "configure aws in the system if you are"
                                        " running s3 test")
            access_key = config_utils.get_config(path, section, "aws_access_key_id")
            secret_key = config_utils.get_config(path, section, "aws_secret_access_key")

            return access_key, secret_key
        except (FileNotFoundError, KeyError, NoSectionError) as error:
            LOGGER.warning(
                "%s: %s", S3Helper.get_local_keys.__name__, str(error))
            return None, None

    def s3server_inject_faulttolerance(self, enable=False, **kwargs) -> tuple:
        """
        Inject(enable/disable) fault tolerance in s3server.

        TODO: Code will be revised based on F-24A feature availability.
        # :param host: IP of the host.
        # :param user: user name of the host.
        # :param password: password for the user.
        :param enable: enable or disable fault to s3server.
        :return: bool, response.
        """
        host = kwargs.get("host", self.host)
        user = kwargs.get("user", self.user)
        password = kwargs.get("password", self.pwd)
        error = "Failed to inject fault tolerance in s3server."
        if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == const.PROD_TYPE_NODE:
            command = commands.UPDATE_FAULTTOLERANCE.format("enable" if enable else "disable")
            status, response = run_remote_cmd(cmd=command, hostname=host,
                                              username=user, password=password)
            status = True if "200" in response else status
            return status, response
        if self.cmn_cfg["product_family"] == const.PROD_FAMILY_LC:
            LOGGER.critical("Product family: LC")
            # TODO: Add LC related calls
            error = "TODO: Add LC related calls"

        return False, error

    @staticmethod
    def verify_and_validate_created_object_fragement(object_name) -> tuple:
        """
        Verify in m0kv output.

        TODO: Code will be revised based on F-24A feature availability.
        Verify the Validate that object list index contains extended entries using m0kv.
        Verify in m0kv output. Main object size and fragment size.
        No of fragments in json value of main object.
        :return: bool, response
        """
        LOGGER.info(object_name)
        return False, "Not implemented: F-24A feature under development."

    def update_s3config(self,
                        section="S3_SERVER_CONFIG",
                        parameter=None,
                        value=None,
                        **kwargs) -> tuple:
        """
        Reset parameter to value in s3config.yaml and return (parameter, value, old_value).

        # :param host: IP of the host.
        # :param user: user name of the host.
        # :param password: password for the user.
        :param parameter: s3 parameters to be updated.
        :param value: s3 parameter value.
        :param section: s3config section.
        # :param backup_path: backup_path.
        :return: True/False, response.
        """
        host = kwargs.get("host", self.host)
        user = kwargs.get("username", self.user)
        pwd = kwargs.get("password", self.pwd)
        backup_path = kwargs.get("backup_path", const.LOCAL_S3_CONFIG)
        nobj = Node(hostname=host, username=user, password=pwd)
        status, resp = nobj.copy_file_to_local(const.S3_CONFIG, backup_path)
        if not status:
            return status, resp
        status, resp = config_utils.read_yaml(backup_path)
        if not status:
            return status, resp
        LOGGER.info(resp)
        old_value = resp[section][parameter]
        LOGGER.info(old_value)
        resp[section][parameter] = value
        status, resp = config_utils.write_yaml(backup_path, resp, backup=True)
        if not status:
            return status, resp
        status, resp = nobj.copy_file_to_remote(backup_path, const.S3_CONFIG)
        if not status:
            return status, resp
        if os.path.exists(backup_path):
            os.remove(backup_path)
        nobj.disconnect()

        return status, (parameter, value, old_value)
