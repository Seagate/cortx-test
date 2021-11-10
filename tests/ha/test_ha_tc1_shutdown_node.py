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
# please email opensource@seagate.com or cortx-questions@seagate.com

"""
 HA: Publish the pod failure event in message bus to Hare - Shutdown node.
"""
import logging
import pytest
import json
import time
from config import CMN_CFG
from commons.helpers.node_helper import Node

LOGGER = logging.getLogger(__name__)

class TestHA:
    @classmethod
    def setup_class(cls):
        """Setup operations."""
        LOGGER.info("STARTED: Setup Module operations")
        cls.node_list = []
        for node in range(len(CMN_CFG["nodes"])):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                        password=cls.passwd)
            cls.node_list.append(cls.node_obj)
            cls.sw_alert_obj = SoftwareAlert(cls.host, cls.uname, cls.passwd)
            LOGGER.info("Running test:Node"+ str(node))
            LOGGER.info("hostname: " + CMN_CFG["nodes"][node]["hostname"])
            LOGGER.info("password: " + CMN_CFG["nodes"][node]["password"])
            LOGGER.info("password: " + CMN_CFG["nodes"][node]["password"])
            LOGGER.info("user: " + CMN_CFG["nodes"][node]["username"])
        LOGGER.info("Done: Setup operations finished.")
        
    def test_ha(self):
        """ TC1: To verify publish the pod failure event in message bus to Hare - Shutdown node. """
        try:
            """ Running test_receiver.py in background and Waiting for event to publish...") """
            response1 = self.node_obj.execute_cmd("python /root/daemon.py")
            LOGGER.info(response1.decode("utf-8").strip())
            """ Step1: Shutdown down the worker node """            
            LOGGER.info("Shutdown down the node...")
            response2 = self.node_list[1].shutdown_node()
            assert response2, "Failed to shutdown node "
            """ Step2: Node status """
            TODO:
            """ Step3: Check node alert """
            TODO:
            """Step4: Publish the event"""
            response5 = self.node_obj.execute_cmd("cat /root/file.txt")
            LOGGER.info(response5.decode("utf-8").strip())
            """Cleanup steps """
            response6 = self.node_obj.execute_cmd("pkill -f /root/test_receiver.py")
            LOGGER.info(response6.decode("utf-8").strip())
            response7 = self.node_obj.execute_cmd("rm -f /root/pidfile")
            LOGGER.info(response7.decode("utf-8").strip())
        except Exception as error:
            LOGGER.error(error)
            assert False
        assert True