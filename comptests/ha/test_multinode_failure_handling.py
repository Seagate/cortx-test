#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
HA component test suit for multi pod failure
"""

import random
import logging

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from libs.ha.ha_comp_libs import HAK8SCompLib
from config import CMN_CFG
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons import constants as const

LOGGER = logging.getLogger(__name__)


class TestMultiNodeFailureHandling:
    """
    Test suite for Multi node failure handling
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_worker_list = []
        cls.node_master_list = []
        cls.host_list = []
        cls.hlth_master_list = []
        cls.hlth_master_list = []
        cls.ha_obj = HAK8s()
        cls.ha_comp_obj = HAK8SCompLib()
        cls.restored = True
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.kvalue = None
        cls.pod_dict = {}
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            cls.hlth_master_list.append(
                Health(hostname=CMN_CFG["nodes"][node]["hostname"], username=CMN_CFG["nodes"][node]["username"],
                       password=CMN_CFG["nodes"][node]["password"]))

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
        LOGGER.info("Get the value of K for the given cluster.")
        resp = self.ha_obj.get_config_value(self.node_master_list[0])
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            LOGGER.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        print(self.kvalue)
        LOGGER.info("The cluster has %s parity pods", self.kvalue)
        LOGGER.info("Checking if all the ha services are up and running")
        resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        assert_utils.assert_true(resp, "HA services are not running")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.info("Check if hare hax service is running in %s", pod_list)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("HAX services of pod are in online state")
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            for pod_name in self.pod_name_list:
                if len(self.pod_dict.get(pod_name)) == 2:
                    deployment_name = self.pod_dict.get(pod_name)[1]
                    deployment_backup = None
                else:
                    deployment_name = self.pod_dict.get(pod_name)[2]
                    deployment_backup = self.pod_dict.get(pod_name)[1]
                resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                               restore_method=self.restore_method,
                                               restore_params={"deployment_name": deployment_name,
                                                               "deployment_backup": deployment_backup})
                LOGGER.debug("Response: %s", resp)
                assert_utils.assert_true(resp[0], f"Failed to restore pod by "
                f"{self.restore_method} way")
                LOGGER.info("Successfully restored pod %s by %s way",
                            pod_name, self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Teardown completed.")

    def verify_ha_prop(self, resp_dict):
        """
        This is a local method to verify the ha logs properties
        """
        source_list = resp_dict['source']
        resource_type_list = resp_dict['resource_type']
        resource_status_list = resp_dict['resource_status']
        generation_id_list = resp_dict['generation_id']
        for index, (data1, data2, data3) in enumerate(zip(source_list, resource_type_list, resource_status_list)):
            assert_utils.assert_equal(data1, 'monitor', f"Source of {generation_id_list[index]} is not from monitor")
            assert_utils.assert_equal(data2, 'node', f"Resource of {generation_id_list[index]} is not node")
            assert_utils.assert_equal(data3, 'failed', f"Resource status of {generation_id_list[index]} is not failed")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36626")
    def test_shutdown_k_data_pod_delete_deployment(self):
        """
        This TC tests the shutdown of K data pod from cluster with delete deployment method
        """
        LOGGER.info("STARTED: Shutdown K data pod from cluster with delete deployment method")

        LOGGER.info("Step 1: Shutdown K data pods from cluster with delete deployment method")
        LOGGER.info(" Shutdown the data pod by deleting deployment (unsafe)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=pod_name))
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
            f"deleting deployment (unsafe)")
            pod_data.append(resp[1])
            pod_data.append(resp[2])
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
        LOGGER.info("Step 1: Successfully deleted %s data pods", self.kvalue)

        LOGGER.info("Step 2: Check pod alert in k8s monitor")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[0], self.kvalue)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 2: Successfully checked pod alert in k8s monitor")

        LOGGER.info("Step 3: Check pod alert in fault tolerance")
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[1],
                                                     self.kvalue, fault_tolerance=True)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod alert in fault tolerance")

        #TODO: Step:4 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        #TODO: Step:5 Health monitor log should show action event for ‘Failed’  event type | CORTX-29127

        #TODO: Step:6 Hare should send ‘Failed’/'Degraded' event to fault tolerance | Currently not supported

        #TODO: Step:7 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        LOGGER.info("COMPLETED: Shutdown K data pod from cluster with delete deployment method")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36628")
    def test_shutdown_k_data_pod_replicas(self):
        """
        This TC tests the shutdown of K data pod from cluster with replica down method
        """
        LOGGER.info("STARTED: Shutdown K data pod from cluster with replica down method")

        LOGGER.info("Step 1: Shutdown K data pods from cluster with replias method")
        LOGGER.info(" Shutdown the data pod by replias method")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=pod_name))
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
            pod_data.append(resp[1])
            self.restore_pod = True
            self.restore_method = const.RESTORE_SCALE_REPLICAS
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by making replicas=0", count, pod_name)
        LOGGER.info("Step 1: Successfully deleted %s data pods", self.kvalue)

        LOGGER.info("Step 2: Check pod alert in k8s monitor")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[0], self.kvalue)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 2: Successfully checked pod alert in k8s monitor")

        LOGGER.info("Step 3: Check pod alert in fault tolerance")
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[1],
                                                     self.kvalue, fault_tolerance=True)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod alert in fault tolerance")

        #TODO: Step:4 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        #TODO: Step:5 Health monitor log should show action event for ‘Failed’  event type | CORTX-29127

        #TODO: Step:6 Hare should send ‘Failed’/'Degraded' event to fault tolerance | Currently not supported

        #TODO: Step:7 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        LOGGER.info("COMPLETED: Shutdown K data pod from cluster with replica down method")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36644")
    def test_shutdown_till_k_data_pod_delete_deployment(self):
        """
        This TC tests the Shutdown till K data pod from cluster using delete deployment method
        """
        LOGGER.info("STARTED: Shutdown till K data pod from cluster using delete deployment method")

        LOGGER.info("Step 1: Shutdown data pods from cluster with delete deployment method")
        LOGGER.info(" Shutdown the data pod by deleting deployment (unsafe)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=pod_name))
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
            f"deleting deployment (unsafe)")
            pod_data.append(resp[1])
            pod_data.append(resp[2])
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
            LOGGER.info("Step 1: Successfully deleted %s data pod", pod_name)

            LOGGER.info("Step 2: Check pod alert in k8s monitor")
            node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
            resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[0], kvalue=1)
            self.verify_ha_prop(resp_dict)
            LOGGER.info("Step 2: Successfully checked pod alert in k8s monitor")

            LOGGER.info("Step 3: Check pod alert in fault tolerance")
            resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[1],
                                                         kvalue=1, fault_tolerance=True)
            self.verify_ha_prop(resp_dict)
            LOGGER.info("Step 3: Successfully checked pod alert in fault tolerance")

            #TODO: Step:4 System health status should be “Failed” | CORTX-29129 - Fix get system health API

            #TODO: Step:5 Health monitor log should show action event for ‘Failed’  event type | CORTX-29127

            #TODO: Step:6 Hare should send ‘Failed’/'Degraded' event to fault tolerance | Currently not supported

            #TODO: Step:7 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        LOGGER.info("COMPLETED: Shutdown till K data pod from cluster with delete deployment method")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36645")
    def test_shutdown_till_k_data_pod_replicas(self):
        """
        This TC tests the Shutdown till K data pod from cluster using replica down method
        """
        LOGGER.info("STARTED: Shutdown till K data pod from cluster using replica method")

        LOGGER.info("Step 1: Shutdown till K data pods from cluster with replias method")
        LOGGER.info(" Shutdown the data pod by replias method")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=pod_name))
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
            pod_data.append(resp[1])
            self.restore_pod = True
            self.restore_method = const.RESTORE_SCALE_REPLICAS
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by making replicas=0", count, pod_name)
            LOGGER.info("Step 1: Successfully deleted %s data pod", pod_name)

            LOGGER.info("Step 2: Check pod alert in k8s monitor")
            node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
            resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[0], kvalue=1)
            self.verify_ha_prop(resp_dict)
            LOGGER.info("Step 2: Successfully checked pod alert in k8s monitor")

            LOGGER.info("Step 3: Check pod alert in fault tolerance")
            resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[1],
                                                         kvalue=1, fault_tolerance=True)
            self.verify_ha_prop(resp_dict)
            LOGGER.info("Step 3: Successfully checked pod alert in fault tolerance")

            #TODO: Step:4 System health status should be “Failed” | CORTX-29129 - Fix get system health API

            #TODO: Step:5 Health monitor log should show action event for ‘Failed’  event type | CORTX-29127

            #TODO: Step:6 Hare should send ‘Failed’/'Degraded' event to fault tolerance | Currently not supported

            #TODO: Step:7 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        LOGGER.info("COMPLETED: Shutdown till K data pod from cluster with replica down method")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30703")
    def test_shutdown_k_data_server_pod_delete_deployment(self):
        """
        This TC tests the shutdown of K data pod and server pods from cluster with delete deployment method
        """
        LOGGER.info("STARTED: Shutdown K data pod and server pod from cluster with delete deployment method")

        LOGGER.info("Step 1: Shutdown K data pods and server pods from cluster with delete deployment method")
        LOGGER.info(" Shutdown the data pod and server pod by deleting deployment (unsafe)")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_list = data_pod_list + server_pod_list
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=pod_name))
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
            f"deleting deployment (unsafe)")
            pod_data.append(resp[1])
            pod_data.append(resp[2])
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
        LOGGER.info("Step 1: Successfully deleted %s  pods", self.kvalue)

        LOGGER.info("Step 2: Check pod alert in k8s monitor")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[0], self.kvalue)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 2: Successfully checked pod alert in k8s monitor")

        LOGGER.info("Step 3: Check pod alert in fault tolerance")
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[1],
                                                     self.kvalue, fault_tolerance=True)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod alert in fault tolerance")

        #TODO: Step:4 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        #TODO: Step:5 Health monitor log should show action event for ‘Failed’  event type | CORTX-29127

        #TODO: Step:6 Hare should send ‘Failed’/'Degraded' event to fault tolerance | Currently not supported

        #TODO: Step:7 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        LOGGER.info("COMPLETED: Shutdown K data pod and server pod from cluster with delete deployment method")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30703")
    def test_shutdown_k_data_server_pod_replicas(self):
        """
        This TC tests the shutdown of K data pod and server pods from cluster with replica down method
        """
        LOGGER.info("STARTED: Shutdown K data pod and server pod from cluster with replica down method")

        LOGGER.info("Step 1: Shutdown K data pod and server pods from cluster with replica down method")
        LOGGER.info(" Shutdown the data pod and serverpod by replica down")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_list = data_pod_list + server_pod_list
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=pod_name))
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
            pod_data.append(resp[1])
            self.restore_pod = True
            self.restore_method = const.RESTORE_SCALE_REPLICAS
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by making replicas=0", count, pod_name)
        LOGGER.info("Step 1: Successfully deleted %s data pod", self.kvalue)

        LOGGER.info("Step 2: Check pod alert in k8s monitor")
        node_obj = self.ha_comp_obj.get_ha_node_object(self.node_master_list[0])
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[0], self.kvalue)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 2: Successfully checked pod alert in k8s monitor")

        LOGGER.info("Step 3: Check pod alert in fault tolerance")
        resp_dict = self.ha_comp_obj.get_ha_log_prop(node_obj, const.HA_SHUTDOWN_LOGS[1],
                                                     self.kvalue, fault_tolerance=True)
        self.verify_ha_prop(resp_dict)
        LOGGER.info("Step 3: Successfully checked pod alert in fault tolerance")

        #TODO: Step:4 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        #TODO: Step:5 Health monitor log should show action event for ‘Failed’  event type | CORTX-29127

        #TODO: Step:6 Hare should send ‘Failed’/'Degraded' event to fault tolerance | Currently not supported

        #TODO: Step:7 System health status should be “Failed” | CORTX-29129 - Fix get system health API

        LOGGER.info("COMPLETED: Shutdown K data pod and server pod from cluster with replica down method")
