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
HA component test suite for shutdown and start cluster.
"""
import logging
import random
import os
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


# pylint: disable=too-many-statements

class TestShutdownStartCluster:
    """
    Test suite for Shutdown and Start Cluster
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_worker_list = []
        cls.node_master_list = []
        cls.ha_comp_obj = HAK8SCompLib()
        cls.ha_obj = HAK8s()
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
        if self.restore_pod:
            LOGGER.info("STARTED: Teardown Operations.")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
            LOGGER.info("Done: Teardown completed.")

    def get_ha_node_object(self, master_node_obj) -> LogicalNode:
        """
        Helper function to get HA node object.
        :param master_node_obj: Master node(Logical Node object)
        :return: HA node object
        """
        pod_name = master_node_obj.get_pod_name(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        ha_hostname = master_node_obj.get_pods_node_fqdn(pod_name[1])
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_name[1]])
        node_obj = object()
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_name[1]]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_name[1]],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        return node_obj

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30701")
    def test_delete_pods_verify_alerts(self):
        """
        This TC tests Delete one data pod and one server pod and then stop cluster and
        then start the cluster and check the cluster status
        """
        LOGGER.info("STARTED: Delete one data pod and one server pod and then stop cluster and "
                    "then start the cluster and check the cluster status.")

        LOGGER.info("Step 1: Shutdown the data pod by making replicas=0")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
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

        LOGGER.info("Step 2: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 2: Successfully sent action event to hare")

        LOGGER.info("Step 3: Shutdown the server pod by making replicas=0")
        LOGGER.info("Get pod name to be deleted")
        pod_list = \
            self.node_master_list[0].get_all_pods(pod_prefix=common_const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        self.restore_pod = True

        LOGGER.info("Step 4: Check for publish action event")
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "to component hare",
                                                         common_const.HA_SHUTDOWN_LOGS[2], lines=4)
        assert_utils.assert_true(resp[0], "Alert not sent to hare")
        LOGGER.info("Step 4: Successfully sent action event to hare")

        LOGGER.info("Step 5: Trigger ‘Start Cluster Shutdown’ message to HA.")
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = self.ha_comp_obj.shutdown_signal(self.node_master_list[0],
                                                common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                                common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Triggered ‘Start Cluster Shutdown’ message to HA. successfully.")

        LOGGER.info("Step 6: Verify fault tolerance log for cluster stop key message.")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Verified fault tolerance log for cluster stop key message.")

        LOGGER.info("Step 7: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Step 7: Shutdown entire cortx Cluster successfully")

        LOGGER.info("Step 8:Verify all HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "SIGTERM", log, lines=18)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8:Verified all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)

        LOGGER.info("Step 9: Start the cluster")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully started the cluster")
        self.restore_pod = False

        LOGGER.info("Step 10: Checking if all the ha services are up and running")
        resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        assert_utils.assert_true(resp, "HA services are not running")
        LOGGER.info("Step 10: Successfully verified and all the ha services are up and running")

        LOGGER.info("COMPLETED: Delete one data pod and one server pod and "
                    "then stop cluster and then start the cluster and check the cluster status")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30698")
    def test_consul_key(self):
        """
        This TC tests Consul key should be updated for cluster_stop_key after receiving shutdown
        signal and start the cluster
        """
        LOGGER.info("STARTED: Consul key should be updated for cluster_stop_key "
                    "after receiving shutdown signal and start the cluster.")

        LOGGER.info("Step 1: Trigger ‘Start Cluster Shutdown’ message to HA.")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = self.ha_comp_obj.shutdown_signal(self.node_master_list[0],
                                                common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                                common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Triggered ‘Start Cluster Shutdown’ message to HA successfully.")

        LOGGER.info("Step 2: Verify fault tolerance log for cluster stop key message.")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified fault tolerance log for cluster stop key message.")

        LOGGER.info("Step 3: Verify the cluster_stop_key is seen (kubectl exec -it <<>>.)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_consul_update_cmd = self.node_master_list[0].execute_cmd(
            common_cmd.K8S_CONSUL_UPDATE_CMD.format(pod_name,
                                                    common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                                                    common_cmd.HA_CONSUL_STR, read_lines=True))
        ha_consul_update_cmd = ha_consul_update_cmd.strip().decode("utf-8")
        assert_utils.assert_in(ha_consul_update_cmd, common_const.HA_CONSUL_VERIFY, "Key not found")
        LOGGER.info("Step 3: Successfully verified the cluster_stop_key is seen "
                    "(kubectl exec -it <<>>.)")

        LOGGER.info("Step 4: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Step 4: Stopped the cluster successfully")

        LOGGER.info("Step 5:Verify all HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "SIGTERM", log)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5:Verified all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)

        LOGGER.info("Step 6: Verify the cluster_stop_key is deleted (kubectl exec -it <<>>.)")
        ha_cmd_output = self.node_master_list[0]. \
            execute_cmd(common_cmd.K8S_CONSUL_UPDATE_CMD.
                        format(pod_name, common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                               common_cmd.HA_CONSUL_STR), read_lines=True, exc=False)
        assert_utils.assert_in("NotFound", ha_cmd_output[1][0], "Key not deleted")
        LOGGER.info("Step 6: Successfully verified the cluster_stop_key is deleted "
                    "(kubectl exec -it <<>>.)")

        LOGGER.info("Step 7: Start the cluster")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully started the cluster")

        LOGGER.info("Step 8: Checking if all the ha services are up and running")
        resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        assert_utils.assert_true(resp, "HA services are not running")
        LOGGER.info("step 8: Successfully verified and all the ha services are up and running")

        LOGGER.info("COMPLETED: Consul key should be updated for cluster_stop_key "
                    "after receiving shutdown signal and start the cluster.")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34982")
    def test_shutdown_signal(self):
        """
        This TC tests Scale down a server pod before shutting down cluster.
        Start the cluster, scale up the pod and verify scale up notification sent.
        """
        LOGGER.info("STARTED: Scale down a server pod before shutting down cluster."
                    "Start the cluster, scale up the pod and verify scale up notification sent.")

        LOGGER.info("Step 1: Trigger ‘Start Cluster Shutdown’ message to HA.")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = self.ha_comp_obj.shutdown_signal(self.node_master_list[0],
                                                common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                                common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Triggered ‘Start Cluster Shutdown’ message to HA successfully.")

        LOGGER.info("Step 2: Verify fault tolerance for cluster stop key message.")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Successfully verified fault tolerance for cluster stop key message.")

        LOGGER.info("Step 3: Shutdown pod using replica set")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown a pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        self.restore_pod = True

        LOGGER.info("Step 4: Verify k8s resource monitor for skipping alert message")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1], lines=1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Verified k8s resource monitor log for skipping alert message")

        LOGGER.info("Step 5: Verify the cluster_stop_key is seen (kubectl exec -it <<>>.)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_consul_update_cmd = self.node_master_list[0].execute_cmd(
            common_cmd.K8S_CONSUL_UPDATE_CMD.format(pod_name,
                                                    common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                                                    common_cmd.HA_CONSUL_STR, read_lines=True))
        ha_consul_update_cmd = ha_consul_update_cmd.strip().decode("utf-8")
        assert_utils.assert_in(ha_consul_update_cmd, common_const.HA_CONSUL_VERIFY, "Key not found")
        LOGGER.info("Step 5: Successfully verified the cluster_stop_key is seen "
                    "(kubectl exec -it <<>>.)")

        LOGGER.info("Step 6: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Step 6: Stopped the cluster successfully")

        LOGGER.info("Step 7:Verify all HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "SIGTERM", log)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7:Verified all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)

        LOGGER.info("Step 8: Start the cluster")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully started the cluster")
        self.restore_pod = False

        LOGGER.info("Step 9: Checking if all the ha services are up and running")
        resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        assert_utils.assert_true(resp, "HA services are not running")
        LOGGER.info("step 9: Successfully verified and all the ha services are up and running")

        LOGGER.info("COMPLETED: Scale down a server pod before shutting down cluster."
                    "Start the cluster, scale up the pod and verify scale up notification sent.")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30700")
    def test_scale_pod_verify_ha_alerts(self):
        """
        This TC tests Send cluster shutdown signal and Health monitor log should not receive
        any message and start the cluster
        """
        LOGGER.info("STARTED: Send cluster shutdown signal and Health monitor log "
                    "should not receive any message and start the cluster")

        LOGGER.info("Step 1: Trigger ‘Start Cluster Shutdown’ message to HA")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = self.ha_comp_obj.shutdown_signal(self.node_master_list[0],
                                                common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                                common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Triggered ‘Start Cluster Shutdown’ message to HA successfully")

        LOGGER.info("Step 2: Verify fault tolerance for cluster stop key message")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified fault tolerance log for cluster stop key message")

        LOGGER.info('Take word count of health monitor logs before pod operation')
        wc_before = self.ha_comp_obj.get_ha_log_wc(node_obj, log_index=2)

        LOGGER.info("Step 3: Shutdown pod using replica set")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown a pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        self.restore_pod = True

        LOGGER.info("Step 4: Verify k8s resource monitor for skipping alert message")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1], lines=1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Verified k8s resource monitor log for skipping alert message")

        LOGGER.info("Step 5: Verify HealthMonitor should not send degraded alert to comp Hare ")
        LOGGER.info('Take word count of health monitor logs after pod operation')
        wc_after = self.ha_comp_obj.get_ha_log_wc(node_obj, log_index=2)
        assert_utils.assert_equal(wc_before, wc_after,
                                  "Failed:cluster degraded alert sent to Hare.")
        LOGGER.info("Step 5: Successfully verified HealthMonitor should not send degraded alert "
                    "to comp Hare")

        LOGGER.info("Step 6: Start pod by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod again by making replicas=1")
        self.restore_pod = False

        LOGGER.info("Step 7: Verify k8s resource monitor for skipping alert message")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                         common_const.HA_SHUTDOWN_LOGS[1], lines=1)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Verified k8s resource monitor log for skipping alert message")

        LOGGER.info("Step 8:Verify HealthMonitor should not send degraded alert to comp Hare")
        LOGGER.info('Take word count of health monitor logs after pod operation')
        wc_after = self.ha_comp_obj.get_ha_log_wc(node_obj, log_index=2)
        assert_utils.assert_equal(wc_before, wc_after,
                                  "Failed:cluster degraded alert sent to Hare.")
        LOGGER.info("Step 8:Verified HealthMonitor should not send degraded alert to comp Hare")

        LOGGER.info("Step 9: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Step 9: Shutdown entire cortx Cluster successfully")

        LOGGER.info("Step 10:Verify the HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = self.ha_comp_obj.check_string_in_log_file(node_obj, "SIGTERM", log)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10:Verify all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)

        LOGGER.info("Step 11: Start the cluster")
        resp = self.ha_obj.cortx_start_cluster(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 11: Successfully started the cluster")

        LOGGER.info("Step 12: Checking if all the ha services are up and running")
        resp = self.ha_comp_obj.check_ha_services(self.node_master_list[0])
        assert_utils.assert_true(resp, "HA services are not running")
        LOGGER.info("step 12: Successfully verified and all the ha services are up and running")

        LOGGER.info("COMPLETED: Send cluster shutdown signal and Health monitor log "
                    "should not receive any message and start the cluster")
