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
#

""" Library for csm users operations """

import logging
from typing import Tuple, Union
from libs.csm.cli.cortx_cli import CortxCli
from commons.commands import CMD_CREATE_CSM_USER
from commons.commands import CMD_DELETE_CSM_USER
from commons.commands import CMD_UPDATE_ROLE
from commons.commands import CMD_RESET_PWD
from commons.commands import CMD_LIST_CSM_USERS
from commons.commands import CMD_HELP_OPTION

LOG = logging.getLogger(__name__)


class CortxCliCsmUser(CortxCli):
    """
    This class has methods for performing operations on CSM user using cortxcli
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliCsmUser
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_csm_user_cli(
            self,
            csm_user_name: str = None,
            email_id: str = None,
            password: str = None,
            confirm_password: str = None,
            **kwargs) -> Tuple[bool, str]:
        """
        This function will create new csm user
        :param csm_user_name: New csm user's name
        :param email_id: Email id of csm user
        :keyword role: role of the new user
        :param password: Password to create csm user.
        :param confirm_password: Confirm password to create csm user.
        :keyword confirm: Confirm option for creating a csm user
        :keyword help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        LOG.info("Creating csm user")
        help_param = kwargs.get("help_param", False)
        confirm = kwargs.get("confirm", "Y")
        role = kwargs.get("role", "manage")
        cmd = " ".join([CMD_CREATE_CSM_USER,
                        "-h"]) if help_param else " ".join([CMD_CREATE_CSM_USER,
                                                            csm_user_name,
                                                            email_id,
                                                            role])
        output = self.execute_cli_commands(cmd=cmd, patterns=["usage:", "Password"])[1]
        if help_param:
            LOG.info("Displaying usage for create csm users")
            return True, output
        if "Password" in output:
            output = self.execute_cli_commands(cmd=password, patterns=["Confirm Password"])[1]
            if "Confirm Password" in output:
                output = self.execute_cli_commands(cmd=confirm_password, patterns=["[Y/n]"])[1]
                if "[Y/n]" in output:
                    output = self.execute_cli_commands(
                              cmd=confirm, patterns=["User created", "cortxcli"])[1]
                    if "User created" in output:

                        return True, output

        return False, output

    def delete_csm_user(
            self,
            user_name: str = None,
            confirm: str = "Y",
            help_param: bool = False) -> Tuple[bool, str]:
        """
        This function will delete csm user
        :param user_name: Name of csm user to be created
        :param confirm: Confirm option for deleting a csm user
        :param help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        LOG.info("Deleting csm user")
        cmd = " ".join([CMD_DELETE_CSM_USER,
                        "-h"]) if help_param else " ".join([CMD_DELETE_CSM_USER,
                                                            user_name])
        output = self.execute_cli_commands(cmd=cmd, patterns=["usage:", "[Y/n]"])[1]
        if help_param:
            LOG.info("Displaying usage for delete csm user")
            return True, output
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd=confirm,
                     patterns=["User deleted", "cortxcli"])[1]
        if "error" in output.lower() or "exception" in output.lower():

            return False, output

        return True, output

    def update_role(
            self,
            user_name: str = None,
            role: str = None,
            current_password: str = None,
            confirm: str = "y",
            **kwargs) -> Tuple[bool, str]:
        """
        This function will update role of user
        :param str user_name: Name of a root user whose role to be updated.
        :param str role: Role to be updated
        :param str current_password: Current password
        :param confirm: Confirm option for updating role of a csm user
        :keyword bool help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        LOG.info("Updating role of CSM user")
        help_param = kwargs.get("help_param", False)
        cmd = " ".join([CMD_UPDATE_ROLE,
                        "-h"]) if help_param else f"{CMD_UPDATE_ROLE} {user_name} -r {role}"
        output = self.execute_cli_commands(cmd=cmd, patterns=["usage:", "Current Password"])[1]
        if help_param:
            LOG.info("Displaying usage for update role")
            return True, output
        if "Current Password" in output:
            output = self.execute_cli_commands(cmd=current_password, patterns=["[Y/n]"])[1]
            if "[Y/n]" in output:
                output = self.execute_cli_commands(cmd=confirm, patterns=["Updated", "updated"])[1]

            if "error" in output.lower() or "exception" in output.lower():
                return False, output

        return True, output

    def reset_root_user_password(
            self,
            user_name: str = None,
            current_password: str = None,
            new_password: str = None,
            confirm_password: str = None,
            **kwargs) -> Tuple[bool, str]:
        """
        This function will reset the user password
        :param str user_name: Name of a root user whose password to be updated.
        :param str current_password: Current password
        :param str new_password: New password to be updated.
        :param bool confirm_password: Confirm password to update new password.
        :keyword: str confirm: Confirm option for resetting a user password.
        :keyword bool help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        LOG.info("Resetting root user password")
        help_param = kwargs.get("help_param", False)
        confirm = kwargs.get("confirm", "Y")
        cmd = " ".join([CMD_RESET_PWD, "-h"]) if help_param else " ".join(
            [CMD_RESET_PWD, user_name])
        output = self.execute_cli_commands(cmd=cmd, patterns=["usage:", "Current Password"])[1]
        if help_param:
            LOG.info("Displaying usage for reset password")
            return True, output
        if "Current Password" in output:
            output = self.execute_cli_commands(
                               cmd=current_password, patterns=["Password"])[1]
            if "Password" in output:
                output = self.execute_cli_commands(cmd=new_password, patterns=["Confirm Password:"])[1]
                if "Confirm Password:" in output:
                    output = self.execute_cli_commands(cmd=confirm_password, patterns=["[Y/n]"])[1]
                    if "[Y/n]" in output:
                        output = self.execute_cli_commands(
                                   cmd=confirm, patterns=["Password Updated"])[1]
                        if "Password Updated" in output:

                            return True, output

        return False, output

    def login_with_username_param(
            self, username, password) -> Tuple[bool, str]:
        """
        This function is used to login to CSM user/admin using username as a parameter
        :param str username: Name of the user
        :param str password: Password to login csmcli
        :return: (Boolean/response)
        """
        LOG.info("Login to csmcli using %s", username)
        cmd = f"cortxcli --username {username}"
        output = self.execute_cli_commands(cmd=cmd, patterns=["Username"])[1]
        if "Username" in output:
            output = self.execute_cli_commands(cmd=username, patterns=["Password"])[1]
            if "Password" in output:
                output = self.execute_cli_commands(
                           cmd=password, patterns=["CORTX Interactive Shell"])[1]
                if "CORTX Interactive Shell" in output:
                    LOG.info(
                        "Logged in CORTX CLI as user %s successfully",
                        username)

                    return True, output

        return False, output

    def list_csm_users(
            self,
            offset: int = None,
            limit: int = None,
            sort_by: str = None,
            sort_dir: str = None,
            **kwargs) -> Tuple[bool, Union[dict, str]]:
        """
        This function will verify list of csm users
        :param offset: value for offset parameter
        :param limit: value for limit parameter
        :param sort_by: value for 'sort_by' parameter criteria used to sort csm users list
                        possible values: <user_id/user_type/created_time/updated_time>
        :param sort_dir: order/direction in which list should be sorted
                         possible values: <asc/desc>
        :keyword op_format: format to list csm users
                       possible values: <table/xml/json>
        :keyword other_param: Combination of above all params
                        e.g : <users show -l 2 -d desc -f json>
        :keyword help_param: True for displaying help/usage
        :return: (boolean/response)
        """
        LOG.info("List CSM users")
        help_param = kwargs.get("help_param", False)
        other_param = kwargs.get("other_param", None)
        op_format = kwargs.get("op_format", None)
        cmd = CMD_LIST_CSM_USERS
        if offset:
            cmd = f"{cmd} -o {offset}"
        if limit:
            cmd = f"{cmd} -l {limit}"
        if sort_by:
            cmd = f"{cmd} -s {sort_by}"
        if sort_dir:
            cmd = f"{cmd} -d {sort_dir}"
        if op_format:
            cmd = f"{cmd} -f {op_format}"
        if other_param:
            cmd = f"{cmd} {other_param}"
        if help_param:
            cmd = f"{CMD_LIST_CSM_USERS} -h"
        output = self.execute_cli_commands(cmd=cmd, patterns=["username", "Username", "usage:"])[1]
        if "error" in output.lower() or "exception" in output.lower():

            return False, output

        if op_format == "json":
            output = self.format_str_to_dict(output)
        if op_format == "xml":
            output = self.xml_data_parsing(output)
        if op_format == "table":
            output = self.split_table_response(output)

        return True, output

    def help_option(self, command: str = None) -> Tuple[bool, str]:
        """
        This function will check the help response
        :param str command: Command whose help response to be validated
        :return: (Boolean, response)
        """
        LOG.info("Performing help option on command %s", command)
        output = self.execute_cli_commands(cmd=CMD_HELP_OPTION, patterns=["usage:"])[1]
        if "error" in output.lower() or "exception" in output.lower():

            return False, output

        return True, output
