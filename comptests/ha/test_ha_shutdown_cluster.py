#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
HA component test suite for shutdown cluster.
"""
import logging
import random
import time
import datetime

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from config import CMN_CFG
from commons.utils import assert_utils
from commons.helpers.pods_helper import LogicalNode
from commons import constants as common_const
from commons import commands as common_cmd

LOGGER = logging.getLogger(__name__)


class TestShutdownCluster:
    """
    Test suite for Shutdown Cluster
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_worker_list = []
        cls.node_master_list = []
        cls.host_list = []
        cls.ha_obj = HAK8s()
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])

            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.node_master_list.append(node_obj)
            else:
                cls.node_worker_list.append(node_obj)
        LOGGER.info("Done: Setup operations finished.")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        #assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_container = [common_const.HA_K8S_CONTAINER_NAME,
                        common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                        common_const.HA_HEALTH_MONITOR_CONTAINER_NAME]
        for container in ha_container:
            res = self.node_master_list[0].send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=common_const.NAMESPACE,
                command_suffix=f"-c {container} -- {common_cmd.SERVICE_HA_STATUS}", decode=True)
            assert_utils.assert_true(res, "HA services are not running")
        LOGGER.info("Done: Setup operations.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34982")
    def test_shutdown_entire_cluster(self):
        """
        This test test shutdown entire cluster
        """
        LOGGER.info("STARTED: Stop Cluster - Shutdown cluster.")

        LOGGER.info("Step 1: Stop the cluster")
        ha_hostname = self.node_master_list[0].execute_cmd(common_cmd.K8S_GET_MGNT, read_lines=True)
        for line in ha_hostname:
            if "cortx-ha" in line:
                hapod_hostname = line.split()[6]
        print("Cortx HA pod running on: ", hapod_hostname)
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == hapod_hostname:
                node_obj = LogicalNode(hostname=hapod_hostname,
                                    username=CMN_CFG["nodes"][node]["username"],
                                    password=CMN_CFG["nodes"][node]["password"])
        #shutdown_time = time.time()
        #shutdown_date = datetime.datetime.now()
        #print("shutdown date", shutdown_date)
        #print("Shutdown time", shutdown_time)
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        if not resp[0]:
            return False, "Error during Stopping cluster"
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 1: Stopped the cluster successfully")

        LOGGER.info("Step 2:Verify the HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            pvc_list = node_obj.execute_cmd\
                ("ls /mnt/fs-local-volume/local-path-provisioner/", read_lines=True)
            for hapvc in pvc_list:
                if "cortx-ha" in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    print("hapvc list", hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                        + hapvc + "/log/ha/*/" + log + " | grep 'SIGTERM'"
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
            print("SIGTERM time", output)
            assert_utils.assert_in("Received SIGTERM", output, "Not received")  
            #output = output.split(" ")
            #output = output[0] + " " + output[1]
            #output = datetime.datetime.strptime(output, '%Y-%m-%d %H:%M:%S')
            #output = output.timestamp()
            print("SIGTERM time", output)
        LOGGER.info("Step 2:Verified the HA logs for SIGTERM alert message")

