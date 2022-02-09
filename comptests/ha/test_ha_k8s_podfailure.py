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

""" HA component level test cases for pod failure events """

import logging
import pytest
import json
import time
from config import CMN_CFG
from commons.helpers.pods_helper import LogicalNode
from commons import commands as comm
from commons.utils import assert_utils
from commons.alerts_simulator.generate_alert_wrappers import \
    GenerateAlertWrapper
from libs.ras.sw_alerts import SoftwareAlert

LOGGER = logging.getLogger(__name__)

class TestHA:
    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.sw_alert_obj_list = []
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            cls.sw_alert_obj = SoftwareAlert(CMN_CFG["nodes"][node]["hostname"], CMN_CFG["nodes"][node]["username"],
                                             CMN_CFG["nodes"][node]["password"])
            cls.sw_alert_obj_list.append(cls.sw_alert_obj)
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        LOGGER.info("Done: Setup operations finished.")

    @pytest.mark.tags("TEST-30212")
    def test_30212(self):
        """"TC1: To verify publish the pod failure event in message bus to Hare - Shutdown node """
        LOGGER.info("Running test_receiver.py in background and waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Step 1: Shutdown down the node.")
        resp = self.worker_node_list[0].shutdown_node()
        assert resp, "Failed to shutdown node "
        # TODO: Step2: Node Status
        # TODO: Step3: Node alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        LOGGER.info("ENDED: Teardown Operation")


    def test_ha2(self):
        """ TC2: To verify Publish the pod failure event in message bus to Hare - Node becomes unreachable (network interface is down)"""
        LOGGER.info(" Running test_receiver.py in background and Waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Step1: Induce network fault")
        ALERT_WRAP = GenerateAlertWrapper()
        resp = ALERT_WRAP.create_network_port_fault(CMN_CFG["nodes"][1]["hostname"],CMN_CFG["nodes"][1]["username"], CMN_CFG["nodes"][1]["password"], { "device":"eth1"} )
        assert resp, "Failed to induce network fault"
        resp = ALERT_WRAP.resolve_network_port_fault(CMN_CFG["nodes"][1]["hostname"],CMN_CFG["nodes"][1]["username"], CMN_CFG["nodes"][1]["password"], { "device":"eth1"})
        assert resp, "Failed to induce network fault"
        # TODO: Step2: Node Status
        # TODO: Step3: Node alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        LOGGER.info("ENDED: Teardown Operation")

    @pytest.mark.tags("TEST-30218")
    def test_3018(self):
        """ TC3: To verify Publish the pod failure event in message bus to Hare - Delete pod """
        LOGGER.info("Running test_receiver.py in background and Waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Check that the host is pinging")
        resp= self.master_node_obj.execute_cmd(cmd=common_cmd.CMD_PING.format(master_node_obj.hostname), read_lines=True)
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS, read_lines=True)
        # This is sample pod_name used, later might be changed
        pod_name='tomcat' 
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS) + pod_name + " -o jsonpath={.status.phase}"
        resp = resp[0].strip()
        if resp == "Running":
            LOGGER.info("The status of pod is Running")
            cmd = self.master_node_obj.execute_cmd(cmd=comm.K8S_DELETE_POD.format(pod_name))
        elif resp == "Pending":
            LOGGER.info("The status of pod is ContainerCreating")
        # TODO: Step2: Node Status
        # TODO: Step3: Node     alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        LOGGER.info("ENDED: Teardown Operation")

    @pytest.mark.tags("TEST-30219")
    def test_30219(self):
        """ TC4: To Verify Publish the pod failure event in message bus to Hare - Delete pod forcefully """
        LOGGER.info("Running test_receiver.py in background and Waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Check that the host is pinging")
        resp= node_obj.execute_cmd(cmd=common_cmd.CMD_PING.format(node_obj.hostname), read_lines=True)
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS, read_lines=True)
        # This is sample pod_name used, later might be changed
        pod_name='tomcat' 
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS) + pod_name + " -o jsonpath={.status.phase}"
        resp = resp[0].strip()
        if resp == "Running":
            LOGGER.info("The status of pod is Running")
            cmd = self.master_node_obj.execute_cmd(cmd=comm.K8S_DELETE_POD.format(pod_name) + " --grace-period=0 --force")
        elif resp == "Pending":
            LOGGER.info("The status of pod is ContainerCreating")
        # TODO: Step2: Node Status
        # TODO: Step3: Node alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        LOGGER.info("ENDED: Teardown Operation")

    @pytest.mark.tags("TEST-30220")
    def test_30220(self):
        """TC5: To verify Publish the pod failure - Stop pod using replicaset"""
        LOGGER.info("Running test_receiver.py in background and Waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Check that the host is pinging")
        resp= node_obj.execute_cmd(cmd=common_cmd.CMD_PING.format(node_obj.hostname), read_lines=True)
        #Note: deployement.yaml file which may change once cortx-stack+ kubernetes is available
        resp = self.master_node_obj.execute_cmd("kubectl create -f /root/deployment.yaml", \
                                                read_lines=True)
        resp = resp[0].strip()
        if resp == "replicaset.apps/my-replicaset created":
            LOGGER.info("The replicaset is successfully created")
        elif resp.find("already exists"):
            resp = self.master_node_obj.execute_cmd("kubectl delete rs my-replicaset")
            LOGGER.info("Replicaset delete successfully")            
        resp = self.master_node_obj.execute_cmd("kubectl get replicaset my-replicaset")
        LOGGER.info("Check that the host is pinging")
        resp= node_obj.execute_cmd(cmd=common_cmd.CMD_PING.format(node_obj.hostname), read_lines=True)
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS, read_lines=True)
        resp = self.master_node_obj.execute_cmd("kubectl scale --replicas=0 replicaset my-replicaset")
        # TODO: Step2: Node Status
        # TODO: Step3: Node alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        resp = self.master_node_obj.execute_cmd("kubectl scale --replicas=1 replicaset my-replicaset")
        LOGGER.info("ENDED: Teardown Operation")

    @pytest.mark.tags("TEST-30221")
    def test_30221(self):
        """TC6: To verify Publish the pod online event in message bus to Hare - deployment stage, pods is online """
        LOGGER.info("Running test_receiver.py in background and Waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Check that the host is pinging")
        resp= node_obj.execute_cmd(cmd=common_cmd.CMD_PING.format(node_obj.hostname), read_lines=True)
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS, read_lines=True)
        # This is sample pod_name used, later might be changed
        pod_name='tomcat' 
        cmd1 = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS + pod_name + " -o jsonpath={.status.phase}")
        resp = str(cmd1)[2:-2]
        LOGGER.info(resp)
        if resp == "Running":
            LOGGER.info("The status of pod is Online")
        elif resp == "Pending":
            LOGGER.info("The status of pod is Pending")
        # TODO: Step2: Node Status
        # TODO: Step3: Node alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        LOGGER.info("ENDED: Teardown Operation")

    def test_ha7(self):
        """Verify Publish the pod online event in message bus to Hare - restart node"""
        LOGGER.info("Running test_receiver.py in background and Waiting for event to publish...")
        resp = self.master_node_obj.execute_cmd("python /root/daemon.py")
        LOGGER.info("Step1: Restart the node ")
        resp = self.sw_alert_obj_list[1].restart_node()
        """ List pod status after node restart"""
        resp = self.master_node_obj.execute_cmd(cmd=comm.K8S_GET_PODS, read_lines=True)
        # TODO: Step2: Node Status
        # TODO: Step3: Node alert
        LOGGER.info("Step 4: Publish the event")
        resp = self.master_node_obj.execute_cmd("cat /root/file.txt")

        yield
        # Perform the clean up for each test.
        LOGGER.info("STARTED: Teardown Operation")
        resp = self.master_node_obj.execute_cmd("pkill -f /root/test_receiver.py")
        resp = self.master_node_obj.execute_cmd("rm -f /root/pidfile")
        LOGGER.info("ENDED: Teardown Operation")

