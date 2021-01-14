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

import logging
from commons.helpers.host import Host

logger = logging.getLogger(__name__)
EXCEPTION_MSG = "*ERROR* An exception occurred in {}: {}"


class Bmc(Host):

    def bmc_node_power_status(
            self,
            bmc_ip: str,
            bmc_user: str,
            bmc_pwd: str) -> str:
        """
        Function to check node power states using BMC
        :param bmc_ip: Node BMC IP
        :param bmc_user: Node BMC user name
        :param bmc_pwd: Node BMC user pwd
        :return: resp
        """
        if not self.execute_cmd("rpm  -qa | grep ipmitool")[0]:
            logger.debug("Installing ipmitool")
            self.execute_cmd("yum install ipmitool")
        try:
            cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pwd} chassis power status"
            if not cmd:
                return "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                EXCEPTION_MSG.format(
                    Bmc.bmc_node_power_status.__name__,
                    error))
            raise error
        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def bmc_node_power_on_off(
            self,
            bmc_ip: str,
            bmc_user: str,
            bmc_pwd: str,
            status: str = "on") -> str:
        """
        Function to on and off node power using BMC IP
        :param bmc_ip: Node BMC IP
        :param bmc_user: Node BMC user name
        :param bmc_pwd: Node BMC user pwd
        :param status: Status of bmc
        :return: resp
        """
        if not self.execute_cmd("rpm  -qa | grep ipmitool")[0]:
            logger.debug("Installing ipmitool")
            self.execute_cmd("yum install ipmitool")
        cmd = f"ipmitool -I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pwd} chassis power {status.lower()}"
        try:
            if not cmd:
                return "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(
                EXCEPTION_MSG.format(
                    Bmc.bmc_node_power_on_off.__name__,
                    error))
            raise error
        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def get_bmc_ip(self) -> str:
        """
        Execute 'ipmitool lan print' on node and return bmc ip.
        :return: bmc ip or none
        """
        bmc_ip = None
        try:
            cmd = "ipmitool lan print"
            logger.info(f"Running command {cmd}")
            response = self.execute_cmd(cmd=cmd, read_lines=False,
                                        read_nbytes=8000)
            response = response.decode(
                "utf-8") if isinstance(response, bytes) else response
            logger.debug(response)
            for res in str(response[1]).split("\\n"):
                if "IP Address" in res and "IP Address Source" not in res:
                    bmc_ip = res.split(":")[-1].strip()
                    break
            logger.debug(f"BMC IP: {bmc_ip}")
        except AttributeError as error:
            logger.error(EXCEPTION_MSG.format(Bmc.get_bmc_ip.__name__, error))
            raise error
        except BaseException as error:
            logger.error(EXCEPTION_MSG.format(Bmc.get_bmc_ip.__name__, error))
            raise error

        return bmc_ip

    def set_bmc_ip(self, bmc_ip: str) -> bool:
        """
        Execute 'ipmitool lan set 1 ipaddr {ip}' on node to change/set/update bmc ip.
        :param bmc_ip: any valid ip.
        :return: True if bmc ip changed else False.
        """
        try:
            logger.info(
                f"Update bmc ip on primary node and set to '{bmc_ip}'.")
            cmd = "ipmitool lan set 1 ipaddr {}".format(bmc_ip)
            logger.info(f"Running command {cmd}")
            response = self.execute_cmd(cmd=cmd, read_nbytes=8000)
            up_bmc_ip = self.get_bmc_ip()
            logger.debug(f"Updated bmc ip: {up_bmc_ip}")
            flg = True if "Setting LAN IP Address to {}".format(
                bmc_ip) in str(response[1]) else False
            flg = True if (bmc_ip == up_bmc_ip and flg) else False

            return flg
        except Exception as error:
            logger.error(EXCEPTION_MSG.format(Bmc.set_bmc_ip.__name__, error))
            raise error

    def create_bmc_ip_change_fault(self, ip: str) -> bool:
        """
        Create bmc ip change fault by updating non ping-able valid ip.
        :param ip: non ping-able valid ip.
        :return: True if bmc ip changed else False.
        """
        try:
            if not ip:
                raise ValueError(f"Invalid ip: {ip}")
            logger.info("Create bmc ip change fault on  node.")
            return self.set_bmc_ip(ip)
        except Exception as error:
            logger.error(
                EXCEPTION_MSG.format(
                    Bmc.create_bmc_ip_change_fault.__name__,
                    error))
            raise error

    def resolve_bmc_ip_change_fault(self, ip: str) -> bool:
        """
        Resolve bmc ip fault.
        :param ip: bmc ip.
        :return: True if bmc ip changed else False.
        """
        try:
            if not ip:
                raise Exception(f"Invalid ip: {ip}")
            logger.info("Resolve bmc ip change fault on node.")
            return self.set_bmc_ip(ip)
        except Exception as error:
            logger.error(
                EXCEPTION_MSG.format(
                    Bmc.resolve_bmc_ip_change_fault.__name__,
                    error))
            raise error
