#!/usr/bin/python # pylint: disable=C0302
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

"""
Test suite for disk failure recovery
"""

import logging
import random
import time

import pytest

from commons import constants as common_const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG, HA_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.durability.disk_failure_recovery_libs import DiskFailureRecoveryLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.durability.near_full_data_storage import NearFullStorage

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestDiskFailureRecovery:
    """
    Test suite for disk failure recovery
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.test_prefix = []
        cls.failed_disks_dict = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.dsk_rec_obj = DiskFailureRecoveryLib()
        cls.s3_clean = None
        cls.parity_units = None
        cls.pod_name = None
        cls.mgnt_ops = ManagementOPs()
        cls.delay_sns_repair = 30

        for node in CMN_CFG["nodes"]:
            host = node["hostname"]
            user_name = node["username"]
            user_pass = node["password"]
            if node["node_type"] == "master":
                cls.node_master_list.append(LogicalNode(hostname=host, username=user_name,
                                                        password=user_pass))
                cls.hlth_master_list.append(Health(hostname=host, username=user_name,
                                                   password=user_pass))
            else:
                cls.node_worker_list.append(LogicalNode(hostname=host, username=user_name,
                                                        password=user_pass))
        cls.near_full_percent = HA_CFG['near_full_system_percent']

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.s3_clean = {}
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")

        LOGGER.info("Getting parity units count.")
        resp = self.dsk_rec_obj.retrieve_durability_values(self.node_master_list[0], "sns")
        assert_utils.assert_true(resp[0], resp[1])
        self.parity_units = resp[1]['parity']

        LOGGER.info("Getting data pod name.")
        resp = self.node_master_list[0].get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        self.pod_name = resp[1]
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        LOGGER.info("Cleanup: Make failed disks online")
        for disk in self.failed_disks_dict:
            resp = self.dsk_rec_obj.change_disk_status_hctl(self.node_master_list[0],
                                                            self.pod_name,
                                                            self.failed_disks_dict[disk][0],
                                                            self.failed_disks_dict[disk][2],
                                                            "online")
            LOGGER.info("disk status change resp: %s", resp)
        LOGGER.info("Cleanup: Made all disks online")

        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36580")
    def test_sns_repair_fail_disk_less_than_k(self):
        """
        Validate SNS repair works fine with failed disks are less than K(parity units)
        """
        LOGGER.info("STARTED: Validate SNS repair works fine with failed disks "
                    "are less than K(parity units)")

        LOGGER.info("Step 1: Do IOs(Write and Read)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix.append('test-36580')
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 2: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 3: Fail disks less than K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        if self.parity_units == 1:
            disk_fail_cnt = 1
        else:
            disk_fail_cnt = random.randint(1, self.parity_units - 1)  # nosec

        resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                          self.node_worker_list, self.pod_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disks_dict = resp[1]
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 4: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        LOGGER.info("Step 5: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36580-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 6: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)

        time.sleep(self.delay_sns_repair)
        LOGGER.info("Step 8: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count after sns repair")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 9: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 10: Read data written in step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36580-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("COMPLETED: Test SNS repair works fine with failed disks "
                    "are less than K(parity units)")

    # pylint: disable=too-many-statements
    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36581")
    def test_sns_repair_fail_disk_equal_to_k(self):
        """
        Validate SNS repair works fine with failed disks are equal to K(parity units)
        """
        LOGGER.info("STARTED: Validate SNS repair works fine with failed disks "
                    "are equal to K(parity units)")

        LOGGER.info("Step 1: Do IOs(Write and Read)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix.append('test-36581')
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 2: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 3: Fail disks equal to K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        disk_fail_cnt = self.parity_units

        resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                          self.node_worker_list, self.pod_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disks_dict = resp[1]
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 4: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        LOGGER.info("Step 5: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36581-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 6: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 8: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after sns repair is greater than "
                                            "or equal to degraded byte count after disk fail")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 9: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 10: Read data written in step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36581-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("COMPLETED: Test SNS repair works fine with failed disks "
                    "are equal to K(parity units)")

    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36393")
    def test_sns_repair_fail_disk_diff_cvg_less_than_k(self):
        """
        Validate SNS repair works fine with failed disks are less than K(parity units)
        and from different cvg
        """
        LOGGER.info("STARTED: Validate SNS repair works fine with failed disks "
                    "are less than K(parity units) and from different cvg")

        LOGGER.info("Step 1: Do IOs(Write and Read)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix.append('test-36393')
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 2: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 3: Fail disks less than K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        if self.parity_units == 1:
            disk_fail_cnt = 1
        else:
            disk_fail_cnt = random.randint(1, self.parity_units - 1)  # nosec

        while disk_fail_cnt >= 1:
            resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                              self.node_worker_list, self.pod_name,
                                              on_diff_cvg=True)
            if "Number of cvg are less" in resp[1]:
                disk_fail_cnt -= 1
            else:
                assert_utils.assert_true(resp[0], resp[1])
                self.failed_disks_dict = resp[1]
                break
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 4: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        LOGGER.info("Step 5: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36393-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 6: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 8: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count after sns repair")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 9: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 10: Read data written in step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36393-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("COMPLETED: Test SNS repair works fine with failed disks "
                    "are less than K(parity units) and from different cvg")

    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36394")
    def test_sns_repair_fail_disk_diff_cvg_equal_to_k(self):
        """
        Validate SNS repair works fine with failed disks are equal to K(parity units)
        and from different cvg
        """
        LOGGER.info("STARTED: Validate SNS repair works fine with failed disks "
                    "are equal to K(parity units) and from different cvg")

        LOGGER.info("Step 1: Do IOs(Write and Read)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix.append('test-36394')
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 2: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 3: Fail disks equal to K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        disk_fail_cnt = self.parity_units

        while disk_fail_cnt >= 1:
            resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                              self.node_worker_list, self.pod_name,
                                              on_diff_cvg=True)
            if "Number of cvg are less" in resp[1]:
                disk_fail_cnt -= 1
            else:
                assert_utils.assert_true(resp[0], resp[1])
                self.failed_disks_dict = resp[1]
                break
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 4: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        LOGGER.info("Step 5: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36394-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 6: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 8: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count after sns repair")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 9: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 10: Read data written in step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36394-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("COMPLETED: Test SNS repair works fine with failed disks "
                    "are equal to K(parity units) and from different cvg")

    # pylint: disable=too-many-statements
    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36396")
    def test_near_full_fail_disk_diff_cvg_less_than_k(self):
        """
        Validate SNS repair works fine on near full system with failed
        disks are less than K(parity units)
        """
        LOGGER.info("STARTED: Validate SNS repair works fine on near full system with failed disks "
                    "are less than K(parity units)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = users
        workload_info = None
        s3userinfo = list(users.values())[0]

        LOGGER.info("Step 1: Perform Write operations till overall disk space is filled %s",
                    self.near_full_percent)
        resp = NearFullStorage.get_user_data_space_in_bytes(self.node_master_list[0],
                                                            self.near_full_percent)
        assert_utils.assert_true(resp[0], resp[1])

        if not resp[1]:
            LOGGER.info("Current Memory usage is already more than expected memory usage,"
                        " skipping write operation")
        else:
            resp = NearFullStorage.perform_near_full_sys_writes(s3userinfo=s3userinfo,
                                                                user_data_writes=resp[1],
                                                                bucket_prefix=self.test_prefix[-1])
            assert_utils.assert_true(resp[0], resp[1])
            workload_info = resp[1]

        LOGGER.info("Step 2: Do IOs(Write and Read)")
        self.test_prefix.append('test-36396')
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 3: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 4: Fail disks less than K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        if self.parity_units == 1:
            disk_fail_cnt = 1
        else:
            disk_fail_cnt = random.randint(1, self.parity_units - 1)  # nosec

        resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                          self.node_worker_list, self.pod_name, on_diff_cvg=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disks_dict = resp[1]
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 5: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        # TODO : check if system goes into read only mode
        LOGGER.info("Step 6: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36396-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 8: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)

        time.sleep(self.delay_sns_repair)
        LOGGER.info("Step 9: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count after sns repair")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 10: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Read data written in step 2")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 12: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36396-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        if workload_info:
            LOGGER.info("Step 13: Read data written in step 1")
            NearFullStorage.perform_operations_on_pre_written_data(s3userinfo=s3userinfo,
                                                             workload_info=workload_info)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("COMPLETED: Test SNS repair works fine on near full system with failed disks "
                    "are less than K(parity units)")

    # pylint: disable=too-many-statements
    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36397")
    def test_near_full_fail_disk_diff_cvg_equal_to_k(self):
        """
        Validate SNS repair works fine on near full system with failed disks
        are equal to K(parity units)
        """
        LOGGER.info("STARTED: Validate SNS repair works fine on near full system with failed disks "
                    "are equal to K(parity units)")

        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = users
        workload_info = None
        s3userinfo = list(users.values())[0]

        LOGGER.info("Step 1: Perform Write operations till overall disk space is filled %s",
                    self.near_full_percent)
        resp = NearFullStorage.get_user_data_space_in_bytes(self.node_master_list[0],
                                                            self.near_full_percent)
        assert_utils.assert_true(resp[0], resp[1])

        if not resp[1]:
            LOGGER.info("Current Memory usage is already more than expected memory usage,"
                        " skipping write operation")
        else:
            resp = NearFullStorage.perform_near_full_sys_writes(s3userinfo=s3userinfo,
                                                                user_data_writes=resp[1],
                                                                bucket_prefix=self.test_prefix[-1])
            assert_utils.assert_true(resp[0], resp[1])
            workload_info = resp[1]

        LOGGER.info("Step 2: Do IOs(Write and Read)")
        self.test_prefix.append('test-36397')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 3: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 4: Fail disks equal to K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        disk_fail_cnt = self.parity_units

        resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                          self.node_worker_list, self.pod_name, on_diff_cvg=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disks_dict = resp[1]
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 5: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        # TODO : check if system goes into read only mode
        LOGGER.info("Step 6: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36397-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 8: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 9: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after sns repair is greater than "
                                            "or equal to degraded byte count after disk fail")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 10: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Read data written in step 2")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 12: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36397-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        if workload_info:
            LOGGER.info("Step 13: Read data written in step 1")
            resp = NearFullStorage.perform_operations_on_pre_written_data(s3userinfo=s3userinfo,
                                                                    workload_info=workload_info)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("COMPLETED: Test SNS repair works fine on near full system with failed disks "
                    "are equal to K(parity units)")

    # pylint: disable=too-many-statements
    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36398")
    def test_fail_disk_same_cvg_less_equal_to_k(self):
        """
        Validate SNS repair works fine with failed disks are less than or equal to K(parity units)
        on same cvg
        """
        LOGGER.info("STARTED: Validate SNS repair works fine with failed disks "
                    "are less than or equal to K(parity units) on same cvg")

        LOGGER.info("Step 1: Do IOs(Write and Read)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix.append('test-36398')
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 2: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(
            self.hlth_master_list[0],
            "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 3: Fail disks less than K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        if self.parity_units == 1:
            disk_fail_cnt = 1
        else:
            disk_fail_cnt = random.randint(1, self.parity_units - 1)  # nosec

        resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                          self.node_worker_list, self.pod_name, on_same_cvg=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disks_dict = resp[1]
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 4: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        LOGGER.info("Step 5: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36398-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 6: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)

        time.sleep(self.delay_sns_repair)
        LOGGER.info("Step 8: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count after repair")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 9: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 10: Read data written in step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36398-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("COMPLETED: Test SNS repair works fine with failed disks "
                    "are less than K(parity units) on same cvg")

    # pylint: disable=too-many-statements
    @pytest.mark.data_durability
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36399")
    def test_near_full_fail_disk_same_cvg_less_equal_to_k(self):
        """
        Validate SNS repair works fine on near full system with failed disks on same cvg
        are less or equal to K(parity units)
        """
        LOGGER.info("STARTED: Validate SNS repair works fine on near full system with failed disks "
                    "on same cvg are equal to K(parity units)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = users
        workload_info = None
        s3userinfo = list(users.values())[0]

        LOGGER.info("Step 1: PerformWrite operations till overall disk space is filled %s",
                    self.near_full_percent)
        resp = NearFullStorage.get_user_data_space_in_bytes(self.node_master_list[0],
                                                            self.near_full_percent)
        assert_utils.assert_true(resp[0], resp[1])

        if not resp[1]:
            LOGGER.info("Current Memory usage is already more than expected memory usage,"
                        " skipping write operation")
        else:
            resp = NearFullStorage.perform_near_full_sys_writes(s3userinfo=s3userinfo,
                                                                user_data_writes=resp[1],
                                                                bucket_prefix=self.test_prefix[-1])
            assert_utils.assert_true(resp[0], resp[1])
            workload_info = resp[1]

        LOGGER.info("Step 2: Do IOs(Write and Read)")
        self.test_prefix.append('test-36399')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 3: Get degraded byte count before failing the disk")
        degraded_byte_cnt_before = self.dsk_rec_obj.get_byte_count_hctl(self.hlth_master_list[0],
                                                                        "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_before)

        LOGGER.info("Step 4: Fail disks equal to K(parity units)")
        LOGGER.info("No of parity units (K): %s", self.parity_units)
        disk_fail_cnt = self.parity_units

        resp = self.dsk_rec_obj.fail_disk(disk_fail_cnt, self.node_master_list[0],
                                          self.node_worker_list, self.pod_name, on_same_cvg=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.failed_disks_dict = resp[1]
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 5: Get degraded byte count after disk failure")
        degraded_byte_cnt_after_fail = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_fail)

        if degraded_byte_cnt_before >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after disk failure less than "
                                            "or equal to degraded byte count before disk fail")
        else:
            LOGGER.info("Degraded byte count is more as expected after disk fail")

        # TODO : check if system goes into read only mode
        LOGGER.info("Step 6: Do IOs(Write and Read) after disk failure")
        self.test_prefix.append('test-36399-after-disk-fail')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 7: Check cluster status")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 8: Start SNS repair")
        resp = self.dsk_rec_obj.sns_repair(self.node_master_list[0], "start", self.pod_name)
        LOGGER.info("sns start resp: %s", resp)
        time.sleep(self.delay_sns_repair)

        LOGGER.info("Step 9: Check degraded byte count after sns repair")
        degraded_byte_cnt_after_repair = self.dsk_rec_obj.get_byte_count_hctl \
            (self.hlth_master_list[0], "degraded_byte_count")
        LOGGER.info("degraded byte count: %s", degraded_byte_cnt_after_repair)

        if degraded_byte_cnt_after_repair >= degraded_byte_cnt_after_fail:
            assert_utils.assert_true(False, "Degraded byte count after sns repair is greater than "
                                            "or equal to degraded byte count after disk fail")
        else:
            LOGGER.info("Degraded byte count after sns repair is less than "
                        "degraded byte count after disk fail")

        LOGGER.info("Step 10: Check cluster status after repair")
        resp = self.hlth_master_list[0].all_cluster_services_online()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 11: Read data written in step 2")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[0],
                                                    skipwrite=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Step 12: Do IOs(Write and Read) after sns repair")
        self.test_prefix.append('test-36399-after-recovery')
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=s3userinfo,
                                                    log_prefix=self.test_prefix[-1],
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])

        if workload_info:
            LOGGER.info("Step 13: Read data written in step 1")
            resp = NearFullStorage.perform_operations_on_pre_written_data(s3userinfo=s3userinfo,
                                                                    workload_info=workload_info)
            assert_utils.assert_true(resp[0],resp[1])
        LOGGER.info("COMPLETED: Validate SNS repair works fine on near full system with failed "
                    "disks on same cvg are equal to K(parity units)")
