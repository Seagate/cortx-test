#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
HA GUI utility methods
"""
import logging
import os

from robot_gui.utils.call_robot_test import trigger_robot
from commons.utils.assert_utils import assert_true
from config import CMN_CFG

LOGGER = logging.getLogger(__name__)

class HAGUILibs:
    """
    This class contains common utility methods for HA GUI related operations.
    """

    def __init__(self):
        self.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        self.csm_url = "https://" + self.mgmt_vip + "/#"
        self.cwd = os.getcwd()
        self.robot_gui_path = os.path.join(self.cwd + '/robot_gui/')
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
        gui_dict['log_path'] = self.cwd + '/log/latest/verify_cluster_state'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        if status == "degraded":
            gui_dict['tag'] = 'CHECK_IN_HEALTH_CLUSTER_DEGRADED'
        else:
            gui_dict['tag'] = 'CHECK_IN_HEALTH_CLUSTER_ONLINE'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_cluster_state")

    def verify_node_state(self, node_id, status):
        """
        This function will verify if node state failed / online
        """
        LOGGER.info("Start : verify_node_state")
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/verify_node_state'+ str(node_id + 1)
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "node_id:" + str(node_id + 1)]
        if status == "failed":
            gui_dict['tag'] = 'CHECK_IN_HEALTH_NODE_FAILED'
        else:
            gui_dict['tag'] = 'CHECK_IN_HEALTH_NODE_ONLINE'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_node_state")

    def verify_node_down_alert(self, node_id = 0):
        """
        This function will verify the node lost alert
        """
        LOGGER.info("Start : verify_node_down_alert")
        alert_description = f'The cluster has lost srvnode-{node_id+1}'
        LOGGER.info(alert_description)
        # TODO: If alert add hostname, update alert_description
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/verify_node_down_alert'+ str(node_id)
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_node_down_alert")

    def verify_node_back_up_alert(self, node_id = 0):
        """
        This function will verify the node joined back alert
        """
        LOGGER.info("Start : verify_node_back_up_alert")
        alert_description = f'has joined back the cluster. System is restored. Extra Info: host=srvnode-{node_id+1}'
        # TODO: If alert add hostname, update alert_description
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/verify_node_back_up_alert'+ str(node_id)
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_node_back_up_alert")

    def acknowledge_node_alerts_in_new_alerts(self):
        """
        This function will Acknowledge all alerts if present in new alert table already
        """
        LOGGER.info("Start : acknowledge_node_alerts_in_new_alerts")
        alert_description = 'The cluster has lost srvnode-'
        # TODO: If alert add hostname, update alert_description
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/acknowledge_node_alerts_in_new_alerts'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'ACKNOWLEDGE_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : acknowledge_node_alerts_in_new_alerts")

    def acknowledge_node_alerts_in_active_alerts(self):
        """
        This function will Acknowledge all alerts if present in active alert table already
        """
        LOGGER.info("Start : acknowledge_node_alerts_in_active_alerts")
        alert_description = 'has joined back the cluster. System is restored. Extra Info: host=srvnode-'
        # TODO: update alert_description if required 
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/acknowledge_node_alerts_in_active_alerts'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : acknowledge_node_alerts_in_active_alerts")

    def verify_network_interface_down_alert(self, eth_number = 0):
        """
        This function will verify the network interface down alert
        """
        LOGGER.info("Start : verify_network_interface_down_alert")
        alert_description = 'Network interface eth' # +eth_number + " is down" # TODO : VERIFY AND ADD
        # TODO: update alert_description if required
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/verify_network_interface_down_alert'+ eth_number
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_network_interface_down_alert")

    def verify_network_interface_back_up_alert(self, eth_number = 0):
        """
        This function will verify the network interface back alert
        """
        LOGGER.info("Start : verify_network_interface_back_up_alert")
        alert_description = 'Network interface eth' # +eth_number + " is down" # TODO : VERIFY AND ADD
        # TODO: update alert_description if required 
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/verify_network_interface_back_up_alert'+ eth_number
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_network_interface_back_up_alert")

    def acknowledge_network_interface_back_up_alerts(self):
        """
        This function will Acknowledge all alerts if present in active alert table already
        """
        LOGGER.info("Start : acknowledge_network_interface_back_up_alerts")
        alert_description = 'Network interface eth' # +eth_number + " is down" # TODO : VERIFY AND ADD
        # TODO: update alert_description if required 
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/acknowledge_network_interface_back_up_alerts'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : acknowledge_network_interface_back_up_alerts")

    def assert_if_network_interface_down_alert_present(self):
        """
        if we have any network port down before starting test tests, we should not continue the tests
        This function will check if any "network interface ethX down" alert is present, we should not continue the tests.
        This function will assert if network interface down alert in new alert table already present
        """
        LOGGER.info("Start : assert_if_network_interface_down_alert_present")
        alert_description = 'Network interface eth'
        # TODO: update alert_description if required
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/assert_if_network_interface_down_alert_present'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['test'] = 'CHECK_IN_NEW_ALERTS_AND_FAIL'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : assert_if_network_interface_down_alert_present")
