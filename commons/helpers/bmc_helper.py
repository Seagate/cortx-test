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
"""BMC helper library."""

import logging
from typing import Any

import commons.errorcodes as err
from commons import commands
from commons.exceptions import CTException
from commons.helpers.host import Host
from commons.utils import system_utils

LOGGER = logging.getLogger(__name__)


class Bmc(Host):
    """BMC helper class."""

    def __init__(self, hostname: str, username: str, password: str):
        super().__init__(hostname, username, password)
        if not system_utils.run_local_cmd(commands.CHECK_IPMITOOL)[0]:
            LOGGER.debug("Installing ipmitool")
            resp = system_utils.run_local_cmd(commands.INSTALL_IPMITOOL)
            if not resp[0]:
                raise CTException(
                    err.CLIENT_CMD_EXECUTION_FAILED, "Could not install "
                                                     "ipmitool on client")

        self.bmc_ip = self.get_bmc_ip()

    def bmc_node_power_status(
            self,
            bmc_user: str,
            bmc_pwd: str) -> Any:
        """
        Function to check node power states using BMC.

        :param bmc_user: Node BMC user name
        :param bmc_pwd: Node BMC user pwd
        :return: resp
        """
        cmd = f"ipmitool -I lanplus -H {self.bmc_ip} -U {bmc_user} " \
              f"-P {bmc_pwd} chassis power status"
        try:
            LOGGER.info("Executing cmd: %s", cmd)
            success, resp = system_utils.run_local_cmd(cmd)
            if not success:
                raise CTException(
                      err.CLIENT_CMD_EXECUTION_FAILED, "Could not get BMC power status")
            LOGGER.debug("Output: %s", str(resp))
        except BaseException as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Bmc.bmc_node_power_status.__name__,
                         error)
            raise error
        LOGGER.info("Successfully executed cmd: %s", cmd)

        return resp

    def bmc_node_power_on_off(
            self,
            bmc_user: str,
            bmc_pwd: str,
            status: str = "on") -> Any:
        """
        Function to on and off node power using BMC IP.

        :param bmc_user: Node BMC user name
        :param bmc_pwd: Node BMC user pwd
        :param status: Status of bmc
        :return: resp
        """
        cmd = f"ipmitool -I lanplus -H {self.bmc_ip} -U {bmc_user} -P " \
              f"{bmc_pwd} chassis power {status.lower()}"
        try:
            LOGGER.info("Executing cmd: %s", cmd)
            success, resp = system_utils.run_local_cmd(cmd)
            if not success:
                raise CTException(
                    err.CLIENT_CMD_EXECUTION_FAILED,
                    f"Could not execute BMC power {status} command")
            LOGGER.debug("Output: %s", str(resp))
        except BaseException as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Bmc.bmc_node_power_on_off.__name__,
                         error)
            raise error
        LOGGER.info("Successfully executed cmd %s", cmd)

        return resp

    def get_bmc_ip(self) -> str:
        """
        Execute 'ipmitool lan print' on node and return bmc ip.

        :return: bmc ip or none
        """
        bmc_ip = None
        try:
            cmd = "ipmitool lan print"
            LOGGER.info("Running command: %s", cmd)
            response = self.execute_cmd(cmd=cmd, read_lines=False,
                                        read_nbytes=8000)

            response = response.decode() if isinstance(response, bytes) else response
            LOGGER.debug(response)
            for res in response.split("\n"):
                if "IP Address" in res and "IP Address Source" not in res:
                    bmc_ip = res.split(":")[-1].strip()
                    break
            LOGGER.debug("BMC IP: %s", bmc_ip)
        except AttributeError as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Bmc.get_bmc_ip.__name__, error)
            raise error
        except BaseException as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Bmc.get_bmc_ip.__name__, error)
            raise error

        return bmc_ip

    def set_bmc_ip(self, bmc_ip: str) -> bool:
        """
        Execute 'ipmitool lan set 1 ipaddr {ip}' on node to change/set/update bmc ip.

        :param bmc_ip: any valid ip.
        :return: True if bmc ip changed else False.
        """
        try:
            LOGGER.info(
                "Update bmc ip on %s node and set to '%s'.", self.hostname,
                bmc_ip)
            cmd = "ipmitool lan set 1 ipaddr {}".format(bmc_ip)
            LOGGER.info("Running command %s", cmd)
            response = self.execute_cmd(cmd=cmd, read_nbytes=8000)
            up_bmc_ip = self.get_bmc_ip()
            LOGGER.debug("Updated bmc ip: %s", up_bmc_ip)
            flg = bool(
                "Setting LAN IP Address to {}".format(bmc_ip) in str(
                    response[1]))
            flg = bool(bmc_ip == up_bmc_ip and flg)

            return flg
        except Exception as error:
            LOGGER.error("*ERROR* An exception occurred in %s: %s",
                         Bmc.set_bmc_ip.__name__, error)
            raise error

    def create_bmc_ip_change_fault(self, bmc_ip: str) -> bool:
        """
        Create bmc ip change fault by updating non ping-able valid ip.

        :param bmc_ip: non ping-able valid ip.
        :return: True if bmc ip changed else False.
        """
        try:
            if not bmc_ip:
                raise ValueError(f"Invalid ip: {bmc_ip}")
            LOGGER.info("Create bmc ip change fault on  node.")
            return self.set_bmc_ip(bmc_ip)
        except Exception as error:
            LOGGER.error(
                "*ERROR* An exception occurred in %s: %s",
                Bmc.create_bmc_ip_change_fault.__name__,
                error)
            raise error

    def resolve_bmc_ip_change_fault(self, bmc_ip: str) -> bool:
        """
        Resolve bmc ip fault.

        :param bmc_ip: bmc ip.
        :return: True if bmc ip changed else False.
        """
        try:
            if not bmc_ip:
                raise Exception(f"Invalid ip: {bmc_ip}")
            LOGGER.info("Resolve bmc ip change fault on node.")
            return self.set_bmc_ip(bmc_ip)
        except Exception as error:
            LOGGER.error(
                "*ERROR* An exception occurred in %s: %s",
                Bmc.resolve_bmc_ip_change_fault.__name__,
                error)
            raise error
