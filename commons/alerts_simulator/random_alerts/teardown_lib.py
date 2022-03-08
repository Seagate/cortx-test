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
"""Library for running teardown after alert is resolved by Cortx."""
import logging
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from config import CMN_CFG, RAS_VAL

LOGGER = logging.getLogger(__name__)


class AlertTearDown(RASTestLib):
    """
    Library for running teardown after alert is resolved
    """
    def __init__(
            self,
            host: str = CMN_CFG["nodes"][0]["host"],
            username: str = CMN_CFG["nodes"][0]["username"],
            password: str = CMN_CFG["nodes"][0]["password"]) -> None:
        """
        Method initializes members of AlertSetupLib and its parent class

        :param str host: host
        :param str username: username
        :param str password: password
        """
        self.host = host
        self.username = username
        self.pwd = password
        self.nd_obj = Node(hostname=host, username=username, password=password)
        super().__init__(host, username, password)

    def enclosure_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of enclosure type
        """
        LOGGER.info("No teardown needed for %s", alert_in_test)

    def raid_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of raid type
        """
        LOGGER.info("No teardown needed for %s", alert_in_test)

    def server_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of server type
        """
        LOGGER.info("Teardown for: %s", alert_in_test)
        LOGGER.info("Retaining the original/default config")
        try:
            cm_cfg = RAS_VAL["ras_sspl_alert"]
            self.retain_config(cm_cfg["file"]["original_sspl_conf"], True)
            # TODO: Restore changed values in config files
            return True, "Retained sspl.conf"
        except BaseException as error:
            LOGGER.error("Error: %s", error)
            return False, error

    def server_fru_fun(self, alert_in_test: str):
        """
        Function for teardown of alerts of server_fru type
        """
        LOGGER.info("Teardown for: %s", alert_in_test)
        try:
            if alert_in_test == 'NW_PORT_FAULT':
                LOGGER.info("Check status of all network interfaces")
                status = self.health_obj.check_nw_interface_status()
                for k, v in status.items():
                    if "DOWN" in v:
                        LOGGER.info("%s is down. Please check network connections and "
                                    "restart tests.", k)
                        assert False, f"{k} is down. Please check network connections " \
                                      f"and restart tests."
                return True, "All network interfaces are up."
        except BaseException as error:
            LOGGER.error("Error: %s", error)
            return False, error
