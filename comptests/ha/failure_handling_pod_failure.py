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
from config import CMN_CFG
from config import HA_TEST_CONFIG_PATH
from commons.utils import assert_utils
from commons.helpers.pods_helper import LogicalNode
from commons import constants as common_const
from commons import commands as common_cmd

LOGGER = logging.getLogger(__name__)


class TestFailureHandlingPodFailure:
    """
    Test suite for Pod Failure handling
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
        assert_utils.assert_true(resp[0], resp[1])
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

        datapod_list = self.node_master_list[0]. \
            get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(datapod_list)
        pod_name = random.sample(datapod_list, 1)[0]
        LOGGER.info("Step 1: Delete data pod and check Pods status(kubectl delete pods <pod>)")
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=False)
        assert resp, "Data pod didn't deleted successfully"
        LOGGER.info("Step 1:Data pod deleted successfully")

        LOGGER.info("Step 2: Check the node status.")
        time.sleep(HA_TEST_CONFIG_PATH["common_params"]["30sec_delay"])
        resp1 = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp1)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        LOGGER.info("Step 2: New data pod created automatically by kubernetes")

        LOGGER.info("Step 3: Check pod failure alert.")
        LOGGER.info("Step 4: Correct event and content should be published to component Hare.")
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
        pvc_list = node_obj.execute_cmd \
            ("ls /mnt/fs-local-volume/local-path-provisioner/", read_lines=True)
        hapvc = None
        for hapvc in pvc_list:
            if "cortx-ha" in hapvc:
                hapvc = hapvc.replace("\n", "")
                print("hapvc list", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        event_type = output.split("{")[1].split(",")[1].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(event_type, "failed", "Event type is failed")
        LOGGER.info("Step 3: Pod failure alert triggered")
        ha_gen_id = output.split("{")[2].split(",")[0].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(pod_name, ha_gen_id, "Deleted Pod Name does not match")
        LOGGER.info("HA pod generation ID %s", ha_gen_id)
        LOGGER.info("Step 4: Correct event and contents published to component Hare.")
        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - Delete pod.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30220")
    def test_delete_pod_replicaset_down(self):
        """
        This test tests delete pod by scalling down pod(replica=0)
        """
        LOGGER.info(
            "STARTED: Publish the pod failure event in message bus to Hare - "
            "Delete pod using replica set.")

        LOGGER.info("Step 1: Shutdown the data pod by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check pod failure alert.")
        LOGGER.info("Step 4: Correct event and content should be published to component Hare.")
        ha_hostname = self.node_master_list[0].execute_cmd(common_cmd.K8S_GET_MGNT, read_lines=True)
        for line in ha_hostname:
            if "cortx-ha" in line:
                hapod_hostname = line.split()[6]
        LOGGER.info("Cortx HA pod running on: %s ", hapod_hostname)
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == hapod_hostname:
                node_obj = LogicalNode(hostname=hapod_hostname,
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
        pvc_list = node_obj.execute_cmd \
            (common_cmd.HA_LOG_PVC, read_lines=True)
        LOGGER.info("Getting the HA pod pvc log dir %s", node_obj)
        hapvc = None
        for hapvc in pvc_list:
            if "cortx-ha" in hapvc:
                hapvc = hapvc.replace("\n", "")
                print("hapvc list", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        event_type = output.split("{")[1].split(",")[1].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(event_type, "failed", "Event type is failed")
        LOGGER.info("Step 3: Pod failure alert triggered")
        ha_gen_id = output.split("{")[2].split(",")[0].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(pod_name, ha_gen_id, "Deleted Pod Name does not match")
        LOGGER.info("HA pod generation ID %s", ha_gen_id)
        LOGGER.info("Step 4: Correct event and contents published to component Hare.")
        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod - delete replica replicaset")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30222")
    def test_delete_pod_deployment(self):
        """
        This test tests delete pod by deleting deployment
        """
        LOGGER.info(
            "STARTED: Publish the pod failure event in message bus to Hare - "
            "Delete pod using deployment.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
        " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment", pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check pod failure alert.")
        LOGGER.info("Step 4: Correct event and content should be published to component Hare.")
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
        pvc_list = node_obj.execute_cmd \
            ("ls /mnt/fs-local-volume/local-path-provisioner/", read_lines=True)
        LOGGER.info("Getting the HA pod pvc log dir %s", node_obj)
        hapvc = None
        for hapvc in pvc_list:
            if "cortx-ha" in hapvc:
                hapvc = hapvc.replace("\n", "")
                print("hapvc list", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        event_type = output.split("{")[1].split(",")[1].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(event_type, "failed", "Event type is failed")
        LOGGER.info("Step 3: Pod failure alert triggered")
        ha_gen_id = output.split("{")[2].split(",")[0].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(pod_name, ha_gen_id, "Deleted Pod Name does not match")
        LOGGER.info("HA pod generation ID %s", ha_gen_id)
        LOGGER.info("Step 4: Correct event and contents published to component Hare.")
        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod deployment - delete deployment")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30219")
    def test_delete_pod_forcefully(self):
        """
        This test tests delete pod using kubectl delete forcefully
        """
        LOGGER.info("STARTED: Publish the pod failure event in message bus to Hare - "
                    "Delete pod forcefully.")

        datapod_list = self.node_master_list[0]. \
            get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(datapod_list)
        pod_name = random.sample(datapod_list, 1)[0]
        LOGGER.info("Step 1: Delete data pod and check Pods status"
                    "(kubectl delete pods <pod>) forcefully")
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=False)
        assert resp, "Data pod didn't deleted successfully"
        LOGGER.info("Step 1:Data pod deleted successfully")

        LOGGER.info("Step 2: Check the node status.")
        time.sleep(HA_TEST_CONFIG_PATH["common_params"]["30sec_delay"])
        resp1 = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp1)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        LOGGER.info("Step 2: New data pod created automatically by kubernetes")

        LOGGER.info("Step 3: Check pod failure alert.")
        LOGGER.info("Step 4: Correct event and content should be published to component Hare.")
        ha_hostname = self.node_master_list[0].execute_cmd(common_cmd.K8S_GET_MGNT, read_lines=True)
        for line in ha_hostname:
            if "cortx-ha" in line:
                hapod_hostname = line.split()[6]
        LOGGER.info("Cortx HA pod running on: ", hapod_hostname)
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == hapod_hostname:
                node_obj = LogicalNode(hostname=hapod_hostname,
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
        pvc_list = node_obj.execute_cmd \
            ("ls /mnt/fs-local-volume/local-path-provisioner/", read_lines=True)
        hapvc = None
        for hapvc in pvc_list:
            if "cortx-ha" in hapvc:
                hapvc = hapvc.replace("\n", "")
                print("hapvc list", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        if isinstance(output, bytes):
            output = str(output, 'UTF-8')
        event_type = output.split("{")[1].split(",")[1].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(event_type, "failed", "Event type is failed")
        LOGGER.info("Step 3: Pod failure alert triggered")
        ha_gen_id = output.split("{")[2].split(",")[0].split(":")[1].strip().replace('"', '')
        assert_utils.assert_exact_string(pod_name, ha_gen_id, "Deleted Pod Name does not match")
        LOGGER.info("HA pod generation ID %s", ha_gen_id)
        LOGGER.info("Step 4: Correct event and contents published to component Hare.")
        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod forcefully.")
