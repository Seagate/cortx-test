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
"""Alert simulator library."""
import os
import logging
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG

LOGGER = logging.getLogger(__name__)


class AlertSetup(RASTestLib):
    """
    Setup lib for alert to be generated
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
        Function for setup of alerts of enclosure type
        :param alert_in_test: Name of the alert to be generated
        """
        LOGGER.info("Setup for : %s", alert_in_test)
        LOGGER.info("Putting enclosure values in CONF store")
        field_list = ["CONF_PRIMARY_IP", "CONF_PRIMARY_PORT",
                      "CONF_SECONDARY_IP", "CONF_SECONDARY_PORT",
                      "CONF_ENCL_USER", "CONF_ENCL_SECRET"]
        try:
            resp = self.update_enclosure_values(enclosure_vals=dict(
                zip(field_list, [None] * len(field_list))))
            return resp
        except BaseException as error:
            LOGGER.error("Error: %s", error)
            return False, error

    def raid_fun(self, alert_in_test: str):
        """
        Function for setup of alerts of raid type
        :param alert_in_test: Name of the alert to be generated
        """
        LOGGER.info("Setup for : %s", alert_in_test)
        md_device = RAS_VAL["raid_param"]["md0_path"]

        LOGGER.info(
            "Fetching the disks details from mdstat for RAID array %s", md_device)
        try:
            md_stat = self.nd_obj.get_mdstat()
            disks = md_stat["devices"][os.path.basename(md_device)]["disks"].keys()
            disk1 = RAS_VAL["raid_param"]["disk_path"].format(list(disks)[0])
            disk2 = RAS_VAL["raid_param"]["disk_path"].format(list(disks)[1])
            return True, md_device, disk1, disk2
        except BaseException as error:
            LOGGER.error("Error: %s", error)
            return False, error

    def server_fun(self, alert_in_test: str):
        """
        Function for setup of alerts of server type
        :param alert_in_test: Name of the alert to be generated
        """
        LOGGER.info("Setup for : %s", alert_in_test)
        LOGGER.info("Retaining the original/default config")
        try:
            cm_cfg = RAS_VAL["ras_sspl_alert"]
            self.retain_config(cm_cfg["file"]["original_sspl_conf"], False)
            return True, f'Retained {cm_cfg["file"]["sspl_conf_filename"]}'
        except BaseException as error:
            LOGGER.error("Error: %s", error)
            return False, error

    def server_fru_fun(self, alert_in_test: str):
        """
        Function for setup of alerts of server_fru type
        :param alert_in_test: Name of the alert to be generated
        """
        LOGGER.info("Setup for : %s", alert_in_test)
        try:
            if alert_in_test == 'NW_PORT_FAULT':
                LOGGER.info("Check status of all network interfaces")
                status = self.health_obj.check_nw_interface_status()
                for k, v in status.items():
                    if "DOWN" in v:
                        LOGGER.debug("%s is down. Please check network "
                                     "connections and restart tests.", k)
                        return False, f"{k} is down. Please check network " \
                                      f"connections and restart tests."

                return True, "All network interfaces are up."
        except BaseException as error:
            LOGGER.error("Error: %s", error)
            return False, error

    def get_runtime_input_params(self, alert_name: str = None):
        """
        Function to get input parameters at runtime
        :param alert_name: Name of the alert for which input parameters are
        required
        """
        mgmt_ip = CMN_CFG["nodes"][0]["ip"]
        setup_type = CMN_CFG['setup_type']
        nw_interfaces = RAS_TEST_CFG["network_interfaces"][setup_type]
        mgmt_device = nw_interfaces["MGMT"]
        public_data_device = nw_interfaces["PUBLIC_DATA"]

        switcher = {
            'MGMT_FAULT': {
                    'host_details': {'host': self.host,
                                     'host_user': self.username,
                                     'host_password': self.pwd},
                    'input_parameters': {'device': mgmt_device}
                },
            'PUBLIC_DATA_FAULT': {
                    'host_details': {'host': mgmt_ip,
                                     'host_user': self.username,
                                     'host_password': self.pwd},
                    'input_parameters': {'device': public_data_device}
                },
            'DG_FAULT_RESOLVED': {
                'host_details': None,
                'input_parameters': {"enclid": 0, "ctrl_name": ["A", "B"],
                                     "operation": "Enabled", "disk_group": "dg00",
                                     "phy_num": [], "poll": True}
            },
            'RAID_STOP_DEVICE_ALERT': {
                'host_details': None,
                'input_parameters': {"operation": "stop", "md_device": None,
                                     "disk": None}
            },
            'RAID_ASSEMBLE_DEVICE_ALERT': {
                'host_details': None,
                'input_parameters': {"operation": "assemble", "md_device": None,
                                     "disk": None},
            },
            'RAID_ADD_DISK_ALERT': {
                'host_details': None,
                'input_parameters': {"operation": "add_disk", "md_device": None,
                                     "disk": None}
            },
            'RAID_REMOVE_DISK_ALERT': {
                'host_details': None,
                'input_parameters': {"operation": "remove_disk", "md_device": None,
                                     "disk": None}
            }
        }

        alert = switcher.get(alert_name, None)
        if alert is None:
            return None, None
        else:
            return switcher[alert_name]['host_details'], \
                   switcher[alert_name]['input_parameters']
