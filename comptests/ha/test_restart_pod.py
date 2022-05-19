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
HA Component test suit for pod restart
"""
import time
import random
import logging

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from libs.ha.ha_comp_libs import HAK8SCompLib
from config import CMN_CFG
from config import HA_CFG
from commons.utils import assert_utils
from commons.helpers.pods_helper import LogicalNode
from commons import constants as common_const

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
        cls.ha_obj = HAK8s()
        cls.ha_comp_obj = HAK8SCompLib()
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
        LOGGER.info("Checking if all the ha services are up and running")
        resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        assert_utils.assert_true(resp, "HA services are not running")
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
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} "
                                              "way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")
        LOGGER.info("Done: Teardown completed.")

    @staticmethod
    def get_node_resource_id(resp_dict, status):
        """
        This is a local method to verify the status and get node and resource ids
        :param resp_dict: halog properties
        :param status: status need to be checked
        :return: node and resource id as tuple
        """
        source_list = resp_dict['source']
        resource_type_list = resp_dict['resource_type']
        resource_status_list = resp_dict['resource_status']
        generation_id_list = resp_dict['generation_id']
        node_id = resp_dict['node_id']
        resource_id = resp_dict['resource_id']
        for index, (data1, data2, data3) in enumerate(zip(source_list, resource_type_list,
                                                          resource_status_list)):
            assert_utils.assert_equal(data1, 'monitor',
                                      f"Source of {generation_id_list[index]} is not from monitor")
            assert_utils.assert_equal(data2, 'node',
                                      f"Resource of {generation_id_list[index]} is not node")
            assert_utils.assert_equal(data3, status,
                                      f"Resource status of {generation_id_list[index]} "
                                      f"is not {status}")
        return node_id, resource_id

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
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        self.restore_pod = True

        LOGGER.info("Step 2: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='failed')
        failed_node_id = resp[0]
        failed_resource_id = resp[1]
        LOGGER.info("Step 2: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 3: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 3: Successfully sent action event to hare")

        LOGGER.info("Step 4: Start pod by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully started the pod again by making replicas=1")
        self.restore_pod = False

        LOGGER.info("Step 5: Check pod online alert and verify node and resource IDs")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='online')
        online_node_id = resp[0]
        online_resource_id = resp[1]
        assert_utils.assert_equal(failed_node_id, online_node_id, "Pod node IDs are different")
        assert_utils.assert_equal(failed_resource_id, online_resource_id, "Pod resource IDs "
                                                                          "are different")
        LOGGER.info("Step 5: Successfully checked pod online event to hare and verified the "
                    "node and resource IDs")

        LOGGER.info("Step 6: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 6: Successfully sent action event to hare")

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
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting"
                                           " deployment (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting "
                    "deployment", pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_method = common_const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True

        LOGGER.info("Step 2: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='failed')
        failed_node_id = resp[0]
        failed_resource_id = resp[1]
        LOGGER.info("Step 2: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 3: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 3: Successfully sent action event to hare")

        LOGGER.info("Step 4: Restore the deleted pod by creating deployment")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully restored pod by %s way", self.restore_method)
        self.restore_pod = False

        LOGGER.info("Step 5: Check pod online alert and verify node and resource IDs")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='online')
        online_node_id = resp[0]
        online_resource_id = resp[1]
        assert_utils.assert_equal(failed_node_id, online_node_id, "Pod node IDs are different")
        assert_utils.assert_equal(failed_resource_id, online_resource_id, "Pod resource IDs "
                                                                          "are different")
        LOGGER.info("Step 5: Successfully checked pod online event to hare and verified the "
                    "node and resource IDs")

        LOGGER.info("Step 6: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 6: Successfully sent action event to hare")

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

        LOGGER.info("Step 2: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True,
                                                     kubectl_delete=True, status='failed')
        resp = self.get_node_resource_id(resp_dict, status='failed')
        failed_node_id = resp[0]
        failed_resource_id = resp[1]
        LOGGER.info("Step 2: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 3: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 3: Successfully sent action event to hare")

        LOGGER.info("Step 4: Check the node status.")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        resp = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_equal(after_del, before_del, "New data pod didn't gets created")
        LOGGER.info("Step 4: New data pod created automatically by kubernetes")

        LOGGER.info("Step 5: Check pod online alert and verify node and resource IDs")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True,
                                                     kubectl_delete=True)
        resp = self.get_node_resource_id(resp_dict, status='online')
        online_node_id = resp[0]
        online_resource_id = resp[1]
        assert_utils.assert_equal(failed_node_id, online_node_id, "Pod node IDs are different")
        assert_utils.assert_equal(failed_resource_id, online_resource_id, "Pod resource IDs "
                                                                          "are different")
        LOGGER.info("Step 5: Successfully checked pod online event to hare and verified the "
                    "node and resource IDs")

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
        pod_list = \
            self.node_master_list[0].get_all_pods(pod_prefix=common_const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting "
                                           "deployment (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting "
                    "deployment", pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_method = common_const.RESTORE_DEPLOYMENT_K8S
        self.restore_pod = True

        LOGGER.info("Step 2: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='failed')
        failed_node_id = resp[0]
        failed_resource_id = resp[1]
        LOGGER.info("Step 2: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 3: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 3: Successfully sent action event to hare")

        LOGGER.info("Step 4: Restore the deleted pod by creating deployment")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully restored pod by %s way", self.restore_method)
        self.restore_pod = False

        LOGGER.info("Step 5: Check pod online alert and verify node and resource IDs")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='online')
        online_node_id = resp[0]
        online_resource_id = resp[1]
        assert_utils.assert_equal(failed_node_id, online_node_id, "Pod node IDs are different")
        assert_utils.assert_equal(failed_resource_id, online_resource_id, "Pod resource IDs "
                                                                          "are different")
        LOGGER.info("Step 5: Successfully checked pod online event to hare and verified the "
                    "node and resource IDs")

        LOGGER.info("Step 6: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 6: Successfully sent action event to hare")

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
        pod_list = \
            self.node_master_list[0].get_all_pods(pod_prefix=common_const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        self.restore_pod = True

        LOGGER.info("Step 2: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='failed')
        failed_node_id = resp[0]
        failed_resource_id = resp[1]
        LOGGER.info("Step 2: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 3: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 3: Successfully sent action event to hare")

        LOGGER.info("Step 4: Start pod by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 4: Successfully started the pod again by making replicas=1")
        self.restore_pod = False

        LOGGER.info("Step 5: Check pod online alert and verify node and resource IDs")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_resource_id(resp_dict, status='online')
        online_node_id = resp[0]
        online_resource_id = resp[1]
        assert_utils.assert_equal(failed_node_id, online_node_id, "Pod node IDs are different")
        assert_utils.assert_equal(failed_resource_id, online_resource_id, "Pod resource IDs "
                                                                          "are different")
        LOGGER.info("Step 5: Successfully checked pod online event to hare and verified the "
                    "node and resource IDs")

        LOGGER.info("Step 6: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 6: Successfully sent action event to hare")

        LOGGER.info("COMPLETED: Publish the pod online event to component Hare- "
                    "Server pod comes online after server pod restart using replicas.")
