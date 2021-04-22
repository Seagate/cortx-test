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

"""Python library which will perform ras component related and system level operations."""
import os
import logging
import time
from typing import Tuple, Any, Union, List
from commons.helpers import node_helper
from commons import constants as cmn_cons
from commons import commands as common_commands
from commons.helpers.health_helper import Health
from libs.s3 import S3H_OBJ
from config import RAS_VAL
from commons.utils.system_utils import run_remote_cmd
from libs.ras import RASCoreLib

LOGGER = logging.getLogger(__name__)


class SoftwareAlert(RASCoreLib):
    """A class including functions for ras component related operations."""

    def __init__(self, host: str, username: str, password: str) -> None:
        """
        Method which initializes members of RASCoreLib.

        :param str host: node hostname
        :param str username: node username
        :param str password: node password
        """
        self.host = host
        self.username = username
        self.pwd = password
        self.node_obj = node_helper.Node(
            hostname=self.host, username=self.username, password=self.pwd)
        self.health_obj = Health(hostname=self.host, username=self.username,
                                 password=self.pwd)
        self.s3obj = S3H_OBJ

    def get_expected_csm_response(action):
        svc_fault_response ={"description":"{service_name} is failed state.",  
                        "alert_type": "fault",
                        "serverity": "critical",
                        "impact": "{service_name} service is unavailable.",
                        "recommendation": "Try to restart the service."}

        svc_timeout_response = {"description":"{service_name} in a {inactive/activating/reloading/deactivating} state for more than {threshold_inactive_time} seconds. ",  
                        "alert_type": "fault",
                        "serverity": "critical",
                        "impact": "{service_name} service is unavailable.",
                        "recommendation": "Try to restart the service."}

        svc_resolved_response ={"description":"{service} in active state.",  
                        "alert_type": "fault_resolved ",
                        "serverity": "informational",
                        "impact": "{service} service is available now.",
                        "recommendation": ""}

        if action == "start":
            systemctl_status = ""
            csm_response = svc_resolved_response

        elif action == "stop":
            csm_response = svc_fault_response

        elif action == "reload":
            csm_response = 

        elif action == "enable":
            csm_response =

        elif action == "disable":
            csm_response = 
        
    def get_svc_status(services:list):
        status ={}
        for svc in services:
            response = node_obj.send_systemctl_cmd("status",svc)
            status[svc]= 