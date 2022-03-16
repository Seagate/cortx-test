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
HA component test suite for pod failure.
"""
import logging
import random
import time

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from config import CMN_CFG
from config import HA_CFG
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
        cls.restored = True
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
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
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
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
        self.restore_pod = self.restore_method = self.deployment_name = None
        self.deployment_backup = None
        self.restored = True
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30218")
    def test_delete_pod(self):
        """
        This test tests Publish the pod failure event to Hare - Delete pod)
        """
        LOGGER.info("STARTED: Publish the pod failure event in message bus to Hare - Delete pod.")

        datapod_list = self.node_master_list[0]. \
            get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(datapod_list)
        pod_name = random.sample(datapod_list, 1)[0]
        LOGGER.info("Step 1: Delete data pod and check Pods status(kubectl delete pods <pod>)")
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=False)
        assert_utils.assert_true(resp, "Data pod didn't deleted successfully")
        LOGGER.info("Step 1:Data pod deleted successfully")

        LOGGER.info("Step 2: Check the node status.")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        resp = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        LOGGER.info("Step 2: New data pod created automatically by kubernetes")

        LOGGER.info("Step 3: Check pod failure alert.")
        LOGGER.info("Step 4: Correct event and content should be published to component Hare.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        node_obj = None
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        hapvc = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("HA log pvc list %s", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        LOGGER.info("Events output :%s", output)

        # TODO: Pod failure alert verification - EOS-28560
        # TODO: Correct event and contents published to component Hare - EOS-28560

        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - Delete pod.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30220")
    def test_delete_pod_replicaset_down(self):
        """
        This test tests delete pod by scaling down pod(replica=0)
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
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        node_obj = None
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        LOGGER.info("Getting the HA pod pvc log dir %s", node_obj)
        hapvc = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("HA log pvc list %s", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        LOGGER.info("Events output :%s", output)

        # TODO: Pod failure alert verification - EOS-28560
        # TODO: Correct event and contents published to component Hare - EOS-28560

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
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        node_obj = None
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        LOGGER.info("Getting the HA pod pvc log dir %s", node_obj)
        hapvc = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("HA log pvc list %s", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        LOGGER.info("Events output :%s", output)

        # TODO: Pod failure alert verification - EOS-28560
        # TODO: Correct event and contents published to component Hare - EOS-28560

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
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=True)
        assert_utils.assert_true(resp, "Data pod didn't deleted successfully")
        LOGGER.info("Step 1:Data pod deleted successfully")

        LOGGER.info("Step 2: Check the node status.")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        resp = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        LOGGER.info("Step 2: New data pod created automatically by kubernetes")

        LOGGER.info("Step 3: Check pod failure alert.")
        LOGGER.info("Step 4: Correct event and content should be published to component Hare.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        node_obj = None
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        hapvc = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("HA log pvc list %s", hapvc)
                break
        cmd_halog = "tail -5 /mnt/fs-local-volume/local-path-provisioner/" \
                    + hapvc + "/log/ha/*/health_monitor.log | grep 'to component hare'"
        output = node_obj.execute_cmd(cmd_halog)
        LOGGER.info("Events output :%s", output)

        # TODO: Pod failure alert verification - EOS-28560
        # TODO: Correct event and contents published to component Hare - EOS-28560

        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod forcefully.")

