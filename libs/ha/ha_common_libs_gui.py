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

"""
HA GUI utility methods
"""
import logging
import os
from datetime import datetime

from commons import Globals
from commons.utils.assert_utils import assert_true
from config import CMN_CFG
from robot_gui.utils.call_robot_test import trigger_robot

LOGGER = logging.getLogger(__name__)


class HAGUILibs:
    """
    This class contains common utility methods for HA GUI related operations.
    """

    def __init__(self):
        self.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        self.csm_url = "https://" + self.mgmt_vip + "/#"
        self.robot_gui_path = os.path.join(os.getcwd() + '/robot_gui/')
        self.robot_test_path = self.robot_gui_path + 'testsuites/gui/.'
        self.browser_type = 'chrome'
        self.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        self.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]

    def verify_cluster_state(self, status):
        """
        This function will verify if cluster state degraded / online
        """
        LOGGER.info("Start : verify_cluster_state")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_cluster_state_' \
                               + "{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        if status == "degraded":
            gui_dict['tag'] = 'CHECK_IN_HEALTH_CLUSTER_DEGRADED'
        else:
            gui_dict['tag'] = 'CHECK_IN_HEALTH_CLUSTER_ONLINE'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_cluster_state")

    def verify_node_state(self, node_id, status):
        """
        This function will verify if node state failed / online
        """
        LOGGER.info("Start : verify_node_state")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_node_state_' + str(node_id) \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "node_id:" + str(node_id)]
        if status == "failed":
            gui_dict['tag'] = 'CHECK_IN_HEALTH_NODE_FAILED'
        else:
            gui_dict['tag'] = 'CHECK_IN_HEALTH_NODE_ONLINE'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_node_state")

    def verify_node_down_alert(self, node_id=0):
        """
        This function will verify the node lost alert
        """
        LOGGER.info("Start : verify_node_down_alert")
        alert_description = f'The cluster has lost srvnode-{node_id + 1}'
        LOGGER.info(alert_description)
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_node_down_alert_' + str(node_id) \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_node_down_alert")

    def verify_node_back_up_alert(self, node_id=0):
        """
        This function will verify the node joined back alert
        """
        LOGGER.info("Start : verify_node_back_up_alert")
        alert_description = f'has joined back the cluster. System is restored. ' \
                            f'Extra Info: host=srvnode-{node_id + 1}'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_node_back_up_alert_' + str(node_id) \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_node_back_up_alert")

    def acknowledge_node_alerts_in_new_alerts(self):
        """
        This function will Acknowledge all alerts if present in new alert table already
        """
        LOGGER.info("Start : acknowledge_node_alerts_in_new_alerts")
        alert_description = 'The cluster has lost srvnode-'
        # TODO: If alert add hostname, update alert_description
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'acknowledge_node_alerts_in_new_alerts' \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'ACKNOWLEDGE_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : acknowledge_node_alerts_in_new_alerts")

    def acknowledge_node_alerts_in_active_alerts(self):
        """
        This function will Acknowledge all alerts if present in active alert table already
        """
        LOGGER.info("Start : acknowledge_node_alerts_in_active_alerts")
        alert_description = 'has joined back the cluster. System is restored. ' \
                            'Extra Info: host=srvnode-'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'acknowledge_node_alerts_in_active_alerts' \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : acknowledge_node_alerts_in_active_alerts")

    def verify_network_interface_down_alert(self, eth_number=0):
        """
        This function will verify the network interface down alert
        """
        LOGGER.info("Start : verify_network_interface_down_alert")
        alert_description = f'Network interface eth{eth_number} is down'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_network_interface_down_alert_' \
                               + str(eth_number) + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_network_interface_down_alert")

    def verify_network_interface_back_up_alert(self, eth_number=0):
        """
        This function will verify the network interface back alert
        """
        LOGGER.info("Start : verify_network_interface_back_up_alert")
        alert_description = f'Network interface eth{eth_number} is up'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_network_interface_back_up_alert' \
                               + str(eth_number) + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_network_interface_back_up_alert")

    def acknowledge_network_interface_back_up_alerts(self):
        """
        This function will Acknowledge all alerts if present in active alert table already
        """
        LOGGER.info("Start : acknowledge_network_interface_back_up_alerts")
        alert_description = 'Network interface eth'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'acknowledge_network_interface_back_up_alerts' \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : acknowledge_network_interface_back_up_alerts")

    def assert_if_network_interface_down_alert_present(self):
        """
        if we have any network port down before starting test tests,
        we should not continue the tests
        This function will check if any "network interface ethX down" alert is present,
        we should not continue the tests.
        This function will assert if network interface down alert in new alert table already present
        """
        LOGGER.info("Start : assert_if_network_interface_down_alert_present")
        alert_description = 'Network interface eth'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'assert_if_network_interface_down_alert_present' \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['test'] = 'CHECK_IN_NEW_ALERTS_AND_FAIL'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : assert_if_network_interface_down_alert_present")
