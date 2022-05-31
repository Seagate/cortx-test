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
"""Test Suite for IO stability Degraded Path workloads."""
import logging
import os
import time
from datetime import datetime, timedelta

import pytest

from commons import configmanager, cortxlogging
from commons.constants import K8S_SCRIPTS_PATH
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils, support_bundle_utils
from config import CMN_CFG
from conftest import LOG_DIR
from libs.dtm.ProcPathStasCollection import EnableProcPathStatsCollection
from libs.durability.near_full_data_storage import NearFullStorage
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.iostability.iostability_lib import IOStabilityLib, send_mail_notification
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_test_lib import S3TestLib


class TestIOWorkloadDegradedPath:
    """Test Class for IO Stability in Degraded path."""

    @classmethod
    def setup_class(cls):
        """Setup class."""

        cls.log = logging.getLogger(__name__)
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.master_node_list = []
        cls.worker_node_list = []
        cls.health_obj_list = []
        for node in CMN_CFG['nodes']:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            if node["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
                cls.health_obj_list.append(Health(hostname=node["hostname"],
                                                  username=node["username"],
                                                  password=node["password"]))
            else:
                cls.worker_node_list.append(node_obj)
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/iostability_test.yaml")
        cls.setup_type = CMN_CFG["setup_type"]
        cls.test_completed = False
        cls.iolib = IOStabilityLib()
        cls.duration_in_days = int(os.getenv("DURATION_OF_TEST_IN_DAYS",
                                             cls.test_cfg['happy_path_duration_days']))

        cls.clients = int(os.getenv("CLIENT_SESSIONS_PER_WORKER_NODE", '0'))
        if cls.clients == 0:
            if cls.setup_type == 'HW':
                cls.clients = cls.test_cfg['sessions_per_node_hw']
            else:
                cls.clients = cls.test_cfg['sessions_per_node_vm']
        cls.sender_mail_id = os.getenv("SENDER_MAIL_ID", None)
        cls.receiver_mail_id = os.getenv("RECEIVER_MAIL_ID", None)
        cls.start_time = datetime.now()
        cls.mail_notify = None
        cls.s3t_obj = S3TestLib()
        cls.ha_obj = HAK8s()
        cls.s3userinfo = {'accesskey': ACCESS_KEY, 'secretkey': SECRET_KEY}

    def setup_method(self):
        """Setup Method"""
        self.log.info("Setup Method Started")
        self.log.info("Start Procpath collection")
        self.proc_path = EnableProcPathStatsCollection(CMN_CFG)
        resp = self.proc_path.setup_requirement()
        assert_utils.assert_true(resp[0], resp[1])
        self.proc_path.start_collection()
        time.sleep(30)
        resp = self.proc_path.validate_collection()
        assert_utils.assert_true(resp[0], resp[1])
        self.test_completed = False
        self.log.info("Setup Method Ended")

    def teardown_method(self):
        """Teardown method."""
        self.log.info("Teardown method")
        if not self.test_completed:
            self.mail_notify.event_fail.set()
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                                   scripts_path=K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)
        else:
            self.mail_notify.event_pass.set()
        self.log.info("Stop Procpath collection")
        self.proc_path.stop_collection()
        self.log.info("Copy files to client")
        resp = self.proc_path.get_stat_files_to_local()
        self.log.debug("Resp : %s", resp)
        self.log.info("Teardown method ended.")

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40172")
    def test_object_crud_single_pod_failure(self):
        """Perform Object CRUD operations in degraded mode in loop using S3bench for n days."""
        self.log.info("STARTED: Test for Object CRUD operations in degraded mode in loop using "
                      "S3bench for %s days", self.duration_in_days)
        test_case_name = cortxlogging.get_frame()
        self.mail_notify = send_mail_notification(self.sender_mail_id, self.receiver_mail_id,
                                                  test_case_name, self.health_obj_list[0])

        self.log.info("Step 1: Create 50 buckets in healthy mode ")
        bucket_creation_healthy_mode = self.test_cfg['bucket_creation_healthy_mode']
        bucket_list = None
        if bucket_creation_healthy_mode:
            resp = self.s3t_obj.create_multiple_buckets(50, 'test-40172')
            bucket_list = resp[1]
            self.log.info("Step 1: Bucket created in healthy mode ")
        else:
            self.log.info("Step 1: Skipped bucket creation in healthy mode ")

        self.log.info("Step 2: Shutdown the data pod safely by making replicas=0,"
                      "check degraded status.")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(self.master_node_list[0],
                                                             self.health_obj_list[0])
        assert_utils.assert_true(resp[0], "Failed in shutdown or expected cluster check")
        self.log.info("Deleted pod : %s", list(resp[1].keys())[0])

        self.log.info("Step 3: Perform IO's using S3bench")
        workload_distribution = self.test_cfg['workloads_distribution']
        clients = (len(self.worker_node_list) - 1) * self.clients
        total_obj = 10000
        self.iolib.execute_workload_distribution(distribution=workload_distribution,
                                                 clients=clients,
                                                 total_obj=total_obj,
                                                 duration_in_days=self.duration_in_days,
                                                 log_file_prefix='test-40172',
                                                 buckets_created=bucket_list)
        self.test_completed = True
        self.log.info("ENDED: Test for Object CRUD operations in degraded mode in loop using "
                      "S3bench for %s days", self.duration_in_days)

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40173")
    def test_disk_near_full_read_in_degraded_s3bench(self):
        """
        Perform disk storage near full once in healthy cluster and read in degraded cluster in loop
        for n days.
        """
        self.log.info("STARTED: Perform disk storage near full once in healthy cluster and "
                      "read in degraded cluster in loop for %s days.", self.duration_in_days)
        test_case_name = cortxlogging.get_frame()
        self.mail_notify = send_mail_notification(self.sender_mail_id, self.receiver_mail_id,
                                                  test_case_name, self.health_obj_list[0])

        bucket_prefix = "testbkt-40173"
        client = len(self.worker_node_list) * self.clients
        percentage = self.test_cfg['nearfull_storage_percentage']

        self.log.info("Step 1: Calculating byte count for required percentage")
        resp = NearFullStorage.get_user_data_space_in_bytes(master_obj=self.master_node_list[0],
                                                            memory_percent=percentage)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Need to add %s bytes for required percentage", resp[1])

        self.log.info("Step 2: Performing writes till we reach required percentage")
        ret = NearFullStorage.perform_near_full_sys_writes(s3userinfo=self.s3userinfo,
                                                           user_data_writes=int(resp[1]),
                                                           bucket_prefix=bucket_prefix,
                                                           client=client)
        assert_utils.assert_true(ret[0], ret[1])
        for each in ret[1]:
            each["num_clients"] = (len(self.worker_node_list) - 1) \
                                  * self.clients
        self.log.debug("Write operation data: %s", ret)

        self.log.info("Step 3: Shutdown the data pod safely by making replicas=0, "
                      "check degraded status.")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(self.master_node_list[0],
                                                             self.health_obj_list[0])
        assert_utils.assert_true(resp[0], "Failed in shutdown or expected cluster check")
        self.log.info("Deleted pod : %s", list(resp[1].keys())[0])

        self.log.info("Step 4: Performing read operations.")
        end_time = datetime.now() + timedelta(days=self.duration_in_days)
        loop = 1
        while datetime.now() < end_time:
            loop += 1
            self.log.info("%s remaining time for reading loop", (end_time - datetime.now()))
            read_ret = NearFullStorage.perform_operations_on_pre_written_data(
                s3userinfo=self.s3userinfo,
                workload_info=ret[1],
                skipread=False,
                validate=True,
                skipcleanup=True)
            self.log.info("%s interation is done", loop)
            assert_utils.assert_true(read_ret[0], read_ret[1])
        # To Do delete operation, will be enabled after support from cortx
        self.test_completed = True
        self.log.info("ENDED: Perform disk storage near full once and read in loop for %s days",
                      self.duration_in_days)

    # pylint: disable-msg=too-many-branches
    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40174")
    def test_degraded_iteration_write_read_partial_delete(self):
        """Perform 30% Writes of user data capacity (Healthy mode) and perform Object CRUD
         (30% write,Read, 20% delete) operation(degraded mode)."""
        write_percent_per_iter = self.test_cfg['write_percent_per_iter']
        delete_percent_per_iter = self.test_cfg['delete_percent_per_iter']

        self.log.info(
            "STARTED: Test for Perform %s percent Writes of user data capacity (Healthy mode) "
            "and perform Object CRUD(%s write,Read,%s delete) operation(degraded mode)",
            write_percent_per_iter, write_percent_per_iter, delete_percent_per_iter)

        self.mail_notify = send_mail_notification(self.sender_mail_id, self.receiver_mail_id,
                                                  cortxlogging.get_frame(), self.health_obj_list[0])

        max_percentage = self.test_cfg['nearfull_storage_percentage']
        clients = (len(self.worker_node_list) - 1) * self.clients
        end_time = datetime.now() + timedelta(days=self.duration_in_days)

        bucket_creation_healthy_mode = self.test_cfg['bucket_creation_healthy_mode']
        avail_buckets = []
        if bucket_creation_healthy_mode:
            self.log.info("Step 1: Create %s buckets in healthy mode",
                          self.test_cfg['create_bucket_count'])
            resp = self.s3t_obj.create_multiple_buckets(self.test_cfg['create_bucket_count'],
                                                        "test-40174-bkt")
            for each in resp[1]:
                avail_buckets.append(each)
            self.log.info("Step 1: Bucket created in healthy mode ")
        else:
            self.log.info("Step 1: Skipped bucket creation in healthy mode ")

        self.log.info("Step 2: Perform %s percent writes and Read the written data in healthy mode",
                      write_percent_per_iter)
        write_per = write_percent_per_iter
        workload_info_list = []

        resp = NearFullStorage.perform_write_to_fill_system_percent(self.master_node_list[0],
                                                                    write_per, self.s3userinfo,
                                                                    "test-40174-bkt", clients,
                                                                    avail_buckets)

        assert_utils.assert_true(resp[0], resp[1])
        if resp[1] is not None:
            for each in resp[1]:
                avail_buckets.remove(each['bucket'])
            workload_info_list.extend(resp[1])
            self.log.info("Write Completed.")

        self.log.info("Step 3 : Perform Single pod shutdown")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(self.master_node_list[0],
                                                             self.health_obj_list[0])
        assert_utils.assert_true(resp[0], "Failed in shutdown or expected cluster check")
        self.log.info("Deleted pod : %s", list(resp[1].keys())[0])

        self.log.info("Step 4: Perform Reads/Delete on data written in healthy mode"
                      " and Write/Reads/Delete on data written in degraded mode")
        loop = 1
        while datetime.now() < end_time:
            self.log.info(" Loop count : %s", loop)
            loop += 1
            self.log.info("Get Current disk usage capacity")
            write_per = write_per + write_percent_per_iter

            if write_per < max_percentage:
                resp = NearFullStorage.perform_write_to_fill_system_percent(
                    self.master_node_list[0], write_per, self.s3userinfo, "test-40174-bkt", clients,
                    avail_buckets)
                assert_utils.assert_true(resp[0], resp[1])
                if resp[1] is not None:
                    for each in resp[1]:
                        avail_buckets.remove(each['bucket'])
                    workload_info_list.extend(resp[1])
                    self.log.info("Write Completed.")

                if len(workload_info_list) > 0:
                    self.log.info("Read and Validate all the written data of the cluster")
                    resp = NearFullStorage.perform_operations_on_pre_written_data(
                        s3userinfo=self.s3userinfo, workload_info=workload_info_list,
                        skipread=False, validate=True, skipcleanup=True)
                    assert_utils.assert_true(resp[0], resp[1])

                    self.log.info("Delete %s percent of the written data", delete_percent_per_iter)
                    resp = NearFullStorage.delete_workload(workload_info_list, self.s3userinfo,
                                                           delete_percent_per_iter)
                    assert_utils.assert_true(resp[0], resp[1])
                    for each in resp[1]:
                        avail_buckets.append(each)
                else:
                    self.log.warning("No buckets available to perform read,validate and"
                                     " delete operations %s", workload_info_list)

            else:
                self.log.info("Write percentage(%s) exceeding the max cluster capacity(%s)",
                              write_per, max_percentage)
                self.log.info("Deleting all the written data.")
                resp = NearFullStorage.delete_workload(workload_info_list, self.s3userinfo, 100)
                assert_utils.assert_true(resp[0], resp[1])
                for each in workload_info_list:
                    avail_buckets.append(each['bucket'])
                self.log.info("Deletion completed.")

        self.test_completed = True
        self.log.info(
            "ENDED: Test for Perform %s percent Writes of user data capacity (Healthy mode) "
            "and perform Object CRUD(%s write,Read,%s delete) operation(degraded mode)",
            write_percent_per_iter, write_percent_per_iter, delete_percent_per_iter)
