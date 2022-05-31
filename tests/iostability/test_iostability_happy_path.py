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
"""Test Suite for IO stability Happy Path workloads."""
import datetime
import logging
import os
import time
from datetime import datetime
from datetime import timedelta

import pytest

from commons import configmanager, cortxlogging
from commons.constants import K8S_SCRIPTS_PATH
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import support_bundle_utils, assert_utils
from config import CMN_CFG
from conftest import LOG_DIR
from libs.dtm.ProcPathStasCollection import EnableProcPathStatsCollection
from libs.durability.near_full_data_storage import NearFullStorage
from libs.iostability.iostability_lib import IOStabilityLib, send_mail_notification
from libs.s3 import ACCESS_KEY
from libs.s3 import SECRET_KEY


class TestIOWorkload:
    """Test Class for IO workloads."""

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
    @pytest.mark.tags("TEST-40039")
    def test_bucket_object_crud_s3bench(self):
        """Perform Bucket and  Object CRUD operations in loop using S3bench for n days."""
        self.log.info("STARTED: Test for Bucket and  Object CRUD operations in loop using "
                      "S3bench for %s days", self.duration_in_days)
        test_case_name = cortxlogging.get_frame()
        self.mail_notify = send_mail_notification(self.sender_mail_id, self.receiver_mail_id,
                                                  test_case_name, self.health_obj_list[0])
        workload_distribution = self.test_cfg['workloads_distribution']
        total_obj = 10000
        total_clients = len(self.worker_node_list) * self.clients
        if self.setup_type == 'HW':
            total_clients = len(self.worker_node_list) * self.test_cfg['sessions_per_node_hw']

        self.iolib.execute_workload_distribution(distribution=workload_distribution,
                                                 clients=total_clients,
                                                 total_obj=total_obj,
                                                 duration_in_days=self.duration_in_days,
                                                 log_file_prefix='test-40039')
        self.test_completed = True
        self.log.info(
            "ENDED: Test for Bucket and  Object CRUD operations in loop using S3bench for %s days",
            self.duration_in_days)

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40041")
    def test_disk_near_full_s3bench(self):
        """Perform disk storage near full once and read in loop for n days."""
        self.log.info("STARTED: Perform disk storage near full once and read in loop for %s days.",
                      self.duration_in_days)
        test_case_name = cortxlogging.get_frame()
        self.mail_notify = send_mail_notification(self.sender_mail_id, self.receiver_mail_id,
                                                  test_case_name, self.health_obj_list[0])

        bucket_prefix = "testbkt-40041"
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
        self.log.debug("Write operation data: %s", ret)

        self.log.info("Step 3: Performing read operations.")
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

        self.log.info("Step 4: Performing delete operations.")
        del_ret = NearFullStorage.perform_operations_on_pre_written_data(
            s3userinfo=self.s3userinfo,
            workload_info=ret[1],
            skipread=True,
            validate=False,
            skipcleanup=False)
        assert_utils.assert_true(del_ret[0], del_ret[1])
        self.test_completed = True
        self.log.info("ENDED: Perform disk storage near full once and read in loop for %s days",
                      self.duration_in_days)

    @pytest.mark.lc
    @pytest.mark.io_stability
    @pytest.mark.tags("TEST-40042")
    def test_iteration_write_read_partial_delete(self):
        """Perform iterations of 30% writes of user capacity ,
        reads entire data, and delete 20% of the data."""
        write_percent_per_iter = self.test_cfg['write_percent_per_iter']
        delete_percent_per_iter = self.test_cfg['delete_percent_per_iter']

        self.log.info(
            "STARTED: Test for performing %s percent writes, read written data and deleting "
            "%s percent of written data.", write_percent_per_iter, delete_percent_per_iter)

        test_case_name = cortxlogging.get_frame()
        self.mail_notify = send_mail_notification(self.sender_mail_id, self.receiver_mail_id,
                                                  test_case_name, self.health_obj_list[0])

        max_cluster_capacity_percent = self.test_cfg['nearfull_storage_percentage']
        clients = len(self.worker_node_list) * self.clients
        bucket_prefix = "test-40042-bkt"

        self.log.info("Step: Perform %s percent writes and Read the written data and %s percent"
                      " deletes. Delete all the written data once %s is reached",
                      write_percent_per_iter, delete_percent_per_iter, max_cluster_capacity_percent)
        workload_info_list = []
        end_time = datetime.now() + timedelta(days=self.duration_in_days)
        write_per = 0
        loop = 1
        while datetime.now() < end_time:
            self.log.info("LOOP COUNT : %s", loop)
            loop += 1
            write_per = write_per + write_percent_per_iter
            self.log.info("Write percentage per iteration : %s", write_percent_per_iter)
            self.log.info("Write percentage to be written in this iteration: %s", write_per)
            if write_per < max_cluster_capacity_percent:
                # Write data to fill cluster upto "write_per" percent
                resp = NearFullStorage.perform_write_to_fill_system_percent(
                    self.master_node_list[0], write_per, self.s3userinfo, bucket_prefix, clients)
                assert_utils.assert_true(resp[0], resp[1])
                if resp[1] is not None:
                    workload_info_list.extend(resp[1])

                if len(workload_info_list) > 0:
                    # Read and validate all written data
                    self.log.info("Read/Validate all the written data of the cluster")
                    resp = NearFullStorage.perform_operations_on_pre_written_data(
                        self.s3userinfo, workload_info_list, False, True, True)
                    assert_utils.assert_true(resp[0], resp[1])

                    # Delete "delete_percent_per_iter" data of all the written data
                    self.log.info("Delete %s percent of the written data", delete_percent_per_iter)
                    resp = NearFullStorage.delete_workload(workload_info_list, self.s3userinfo,
                                                           delete_percent_per_iter)
                    assert_utils.assert_true(resp[0], resp[1])

                else:
                    self.log.warning("No buckets available to perform read,validate,delete"
                                     " operations %s", workload_info_list)
            else:
                self.log.info("Write percentage(%s) exceeding the max cluster capacity(%s)",
                              write_per, max_cluster_capacity_percent)
                self.log.info("Deleting all the written data.")
                resp = NearFullStorage.delete_workload(workload_info_list, self.s3userinfo, 100)
                assert_utils.assert_true(resp[0], resp[1])
                self.log.info("Deletion completed.")

        self.test_completed = True
        self.log.info(
            "ENDED: Test for performing %s percent writes, read written data and deleting "
            "%s percent of written data.", write_percent_per_iter, delete_percent_per_iter)
