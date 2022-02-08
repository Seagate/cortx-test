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
import os

import pytest

from libs.ha.ha_common_libs_k8s import HAK8s
from libs.csm.rest.csm_rest_system_health import SystemHealth
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
        cls.ha_system_obj = SystemHealth()
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

    def teardown_method(self):

        LOGGER.info("STARTED: Teardown Operations.")
        self.restored = True
        if self.restored:
            LOGGER.info("Cleanup: Check cluster status and start it if not up.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            if not resp[0]:
                LOGGER.debug("Cluster status: %s", resp)
                resp = self.ha_obj.restart_cluster(self.node_master_list[0])
                assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34982")
    def test_shutdown_entire_cluster(self):
        """
        This tests test shutdown entire cluster and verify HA alerts logs for SIGTERM
        """

        LOGGER.info("STARTED: Stop Cluster - Shutdown cluster.")
        LOGGER.info("Step 1: Stop the cluster")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 1: Stopped the cluster successfully")

        LOGGER.info("Step 2:Verify all HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            pvc_list = node_obj.execute_cmd\
                (common_cmd.HA_LOG_PVC, read_lines=True)
            hapvc = None
            for hapvc in pvc_list:
                if common_const.HA_POD_NAME_PREFIX in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    LOGGER.info("hapvc list %s",  hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                        + hapvc + "/log/ha/*/" + log + " | grep 'SIGTERM'"
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
            assert_utils.assert_in("Received SIGTERM", output, "SIGTERM not received")              
        LOGGER.info("Step 2:Verified all HA logs for SIGTERM alert message")
        LOGGER.info("Completed: Stopped Cluster - Shutdown cluster ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30700")
    def test_consul_key(self):
        """
        This tests test the consul key after shutdown signal and shutdown cluster
        """
        LOGGER.info("STARTED: Verify consul key.")
     
        LOGGER.info("Step 1: Send the cluster shutdown signal.")
        base_path=os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        ha_cp_remote = self.node_master_list[0].copy_file_to_remote(local_path=common_const.HA_SHUTDOWN_SIGNAL_PATH, remote_path=common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(ha_cp_remote[0])
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_pod_copy = self.node_master_list[0].execute_cmd(common_cmd.HA_COPY_CMD.format(common_const.HA_TMP + '/ha_shutdown_signal.py',pod_name,common_const.HA_TMP),
                                                           read_lines=True)
        LOGGER.info("kubectl cp %s", ha_pod_copy)
        ha_pod_run_script = self.node_master_list[0].execute_cmd(common_cmd.HA_POD_RUN_SCRIPT.format(pod_name,'/usr/bin/python3', common_const.HA_TMP + '/' + base_path),
                                                           read_lines=True)
        LOGGER.info("Step 1: Sent the cluster shutdown signal successfully.")
        
        LOGGER.info("Step 2: Verify HA logs for cluster stop key message.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
            else:
                LOGGER.error("HA pod name: " + pod_nameha + ".")
        for log in range(len(common_const.HA_SHUTDOWN_LOGS) -1):              
            pvc_list = node_obj.execute_cmd \
                (common_cmd.HA_LOG_PVC, read_lines=True)
            hapvc = None
            for hapvc in pvc_list:
                if common_const.HA_POD_NAME_PREFIX in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    LOGGER.info("hapvc list %s", hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                + hapvc + "/log/ha/*/" + common_const.HA_SHUTDOWN_LOGS[log] + " | grep '{}'"            
            if log == 0:
                cluster_stop_cmd = "cluster stop"    
            else:      
                cluster_stop_cmd = "cluster_stop_key"   
            cmd_halog = cmd_halog.format(cluster_stop_cmd)
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
                LOGGER.info("Cluster stop timing %s", output)
                assert_utils.assert_in(cluster_stop_cmd, output, "SIGTERM Not received")
        LOGGER.info("Step 2: Verify HA logs for cluster stop key message.")

        LOGGER.info("Step 3: Shutdown a data pod using replica set")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown a pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 4: Verify consul key after shutdown signal is sent")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_consul_update_cmd = self.node_master_list[0].execute_cmd(
            common_cmd.HA_CONSUL_UPDATE_CMD.format(pod_name, 
                                                   common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                                                   common_const.HA_CONSUL_STR, read_lines=True))
        ha_consul_update_cmd = ha_consul_update_cmd.strip().decode("utf-8")
        assert_utils.assert_in(ha_consul_update_cmd,common_const.HA_CONSUL_VERIFY, "Key not found")
        LOGGER.info("Step 4: Verified consul key after shutdown signal is sent")

        LOGGER.info("Step 5: Stop the cluster")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 5: Stopped the cluster successfully")

        LOGGER.info("Step 6: Verify consul key after shutdown cluster")
        ha_cmd_output = self.node_master_list[0].\
            execute_cmd(common_cmd.HA_CONSUL_UPDATE_CMD.
                        format(pod_name,common_const.HA_FAULT_TOLERANCE_CONTAINER_NAME,
                               common_const.HA_CONSUL_STR), read_lines=True, exc=False)                                         
        assert_utils.assert_in("NotFound",ha_cmd_output[1][0],"Key not deleted")                
        LOGGER.info("Step 6: Verified consul key after shutdown cluster")
        LOGGER.info("Completed: Verified consul key ")
              
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30701")
    def test_shutdown_signal(self):
        """
        This tests test shutdown signal and shutdown cluster
        """
        LOGGER.info("START: Send Shutdown Signal and Shutdown Cluster.")
        LOGGER.info("Step 1: Send the cluster shutdown signal.")
        base_path=os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        ha_cp_remote = self.node_master_list[0].copy_file_to_remote(local_path=common_const.HA_SHUTDOWN_SIGNAL_PATH, remote_path=common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(ha_cp_remote[0])
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_pod_copy = self.node_master_list[0].execute_cmd(common_cmd.HA_COPY_CMD.format(common_const.HA_TMP + '/ha_shutdown_signal.py',pod_name,common_const.HA_TMP),
                                                           read_lines=True)
        ha_pod_run_script = self.node_master_list[0].execute_cmd(common_cmd.HA_POD_RUN_SCRIPT.format(pod_name,'/usr/bin/python3', common_const.HA_TMP + '/' + base_path),
                                                           read_lines=True)
        LOGGER.info("Step 1: Sent the cluster shutdown signal successfully.")

        LOGGER.info("Step 2: Verify HA logs for cluster stop key message.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
            else:
                LOGGER.error("HA pod name: " + pod_nameha + ".")
        for log in range(len(common_const.HA_SHUTDOWN_LOGS) -1):              
            pvc_list = node_obj.execute_cmd \
                (common_cmd.HA_LOG_PVC, read_lines=True)
            hapvc = None
            for hapvc in pvc_list:
                if common_const.HA_POD_NAME_PREFIX in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    LOGGER.info("hapvc list %s", hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                + hapvc + "/log/ha/*/" + common_const.HA_SHUTDOWN_LOGS[log] + " | grep '{}'"            
            if log == 0:
                cluster_stop_cmd = "cluster stop"    
            else:      
                cluster_stop_cmd = "cluster_stop_key"   
            cmd_halog = cmd_halog.format(cluster_stop_cmd)
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
                LOGGER.info("Cluster stop timing %s", output)
                assert_utils.assert_in(cluster_stop_cmd, output, "SIGTERM Not received")
        LOGGER.info("Step 2: Verify HA logs for cluster stop key message.")

        LOGGER.info("Step 3: Stop the cluster")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 3: Stopped the cluster successfully")

        LOGGER.info("Step 4:Verify the HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            pvc_list = node_obj.execute_cmd\
                (common_cmd.HA_LOG_PVC, read_lines=True)
            hapvc = None
            for hapvc in pvc_list:
                if common_const.HA_POD_NAME_PREFIX in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    LOGGER.info("hapvc list %s", hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                        + hapvc + "/log/ha/*/" + log + " | grep 'SIGTERM'"
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
            assert_utils.assert_in("Received SIGTERM", output, "SIGTERM not received")  
        LOGGER.info("Step 4:Verified the HA logs for SIGTERM alert message")
        LOGGER.info("COMPETED: Sent Shutdown Signal and Shutdown Cluster")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-30698")
    def test_scale_pod_verify_ha_alerts(self):
        """
        This tests test scale pod down and up and verify HA alerts
        """
        LOGGER.info("STARTED: Scale pod down and up and verify HA alerts.")
        LOGGER.info("Step 1: Send the cluster shutdown signal.")
        base_path=os.path.basename(common_const.HA_SHUTDOWN_SIGNAL_PATH)
        ha_cp_remote = self.node_master_list[0].copy_file_to_remote(local_path=common_const.HA_SHUTDOWN_SIGNAL_PATH, remote_path=common_const.HA_TMP + '/' + base_path)
        assert_utils.assert_true(ha_cp_remote[0])
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_name = pod_list[0]
        ha_pod_copy = self.node_master_list[0].execute_cmd(common_cmd.HA_COPY_CMD.format(common_const.HA_TMP + '/ha_shutdown_signal.py',pod_name,common_const.HA_TMP),
                                                           read_lines=True)
        LOGGER.info("kubectl cp %s", ha_pod_copy)
        ha_pod_run_script = self.node_master_list[0].execute_cmd(common_cmd.HA_POD_RUN_SCRIPT.format(pod_name,'/usr/bin/python3', common_const.HA_TMP + '/' + base_path),
                                                           read_lines=True)
        LOGGER.info("Step 1: Sent the cluster shutdown signal successfully.")

        LOGGER.info("Step 2: Verify HA logs for cluster stop key message.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
            else:
                LOGGER.error("HA pod name: " + pod_nameha + ".")
        for log in range(len(common_const.HA_SHUTDOWN_LOGS) -1):              
            pvc_list = node_obj.execute_cmd \
                (common_cmd.HA_LOG_PVC, read_lines=True)
            hapvc = None
            for hapvc in pvc_list:
                if common_const.HA_POD_NAME_PREFIX in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    LOGGER.info("hapvc list %s", hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                + hapvc + "/log/ha/*/" + common_const.HA_SHUTDOWN_LOGS[log] + " | grep '{}'"            
            if log == 0:
                cluster_stop_cmd = "cluster stop"    
            else:      
                cluster_stop_cmd = "cluster_stop_key"   
            cmd_halog = cmd_halog.format(cluster_stop_cmd)
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
                LOGGER.info("Cluster stop timing %s", output)
                assert_utils.assert_in(cluster_stop_cmd, output, "SIGTERM Not received")
        LOGGER.info("Step 2: Verify HA logs for cluster stop key message.")

        LOGGER.info("Step 3: Scale down and up pod using replica set")
        pvc_list = node_obj.execute_cmd(common_cmd.HA_LOG_PVC, read_lines=True)
        hapvc = None
        for hapvc in pvc_list:
            if common_const.HA_POD_NAME_PREFIX in hapvc:
                hapvc = hapvc.replace("\n", "")
                LOGGER.info("hapvc list %s", hapvc)
                break
        ha_wc_count_cmd = "/mnt/fs-local-volume/local-path-provisioner/"+ hapvc + "/log/ha/*/"+ common_const.HA_SHUTDOWN_LOGS[2]
        ha_wc_count_cmd = common_cmd.LINE_COUNT_CMD.format(ha_wc_count_cmd)
        ha_wc_count = node_obj.execute_cmd(ha_wc_count_cmd)
        if isinstance(ha_wc_count, bytes):
            ha_wc_count = str(ha_wc_count, 'UTF-8')
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        LOGGER.info("Deleting pod %s", pod_name)
        LOGGER.info("Step 3.1: Scale down pod")
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to scale up pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3.1: Scale down a pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = common_const.RESTORE_SCALE_REPLICAS
        LOGGER.info("Step 3.2: Scale up pod")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 3.2: Scale up the pod again by making replicas=1")
        self.restore_pod = False

        LOGGER.info("Step 4: Verify health monitor log")
        ha_wc_count_after_scale = node_obj.execute_cmd(ha_wc_count_cmd)
        if isinstance(ha_wc_count_after_scale, bytes):
            ha_wc_count_after_scale = str(ha_wc_count_after_scale, 'UTF-8')
        LOGGER.info("count after scale %s", ha_wc_count_after_scale)
        assert_utils.assert_equal(ha_wc_count,ha_wc_count_after_scale,"Count does not match" )
        LOGGER.info("Step 4: Verified health monitor log")
        
        LOGGER.info("Step 5: Stop the cluster")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=common_const.HA_POD_NAME_PREFIX)
        pod_nameha = pod_list[0]
        ha_hostname = self.node_master_list[0].get_pods_node_fqdn(pod_nameha)
        LOGGER.info("Cortx HA pod running on: %s ", ha_hostname[pod_nameha])
        for node in range(self.num_nodes):
            if CMN_CFG["nodes"][node]["hostname"] == ha_hostname[pod_nameha]:
                node_obj = LogicalNode(hostname=ha_hostname[pod_nameha],
                                       username=CMN_CFG["nodes"][node]["username"],
                                       password=CMN_CFG["nodes"][node]["password"])
                break
        resp = self.ha_obj.cortx_stop_cluster(pod_obj=self.master_node_obj)
        assert_utils.assert_true(resp[0], "Error during Stopping cluster")
        LOGGER.info("Check all Pods are offline.")
        LOGGER.info("Step 5: Stopped the cluster successfully")

        LOGGER.info("Step 6:Verify the HA logs for SIGTERM alert message")
        for log in common_const.HA_SHUTDOWN_LOGS:
            pvc_list = node_obj.execute_cmd\
                (common_cmd.HA_LOG_PVC, read_lines=True)
            hapvc = None
            for hapvc in pvc_list:
                if common_const.HA_POD_NAME_PREFIX in hapvc:
                    hapvc = hapvc.replace("\n", "")
                    LOGGER.info("hapvc list %s", hapvc)
                    break
            cmd_halog = "tail -10 /mnt/fs-local-volume/local-path-provisioner/"\
                        + hapvc + "/log/ha/*/" + log + " | grep 'SIGTERM'"
            output = node_obj.execute_cmd(cmd_halog)
            if isinstance(output, bytes):
                output = str(output, 'UTF-8')
            assert_utils.assert_in("Received SIGTERM", output, "SIGTERM Not received")  
        LOGGER.info("Step 6:Verified the HA logs for SIGTERM alert message")
        LOGGER.info("COMPETED: Scaled pod down and up and verified HA alerts")


