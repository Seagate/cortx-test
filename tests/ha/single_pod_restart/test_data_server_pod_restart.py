#!/usr/bin/python  # pylint: disable=too-many-instance-attributes
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
HA test suite for single data and server Pod restart
"""

import logging
import os
import secrets
import threading
import time
from multiprocessing import Queue
import re
from time import perf_counter_ns

import pytest

from commons import commands as cmd
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestDataServerPodRestart:
    """
    Test suite for single Data and Server Pod Restart
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = list()
        cls.password = list()
        cls.node_master_list = list()
        cls.hlth_master_list = list()
        cls.node_worker_list = list()
        cls.ha_obj = HAK8s()
        cls.random_time = cls.s3_clean = cls.test_prefix = cls.test_prefix_deg = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_node = cls.multipart_obj_path = None
        cls.restore_ip = cls.node_iface = cls.new_worker_obj = cls.node_ip = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
                cls.hlth_master_list.append(Health(hostname=cls.host,
                                                   username=cls.username[node],
                                                   password=cls.password[node]))
            else:
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restore_node = False
        self.restore_ip = False
        self.s3_clean = dict()
        self.restore_pod = self.restore_method = self.deployment_name = self.set_name = None
        self.deployment_backup = None
        if not os.path.exists(self.test_dir_path):
            resp = sysutils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        convert = lambda text: int(text) if text.isdigit() else text
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        LOGGER.info("Get %s and %s pods to be deleted", const.POD_NAME_PREFIX,
                    const.SERVER_POD_NAME_PREFIX)
        self.pod_dict = dict()
        for prefix in [const.POD_NAME_PREFIX, const.SERVER_POD_NAME_PREFIX]:
            self.pod_list = list()
            sts_dict = self.node_master_list[0].get_sts_pods(pod_prefix=prefix)
            sts_list = list(sts_dict.keys())
            LOGGER.debug("%s Statefulset: %s", prefix, sts_list)
            sts = self.system_random.sample(sts_list, 1)[0]
            sts_dict_val = sorted(sts_dict.get(sts), key=alphanum_key)
            self.delete_pod = sts_dict_val[-1]
            LOGGER.info("Pod to be deleted is %s", self.delete_pod)
            self.set_type, self.set_name = self.node_master_list[0].get_set_type_name(
                pod_name=self.delete_pod)
            self.pod_list.append(self.delete_pod)
            self.pod_list.append(self.set_name)
            resp = self.node_master_list[0].get_num_replicas(self.set_type, self.set_name)
            assert_utils.assert_true(resp[0], resp)
            self.num_replica = int((resp[1]))
            self.pod_list.append(self.num_replica)
            self.pod_dict[prefix] = self.pod_list
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.restore_pod:
            for pod_prefix in self.pod_dict:
                self.restore_method = self.pod_dict.get(pod_prefix)[-1]
                resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                               restore_method=self.restore_method,
                                               restore_params={
                                                   "deployment_name":
                                                       self.pod_dict.get(pod_prefix)[-2],
                                                   "deployment_backup": self.deployment_backup,
                                                   "num_replica": self.pod_dict.get(pod_prefix)[2],
                                                   "set_name": self.pod_dict.get(pod_prefix)[1]})
                LOGGER.debug("Response: %s", resp)
                assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method}"
                                                  " way")
                LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if self.restore_node:
            LOGGER.info("Cleanup: Power on the %s down node.", self.node_name)
            resp = self.ha_obj.host_power_on(host=self.node_name)
            assert_utils.assert_true(resp, f"Failed to power on {self.node_name}.")
        if self.restore_ip:
            LOGGER.info("Cleanup: Get the network interface up for %s ip", self.node_ip)
            self.new_worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(self.node_iface, "up"),
                                            read_lines=True)
            resp = sysutils.check_ping(host=self.node_ip)
            assert_utils.assert_true(resp, "Interface is still not up.")
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp)
        for file in self.extra_files:
            if os.path.exists(file):
                sysutils.remove_file(file)
        LOGGER.info("Removing all files from %s", self.test_dir_path)
        sysutils.cleanup_dir(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="VM restart getting stuck CORTX-32933")
    @pytest.mark.tags("TEST-34086")
    def test_pod_restart_node_down(self):
        """
        Verify IOs before and after data pod restart (pod shutdown by making worker node down).
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making worker node down.")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34086'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown data pod by shutting node on which its hosted.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        resp = self.ha_obj.get_data_pod_no_ha_control(data_pod_list, self.node_master_list[0])
        data_pod_name = resp[0]
        server_pod_name = resp[1]
        data_node_fqdn = resp[2]
        srv_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        self.node_name = data_node_fqdn
        LOGGER.info("Shutdown the node: %s", data_node_fqdn)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=data_node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where data pod was running.", data_node_fqdn)
        self.restore_node = True
        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")
        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        LOGGER.info("Check services on %s data pod", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Check services on %s server pod", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name], fail=True,
                                                           hostname=srv_pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of data and server pods are in offline state")
        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(
            pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")
        LOGGER.info("Step 6: Perform WRITE/READ/Verify in degraded cluster.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users_deg = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users_deg)
            self.test_prefix_deg = 'test-34086-deg'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Perform WRITE/READ/Verify on buckets created in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs completed successfully.")
        LOGGER.info("Step 7: Start the pod %s back by powering on the node %s",
                    data_pod_name, data_node_fqdn)
        LOGGER.info("Power on the %s down node.", data_node_fqdn)
        resp = self.ha_obj.host_power_on(host=data_node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered on")
        LOGGER.info("Step 7: Node %s is restarted", data_node_fqdn)
        self.restore_node = False
        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        LOGGER.info("Step 9: Perform READ/Verify on already created buckets.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Perform READ/Verify on buckets created in degraded cluster.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipwrite=True, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Perform READ/Verify on buckets created in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Completed READ/Verify on already created buckets.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 10: Start IOs (create IAM user, buckets and upload objects).")
            users_rst = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users_rst)
            self.test_prefix = 'test-34086-restart'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 10: IOs completed successfully.")
        LOGGER.info("COMPLETED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making worker node down.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="VM restart getting stuck CORTX-32933")
    @pytest.mark.tags("TEST-34085")
    def test_pod_restart_node_nw_down(self):
        """
        Verify IOs before and after data pod restart,
        pod shutdown by making mgmt ip of worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making mgmt ip of worker node down")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34085'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown data pod by making network down of node "
                    "on which its hosted.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        resp = self.ha_obj.get_data_pod_no_ha_control(data_pod_list, self.node_master_list[0])
        data_pod_name = resp[0]
        server_pod_name = resp[1]
        data_node_fqdn = resp[2]
        srv_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        LOGGER.info("Get the ip of the host from the node %s", data_node_fqdn)
        resp = self.ha_obj.get_nw_iface_node_down(host_list=self.host_worker_list,
                                                  node_list=self.node_worker_list,
                                                  node_fqdn=data_node_fqdn)
        self.node_ip = resp[1]
        self.node_iface = resp[2]
        self.new_worker_obj = resp[3]
        assert_utils.assert_true(resp[0], "Node network is still up")
        LOGGER.info("Step 2: %s Node's network is down.", data_node_fqdn)
        self.restore_ip = True
        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")
        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        LOGGER.info("Check services on %s data pod", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Check services on %s server pod", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name], fail=True,
                                                           hostname=srv_pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of data and server pods are in offline state")
        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(
            pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")
        LOGGER.info("Step 6: Perform WRITE/READ/Verify in degraded cluster.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Create new IAM user, buckets and run IOs")
            users_deg = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users_deg)
            self.test_prefix_deg = 'test-34085-deg'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Perform WRITE/READ/Verify on buckets created in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs completed successfully.")
        LOGGER.info("Step 7: Get the network back up for node %s", data_node_fqdn)
        LOGGER.info("Get the network interface up for %s ip", self.node_ip)
        self.new_worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(self.node_iface, "up"),
                                        read_lines=True)
        resp = sysutils.execute_cmd(cmd.CMD_PING.format(self.node_ip),
                                    read_lines=True, exc=False)
        assert_utils.assert_not_in(b"100% packet loss", resp[1][0],
                                   f"Node interface still down. {resp}")
        LOGGER.info("Step 7: Network interface is back up for %s node", data_node_fqdn)
        self.restore_ip = False
        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        LOGGER.info("Step 9: Perform READ/Verify on already created buckets.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Perform READ/Verify on buckets created in degraded cluster.")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_deg.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipwrite=True, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Perform READ/Verify on buckets created in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipwrite=True, skipcleanup=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Completed READ/Verify on already created buckets.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 10: Start IOs (create IAM user, buckets and upload objects).")
            users_rst = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users_rst)
            self.test_prefix = 'test-34086-restart'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_rst.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 10: IOs completed successfully.")
        LOGGER.info("COMPLETED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making mgmt ip of worker node down")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45510")
    def test_io_data_server_pod_restart(self):
        """
        Verify IO when any 1 data pod and any 1 server pod restart by replica method
        """
        LOGGER.info("STARTED: Verify IO when any 1 data pod and any 1 server pod restart by "
                    "replica method")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = f'test-45510-{int(perf_counter_ns())}'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects")
        LOGGER.info("Step 2: Shutdown one data and one server pod with replica method and verify"
                    " cluster & remaining pods status")
        for pod_prefix in self.pod_dict:
            num_replica = self.pod_dict[pod_prefix][-1] - 1
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                pod_prefix=[pod_prefix], delete_pod=[self.pod_dict.get(pod_prefix)[0]],
                num_replica=num_replica)
            # Assert if empty dictionary
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1].keys())[0]
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['deployment_name'])
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['method'])
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("successfully shutdown pod %s", self.pod_dict.get(pod_prefix)[0])
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown one data and one server pod. Verified cluster "
                    "and services states are as expected & remaining pods status is online")
        LOGGER.info("STEP 3: Perform READs/Verify on data written in healthy cluster.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs/Verify on data written in healthy cluster.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 4: Create new bucket and perform WRITEs/READs/Verify with variable "
                        "object sizes in degraded mode")
            self.test_prefix_deg = f'test-45510-deg-{int(perf_counter_ns())}'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipcleanup=True, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Create new objects and perform WRITEs/READs/Verify with variable "
                    "object sizes in degraded mode")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs/READs/Verify with variable sizes objects in "
                    "degraded mode")
        LOGGER.info("Step 5: Restore data and server pod and check cluster status.")
        for pod_prefix in self.pod_dict:
            self.restore_method = self.pod_dict.get(pod_prefix)[-1]
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={
                                               "deployment_name": self.pod_dict.get(pod_prefix)[-2],
                                               "deployment_backup": self.deployment_backup,
                                               "num_replica": self.pod_dict.get(pod_prefix)[2],
                                               "set_name": self.pod_dict.get(pod_prefix)[1]})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Step 5: Successfully started data and server pod and cluster is online.")
        self.restore_pod = False
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 6: Perform READs and verify DI on the data written on buckets "
                        "created in degraded mode")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix_deg,
                                                        skipwrite=True, skipcleanup=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Successfully run READ/Verify on data written on buckets created "
                        "in degraded mode")
        LOGGER.info("Step 7: Perform READ/Verify on data written with buckets created in healthy "
                    "mode")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully run READ/Verify on data written with buckets created in "
                    "healthy mode")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 8: Create new IAM user and buckets, Perform WRITEs-READs-Verify with "
                        "variable object sizes after data and server pod restart")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = f'test-45510-restart-{int(perf_counter_ns())}'
            self.s3_clean.update(users)
        else:
            LOGGER.info("Step 8: Create new objects, Perform WRITEs-READs-Verify with variable "
                        "object sizes after data and server pod restart")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed WRITEs-READs-Verify with variable sizes objects after "
                    "data and server pod restart")
        LOGGER.info("COMPLETED: Verify IO when any 1 data pod and any 1 server pod restart by "
                    "replica method")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45517")
    def test_cont_io_data_server_pod_restart(self):
        """
        Verify Continuous IO when any 1 data pod and any 1 server pod restart by replica method
        """
        LOGGER.info("STARTED: Verify Continuous IO when any 1 data pod and any 1 server pod"
                    " restart by replica method")
        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes")
        users_org = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = f'test-45517-{int(perf_counter_ns())}'
        self.s3_clean.update(users_org)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("Step 2: Shutdown one data and one server pod with replica method and verify "
                    "cluster & remaining pods status")
        for pod_prefix in self.pod_dict:
            num_replica = self.pod_dict[pod_prefix][-1] - 1
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                pod_prefix=[pod_prefix], delete_pod=[self.pod_dict.get(pod_prefix)[0]],
                num_replica=num_replica)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1].keys())[0]
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['deployment_name'])
            self.pod_dict[pod_prefix].append(resp[1][pod_name]['method'])
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("successfully shutdown pod %s", self.pod_dict.get(pod_prefix)[0])
        self.restore_pod = True
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown one data and one server pod. Verified cluster "
                    "and services states are as expected & remaining pods status is online")
        event = threading.Event()  # Event to be used to send when pod restart start
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 3.1: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        remaining_bkt = HA_CFG["s3_bucket_data"]["no_bck_writes"]
        del_bucket = wr_bucket - remaining_bkt
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]['accesskey']
        secret_key = list(users.values())[0]['secretkey']
        test_prefix_del = f'test-delete-45517-{int(perf_counter_ns())}'
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           "number of buckets")
        s3_data = wr_resp[0]
        LOGGER.info("Step 3.1: Successfully performed WRITEs with variable object sizes on %s "
                    "buckets for parallel DELETEs.", wr_bucket)
        LOGGER.info("Step 3.2: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = f'test-read-45517-{int(perf_counter_ns())}'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3.2: Performed WRITEs with variable sizes objects for parallel READs.")
        LOGGER.info("Step 4: Starting three independent background threads for READs, WRITEs & "
                    "DELETEs.")
        LOGGER.info("Step 4.1: Start continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = s3_data.keys()
        get_random_buck = self.system_random.sample(bucket_list, del_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 4.1: Successfully started DELETEs in background for %s buckets",
                    del_bucket)
        LOGGER.info("Step 4.2: Perform WRITEs with variable object sizes in background")
        test_prefix_write = f'test-write-45517-{int(perf_counter_ns())}'
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 4.2: Successfully started WRITEs with variable sizes objects in "
                    "background")
        LOGGER.info("Step 4.3: Perform READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 4.3: Successfully started READs and verify on the written data in "
                    "background")
        LOGGER.info("Step 4: Successfully starting three independent background threads for READs,"
                    " WRITEs & DELETEs.")
        LOGGER.info("Wait for %s seconds for all background operations to start",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 5: Restore data and server pod and check cluster status.")
        event.set()
        for pod_prefix in self.pod_dict:
            self.restore_method = self.pod_dict.get(pod_prefix)[-1]
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={
                                               "deployment_name": self.pod_dict.get(pod_prefix)[-2],
                                               "deployment_backup": self.deployment_backup,
                                               "num_replica": self.pod_dict.get(pod_prefix)[2],
                                               "set_name": self.pod_dict.get(pod_prefix)[1]},
                                           clstr_status=True)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Step 5: Successfully started data and server pod and cluster is online.")
        self.restore_pod = False
        event.clear()
        LOGGER.info("Step 6: Verify status for In-flight READs/WRITEs/DELETEs while data and "
                    "server pod was restarted")
        LOGGER.info("Waiting for background IOs thread to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 6.1: Verify status for In-flight DELETEs")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  "Expected all pass, Buckets which failed in DELETEs before and "
                                  f"after pod deletion: {fail_del_bkt}. Buckets which failed in "
                                  f"DELETEs during pod deletion: {event_del_bkt}.")
        LOGGER.info("Step 6.1: Verified status for In-flight DELETEs")
        LOGGER.info("Step 6.2: Verify status for In-flight WRITEs")
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "WRITEs before and after pod deletion are "
                                                "expected to pass.Logs which contain failures:"
                                                f"{resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "In-flight WRITEs Logs which contain failures: "
                                                f"{resp[1]}")
        LOGGER.info("Step 6.2: Verified status for In-flight WRITEs")
        LOGGER.info("Step 6.3: Verify status for In-flight READs/Verify DI")
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "READs/VerifyDI logs which contain failures:"
                                                f"{resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "READs/VerifyDI Logs which contain failures: "
                                                f"{resp[1]}")
        LOGGER.info("Step 6.3: Verified status for In-flight READs/Verify DI")
        LOGGER.info("Step 6: Verified status for In-flight READs/WRITEs/DELETEs while data and "
                    "server pod was restarted")
        LOGGER.info("Step 7: Verify READ/Verify for data written in healthy cluster and delete "
                    "buckets")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_org.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Verified READ/Verify on data written in healthy mode and deleted "
                    "buckets")
        LOGGER.info("COMPLETED: Verify Continuous IO when any 1 data pod and any 1 server pod"
                    " restart by replica method")
