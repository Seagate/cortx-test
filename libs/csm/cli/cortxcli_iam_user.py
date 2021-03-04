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

""" Library for IAM users operations """

import logging
from typing import Tuple
from libs.csm.cli.cortx_cli import CortxCli
from commons.commands import CREATE_IAM_USER, DELETE_IAM_USER, LIST_IAM_USER

LOG = logging.getLogger(__name__)


class CortxCliIamUser(CortxCli):
    """This class has all IAM methods"""

    def create_iam_user(
            self,
            user_name: str = None,
            password: str = None,
            confirm_password: str = None,
            **kwargs) -> Tuple[bool, str]:
        """
        This function will create new IAM user
        :param user_name: Name of IAM user to be created
        :param password: Password to create s3 IAM user.
        :param confirm_password: Confirm password to create s3 IAM user.
        :keyword confirm: Confirm option for creating a IAM user
        :keyword help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        help_param = kwargs.get("help_param", False)
        confirm = kwargs.get("confirm", "Y")
        if help_param:
            cmd = " ".join([CREATE_IAM_USER, "-h"])
        else:
            cmd = " ".join(
                [CREATE_IAM_USER, user_name])
        output = self.execute_cli_commands(cmd=cmd)[1]
        if help_param:
            LOG.info("Displaying usage for create iam users")
            return True, output
        if "Password" in output:
            output = self.execute_cli_commands(cmd=password)[1]
            if "Confirm Password" in output:
                output = self.execute_cli_commands(cmd=confirm_password)[1]
                if "[Y/n]" in output:
                    output = self.execute_cli_commands(cmd=confirm)[1]
                    if ("User Name" in output) and (
                            "User ID" in output) and ("ARN" in output):

                        return True, output

        return False, output

    def list_iam_user(self, output_format: str = None,
                      help_param: bool = False) -> Tuple[bool, str]:
        """
        This function lists IAM users with given format
        (CLI will list IAM users in table format if format is set to None)
        :param output_format: Format of Output(table,xml,json)
        :param help_param: True for displaying help/usage
        :return: List of IAM users in given format
        """
        list_iam_user = LIST_IAM_USER
        if help_param:
            list_iam_user = " ".join([list_iam_user, "-h"])
        if output_format:
            list_iam_user = " ".join(
                [list_iam_user, "-f", output_format])
        output = self.execute_cli_commands(cmd=list_iam_user)[1]
        if help_param:
            LOG.info("Displaying usage for show iam users")
            return True, output
        if not ("user_name" in output or
                "user_id" in output or
                "arn" in output):
            return False, output
        if output_format == "json":
            output = self.format_str_to_dict(output)
        if output_format == "xml":
            output = self.xml_data_parsing(output)
        if output_format == "table":
            output = self.split_table_response(output)

        return True, output

    def delete_iam_user(
            self,
            user_name: str = None,
            confirm: str = "Y",
            help_param: bool = False) -> Tuple[bool, str]:
        """
        This function will delete IAM user
        :param user_name: Name of IAM user to be created
        :param confirm: Confirm option for deleting a IAM user
        :param help_param: True for displaying help/usage
        """
        if help_param:
            cmd = " ".join([DELETE_IAM_USER, "-h"])
        else:
            cmd = " ".join([DELETE_IAM_USER, user_name])
        output = self.execute_cli_commands(cmd=cmd)[1]
        if help_param:
            LOG.info("Displaying usage for delete iam user")
            return True, output
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd=confirm)[1]

        if "error" in output.lower() or "exception" in output.lower():
            return False, output

        return True, output
