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

""" This file contains methods for CLI alert feature"""

import logging
from typing import Tuple
from libs.csm.cli.cortx_cli import CortxCli

LOG = logging.getLogger(__name__)


class CortxCliAlerts(CortxCli):
    """
    This class has methods for performing operations on alerts using cortxcli
    """

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
            show_alert_cmd = "{0} -d {1}".format(show_alert_cmd, duration)
        if limit:
            show_alert_cmd = "{0} -l {1}".format(show_alert_cmd, limit)
        if output_format:
            show_alert_cmd = "{0} -f {1}".format(
                show_alert_cmd, output_format)
        if other_param:
            show_alert_cmd = "{0} {1}".format(show_alert_cmd, other_param)
        if help_param:
            show_alert_cmd = "{0} -h".format(show_alert_cmd)

        output = self.execute_cli_commands(cmd=show_alert_cmd)[1]

        if help_param:
            self.LOG.info("Displaying usage for show alerts")
            return True, output

        if not ("Alert Id" in output or "total_records" in output):
            LOG.error(
                "Show alerts failed with error: %s", output)
            return False, output

        return True, output
