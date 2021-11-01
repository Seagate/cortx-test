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
 HA: To test Publish the pod failure event in message bus to Hare - Node becomes unreachable (network interface is down).
"""
import logging
import pytest
import json
import time
import yaml
from config import CMN_CFG
from commons.helpers.node_helper import Node
from libs.ras.sw_alerts import SoftwareAlert
from commons.alerts_simulator.generate_alert_wrappers import \
    GenerateAlertWrapper

LOGGER = logging.getLogger(__name__)
ALERT_WRAP = GenerateAlertWrapper()


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

    def test_ha(self):
        """Verify Publish the pod failure event in message bus to Hare - Node becomes unreachable (network interface is down) """
        for index in range(0,3):
            LOGGER.info("Running test:Node"+ str(index))
            LOGGER.info("hostname: " + CMN_CFG["nodes"][index]["hostname"])
            LOGGER.info("password: " + CMN_CFG["nodes"][index]["password"])
            LOGGER.info("user: " + CMN_CFG["nodes"][index]["username"])
        LOGGER.info("Done: Setup operations finished.")
        try:
            LOGGER.info("pre-condition: subscribe.py, publish.py, test_receiver.py, daemon.py should be available in Cortx Stack root dirctory \n")
            response1 = self.node_obj.execute_cmd("/root/subscribe.py")
            LOGGER.info("1." + response1.decode("utf-8").strip() + " Subscribe event successfully")
            LOGGER.info("\n 2. Running test_receiver.py in background and Waiting for event to publish...")
            response2 = self.node_obj.execute_cmd("python /root/daemon.py")
            LOGGER.info(response2.decode("utf-8").strip())
            """ Induce network fault"""
            LOGGER.info("Induce network fault: ifdown eth1")
            response1 = ALERT_WRAP.create_network_port_fault(CMN_CFG["nodes"][1]["hostname"],CMN_CFG["nodes"][1]["username"], CMN_CFG["nodes"][1]["password"], { "device":"eth1"} )
            response2 = ALERT_WRAP.resolve_network_port_fault(CMN_CFG["nodes"][1]["hostname"],CMN_CFG["nodes"][1]["username"], CMN_CFG["nodes"][1]["password"], { "device":"eth1"})
            LOGGER.info(str(response1))
            LOGGER.info(str(response2))
            LOGGER.info("\n Publishing  the event... \n")
            response4 = self.node_obj.execute_cmd("/root/publish.py")
            LOGGER.info(response4.decode("utf-8").strip())
            LOGGER.info("\n Publish event successfully")
            LOGGER.info("\n 5. Event Message printing... \n")
            response5 = self.node_obj.execute_cmd("cat /root/file.txt")
            LOGGER.info(response5.decode("utf-8").strip())
            LOGGER.info("\n Event Message printed successfully")
            LOGGER.info("\n 6. Killng process test reciever...")
            response6 = self.node_obj.execute_cmd("pkill -f /root/test_receiver.py")
            LOGGER.info(response6.decode("utf-8").strip())
            LOGGER.info("Killed test_receiver successfully")
            LOGGER.info("\n 7. Removing pidfile...")
            response7 = self.node_obj.execute_cmd("rm -f /root/pidfile")
            LOGGER.info(response7.decode("utf-8").strip())
            LOGGER.info("Removed pidfile successfully") 
        except Exception as error:
            print(error)
            assert False
        assert True