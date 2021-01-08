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

################################################################################
# Local libraries
################################################################################
from commons.helpers.host import Host

################################################################################
# Constants
################################################################################
logger = logging.getLogger(__name__)


class BmcHelper(Host):

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
                return "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(error)
            return error
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
                return "Command not found"
            logger.info(f"Executing cmd: {cmd}")
            resp = self.execute_cmd(cmd)
            logger.debug("Output:", resp)
        except BaseException as error:
            logger.error(error)
            return error
        logger.info(f"Successfully executed cmd {cmd}")
        return resp

    def get_bmc_ip(self):
        """
        Execute 'ipmitool lan print' on node and return bmc ip.
        :return: bmc ip or none
        :rtype: str.
        """
        bmc_ip = None
        try:
            cmd = "ipmitool lan print"
            logger.info(f"Running command {cmd}")
            response = self.execute_cmd(cmd=cmd,read_lines=False,
                                                        read_nbytes=8000)
            response = response.decode("utf-8") if isinstance(response, bytes) else response
            logger.debug(response)
            for res in str(response[1]).split("\\n"):
                if "IP Address" in res and "IP Address Source" not in res:
                    bmc_ip = res.split(":")[-1].strip()
                    break
            logger.debug(f"BMC IP: {bmc_ip}")
        except AttributeError as error:
            logger.error(error)
        except BaseException as error:
            logger.error(error)
            return error

        return bmc_ip

    def set_bmc_ip(self, bmc_ip):
        """
        Execute 'ipmitool lan set 1 ipaddr {ip}' on node to change/set/update bmc ip.
        :param bmc_ip: any valid ip.
        :type bmc_ip: str/ip.
        :return: True if bmc ip changed else False.
        :rtype: bool.
        """
        try:
            logger.info(f"Update bmc ip on primary node and set to '{bmc_ip}'.")
            cmd = "ipmitool lan set 1 ipaddr {}".format(bmc_ip)
            logger.info(f"Running command {cmd}")
            response = self.execute_cmd(cmd=cmd, nbytes=8000)
            up_bmc_ip = self.get_bmc_ip()
            logger.debug(f"Updated bmc ip: {up_bmc_ip}")
            flg = True if "Setting LAN IP Address to {}".format(bmc_ip) in str(response[1]) else False
            flg = True if (bmc_ip == up_bmc_ip and flg) else False

            return flg
        except Exception as error:
            logger.error(error)
            return error

    def create_bmc_ip_change_fault(self, ip):
        """
        Create bmc ip change fault by updating non ping-able valid ip.
        :param ip: non ping-able valid ip.
        :type ip: str/ip.
        :return: True if bmc ip changed else False.
        :rtype: bool.
        """
        try:
            if not ip:
                raise Exception(f"Invalid ip: {ip}")
            logger.info("Create bmc ip change fault on  node.")
            return self.set_bmc_ip(ip)
        except Exception as error:
            logger.error(error)
            return error

    def resolve_bmc_ip_change_fault(self, ip):
        """
        Resolve bmc ip fault.
        :param ip: bmc ip.
        :type ip: str/ip.
        :return: True if bmc ip changed else False.
        :rtype: bool.
        """
        try:
            if not ip:
                raise Exception(f"Invalid ip: {ip}")
            logger.info("Resolve bmc ip change fault on node.")
            return self.set_bmc_ip(ip)
        except Exception as error:
           logger.error(error)
           return error