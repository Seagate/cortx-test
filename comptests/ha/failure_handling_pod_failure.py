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
HA component test suite for stop cluster.
"""
import logging
import random
import time

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from commons.utils import assert_utils
from config import CMN_CFG
from commons.helpers.pods_helper import LogicalNode
from commons import constants as common_const
from commons import commands as common_cmd

LOGGER = logging.getLogger(__name__)


class TestFailureHandlingPodFailure:
    """
    Test suite for Pod Failure hadling
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
    @pytest.mark.tags("TEST-30218")
    def test_delete_pod(self):
        """
        This test tests delete pod using kubectl cmd
        """
        LOGGER.info("STARTED: Publish the pod failure event in message bus to Hare - Delete pod.")

        datapod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(datapod_list)
        print("################", datapod_list)
        pod_name = random.sample(datapod_list, 1)[0]
        LOGGER.info("Step 1: Delete data pod and check Pods status(kubectl delete pods <pod>)")
        LOGGER.info("Deleting pod %s", pod_name)
        delpod_time=time.time()
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=False)
        print("#################", delpod_time)
        assert resp, "Data pod didn't deleted successfully"
        LOGGER.info("Step 2: Check the node status.")
        time.sleep(30)
        resp1 = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp1)
        print("after delete", after_del)
        print("before delete", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        pod_list = self.node_master_list[0].get_all_pods\
            (pod_prefix=common_const.HA_POD_NAME_PREFIX)
        LOGGER.info("Get the HA pod hostname")
        ha_hostname = self.node_master_list[0].execute_cmd(common_cmd.K8S_GET_MGNT, read_lines=True)
        for line in ha_hostname:
            if "cortx-ha" in line:
                hapod_hostname = line.split()[6]
        print("Cortx HA pod running on: ", hapod_hostname)
        node_obj = LogicalNode(hostname=hapod_hostname,
                                        username="root",password="seagate1")
        time.sleep(20)
        cm = "tail -2 /mnt/fs-local-volume/local-path-provisioner" \
             "/pvc-b775c91c-1921-45e9-a3a4-ebc250137ef0_default_cortx-ha-fs-local-pvc-default" \
             "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cm)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        lt = output.split("{")[1].split(",")[-2].strip().split(":")[1].strip()
        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - Delete pod.")
