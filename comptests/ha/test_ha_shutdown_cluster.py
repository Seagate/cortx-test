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
HA component test suite for shutdown cluster.
"""
import logging
import random
import os
import time

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from libs.ha.ha_comp_libs import HAK8SCompLib
from libs.csm.rest.csm_rest_system_health import SystemHealth
from config import CMN_CFG
from config import HA_CFG
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
        cls.ha_system_obj = SystemHealth()
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
        Setup Method
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
        if self.restored:
            LOGGER.info("Cleanup: Check cluster status and start it if not up.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            if not resp[0]:
                LOGGER.debug("Cluster status: %s", resp)
                resp = self.ha_obj.restart_cluster(self.node_master_list[0])
                assert_utils.assert_true(resp[0], resp[1])
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
    @pytest.mark.tags("TEST-34982")
    def test_shutdown_entire_cluster(self):
        """
        This TC tests shutdown entire cluster and verify HA alerts logs for SIGTERM
        """
        LOGGER.info("STARTED: Stop Cluster - Shutdown cluster and verify HA logs.")
        LOGGER.info("Step 1: Shutdown entire cortx Cluster")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 1: Shutdown entire cortx Cluster successfully")

        LOGGER.info("Step 2:Verify all HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = HAK8SCompLib.check_string_in_log_file(node_obj, "SIGTERM", log)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2:Verified all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)
        LOGGER.info("Completed: Stopped Cluster - Shutdown cluster, verified HA alerts log SIGTERM")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30700")
    def test_consul_key(self):
        """
        This TC test Consul key should be update cluster_stop_key when receiving shutdown signal
        """
        LOGGER.info("STARTED: Consul key update cluster_stop_key when receiving shutdown signal.")
        LOGGER.info("Step 1: Trigger ‘Start Cluster Shutdown’ message to HA.")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = HAK8SCompLib.shutdown_signal(self.node_master_list[0],
                                            common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                            common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Triggered ‘Start Cluster Shutdown’ message to HA. successfully.")
        LOGGER.info("Step 2: Verify k8s and fault tolerance log for cluster stop key message.")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = HAK8SCompLib.check_string_in_log_file(node_obj, "cluster stop",
                                                     common_const.HA_SHUTDOWN_LOGS[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = HAK8SCompLib.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                     common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified k8s and fault tolerance log for cluster stop key message.")
        LOGGER.info("Step 3: Verify the cluster_stop_key is seen (kubectl exec -it <<>>.)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_consul_update_cmd = self.node_master_list[0].execute_cmd(
            common_cmd.K8S_CONSUL_UPDATE_CMD.format(pod_name,
                                                    common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                                                    common_cmd.HA_CONSUL_STR, read_lines=True))
        ha_consul_update_cmd = ha_consul_update_cmd.strip().decode("utf-8")
        assert_utils.assert_in(ha_consul_update_cmd, common_const.HA_CONSUL_VERIFY, "Key not found")
        LOGGER.info("Step 3: Verified the cluster_stop_key is seen (kubectl exec -it <<>>.)")
        LOGGER.info("Step 4: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 4: Stopped the cluster successfully")
        LOGGER.info("Step 5: Verify the cluster_stop_key is deleted (kubectl exec -it <<>>.)")
        ha_cmd_output = self.node_master_list[0]. \
            execute_cmd(common_cmd.K8S_CONSUL_UPDATE_CMD.
                        format(pod_name, common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                               common_cmd.HA_CONSUL_STR), read_lines=True, exc=False)
        assert_utils.assert_in("NotFound", ha_cmd_output[1][0], "Key not deleted")
        LOGGER.info("Step 5: Verified the cluster_stop_key is deleted (kubectl exec -it <<>>.)")
        LOGGER.info("Completed:Consul key updated cluster_stop_key when receiving shutdown signal")

    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30701")
    def test_shutdown_signal(self):
        """
        This TC test Shutdown entire Cluster with prior message sent to HA logs
        """
        LOGGER.info("START: Shutdown entire Cluster with prior message sent to HA logs.")
        LOGGER.info("Step 1: Trigger ‘Start Cluster Shutdown’ message to HA.")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = HAK8SCompLib.shutdown_signal(self.node_master_list[0],
                                            common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                            common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Triggered ‘Start Cluster Shutdown’ message to HA successfully.")

        LOGGER.info("Step 2: Verify k8s and fault tolerance for cluster stop key message.")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = HAK8SCompLib.check_string_in_log_file(node_obj, "cluster stop",
                                                     common_const.HA_SHUTDOWN_LOGS[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = HAK8SCompLib.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                     common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified k8s and fault tolerance for cluster stop key message.")

        LOGGER.info("Step 3: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Step 3: Stopped the cluster successfully")

        LOGGER.info("Step 4:Verify all HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = HAK8SCompLib.check_string_in_log_file(node_obj, "SIGTERM", log)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4:Verified all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)
        LOGGER.info("COMPETED: Shutdown entire Cluster with prior message sent to HA logs")

    # pylint: disable=too-many-statements
    @pytest.mark.comp_ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30698")
    def test_scale_pod_verify_ha_alerts(self):
        """
        This TC tests Send cluster shutdown signal and Health monitor log should not receive alerts
        """
        LOGGER.info("STARTED: Send shutdown signal and Health monitor should not receive alerts")
        LOGGER.info("Step 1: Trigger ‘Start Cluster Shutdown’ message to HA")
        node_obj = self.get_ha_node_object(self.node_master_list[0])
        base_path = os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        resp = HAK8SCompLib.shutdown_signal(self.node_master_list[0],
                                            common_const.HA_SHUTDOWN_SIGNAL_PATH,
                                            common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Triggered ‘Start Cluster Shutdown’ message to HA successfully")
        LOGGER.info("Step 2: Verify k8s and fault tolerance for cluster stop key message")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        resp = HAK8SCompLib.check_string_in_log_file(node_obj, "cluster stop",
                                                     common_const.HA_SHUTDOWN_LOGS[0])
        assert_utils.assert_true(resp[0], resp[1])
        resp = HAK8SCompLib.check_string_in_log_file(node_obj, "cluster_stop_key",
                                                     common_const.HA_SHUTDOWN_LOGS[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Verified k8s and fault tolerance log for cluster stop key message")
        LOGGER.info("Step 3: Shutdown pod using replica set")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown a pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        LOGGER.info("Step 4:Verify HealthMonitor should not send degraded alert to comp Hare ")
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        hapvc = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("hapvc list %s", hapvc)
                break
        ha_wc_count_cmd = common_const.HA_LOG + hapvc + "/log/ha/*/" + \
                          common_const.HA_SHUTDOWN_LOGS[2]
        ha_wc_count_cmd = common_cmd.LINE_COUNT_CMD.format(ha_wc_count_cmd)
        ha_wc_count = node_obj.execute_cmd(ha_wc_count_cmd)
        if isinstance(ha_wc_count, bytes):
            ha_wc_count = str(ha_wc_count, 'UTF-8')
        ha_wc_count_after_scale = node_obj.execute_cmd(ha_wc_count_cmd)
        if isinstance(ha_wc_count_after_scale, bytes):
            ha_wc_count_after_scale = str(ha_wc_count_after_scale, 'UTF-8')
        LOGGER.info("cluster degraded alerts not seen %s", ha_wc_count_after_scale)
        assert_utils.assert_equal(ha_wc_count, ha_wc_count_after_scale,
                                  "Failed:cluster degraded alert sent to Hare.")
        LOGGER.info("Step 4:Verified HealthMonitor should not send degraded alert to comp Hare")
        LOGGER.info("Step 5: Start pod by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 5: Successfully started the pod again by making replicas=1")
        self.restore_pod = False
        LOGGER.info("Step 6:Verify HealthMonitor should not send degraded alert to comp Hare")
        ha_wc_count_after_scale = node_obj.execute_cmd(ha_wc_count_cmd)
        if isinstance(ha_wc_count_after_scale, bytes):
            ha_wc_count_after_scale = str(ha_wc_count_after_scale, 'UTF-8')
        LOGGER.info("cluster degraded alerts not seen %s", ha_wc_count_after_scale)
        assert_utils.assert_equal(ha_wc_count, ha_wc_count_after_scale,
                                  "Failed:cluster degraded alert sent to hare .")
        LOGGER.info("Step 6:Verified HealthMonitor should not send degraded alert to comp Hare")
        LOGGER.info("Step 7: Shutdown entire cortx Cluster")
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 7: Shutdown entire cortx Cluster successfully")
        LOGGER.info("Step 8:Verify the HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            resp = HAK8SCompLib.check_string_in_log_file(node_obj, "SIGTERM", log)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8:Verify all HA logs for SIGTERM alert message %s",
                    common_const.HA_SHUTDOWN_LOGS)
        LOGGER.info("COMPETED: Sent shutdown signal and Health monitor should not receive alert")
