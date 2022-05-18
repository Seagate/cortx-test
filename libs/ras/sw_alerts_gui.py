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
#

"""
RAS GUI utility methods
"""
import logging
import os
from datetime import datetime

from commons import Globals
from commons.utils.assert_utils import assert_true
from config import CMN_CFG
from robot_gui.utils.call_robot_test import trigger_robot

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class SoftwareAlertGUI:
    """
    This class contains common utility methods for RAS GUI related operations.
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

    def verify_sw_service_init(self, svc):
        """
        This function will verify setup initial stage of any service test
        """
        LOGGER.info("Start : verify_sw_service_inactive_alert")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_init_' + svc + \
                               "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_inactive_alert")

    def verify_sw_service_inactive_alert(self, svc):
        """
        This function will verify the sw service is in inactive state
        """
        LOGGER.info("Start : verify_sw_service_inactive_alert")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_inactive_alert_' + svc \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_inactive_alert")

    def verify_sw_service_inactive_alert_resolved(self, svc):
        """
        This function will verify the sw service is in inactive alert is now in resolved state
        """
        LOGGER.info("Start : verify_sw_service_inactive_alert_resolved")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_inactive_alert_resolved_'\
                               + svc + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_inactive_alert_resolved")

    def verify_sw_service_deactivat_alert(self, svc):
        """
        This function will verify the sw service is in deactivat state
        """
        LOGGER.info("Start : verify_sw_service_deactivat_alert")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_deactivat_alert_' \
                               + svc + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_deactivat_alert")

    def verify_sw_service_deactivat_alert_resolved(self, svc):
        """
        This function will verify the sw service is in deactivat alert is now in resolved state
        """
        LOGGER.info("Start : verify_sw_service_deactivat_alert_resolved")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_deactivat_alert_resolved' + \
                               svc + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_true(gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_deactivat_alert_resolved")
