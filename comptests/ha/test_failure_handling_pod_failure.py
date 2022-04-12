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
from libs.ha.ha_comp_libs import HAK8SCompLib
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
        cls.ha_comp_obj = HAK8SCompLib()
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
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")
        LOGGER.info("Done: Teardown completed.")

    @staticmethod
    def get_node_status_log(resp_dict):
        """
        This is a local method to verify the pod status
        :param resp_dict: halog properties
        """
        source_list = resp_dict['source']
        resource_type_list = resp_dict['resource_type']
        resource_status_list = resp_dict['resource_status']
        generation_id_list = resp_dict['generation_id']
        for index, (data1, data2, data3) in enumerate(zip(source_list, resource_type_list,
                                                          resource_status_list)):
            assert_utils.assert_equal(data1, 'monitor',
                                      f"Source of {generation_id_list[index]} is not from monitor")
            assert_utils.assert_equal(data2, 'node',
                                      f"Resource of {generation_id_list[index]} is not node")
            assert_utils.assert_equal(data3, 'failed',
                                      f"Resource status of {generation_id_list[index]} "
                                      "is not failed")

    @pytest.mark.skip(reason="No way of testing this currently - need fix CORTX-28823")
    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30218")
    def test_delete_pod(self):
        """
        This TC tests Publish the pod failure event to Hare - Delete pod(kubectl delete))
        """
        LOGGER.info("STARTED: Publish the pod failure event in message bus to Hare - Delete pod."
                    "(kubectl delete)")

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

        LOGGER.info("Step 3: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True,
                                                     kubectl_delete=True, status='failed')
        resp = self.get_node_status_log(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 4: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 4: Successfully sent action event to hare")

        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - Delete pod.")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30220")
    def test_delete_pod_replicaset_down(self):
        """
        This TC tests delete pod by scaling down pod(replica=0)
        """
        LOGGER.info(
            "STARTED: Publish the pod failure event in message bus to Hare - "
            "Delete pod using replica set.")

        LOGGER.info("Step 1: Shutdown the data pod by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(pod_list)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 2: Check the node status.")
        resp = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_not_equal(after_del, before_del, "Data pod didn't gets deleted")
        LOGGER.info("Step 2: Node status updated after pod deleted successfully")

        LOGGER.info("Step 3: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_status_log(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 4: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 4: Successfully sent action event to hare")

        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod - delete replica replicaset")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30222")
    def test_delete_pod_deployment(self):
        """
        This TC tests delete pod by deleting deployment
        """
        LOGGER.info(
            "STARTED: Publish the pod failure event in message bus to Hare - "
            "Delete pod using deployment.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        before_del = len(pod_list)
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

        LOGGER.info("Step 2: Check the node status.")
        resp = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        after_del = len(resp)
        LOGGER.info("After delete %s", after_del)
        LOGGER.info("Before delete %s", before_del)
        assert_utils.assert_not_equal(after_del, before_del, "Data pod didn't gets deleted")
        LOGGER.info("Step 2: Node status updated after pod deleted successfully")

        LOGGER.info("Step 3: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True)
        resp = self.get_node_status_log(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 4: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 4: Successfully sent action event to hare")

        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod deployment - delete deployment")

    @pytest.mark.skip(reason="No way of testing this currently - need fix CORTX-28823")
    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30219")
    def test_delete_pod_forcefully(self):
        """
        This TC tests delete pod using kubectl delete forcefully
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
        LOGGER.info("Step 3: Check pod failed alert in health monitor log")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, common_const.HA_SHUTDOWN_LOGS[2],
                                                     kvalue=1, health_monitor=True,
                                                     kubectl_delete=True, status='failed')
        resp = self.get_node_status_log(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod failed alert in health monitor log")

        LOGGER.info("Step 4: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 4: Successfully sent action event to hare")

        LOGGER.info("COMPLETED:Publish the pod failure event in message bus to Hare - "
                    "Delete pod forcefully.")
