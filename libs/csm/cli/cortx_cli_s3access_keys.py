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
This library contains methods for S3 access key operations using CORTX CLI
"""

import logging
from commons import commands
from libs.csm.cli.cortx_cli import CortxCli

LOGGER = logging.getLogger(__name__)


class CortxCliS3AccessKeys(CortxCli):
    """
    This class has all s3 access key operations
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliS3AccessKeys
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_s3user_access_key(self,
                                  user_name: str) -> tuple:
        """
        This function will create/generate access key for s3 user using CORTX CLI.

        :param user_name: Name of s3 user for which access key should be created.
        :return: True/False and dictionary
        """
        response_dict = {}
        command = commands.CMD_CREATE_S3ACC_ACCESS_KEY.format(user_name)
        LOGGER.info("Creating s3accesskey for user %s", user_name)
        response = self.execute_cli_commands(cmd=command, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.execute_cli_commands(cmd="Y", patterns=["Access Key"])[1]
            if "Access Key" in response:
                LOGGER.info("Response returned: \n%s", response)
                response = self.split_table_response(response)
                response_dict["access_key"] = response[0][0]
                response_dict["secret_key"] = response[0][1]
                return True, response_dict

        return False, response

    def show_s3user_access_key(
            self,
            user_name: str,
            output_format: str = "json") -> tuple:
        """
        This function will list access keys of given s3 user.

        :param user_name: Name of s3 user
        :param output_format: Format for show access key (optional) (default value: table)
                       (possible values: table/xml/json)
        :return: True/False and dictionary.
        """
        command = f"{commands.CMD_SHOW_S3ACC_ACCESS_KEY.format(user_name)} -f {output_format}"
        LOGGER.info("Listing s3 user accesskey of user %s", user_name)
        status, response = self.execute_cli_commands(cmd=command,
                      patterns=["Access Key", "access_keys"])
        if output_format == "json":
            response = self.format_str_to_dict(response)
        if output_format == "xml":
            response = self.xml_data_parsing(response)
        if output_format == "table":
            response = self.split_table_response(response)

        return status, response

    def create_s3_iam_access_key(self,
                                 user_name: str) -> tuple:
        """
        This function will create s3 access key for IAM user using CORTX CLI.
        :param user_name: Name of S3 IAM user for which access key should be created.
        :return: True/False and dictionary
        """
        response_dict = {}
        command = " ".join(
            [commands.CMD_CREATE_ACCESS_KEY, user_name])
        LOGGER.info("Creating s3accesskey for user %s", user_name)
        response = self.execute_cli_commands(cmd=command, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.execute_cli_commands(cmd="Y", patterns=["Access Key"])[1]
            if "Access Key" in response:
                LOGGER.info("Response returned: \n%s", response)
                response = self.split_table_response(response)
                response_dict["access_key"] = response[0][0]
                response_dict["secret_key"] = response[0][1]
                return True, response_dict

        return False, response

    def delete_s3access_key(self,
                            access_key: str,
                            user_name: str = None) -> tuple:
        """
        This function will delete given s3 access key.
        :param access_key: Access of user
        :param user_name: Name of user for which access key should be deleted.
        :return: True/False and Response returned by CORTX CLI
        """

        command = " ".join(
            [commands.CMD_DELETE_ACCESS_KEY, access_key])
        if user_name:
            command = " ".join(
                [commands.CMD_DELETE_ACCESS_KEY, access_key, user_name])
        LOGGER.info("Deleting s3accesskey %s", access_key)
        response = self.execute_cli_commands(cmd=command, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.execute_cli_commands(cmd="Y", patterns=["Access Key Deleted"])[1]
            if "Access Key Deleted" in response:
                LOGGER.info("Response returned: \n%s", response)
                return True, response

        return False, response

    def show_s3access_key(
            self,
            user_name: str,
            output_format: str = "json") -> str:
        """
        This function will list access keys of given user.
        :param user_name: Name of user
        :param output_format: Format for show access key (optional) (default value: table)
                       (possible values: table/xml/json)
        :return: Response returned by CORTX CLI
        """
        command = f"{commands.CMD_SHOW_ACCESS_KEY} {user_name} -f {output_format}"
        LOGGER.info("Listing s3accesskey of user %s", user_name)
        response = self.execute_cli_commands(cmd=command, patterns=["Access Key", "access_keys"])[1]
        if output_format == "json":
            response = self.format_str_to_dict(response)
        if output_format == "xml":
            response = self.xml_data_parsing(response)
        if output_format == "table":
            response = self.split_table_response(response)

        return response

    def update_s3access_key(
            self,
            user_name: str,
            access_key: str,
            status: str) -> tuple:
        """
        This function will update status of access key for given user.
        :param user_name: Name of user
        :param access_key: Access of user
        :param status: Status for update access key
                        (possible values: Active/Inactive)
        :return: True/False and Response returned by CORTX CLI
        """

        command = " ".join(
            [commands.CMD_UPDATE_ACCESS_KEY, user_name, access_key, status])
        LOGGER.info("Updating s3accesskey for user %s", user_name)
        response = self.execute_cli_commands(cmd=command, patterns=["[Y/n]"])[1]
        if "[Y/n]" in response:
            response = self.execute_cli_commands(cmd="Y", patterns=["Access Key updated"])[1]
            if "Access Key updated" in response:
                LOGGER.info("Response returned: \n%s", response)
                return True, response

        return False, response
