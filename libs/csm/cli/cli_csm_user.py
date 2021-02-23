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

""" Library for csm users operations """

import logging
from typing import Tuple
from libs.csm.cli.cortx_cli import CortxCli
from commons import commands as common_commands

LOG = logging.getLogger(__name__)


class CortxCliCsmUser(CortxCli):
    """
    This class has methods for performing operations on CSM user using cortxcli
    """

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
        create_csm_user = common_commands.CREATE_CSM_USER

        help_param = kwargs.get("help_param", False)
        confirm = kwargs.get("confirm", "Y")
        role = kwargs.get("role", "manage")

        if help_param:
            cmd = " ".join([create_csm_user, "-h"])
        else:
            cmd = " ".join(
                [create_csm_user, csm_user_name, email_id, role])
        output = self.execute_cli_commands(cmd=cmd)[1]
        if help_param:
            LOG.info("Displaying usage for create csm users")
            return True, output

        if "Password" in output:
            output = self.execute_cli_commands(cmd=password)[1]
            if "Confirm Password" in output:
                output = self.execute_cli_commands(cmd=confirm_password)[1]
                if "[Y/n]" in output:
                    output = self.execute_cli_commands(cmd=confirm)[1]
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
        delete_csm_user = common_commands.DELETE_CSM_USER
        if help_param:
            cmd = " ".join([delete_csm_user, "-h"])
        else:
            cmd = " ".join([delete_csm_user, user_name])
        output = self.execute_cli_commands(cmd=cmd)[1]
        if help_param:
            LOG.info("Displaying usage for delete csm user")
            return True, output

        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd=confirm)[1]

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
        update_role = common_commands.UPDATE_ROLE
        if help_param:
            cmd = "{0} -h".format(update_role)
        else:
            cmd = "{0} {1} -r {2}".format(
                update_role, user_name, role)

        output = self.execute_cli_commands(cmd=cmd)[1]

        if help_param:
            LOG.info("Displaying usage for update role")
            return True, output

        if "Current Password" in output:
            output = self.execute_cli_commands(cmd=current_password)[1]
            if "[Y/n]" in output:
                output = self.execute_cli_commands(cmd=confirm)[1]

                return True, output

        return False, output

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
        reset_pwd = common_commands.RESET_PWD
        if help_param:
            cmd = "{0} -h".format(reset_pwd)
        else:
            cmd = "{0} {1}".format(
                reset_pwd, user_name)

        output = self.execute_cli_commands(cmd=cmd)[1]

        if help_param:
            LOG.info("Displaying usage for reset password")
            return True, output

        if "Current Password" in output:
            output = self.execute_cli_commands(cmd=current_password)[1]
            if "Password" in output:
                output = self.execute_cli_commands(cmd=new_password)[1]
                if "Confirm Password:" in output:
                    output = self.execute_cli_commands(cmd=confirm_password)[1]
                    if "[Y/n]" in output:
                        output = self.execute_cli_commands(cmd=confirm)[1]
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

        cmd = "cortxcli --username {0}".format(username)
        output = self.execute_cli_commands(cmd=cmd)[1]
        if "Username" in output:
            output = self.execute_cli_commands(cmd=username)[1]
            if "Password" in output:
                output = self.execute_cli_commands(cmd=password)[1]
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
            **kwargs) -> Tuple[bool, str]:
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
        cmd = common_commands.LIST_CSM_USERS
        if offset:
            cmd = "{0} -o {1}".format(cmd, offset)
        if limit:
            cmd = "{0} -l {1}".format(cmd, limit)
        if sort_by:
            cmd = "{0} -s {1}".format(cmd, sort_by)
        if sort_dir:
            cmd = "{0} -d {1}".format(cmd, sort_dir)
        if op_format:
            cmd = "{0} -f {1}".format(cmd, op_format)
        if other_param:
            cmd = "{0} {1}".format(cmd, other_param)
        if help_param:
            cmd = "{0} -h".format(cmd)

        output = self.execute_cli_commands(cmd=cmd)[1]

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
        command = common_commands.HELP_OPTION

        output = self.execute_cli_commands(cmd=command)[1]

        if "error" in output.lower() or "exception" in output.lower():
            return False, output

        return True, output
