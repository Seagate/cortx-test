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

""" This file contains methods for CLI alert feature"""

import logging
import time
from typing import Tuple
from libs.csm.cli.cortx_cli import CortxCli

LOG = logging.getLogger(__name__)


class CortxCliAlerts(CortxCli):
    """
    This class has methods for performing operations on alerts using cortxcli
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliAlerts
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def show_alerts_cli(
            self,
            duration: str = None,
            limit: int = None,
            output_format: str = None,
            other_param: str = None,
            **kwargs) -> Tuple[bool, str]:
        """
        This function will list alerts using cortxcli as per the provided parameters
        :param duration: Time period, for which we request alerts e.g., '30s', '5m', '8h', '2d' etc
        :param limit: No. of alerts to display
        :param output_format: Format of output like "table", "json" or "xml"
        :param other_param: '-s' to display all alerts, '-a' to display active alerts
        :keyword help_param: True for displaying help/usage
        :return: (Boolean/response)
        """
        help_param = kwargs.get("help_param", False)
        show_alert_cmd = "alerts show"
        if duration:
            show_alert_cmd = f"{show_alert_cmd} -d {duration}"
        if limit:
            show_alert_cmd = f"{show_alert_cmd} -l {limit}"
        if output_format:
            show_alert_cmd = f"{show_alert_cmd} -f {output_format}"
        if other_param:
            show_alert_cmd = f"{show_alert_cmd} {other_param}"
        if help_param:
            show_alert_cmd = f"{show_alert_cmd} -h"

        output = self.execute_cli_commands(cmd=show_alert_cmd, patterns=["Alert Id"])[1]

        if help_param:
            self.log.info("Displaying usage for show alerts")
            return True, output

        if not ("Alert Id" in output or "total_records" in output):
            LOG.error(
                "Show alerts failed with error: %s", output)
            return False, output

        return True, output

    def acknowledge_alert_cli(self,
                              alert_id: str = None,
                              ack: bool = True,
                              confirm: str = "Y",
                              help_param: bool = False) -> Tuple[bool,
                                                                 str]:
        """
        This function will acknowledge or un-acknowledge the alert using cortxcli
        :param alert_id: Alert ID to be acknowledge or un-acknowledge
        :param ack: True to mark alert as acknowledge, False to un-acknowledge
        :param confirm: Confirm option for acknowledge alert
        :param help_param: True for displaying help/usage
        :return: (Boolean/response)
        """
        acknowledge_alerts_cmd = "{} {}".format(
            "alerts acknowledge", alert_id)
        if ack:
            acknowledge_alerts_cmd = f"{acknowledge_alerts_cmd} -ack"
        if help_param:
            acknowledge_alerts_cmd = f"{acknowledge_alerts_cmd} -h"

        output = self.execute_cli_commands(cmd=acknowledge_alerts_cmd,
                            patterns=["[Y/n]","usage:"])[1]
        if help_param:
            self.log.info("Displaying usage for acknowledge alerts")
            return True, output

        if "[Y/n]" not in output:
            return False, output

        output = self.execute_cli_commands(cmd=confirm, patterns=["Alert Updated"])[1]
        if "Alert Updated" in output:
            return True, output

        return False, output

    def show_alerts_comment_cli(
            self,
            alert_id: str = None,
            help_param: bool = False,
            output_format: str = None) -> Tuple[bool, str]:
        """
        This function will list comments of alerts using cortxcli
        :param alert_id: Alert ID to be commented
        :param help_param: True for displaying help/usage
        :param output_format: Format of output like "table", "json" or "xml"
        :return: (Boolean/response)
        """
        show_alert_comment_cmd = "alerts comment show"
        if help_param:
            show_alert_comment_cmd = f"{show_alert_comment_cmd} -h"

        if output_format:
            show_alert_comment_cmd = f"{show_alert_comment_cmd} -f {output_format} {alert_id}"

        else:
            show_alert_comment_cmd = f"{show_alert_comment_cmd} {alert_id}"

        output = self.execute_cli_commands(cmd=show_alert_comment_cmd)[1]

        if help_param:
            self.log.info("Displaying usage for show alerts comments")
            return True, output

        if not (
            ("Comment Id" in output) or (
                "Comment" in output) or (
                "Created By" in output) or (
                "Created Time" in output)):
            self.log.error(
                "Show alerts comment failed with error: %s", output)
            return False, output

        if output_format == "json":
            alerts = self.format_str_to_dict(output)
        elif output_format == "xml":
            alerts = self.xml_data_parsing(output)
        else:
            alerts = self.split_table_response(output)

        return True, alerts

    def add_comment_alert(
            self,
            alert_id: str = None,
            comment_text: str = None,
            confirm: str = "Y",
            help_param: bool = False) -> Tuple[bool, str]:
        """
        This function will add comment to the alert using cortxcli
        :param alert_id: Alert ID for which comment need's to added
        :param comment_text: Comment to be added
        :param confirm: Confirm option for adding comment
        :param help_param: True for displaying help/usage
        :return: (Boolean/response)
        """
        cmd = "alerts comment add"
        add_alert_comment_cmd = f"{cmd} {alert_id} {comment_text}"

        if help_param:
            add_alert_comment_cmd = "{cmd} -h"

        output = self.execute_cli_commands(cmd=add_alert_comment_cmd,
                          patterns=["usage:","[Y/n]"])[1]
        if help_param:
            self.log.info("Displaying usage for add alert comment")
            return True, output

        if "[Y/n]" not in output:
            return False, output

        output = self.execute_cli_commands(cmd=confirm, patterns=["Alert Comment Added"])[1]
        if "Alert Comment Added" in output:
            return True, output

        return False, output

    def alerts_xml_formatter(self, cli_xml_output: str = None) -> list:
        """
        This function will convert the cortxcli xml output for alerts into proper xml form
        :param str cli_xml_output: cortxcli output in xml format
        :return: alerts list
        """
        alerts = list()
        offset = 0
        input_str = cli_xml_output.replace("\r\n  ", "").replace("\r\n", "")
        for i in range(input_str.count("<alerts>")):
            self.log.info(i)
            start_index = input_str.find("<alerts>", offset)
            end_index = input_str.find(
                "</alerts>", offset) + len("</alerts>")
            alerts.append(input_str[start_index:end_index])
            offset = end_index

        alerts.append(input_str[input_str.find("<total_records>"):input_str.find(
            "</total_records>") + len("</total_records>")])

        return alerts

    def help_option(self, command: str = None) -> Tuple[bool, str]:
        """
        This function will check the help response for the specified command.
        :param command: Command whose help response to be validated.
        :return: (True/False, Response)
        """
        self.log.info(
            "Checking help response for command %s", command)
        # Forming a command to display help for the given command
        command = " ".join([command, "-h"])

        # Executing a command
        output = self.execute_cli_commands(cmd=command, patterns=["usage:"])[1]

        # Checking for error response
        if "error" in output.lower() or "exception" in output.lower():
            self.log.error(
                "Checking help response for command %s failed with %s", (
                    command, output))
            return False, output

        return True, output

    def wait_for_alert(self,
                       timeout: int = 180,
                       start_time: float = 0,
                       **kwargs) -> Tuple[bool,
                                          str]:
        """
        This function is used to wait till alert gets generated within expected time
        :param timeout: max time to wait for alert generation
        :param start_time: start time of command execution of generate alert
        :return: True/False, Response)
        """
        poll = int(time.time()) + timeout
        while poll > time.time():
            duration = "{0}{1}".format(int((time.time() - start_time)), "s")
            output = self.show_alerts_cli(
                duration=duration,
                limit=1,
                output_format="json",
                **kwargs)[1]
            if len(output["alerts"]) > 0:
                break
        else:
            self.log.error("No alert received within expected duration")
            return False, output

        return True, output
