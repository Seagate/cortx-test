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
"""
This library contains methods for S3 Account operations using CORTX CLI
"""

import logging
from libs.csm.cli.cortx_cli import CortxCli

LOGGER = logging.getLogger(__name__)


class CortxCliS3AccountOperations(CortxCli):
    """
    This class has all s3 account operations
    """

    def create_s3account_cortx_cli(
            self,
            account_name: str,
            account_email: str,
            password: str) -> tuple:
        """
        This function will create s3 account with specified name using CORTX CLI.
        :param str account_name: Name of s3 account to be created.
        :param str account_email: Account email for account creation.
        :param str password: Password to create s3 account user.
        :return: True/False and Response returned by CORTX CLI
        """
        create_s3acc_cmd = "s3accounts create"
        command = " ".join([create_s3acc_cmd, account_name, account_email])
        LOGGER.info("Creating S3 account with name %s", account_name)
        response = self.execute_cli_commands(cmd=command)[1]

        if "Password:" in response:
            response = self.execute_cli_commands(cmd=password)[1]
            if "Confirm Password:" in response:
                response = self.execute_cli_commands(cmd=password)[1]
                if "[Y/n]" in response:
                    response = self.execute_cli_commands(cmd="Y")[1]
                    if account_name in response:
                        return True, response

        return False, response

    def show_s3account_cortx_cli(self, output_format: str = None) -> tuple:
        """
        This function will list all S3 accounts using CORTX CLI
        :param str output_format: Format for account list (optional) (default value: table)
                       (possible values: table/xml/json)
        :return: responsed returned by cortxcli
        """
        show_s3accounts_cmd = "s3accounts show"
        if output_format:
            show_s3accounts_cmd = "{} -f {}".format(
                show_s3accounts_cmd, output_format)
        LOGGER.info("Listing s3 accounts with cmd: %s", show_s3accounts_cmd)
        response = self.execute_cli_commands(cmd=show_s3accounts_cmd)
        LOGGER.info("Response returned: \n%s", response)
        return response

    def delete_s3account_cortx_cli(self, account_name: str) -> tuple:
        """
        This function will delete specified s3 account using CORTX CLI.
        :param str account_name: Name of the s3 account to be deleted
        :param: str confirm: Confirm option for deleting a user password.
        :return: True/False and Response returned by CORTX CLI
        """
        delete_s3acc_cmd = "s3accounts delete {}".format(account_name)
        LOGGER.info("Deleting s3 account %s", account_name)
        response = self.execute_cli_commands(cmd=delete_s3acc_cmd)[1]
        if "[Y/n]" in response:
            response = self.execute_cli_commands(cmd="Y")[1]
            if "Account Deleted" in response:
                return True, response

        return False, response
