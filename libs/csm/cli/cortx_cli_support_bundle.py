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
This library contains methods for support bundle operations using CORTX CLI
"""

import logging
from typing import Union, Tuple
from libs.csm.cli.cortx_cli import CortxCli
from commons.commands import CMD_GENERATE_SUPPORT_BUNDLE
from commons.commands import CMD_GENERATE_SUPPORT_BUNDLE_OS
from commons.commands import CMD_SUPPORT_BUNDLE_STATUS
from commons import constants as const
from commons import commands
from commons.helpers import node_helper
from commons.utils import system_utils
from config import CMN_CFG

LOGGER = logging.getLogger(__name__)


class CortxCliSupportBundle(CortxCli):
    """
    This class has all support bundle operations
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliSupportBundle
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def generate_support_bundle(self, comment: str = None) -> Tuple[bool, str]:
        """
        This function is used to generate support bundle
        :param comment: Specify the Reason for Generating Support Bundle.
        :return: (Boolean/Response)
        """
        LOGGER.info("Generating support bundle using cortxcli command")
        command = " ".join(
            [CMD_GENERATE_SUPPORT_BUNDLE, comment])
        output = self.execute_cli_commands(cmd=command, time_out=900, sleep_time=9)[1]

        if "error" in output.lower() or "exception" in output.lower():
            return False, output
        if "Please Find the file on -> /tmp/support_bundle/" not in output:
            return False, output

        return True, output

    def extract_support_bundle(
            self,
            bundle_id: str = None,
            node: str = None,
            dest_dir: str = None,
            **kwargs) -> Tuple[bool, Union[list, tuple]]:
        """
        This function is used to extract support bundle files
        :param bundle_id: Specify the id Support Bundle.
        :param node: Name of node
        :param dest_dir: Name of directory to extract support bundle
        :keyword host: host ip or domain name
        :keyword user: host machine user name
        :keyword pwd: host machine password
        :return: (Boolean, response)
        :rtype: Tuple
        """
        self.log.info("Extracting support bundle files")
        host = kwargs.get("host", CMN_CFG["csm"]["mgmt_vip"])
        user = kwargs.get("user", CMN_CFG["csm"]["admin_user"])
        pwd = kwargs.get("pwd", CMN_CFG["csm"]["admin_pass"])
        tar_file_name = f"{const.SUPPORT_BUNDLE_PATH}{bundle_id}_{node}.{const.TAR_POSTFIX}"

        # Check if file is exists on node
        obj = node_helper.Node(hostname=host, username=user, password=pwd)
        resp = obj.path_exists(tar_file_name)
        if not resp:
            return False, resp

        obj.make_dir(dpath=dest_dir)

        # Extract support bundle
        tar_cmd = commands.CMD_TAR.format(tar_file_name, dest_dir)
        system_utils.run_remote_cmd(
            cmd=tar_cmd,
            hostname=host,
            username=user,
            password=pwd)

        # List directory
        path = f"{dest_dir}{bundle_id}/"
        list_dir = obj.list_dir(path)
        if not list_dir:
            return False, list_dir
        list_dir = [i for i in list_dir if "." not in i]
        if not list_dir:
            return False, list_dir

        return True, list_dir

    def generate_support_bundle_for_os(
            self, comment: str = None) -> Tuple[bool, str]:
        """
        This function is used to generate support bundle for os
        :param comment: Specify the Reason for Generating Support Bundle.
        :return: (Boolean/Response)
        """
        LOGGER.info("Generating support bundle using cortxcli command")
        cmd = CMD_GENERATE_SUPPORT_BUNDLE_OS.format(comment)
        output = self.execute_cli_commands(cmd=cmd, time_out=900, sleep_time=9)[1]

        if "error" in output.lower() or "exception" in output.lower():
            return False, output
        if "Please Find the file on -> /tmp/support_bundle/" not in output:
            return False, output

        return True, output

    # pylint-disable-message=too-many-return-statements
    # pylint: disable-msg=too-many-branches
    def support_bundle_status(
            self,
            bundle_id: str = None,
            output_format: str = None,
            help_param: bool = False) -> Tuple[bool, Union[list, dict]]:
        """
        This function will show status of specific support bundle
        :param str bundle_id: Bundle id which is generated after support bundle
        :param str output_format: Format of output like "table", "json" or "xml"
        :param bool help_param: True for displaying help/usage
        :return: (Boolean/Response)
        """
        if output_format:
            support_bundle_status_cmd=f"{CMD_SUPPORT_BUNDLE_STATUS} {bundle_id} -f {output_format}"
        elif help_param:
            support_bundle_status_cmd = f"{CMD_SUPPORT_BUNDLE_STATUS} -h"
        else:
            support_bundle_status_cmd = f"{CMD_SUPPORT_BUNDLE_STATUS} {bundle_id}"

        output = self.execute_cli_commands(cmd=support_bundle_status_cmd)[1]
        LOGGER.info(output)

        if help_param:
            LOGGER.info("Displaying usage for support bundle status")
            return True, output

        if "error" in output.lower() or "exception" in output.lower():
            LOGGER.error(
                "Support bundle status failed with error: %s", output)
            return False, output

        if output_format == const.JSON_LIST_FORMAT:
            json_resp = self.format_str_to_dict(output)
            if not json_resp:
                return False, output
            else:
                status = json_resp[const.SB_STATUS]
                for each in status:
                    if len(each) == 5:
                        # Verifying keys present in each status of support
                        # bundle dict
                        if not (
                                const.BUNDLE_ID in each and
                                const.SB_COMMENT in each and
                                const.MESSAGE in each and
                                const.NODE_NAME in each and
                                const.RESULT in each):
                            LOGGER.error(
                                "The expected keys in %s response are missing",
                                const.JSON_LIST_FORMAT)
                            return False, json_resp
                    else:
                        LOGGER.error(
                            "%s response is not as expected",
                            const.JSON_LIST_FORMAT)
                        return False, json_resp
                output = json_resp
        elif output_format == const.XML_LIST_FORMAT:
            xml_out = self.xml_data_parsing(output)
            if not xml_out:
                return False, output
            else:
                for each in xml_out:
                    if len(each[const.SB_STATUS]) == 5:
                        # Verifying keys present in each status of support
                        # bundle dict
                        if not (
                                const.BUNDLE_ID in each[const.SB_STATUS] and
                                const.SB_COMMENT in each[const.SB_STATUS] and
                                const.MESSAGE in each[const.SB_STATUS] and
                                const.NODE_NAME in each[const.SB_STATUS] and
                                const.RESULT in each[const.SB_STATUS]):
                            LOGGER.error(
                                "The expected keys in %s response are missing",
                                const.XML_LIST_FORMAT)
                            return False, xml_out
                    else:
                        LOGGER.error(
                            "%s response is not as expected",
                            const.XML_LIST_FORMAT)
                        return False, xml_out
                output = xml_out
        elif output_format == const.TABLE_LIST_FORMAT:
            table_data = self.split_table_response(output)
            status_list = []
            if not table_data:
                return False, output
            else:
                for each in table_data:
                    status_data = []
                    for data in each:
                        if data:
                            status_data.append(data)
                    status_list.append(status_data)
                for each in status_list:
                    # Verifying only two elements are present in each support
                    # bundle status
                    if len(each) != 5:
                        LOGGER.error(
                            "The expected support bundle details"
                            " in %s response are missing",
                            const.TABLE_LIST_FORMAT)
                        return False, table_data
            output = status_list

        return True, output
