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
"""
This library contains methods for S3 Account operations using CORTX CLI
"""

import logging
from typing import Tuple
from commons import commands
from libs.csm.cli.cortx_cli import CortxCli

LOGGER = logging.getLogger(__name__)


class CortxCliS3AccountOperations(CortxCli):
    """
    This class has all s3 account operations
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliS3AccountOperations
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_s3account_cortx_cli(
            self,
            account_name: str,
            account_email: str,
            password: str,
            **kwargs) -> tuple:
        """
        This function will create s3 account with specified name using CORTX CLI.
        :param str account_name: Name of s3 account to be created.
        :param str account_email: Account email for account creation.
        :param str password: Password to create s3 account user.
        :keyword confirm_password: Confirm password in case want to enter different than password
        :return: True/False and Response returned by CORTX CLI
        """
        confirm_password = kwargs.get("confirm_password", password)
        command = " ".join(
            [commands.CMD_CREATE_S3ACC, account_name, account_email])
        LOGGER.info("Creating S3 account with name %s", account_name)
        response = self.execute_cli_commands(
            cmd=command, patterns=["Password:"])[1]

        if "Password:" in response:
            response = self.execute_cli_commands(
                cmd=password, patterns=["Confirm Password:"])[1]
            if "Confirm Password:" in response:
                response = self.execute_cli_commands(
                    cmd=confirm_password, patterns=["[Y/n]"])[1]
                if "[Y/n]" in response:
                    response = self.execute_cli_commands(
                        cmd="Y", patterns=[account_name])[1]
                    if account_name in response:
                        LOGGER.info("Response returned: \n%s", response)
                        return True, response

        return False, response

    def show_s3account_cortx_cli(self, output_format: str = None) -> tuple:
        """
        This function will list all S3 accounts using CORTX CLI
        :param str output_format: Format for account list (optional) (default value: table)
                       (possible values: table/xml/json)
        :return: responsed returned by cortxcli
        """
        show_s3accounts_cmd = commands.CMD_SHOW_S3ACC
        if output_format:
            show_s3accounts_cmd = "{} -f {}".format(
                show_s3accounts_cmd, output_format)
        LOGGER.info("Listing s3 accounts with cmd: %s", show_s3accounts_cmd)
        response = self.execute_cli_commands(
            cmd=show_s3accounts_cmd, patterns=[
                "Account Name", "account_email"])
        LOGGER.info("Response returned: \n%s", response)

        return response

    def delete_s3account_cortx_cli(self, account_name: str) -> tuple:
        """
        This function will delete specified s3 account using CORTX CLI.
        :param str account_name: Name of the s3 account to be deleted
        :param: str confirm: Confirm option for deleting a user password.
        :return: True/False and Response returned by CORTX CLI
        """
        delete_s3acc_cmd = commands.CMD_DELETE_S3ACC.format(account_name)
        LOGGER.info("Deleting s3 account %s", account_name)
        response = self.execute_cli_commands(
            cmd=delete_s3acc_cmd, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.execute_cli_commands(
                cmd="Y", patterns=["Account Deleted"])[1]
            if "Account Deleted" in response:
                LOGGER.info("Response returned: \n%s", response)
                return True, response

        return False, response

    def reset_s3account_password(
            self,
            account_name: str,
            new_password: str,
            **kwargs) -> tuple:
        """
        This function will update password for specified s3 account to new_password using CORTX CLI.
        :param account_name: Name of the s3 account whose password is to be update
        :param new_password: New password for s3 account
        :keyword reset_password: Y/n
        :return: True/False and Response returned by CORTX CLI
        """
        reset_password = kwargs.get("reset_password", "Y")
        reset_pwd_cmd = commands.CMD_RESET_S3ACC_PWD.format(account_name)
        LOGGER.info("Resetting s3 account password to %s", new_password)
        response = self.execute_cli_commands(
            cmd=reset_pwd_cmd, patterns=["Password:"])[1]
        if "Password:" in response:
            response = self.execute_cli_commands(
                cmd=new_password, patterns=["Confirm Password:"])[1]
            if "Confirm Password:" in response:
                response = self.execute_cli_commands(
                    cmd=new_password, patterns=["[Y/n]"])[1]
                if "[Y/n]" in response:
                    response = self.execute_cli_commands(cmd=reset_password, patterns=[
                                                         account_name, "cortxcli"])[1]
                    if account_name in response:
                        LOGGER.info("Response returned: \n%s", response)
                        return True, response

        return False, response

    def help_option(self, command: str = None) -> Tuple[bool, str]:
        """
        This function will check the help response
        :param str command: Command whose help response to be validated
        :return: (Boolean, response)
        """
        LOGGER.info("Performing help option on command %s", command)
        output = self.execute_cli_commands(cmd=command, patterns=["usage:"])[1]
        if "error" in output.lower() or "exception" in output.lower():
            return False, output

        return True, output
