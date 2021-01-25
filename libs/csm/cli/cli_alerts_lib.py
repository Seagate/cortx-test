import logging
from typing import Tuple
from libs.csm.cli.cortxcli_test_lib import CortxCliTestLib

log = logging.getLogger(__name__)


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
            help_param: bool = False) -> Tuple[bool, str]:
        """
        This function will list alerts using cortxcli as per the provided parameters
        :param duration: Time period, for which we request alerts e.g., '30s', '5m', '8h', '2d' etc
        :param limit: No. of alerts to display
        :param output_format: Format of output like "table", "json" or "xml"
        :param other_param: '-s' to display all alerts, '-a' to display active alerts
        :param help_param: True for displaying help/usage
        :return: (Boolean/response)
        """
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
            log.error(
                "Show alerts failed with error: {0}".format(output))
            return False, output

        return True, output
