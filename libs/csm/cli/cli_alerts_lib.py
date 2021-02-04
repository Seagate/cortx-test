""" Library for csm alerts Operations """

import logging
from typing import Tuple
from libs.csm.cli.cortxcli_test_lib import CortxCliTestLib

LOG = logging.getLogger(__name__)


class CortxCliAlerts(CortxCliTestLib):
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
            acknowledge_alerts_cmd = "{} -ack".format(
                acknowledge_alerts_cmd)
        if help_param:
            acknowledge_alerts_cmd = "{} -h".format(acknowledge_alerts_cmd)

        output = self.execute_cli_commands(cmd=acknowledge_alerts_cmd)[1]
        if help_param:
            self.log.info("Displaying usage for acknowledge alerts")
            return True, output

        if "[Y/n]" not in output:
            return False, output

        output = self.execute_cli_commands(cmd=confirm)[1]
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
            show_alert_comment_cmd = "{} -h".format(show_alert_comment_cmd)

        if output_format:
            show_alert_comment_cmd = "{} -f {} {}".format(
                show_alert_comment_cmd, output_format, alert_id)

        else:
            show_alert_comment_cmd = "{} {}".format(
                show_alert_comment_cmd, alert_id)

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
        add_alert_comment_cmd = "{} {} {}".format(
            cmd, alert_id, comment_text)

        if help_param:
            add_alert_comment_cmd = "{} -h".format(
                cmd)

        output = self.execute_cli_commands(cmd=add_alert_comment_cmd)[1]
        if help_param:
            self.log.info("Displaying usage for add alert comment")
            return True, output

        if "[Y/n]" not in output:
            return False, output

        output = self.execute_cli_commands(cmd=confirm)[1]
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

    def help_option(
            self, command: str = None):
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
        output = self.execute_cli_commands(cmd=command)[1]

        # Checking for error response
        if "error" in output.lower() or "exception" in output.lower():
            self.log.error(
                "Checking help response for command %s failed with %s", (
                    command, output))
            return False, output

        return True, output
