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
#

"""
RAS GUI utility methods
"""
import logging
import os
from datetime import datetime

from commons import Globals
from robot_gui.utils.call_robot_test import trigger_robot
from commons.utils.assert_utils import assert_true
from config import CMN_CFG

LOGGER = logging.getLogger(__name__)


class SoftwareAlertGUI():
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
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_init_' + svc \
                               + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
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
        assert_true( gui_response, 'GUI FAILED')
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
        assert_true( gui_response, 'GUI FAILED')
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
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_deactivat_alert")

    def verify_sw_service_deactivat_alert_resolved(self, svc):
        """
        This function will verify the sw service is in deactivat alert is now in resolved state
        """
        LOGGER.info("Start : verify_sw_service_deactivat_alert_resolved")
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + 'verify_sw_service_deactivat_alert_resolved' \
                               + svc + "_{:%Y_%m_%d_%H_%M_%S}".format(datetime.now())
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_true( gui_response, 'GUI FAILED')
        LOGGER.info("End : verify_sw_service_deactivat_alert_resolved")
