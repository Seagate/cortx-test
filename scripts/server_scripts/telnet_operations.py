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

"""File contains methods for performing telnet operations."""
import logging
import telnetlib
import time
import os
import subprocess
import argparse
import errno

LOGGER = logging.getLogger(__name__)


class TelnetOperations:
    """
    This class includes functions for telnet operations which are needed to
    be performed from node.
    """

    def get_mc_ver_sr(self, enclosure_ip, enclosure_user, enclosure_pwd, cmd):
        """
        Function to get the version and serial number of the management
        controller.

        :param enclosure_ip: IP of the enclosure
        :type: str
        :param enclosure_user: Username of the enclosure
        :type: str
        :param enclosure_pwd: Password of the enclosure
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: version and serial number of the management controller
        :rtype: Boolean, Strings
        """
        tel_obj = telnetlib.Telnet(host=enclosure_ip)

        try:
            output = tel_obj.read_until(b"login: ", 15)
            tel_obj.write(enclosure_user.encode() + b"\r\n")

            tel_obj.read_until(b"Password: ", 15)
            tel_obj.write(enclosure_pwd.encode() + b"\r\n")
            time.sleep(5)

            LOGGER.info("Running command %s", cmd)
            tel_obj.write(cmd.encode() + b"\r\n")
            time.sleep(5)
            out = tel_obj.read_very_eager()
            LOGGER.info(out)
            tel_obj.write(b"exit\r\n")
            time.sleep(10)
            LOGGER.info("Telnet Connection closed")
        except Exception as err:
            LOGGER.info("%s occurred", err.__class__)
            return False, err

        f_pointer = open('temp.txt', 'wb')
        _ = f_pointer.write(output)
        f_pointer.close()

        mc_ver = os.popen("sed '/MC Version/!d' temp.txt | awk '{print "
                          "$NF}'").read()

        mc_sr = os.popen("sed '/Serial Number/!d' temp.txt | awk '{print "
                         "$NF}'").read()
        os.remove('temp.txt')

        return True, mc_ver, mc_sr

    def simulate_fault_ctrl(self, mc_deb_password, enclosure_ip, telnet_port,
                            timeout, cmd):
        """
        Function to simulate faults on the controller.

        :param mc_deb_password: Password of Management controller debug console
        :type: str
        :param enclosure_ip: IP of the enclosure
        :type: str
        :param telnet_port: Telnet port number for connecting to MC debug
        console
        :type: str
        :param timeout: Timeout value
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: Boolean, Response
        :rtype: Tuple of (bool, String)
        """
        try:
            tel_obj = telnetlib.Telnet(host=enclosure_ip,
                                       port=telnet_port,
                                       timeout=int(timeout))

            read_str = tel_obj.read_until(b"Password: ", 15)
            if read_str.decode() == "Password:":
                LOGGER.info("Entering the password")
                tel_obj.write(mc_deb_password.encode())
                time.sleep(2)
                out = tel_obj.read_very_eager()
                LOGGER.info(out)
                tel_obj.write(b"\r\n\n\n")
                time.sleep(5)

                tel_obj.write(b"\r\n\n")
                LOGGER.info("Running command %s", cmd)
                tel_obj.write(cmd.encode() + b"\r\n")
                tel_obj.write(b"\r\n\n\n")
                LOGGER.info("Waiting for 15 seconds for alert generation")
                time.sleep(15)
                out = tel_obj.read_very_eager()
                LOGGER.info(out)
                tel_obj.write(b"exit\r\n")
                time.sleep(5)
                return True, read_str.decode()
            else:
                tel_obj.close()
                return False, read_str.decode()
        except Exception as err:
            LOGGER.info("%s occurred", err.__class__)
            return False, err

    def set_drive_status_telnet(
            self,
            enclosure_ip,
            username,
            pwd,
            status,
            cmd):
        """
        Enable or Disable drive status from disk group.

        :param enclosure_ip: IP of the Enclosure
        :type: str
        :param username: Username of the enclosure
        :type: str
        :param pwd: password for the enclosure user
        :type: str
        :param status: Status of the drive. Value will be enabled or disabled
        :type: str
        :param cmd: Command to be run on MC debug console
        :type: str
        :return: True/False, drive status
        :rtype: Boolean, string
        """
        tel_obj = telnetlib.Telnet(host=enclosure_ip)

        try:
            tel_obj.read_until(b"login: ", 15)
            tel_obj.write(username.encode() + b"\r\n")

            tel_obj.read_until(b"Password: ", 15)
            tel_obj.write(pwd.encode() + b"\r\n")
            time.sleep(5)

            LOGGER.info("Running command %s", cmd)

            out = tel_obj.write(cmd.encode() + b"\r\n")
            time.sleep(5)
            if status == "Disabled":
                out = tel_obj.write(b"y\r\n")
                time.sleep(5)

            LOGGER.info(out)
            tel_obj.write(b"exit\r\n")
            time.sleep(10)
            LOGGER.info("Telnet Connection closed")
            return True, status
        except Exception as err:
            LOGGER.info("%s occurred", err.__class__)
            return False, err

    def show_disks(self, enclosure_ip, enclosure_user, enclosure_pwd,
                   telnet_filepath, cmd):
        """
        Function to get the version and serial number of the management
        controller.

        :param enclosure_ip: IP of the enclosure
        :type: str
        :param enclosure_user: Username of the enclosure
        :type: str
        :param enclosure_pwd: Password of the enclosure
        :type: str
        :param telnet_filepath: File path to save response of telnet command
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: True/False, Path of the telnet file
        :rtype: Boolean, String
        """
        try:
            command = "yum -y install sshpass"
            os.system(command)

            time.sleep(5)
            command = "sshpass -p {} ssh -o 'StrictHostKeyChecking no' {}@{} " \
                      "{}".format(enclosure_pwd, enclosure_user,
                                  enclosure_ip, cmd)

            resp = subprocess.call(command, stdout=open(telnet_filepath, 'w'),
                                   shell=True)
            return True, telnet_filepath
        except Exception as err:
            LOGGER.info("%s occurred", err.__class__)
            return False, err

    def execute_cmd_on_enclosure(self,
                                 enclosure_ip,
                                 enclosure_user,
                                 enclosure_pwd,
                                 file_path,
                                 cmd):
        """
        Function to execute command on enclosure and save result into log file path.

        :param enclosure_ip: IP of the enclosure.
        :type: str
        :param enclosure_user: Username of the enclosure.
        :type: str
        :param enclosure_pwd: Password of the enclosure.
        :type: str
        :param file_path: File path to save response of telnet command.
        :type: str
        :param cmd: Supported commands by enclosure.
        :type: str
        :return: True/False, Path of the telnet file.
        :rtype: tuple.
        """
        try:
            command = "yum -y install sshpass"
            LOGGER.info("Command: %s", command)
            os.system(command)
            time.sleep(5)
            command = "sshpass -p {} ssh -o 'StrictHostKeyChecking no' {}@{} " \
                      "{}".format(enclosure_pwd, enclosure_user,
                                  enclosure_ip, cmd)
            LOGGER.info("Execution command: %s", command)
            status = subprocess.call(command, stdout=open(file_path, 'w'),
                                     shell=True)
            if status != 0:
                raise Exception("Execution failed.")
            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    errno.ENOENT, os.strerror(errno.ENOENT), file_path)
            # Added to remove first line from log.
            os.system("sed -i '1d; $d' {}".format(file_path))
            return True, file_path
        except Exception as err:
            LOGGER.error("Error occurred in %s: %s",
                         TelnetOperations.execute_cmd_on_enclosure.__name__,
                         err)
            return False, err

    def clear_metadata(self, enclosure_ip, enclosure_user, enclosure_pwd, cmd):
        """
        Function to clear the metadata of given drive.

        :param enclosure_ip: IP of the enclosure
        :type: str
        :param enclosure_user: Username of the enclosure
        :type: str
        :param enclosure_pwd: Password of the enclosure
        :type: str
        :param cmd: Command to be run on telnet session
        :type: str
        :return: version and serial number of the management controller
        :rtype: Boolean, Strings
        """
        tel_obj = telnetlib.Telnet(host=enclosure_ip)

        try:
            tel_obj.read_until(b"login: ", 15)
            tel_obj.write(enclosure_user.encode() + b"\r\n")

            tel_obj.read_until(b"Password: ", 15)
            tel_obj.write(enclosure_pwd.encode() + b"\r\n")
            time.sleep(5)

            LOGGER.info("Running command %s", cmd)
            tel_obj.write(cmd.encode() + b"\r\n")
            time.sleep(5)
            tel_obj.write(b"y\r\n")
            time.sleep(10)

            out = tel_obj.read_very_eager()
            LOGGER.info(out)
            tel_obj.write(b"exit\r\n")
            time.sleep(10)
            LOGGER.info("Telnet Connection closed")
        except Exception as err:
            LOGGER.info("%s occurred", err.__class__)
            return False, err

        f_pointer = open('temp.txt', 'wb')
        _ = f_pointer.write(out)
        f_pointer.close()

        status = False
        string = "Success: Command completed successfully. " \
                 "- Metadata was cleared."
        with open('temp.txt', 'r') as read_obj:
            for line in read_obj:
                if string in line:
                    status = True

        os.remove('temp.txt')
        return status, out


def main(telnet_op):
    telnet_op = telnet_op.replace("\\", "")
    operation = TelnetOperations()
    response = eval("operation.{}".format(telnet_op))
    print(response)
    return response


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description='Telnet Operations')
    PARSER.add_argument('--telnet_op', dest='telnet_op', required=True,
                        help='Telnet operation to be performed')
    ARGS = PARSER.parse_args()

    main(ARGS.telnet_op)
