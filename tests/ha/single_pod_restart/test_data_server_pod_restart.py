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
import secrets
import time
from time import perf_counter_ns

import pytest

from commons import commands as cmd
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from config import CMN_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

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
        cls.username = []
        cls.password = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.node_worker_list = []
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

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restore_node = False
        self.restore_ip = False
        self.s3_clean = dict()
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("STARTED: Teardown Operations.")
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
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
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
