#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
HA Component test suit for pod restart
"""
import time
import random
import logging

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from config import CMN_CFG
from config import HA_CFG
from commons.utils import assert_utils
from commons.helpers.pods_helper import LogicalNode
from commons import constants as common_const
from commons import commands as common_cmd

LOGGER = logging.getLogger(__name__)


class TestRestartPod:
    """
    Test suite for Pod restart
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
        self.restored = True
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        output = self.node_master_list[0].execute_cmd(
            cmd=common_cmd.KUBECTL_GET_POD_CONTAINERS.format(pod_list[0]),
            read_lines=True)
        container_list = output[0].split()
        for container in container_list:
            res = self.node_master_list[0].send_k8s_cmd(
                operation="exec", pod=pod_name, namespace=common_const.NAMESPACE,
                command_suffix=f"-c {container} -- {common_cmd.SERVICE_HA_STATUS}", decode=True)
            assert_utils.assert_true(res, "HA services are not running")
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

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36017")
    def test_datapod_status_online_after_replicas(self):
        """
        This TC tests pod online event to component Hare -
        data pod comes online after data pod restart using replicas
        """
        LOGGER.info("STARTED: Publish the pod online event to component Hare- "
                    "Data pod comes online after data pod restart using replicas.")

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
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        # TODO Step-2,3 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-2,3 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("Step 4: Start pod by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully started the pod again by making replicas=1")

        # TODO Step-5,6 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-5,6 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("COMPLETED: Publish the pod online event to component Hare- "
                    "Data pod comes online after data pod restart using replicas.")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36161")
    def test_datapod_status_online_after_delete_deployment(self):
        """
        This TC tests pod online event to component Hare -
        data pod comes online after data pod restart using deployment
        """
        LOGGER.info("STARTED: Publish the pod online event to component Hare- "
                    "data pod comes online after data pod restart using deployment")

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

        # TODO Step-2,3 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-2,3 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("Step 4: Start the deleted pod by creating deployment")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully restored pod by %s way", self.restore_method)
        self.restore_pod = False

        # TODO Step-5,6 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-5,6 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("COMPLETED: Publish the pod online event to component Hare - "
                    "Data pod comes online after data pod restart using deployment")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36162")
    def test_pod_status_online_after_delete_pod(self):
        """
        This TC tests pod online event to component Hare -
        data pod comes online after data pod restart using kubectl delete pod.
        """
        LOGGER.info("STARTED: pod online event to component Hare -"
                    "data pod comes online after data pod restart using kubectl delete pod")

        datapod_list = self.node_master_list[0]. \
            get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(datapod_list)
        pod_name = random.sample(datapod_list, 1)[0]
        LOGGER.info("Step 1: Delete data pod and check Pods status(kubectl delete pods <pod>)")
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=False)
        assert_utils.assert_true(resp, "Data pod didn't deleted successfully")
        LOGGER.info("Step 1:Data pod deleted successfully")

        # TODO Step-2,3 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-2,3 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("Step 4: Check the node status.")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        resp = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        LOGGER.info("Step 4: New data pod created automatically by kubernetes")

        # TODO Step-5,6 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-5,6 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("COMPLETED: pod online event to component Hare -"
                    "data pod comes online after data pod restart using kubectl delete pod")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36193")
    def test_serverpod_status_online_after_delete_deployment(self):
        """
        Publish the pod online event to Hare -
        server pod comes online after server pod restart using deployment
        """
        LOGGER.info(
            "STARTED: Publish the pod online event to component Hare - "
            "Server pod comes online after server pod restart using deployment")

        LOGGER.info("Step 1: Shutdown the server pod by deleting deployment")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods\
            (pod_prefix=common_const.SERVER_POD_NAME_PREFIX)
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

        # TODO Step-2,3 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-2,3 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("Step 4: Start the deleted pod by creating deployment")
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully restored pod by %s way", self.restore_method)
        self.restore_pod = False

        # TODO Step-5,6 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-5,6 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("COMPLETED: Publish the pod online event to component Hare - "
                    "Server pod comes online after server pod restart using deployment")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36197")
    def test_serverpod_status_online_after_replicas(self):
        """
        This TC tests pod online event to component Hare-
        server pod comes online after server pod restart using replicas
        """

        LOGGER.info("STARTED: Publish the pod online event to component Hare- "
                    "Server pod comes online after server pod restart using replicas.")

        LOGGER.info("Step 1: Shutdown the data pod by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods\
            (pod_prefix=common_const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        # TODO Step-2,3 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-2,3 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("Step 4: Start pod by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully started the pod again by making replicas=1")

        # TODO Step-5,6 | Getting multiple events for pod delete operation - CORTX-28560
        # TODO Step-5,6 | Pod Online events are not seeing in the health monitor log - CORTX-28867

        LOGGER.info("COMPLETED: Publish the pod online event to component Hare- "
                    "Data pod comes online after data pod restart using replicas.")
