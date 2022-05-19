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

"""Module to maintain all common functions across component."""

import logging
import time
from typing import List
from typing import Tuple
from typing import Union

from commons import commands, constants
from commons.helpers.host import Host

log = logging.getLogger(__name__)


class Node(Host):
    """Class to maintain all common functions across component."""

    def get_authserver_log(self, path: str, option: str = "-n 3") -> Tuple:
        """Get authserver log from node."""
        cmd = "tail {} {}".format(path, option)
        res = self.execute_cmd(cmd)
        return res

    def send_systemctl_cmd(
            self,
            command: str,
            services: list,
            decode=False,
            **kwargs) -> list:
        """send/execute command on remote node."""
        valid_commands = {"start", "stop",
                          "reload", "enable", "disable", "status", "restart",
                          "is-active"}
        if command not in valid_commands:
            raise ValueError(
                "command parameter must be one of %r." % valid_commands)
        out = []
        for service in services:
            log.debug(
                "Performing %s on service %s...", command, service)
            cmd = commands.SYSTEM_CTL_CMD.format(command, service)
            resp = self.execute_cmd(cmd, **kwargs)
            if decode:
                resp = resp.decode("utf8").strip()
            out.append(resp)

        return out

    def status_service(
            self,
            services: list,
            expected_status: str,
            timeout: int = 2) -> dict:
        """Function display status of services."""
        result = dict()
        result["output"] = {}
        status_list = []
        for service in services:
            log.debug("service status %s", service)
            cmd = commands.SYSTEM_CTL_STATUS_CMD.format(service)
            out = self.execute_cmd(cmd, read_lines=True, timeout=timeout)
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

    def toggle_apc_node_power(
            self,
            pdu_ip,
            pdu_user,
            pdu_pwd,
            node_slot,
            **kwargs):
        """
        Function to toggle node power status usng APC PDU switch.

        :param string pdu_ip: IP or end pont for the PDU
        :param string pdu_user: PDU login user
        :param string pdu_pwd: PDU logn user password
        :param string node_slot: Node blank sort or port
        :return: [bool, response]
        """
        timeout = kwargs.get("timeout") if kwargs.get("timeout", None) else 120
        status = kwargs.get("status") if kwargs.get("status", None) else None
        if not self.execute_cmd("rpm  -qa | grep expect")[0]:
            log.debug("Installing expect package")
            self.execute_cmd("yum install expect")

        if status.lower() == "on":
            cmd = commands.CMD_PDU_POWER_ON.format(pdu_ip, pdu_user, pdu_pwd, node_slot)
        elif status.lower() == "off":
            cmd = commands.CMD_PDU_POWER_OFF.format(pdu_ip, pdu_user, pdu_pwd, node_slot)
        else:
            cmd = commands.CMD_PDU_POWER_CYCLE.format(pdu_ip, pdu_user, pdu_pwd, node_slot, timeout)

        try:
            if not cmd:
                return False, "Command not found"
            log.debug("Executing cmd: %s", cmd)
            resp = self.execute_cmd(cmd)
            log.debug("Output: %s", resp)
        except BaseException as error:
            log.error("*ERROR* An exception occurred in %s: %s",
                      Node.toggle_apc_node_power.__name__, error)
            return False, error

        log.debug("Successfully executed cmd %s", cmd)

        return resp

    def disk_usage_python_interpreter_cmd(self,
                                          dir_path: str,
                                          field_val: int = 3) -> Tuple[bool,
                                                                       Union[List[str],
                                                                             str,
                                                                             bytes,
                                                                             BaseException]]:
        """
        Function will return disk usage associated with given path.

        :param dir_path: Directory path of which size is to be calculated.
        :param field_val: 0, 1, 2 and 3 for total, used, free in bytes and percent used
        space respectively.
        :return: Output of the python interpreter command.
        """
        try:
            cmd = "python3 -c 'import psutil; print(psutil.disk_usage(\"{a}\")[{b}])'".format(
                a=str(dir_path), b=int(field_val))
            log.info("Running python command %s", cmd)
            resp = self.execute_cmd(cmd=cmd)

            return True, resp
        except BaseException as error:
            log.error(
                "*ERROR* An exception occurred in %s: %s",
                Node.disk_usage_python_interpreter_cmd.__name__, error)
            return False, error

    def get_ldap_credential(self):
        """Get the ldap credential from node."""
        # Fetch ldap username.
        ldap_user = self.execute_cmd(commands.LDAP_USER)
        ldap_user = ldap_user.decode("utf-8") if isinstance(ldap_user, bytes) else ldap_user
        ldap_user = ldap_user.split(",")[0].lstrip("cn=").strip()
        # Fetch ldap password.
        ldap_passwd = self.execute_cmd(commands.LDAP_PWD)
        ldap_passwd = ldap_passwd.decode(
            "utf-8").strip() if isinstance(ldap_passwd, bytes) else ldap_passwd
        log.debug("LDAP USER: %s, LDAP Password: %s", ldap_user, ldap_passwd)

        return ldap_user, ldap_passwd

    def make_remote_file_copy(self, path: str, backup_path: str) -> \
            Tuple[bool, Tuple[Union[List[str], str, bytes]]]:
        """
        copy file with remote machine cp cmd.

        :param path: source path
        :param backup_path: destination path
        :return: response in tuple
        """
        try:
            cmd = commands.COPY_FILE_CMD.format(path, backup_path)
            resp = self.execute_cmd(cmd=cmd, read_nbytes=constants.BYTES_TO_READ)
        except Exception as error:
            log.error(
                "%s %s: %s", constants.EXCEPTION_ERROR,
                self.make_remote_file_copy.__name__, error)
            return False, error

        return True, resp
