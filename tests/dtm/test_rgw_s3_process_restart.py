#!/usr/bin/python # pylint: disable=too-many-lines
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
Test suite for testing RGW Process Restart with DTM enabled.
"""
import logging
import multiprocessing
import os
import secrets
import threading
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import configmanager
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import DTM_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from conftest import LOG_DIR
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


# pylint: disable=too-many-instance-attributes
class TestRGWProcessRestart:
    """Test Class for RGW Process Restart."""

    @classmethod
    def setup_class(cls):
        """Setup class."""

        cls.log = logging.getLogger(__name__)
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.master_node_list = []
        cls.worker_node_list = []
        for node in CMN_CFG['nodes']:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            if node["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.setup_type = CMN_CFG["setup_type"]
        cls.test_completed = False
        cls.health_obj = Health(cls.master_node_list[0].hostname,
                                cls.master_node_list[0].username,
                                cls.master_node_list[0].password)
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/test_dtm_config.yaml")
        cls.rgw_process = 'radosgw'
        cls.log.info("Setup S3bench")
        resp = s3bench.setup_s3bench()
        assert_utils.assert_true(resp)
        cls.ha_obj = HAK8s()
        cls.rest_obj = S3AccountOperations()
        cls.setup_type = CMN_CFG["setup_type"]
        cls.system_random = secrets.SystemRandom()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "DTMTestData")

    def setup_method(self):
        """Setup Method"""
        self.log.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Cluster status is online.")
        self.random_time = int(perf_counter_ns())
        self.s3acc_name = f"dps_s3acc_{self.random_time}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"dps-bkt-{self.random_time}"
        self.object_name = f"dps-obj-{self.random_time}"
        self.deploy = False
        self.iam_user = dict()
        self.log.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        self.access_key = resp[1]["access_key"]
        self.secret_key = resp[1]["secret_key"]
        self.iam_user = {'s3_acc': {'accesskey': self.access_key, 'secretkey': self.secret_key,
                                    'user_name': self.s3acc_name}}
        self.s3_test_obj = S3TestLib(access_key=self.access_key, secret_key=self.secret_key,
                                     endpoint_url=S3_CFG["s3_url"])
        self.dtm_obj = DTMRecoveryTestLib(access_key=self.access_key, secret_key=self.secret_key)
        self.log.info("Created IAM user with name %s", self.s3acc_name)
        if not os.path.exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)

    def teardown_method(self):
        """Teardown class method."""
        if not self.test_completed:
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(
                local_dir_path=path, scripts_path=const.K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)
        if self.iam_user:
            self.log.info("Cleanup: Cleaning created IAM users and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.iam_user)
            assert_utils.assert_true(resp[0], resp[1])
        if os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42244")
    def test_read_during_rgw_svc_restart(self):
        """Verify READs during rgw_s3 service restart using pkill."""
        self.log.info("STARTED: Verify READs during rgw_s3 service restart using pkill")
        log_file_prefix = 'test-42244'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform write operation for background read")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]
        self.log.info("Step 2: Perform Read Operations on the data written in step 1 in background")
        args = {'workload_info': workload_info, 'queue': que, 'skipread': False, 'validate': True,
                'skipcleanup': True, 'retry': DTM_CFG["io_retry_count"]}
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops, kwargs=args)
        proc_read_op.start()

        self.log.info("Step 3: Perform rgw_s3 Process Restart During Read Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for READ operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 5: Perform Read operations after rgw_s3 process restart")
        args = {'workload_info': workload_info, 'queue': que, 'skipread': False, 'validate': True,
                'skipcleanup': True}
        self.dtm_obj.perform_ops(**args)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify READs during rgw_s3 restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42245")
    def test_write_during_rgw_svc_restart(self):
        """Verify WRITEs during rgw_s3 service restart using pkill."""
        self.log.info("STARTED: Verify WRITEs during rgw_s3 service restart using pkill")
        log_file_prefix = 'test-42245'

        que = multiprocessing.Queue()

        self.log.info("Step 1: Start WRITE operation in background")

        args = {'bucket_prefix': self.bucket_name, 'object_prefix': self.object_name,
                'no_of_clients': self.test_cfg['clients'],
                'no_of_samples': self.test_cfg['samples'], 'log_file_prefix': log_file_prefix,
                'queue': que, 'retry': DTM_CFG["io_retry_count"]}
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                kwargs=args)
        proc_write_op.start()

        self.log.info("Step 2: Perform rgw_s3 Process Restart During WRITE Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 2: Wait for WRITE Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 3: Perform READ Operation on data written in Step 1")
        self.dtm_obj.perform_ops(workload_info, que, False, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True

        self.log.info("ENDED: Verify WRITEs during rgw_s3 restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42246")
    def test_delete_during_rgw_svc_restart(self):
        """Verify DELETEs during rgw_s3 service restart using pkill."""
        self.log.info("STARTED: Verify DELETEs during rgw_s3 service restart using pkill")
        test_prefix = 'test-42246'
        wr_output = Queue()
        test_cfg = DTM_CFG["test_42246"]

        event = threading.Event()  # Event to be used to send intimation of rgw_s3 process restart

        self.log.info("Step 1: Perform WRITEs-READs-Validate Operations")
        self.dtm_obj.perform_write_op(bucket_prefix=f"bucket-{test_prefix}",
                                      object_prefix=f"object-{test_prefix}",
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      log_file_prefix=test_prefix, queue=wr_output,
                                      loop=test_cfg['num_loop'])
        resp = wr_output.get()
        assert_utils.assert_true(resp[0], resp[1])

        buckets = self.s3_test_obj.bucket_list()[1]
        self.log.info("Step 1: Successfully created %s buckets & performed WRITEs-READs-Validate"
                      " with variable size objects.", len(buckets))

        output = Queue()
        self.log.info("Step 2: Start Continuous DELETEs of buckets %s in background", buckets)
        args = {'test_prefix': test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': buckets, 'output': output}

        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, self.s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        self.log.info("Step 2: Successfully started DELETEs in background")

        event.set()
        self.log.info("Step 3: Perform rgw_s3 Process Restart During DELETE Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        event.clear()
        self.log.info("Step 3: Successfully Performed Single rgw_s3 Process Restart During Delete "
                      "Operations")

        self.log.info("Step 4: Verify status for In-flight DELETEs while service was restarting")
        thread.join()
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  f"Bucket deletion failed, before/after restart:{fail_del_bkt} "
                                  f"and during restart: {event_del_bkt}")

        self.log.info("Step 4: Successfully verified status for In-flight DELETEs while service "
                      "was restarting")

        self.log.info("ENDED: Verify DELETEs during rgw_s3 service restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42253")
    def test_copy_object_after_rgw_restart(self):
        """Verify copy object after rgw restart using pkill."""
        self.log.info("STARTED: Verify copy object after rgw restart using pkill")
        object_name = 'object-test-42253'
        bucket_list = list()
        self.log.info("Step 1: Start write Operations :")
        for i in range(0, 2):
            bucket_name = f"bucket-test-42253-{i}"
            resp = self.s3_test_obj.create_bucket(bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            bucket_list.append(bucket_name)
        for size in self.test_cfg["size_list"]:
            file_name = "{}{}".format("dtm-test-42253", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            system_utils.create_file(file_path, size)
            resp = self.s3_test_obj.put_object(bucket_list[0], f"{object_name}_{size}", file_path)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Single rgw Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False)
        assert_utils.assert_true(resp, "Failure observed during process restart")
        self.log.info("Step 3: Perform Copy Object to bucket-2, download and verify on copied "
                      "Objects")
        for size in self.test_cfg["size_list"]:
            resp = self.s3_test_obj.copy_object(source_bucket=bucket_list[0],
                                                source_object=f"{object_name}_{size}",
                                                dest_bucket=bucket_list[1],
                                                dest_object=f"{object_name}_{size}")
            assert_utils.assert_true(resp[0], resp[1])
            file_name_copy = "{}{}".format("dtm-test-42253-copy", size)
            file_path_copy = os.path.join(self.test_dir_path, file_name_copy)
            resp = self.s3_test_obj.object_download(bucket_name=bucket_list[1],
                                                    obj_name=f"{object_name}_{size}",
                                                    file_path=file_path_copy)
            assert_utils.assert_true(resp[0], resp[1])
            file_name = "{}{}".format("dtm-test-42253", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            resp = system_utils.validate_checksum(file_path_1=file_path, file_path_2=file_path_copy)
            assert_utils.assert_true(resp, "Checksum validation Failed.")
        self.test_completed = True
        self.log.info("ENDED: Verify copy object after rgw restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42254")
    def test_copy_object_during_rgw_restart(self):
        """Verify copy object during rgw restart using pkill."""
        self.log.info("STARTED: Verify copy object during rgw restart using pkill")
        object_name = 'object-test-42254'
        workload = dict()
        obj_list = list()
        bucket_list = list()
        que = multiprocessing.Queue()

        self.log.info("Step 1: Start write Operations :")
        for i in range(0, 2):
            bucket_name = f"bucket-test-42254-{i}"
            resp = self.s3_test_obj.create_bucket(bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            bucket_list.append(bucket_name)
        for size in self.test_cfg["size_list"]:
            file_name = "{}{}".format("dtm-test-42254-", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            system_utils.create_file(file_path, size)
            resp = self.s3_test_obj.put_object(bucket_list[0], f"{object_name}_{size}",
                                               file_path)
            obj_list.append(f"{object_name}_{size}")
            assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 2: Perform Copy object to bucket-2 in background")
        workload["source_bucket"] = bucket_list[0]
        workload["dest_bucket"] = bucket_list[1]
        workload["obj_list"] = obj_list
        proc_cp_op = multiprocessing.Process(target=self.dtm_obj.perform_copy_objects,
                                             args=(workload, que))
        proc_cp_op.start()

        self.log.info("Step 3: Perform Single rgw_s3 Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False)
        assert_utils.assert_true(resp, "Failure observed during process restart")

        self.log.info("Step 4: Wait for copy object to finish")
        if proc_cp_op.is_alive():
            proc_cp_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 5: Perform Download and verify on copied Objects")
        for size in self.test_cfg["size_list"]:
            file_name_copy = "{}{}".format("dtm-test-42254-copy", size)
            file_path_copy = os.path.join(self.test_dir_path, file_name_copy)
            resp = self.s3_test_obj.object_download(bucket_name=bucket_list[1],
                                                    obj_name=f"{object_name}_{size}",
                                                    file_path=file_path_copy)
            assert_utils.assert_true(resp[0], resp[1])
            file_name = "{}{}".format("dtm-test-42254-", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            resp = system_utils.validate_checksum(file_path_1=file_path, file_path_2=file_path_copy)
            assert_utils.assert_true(resp, "Checksum validation Failed.")
        self.test_completed = True
        self.log.info("ENDED: Verify copy object during rgw restart using pkill.")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42247")
    def test_continuous_read_during_rgw_s3_restart(self):
        """Verify continuous READ during rgw_s3 restart using pkill."""
        self.log.info("STARTED: Verify continuous READ during rgw_s3 restart using pkill")
        log_file_prefix = 'test-42247'
        que = multiprocessing.Queue()
        test_cfg = DTM_CFG["test_42247"]

        self.log.info("Step 1: Start write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=test_cfg['nclients'],
                                      no_of_samples=test_cfg['nsamples'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]
        self.log.info("Step 2: Start READ Operations in loop in background:")
        args = {'workload_info': workload_info, 'queue': que, 'skipread': False, 'validate': True,
                'skipcleanup': True, 'retry': DTM_CFG["io_retry_count"],
                'loop': self.test_cfg['loop_count']}
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops, kwargs=args)
        proc_read_op.start()

        self.log.info("Step 3: Perform rgw_s3 Process Restart for %s times During Read "
                      "Operations", DTM_CFG["rgw_restart_cnt"])
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False,
                                            restart_cnt=DTM_CFG["rgw_restart_cnt"])
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for READ Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 5: Perform READ operations after rgw_s3 process restarts")
        args = {'workload_info': workload_info, 'queue': que, 'skipread': False, 'validate': True,
                'skipcleanup': True}
        self.dtm_obj.perform_ops(**args)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify continuous READ during rgw_s3 restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42248")
    def test_continuous_write_during_rgw_s3_restart(self):
        """Verify continuous WRITEs during rgw_s3 service restart using pkill."""
        self.log.info("STARTED: Verify continuous WRITEs during rgw_s3 service restart using pkill")
        log_file_prefix = 'test-42248'
        que = multiprocessing.Queue()
        test_cfg = DTM_CFG["test_42247"]

        self.log.info("Step 1: Start WRITE operation in background")
        args = {'bucket_prefix': self.bucket_name, 'object_prefix': self.object_name,
                'no_of_clients': test_cfg['clients'], 'no_of_samples': test_cfg['samples'],
                'log_file_prefix': log_file_prefix, 'queue': que,
                'retry': DTM_CFG["io_retry_count"], 'loop': self.test_cfg['loop_count']}
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op, kwargs=args)
        proc_write_op.start()

        self.log.info("Step 2: Perform rgw_s3 Process Restart for %s times During Write "
                      "Operations", DTM_CFG["rgw_restart_cnt"])
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False,
                                            restart_cnt=DTM_CFG["rgw_restart_cnt"])
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 3: Wait for WRITE Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 4: Perform READ Operation on data written in Step 1")
        self.dtm_obj.perform_ops(workload_info, que, False, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True

        self.log.info("ENDED: Verify continuous WRITEs during rgw_s3 restart using pkill")
