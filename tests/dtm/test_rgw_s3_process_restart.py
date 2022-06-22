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
import time
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
                                            process=self.rgw_process, check_proc_state=True)
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
                                            process=self.rgw_process, check_proc_state=True)
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
                                      loop=test_cfg['num_loop'], skip_read=False, validate=True)
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
                                            process=self.rgw_process, check_proc_state=True)
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
            file_name = f"dtm-test-42253{size}"
            file_path = os.path.join(self.test_dir_path, file_name)
            system_utils.create_file(file_path, size)
            resp = self.s3_test_obj.put_object(bucket_list[0], f"{object_name}_{size}", file_path)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Single rgw Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart")
        self.log.info("Step 3: Perform Copy Object to bucket-2, download and verify on copied "
                      "Objects")
        for size in self.test_cfg["size_list"]:
            resp = self.s3_test_obj.copy_object(source_bucket=bucket_list[0],
                                                source_object=f"{object_name}_{size}",
                                                dest_bucket=bucket_list[1],
                                                dest_object=f"{object_name}_{size}")
            assert_utils.assert_true(resp[0], resp[1])
            file_name_copy = f"dtm-test-42253-copy{size}"
            file_path_copy = os.path.join(self.test_dir_path, file_name_copy)
            resp = self.s3_test_obj.object_download(bucket_name=bucket_list[1],
                                                    obj_name=f"{object_name}_{size}",
                                                    file_path=file_path_copy)
            assert_utils.assert_true(resp[0], resp[1])
            file_name = f"dtm-test-42253{size}"
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
            file_name = f"dtm-test-42254-{size}"
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
                                            process=self.rgw_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart")

        self.log.info("Step 4: Wait for copy object to finish")
        if proc_cp_op.is_alive():
            proc_cp_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 5: Perform Download and verify on copied Objects")
        for size in self.test_cfg["size_list"]:
            file_name_copy = f"dtm-test-42254-copy{size}"
            file_path_copy = os.path.join(self.test_dir_path, file_name_copy)
            resp = self.s3_test_obj.object_download(bucket_name=bucket_list[1],
                                                    obj_name=f"{object_name}_{size}",
                                                    file_path=file_path_copy)
            assert_utils.assert_true(resp[0], resp[1])
            file_name = f"dtm-test-42254-{size}"
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
        self.log.info("Step 2: Start READ-Validate Operations in loop in background:")
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
                                            process=self.rgw_process, check_proc_state=True,
                                            restart_cnt=DTM_CFG["rgw_restart_cnt"])
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for READ Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 5: Perform READ-Validate operations after rgw_s3 process restarts")
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
        """Verify continuous WRITEs during rgw_s3 service restart using pkill"""
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
                                            process=self.rgw_process, check_proc_state=True,
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

    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=cell-var-from-loop
    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42249")
    def test_cont_delete_during_rgw_svc_restart(self):
        """Verify continuous DELETEs during rgw_s3 service restart using pkill."""
        self.log.info("STARTED: Verify continuous DELETEs during rgw_s3 service restart using "
                      "pkill")
        test_prefix = 'test-42249'
        wr_output = Queue()
        test_cfg = DTM_CFG["test_42246"]
        del_output = Queue()
        rd_output = Queue()
        event = threading.Event()  # Event to be used to send intimation of rgw_s3 process restart

        self.log.info("Step 1: Perform WRITEs-READs-Validate Operations")
        self.dtm_obj.perform_write_op(bucket_prefix=f"bucket-{test_prefix}",
                                      object_prefix=f"object-{test_prefix}",
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      log_file_prefix=test_prefix, queue=wr_output,
                                      loop=test_cfg['num_loop'], skip_read=False, validate=True)
        resp = wr_output.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        buckets = self.s3_test_obj.bucket_list()[1]
        self.log.info("Step 1: Successfully created %s buckets & performed WRITEs-READs-Validate"
                      " with variable size objects.", len(buckets))

        for i_i in range(DTM_CFG["rgw_restart_cnt"]):
            self.log.info("Loop: %s", i_i)
            bkts_to_del = self.system_random.sample(buckets, 50)

            self.log.info("Step 2: Start Continuous DELETEs of buckets %s in background",
                          bkts_to_del)
            args = {'test_prefix': test_prefix, 'test_dir_path': self.test_dir_path,
                    'skipput': True, 'skipget': True, 'bkt_list': bkts_to_del, 'output': del_output}
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
                                                process=self.rgw_process, check_proc_state=True)
            assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
            event.clear()
            self.log.info("Step 3: Successfully Performed Single rgw_s3 Process Restart During "
                          "Delete Operations")

            self.log.info("Step 4: Verify status for In-flight DELETEs while service was "
                          "restarting")
            thread.join()
            del_resp = tuple()
            while len(del_resp) != 2:
                del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            event_del_bkt = del_resp[0]
            fail_del_bkt = del_resp[1]
            assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                      f"Bucket deletion failed, before/after restart:{fail_del_bkt}"
                                      f" and during restart: {event_del_bkt}")

            self.log.info("Step 4: Successfully verified status for In-flight DELETEs while service"
                          " was restarting")

            workload_info = list(filter(lambda a: a['bucket'] not in bkts_to_del, workload_info))
            buckets = list(set(buckets) - set(bkts_to_del))
            self.log.info("Step 5: Perform READ Operation on remaining buckets %s", buckets)
            self.dtm_obj.perform_ops(workload_info, rd_output, False, True, True)
            resp = rd_output.get()
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step 5: Successfully performed READ Operation.")

        self.test_completed = True
        self.log.info("ENDED: Verify continuous DELETEs during rgw_s3 service restart using "
                      "pkill")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42255")
    def test_ios_during_multi_rc_rgw_restarts(self):
        """Verify IOs during multiple RC pod rgw_s3 process restarts using pkill."""
        self.log.info("STARTED: Verify IOs during multiple RC pod rgw_s3 process restarts using "
                      "pkill")
        test_cfg = DTM_CFG['test_42255']
        output = Queue()
        test_prefix = 'test-42255'

        self.log.info("Step 1: Perform WRITEs/READs-Verify/DELETEs with variable object sizes in "
                      "background")
        args = {'bucket_prefix': self.bucket_name, 'object_prefix': self.object_name,
                'no_of_clients': test_cfg['clients'], 'no_of_samples': test_cfg['samples'],
                'log_file_prefix': test_prefix, 'queue': output, 'loop': test_cfg['num_loop'],
                'retry': DTM_CFG["io_retry_count"], 'skip_read': False, 'skip_cleanup': False,
                'validate': True}
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                kwargs=args)
        proc_write_op.start()
        self.log.info("Step 1: Started WRITEs/READs-Verify/DELETEs with variable object sizes "
                      "in background")
        self.log.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        self.log.info("Step 2: Perform restart of rgw process %s times during IOs, on pod hosted "
                      "on RC node and check hctl status", DTM_CFG["rgw_restart_cnt"])
        self.log.info("Get RC node name")
        rc_node = self.ha_obj.get_rc_node(self.master_node_list[0])
        rc_info = self.master_node_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        rc_node_name = list(rc_info.values())[0]
        self.log.info("RC Node is running on %s node", rc_node_name)
        self.log.info("Get the server pod running on %s node", rc_node_name)
        server_pods = self.master_node_list[0].get_pods_node_fqdn(const.SERVER_POD_NAME_PREFIX)
        rc_serverpod = None
        for pod_name, node in server_pods.items():
            if node == rc_node_name:
                rc_serverpod = pod_name
                break
        self.log.info("RC node %s has server pod: %s ", rc_node_name, rc_serverpod)
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=rc_serverpod,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=True,
                                            restart_cnt=DTM_CFG["rgw_restart_cnt"])
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 2: Successfully performed restart of rgw process %s times during IOs, "
                      "on pod hosted on RC node and checked hctl status",
                      DTM_CFG["rgw_restart_cnt"])
        if proc_write_op.is_alive():
            proc_write_op.join()
        self.log.info("Thread has joined.")

        self.log.info("Step 3: Verify responses from background process")
        resp = output.get()
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Successfully completed WRITEs/READs-Verify/DELETEs with variable "
                      "object sizes in background")
        self.test_completed = True
        self.log.info("ENDED: Verify IOs during RC pod rgw_s3 restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42250")
    def test_write_read_delete_during_rgw_restart(self):
        """Verify WRITE, READ, DELETE during rgw restart using pkill."""
        self.log.info("STARTED: Verify WRITE, READ, DELETE during rgw restart using pkill")
        log_file_prefix = 'test-42250'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Start Write Operations for parallel reads "
                      "and parallel deletes during rgw restart:")
        write_proc = []
        w_args = {'bucket_prefix': self.bucket_name, 'object_prefix': self.object_name,
                  'no_of_clients': self.test_cfg['clients'],
                  'no_of_samples': self.test_cfg['samples'],
                  'log_file_prefix': log_file_prefix, 'queue': que}

        for _ in range(0, 2):
            proc = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                           kwargs=w_args)
            proc.start()
            write_proc.append(proc)

        self.log.info("Step 2: Wait for Write Operation to complete.")
        workload_info_list = []
        for each in write_proc:
            if each.is_alive():
                each.join()
            resp = que.get()
            assert_utils.assert_true(resp[0], resp[1])
            workload_info_list.append(resp[1])

        self.log.info("Step 3: Perform Write,Read,Delete Parallely during rgw restart")
        parallel_proc = []

        self.log.info("Step 3a: Start Write in new process")
        w_args.update({'retry': DTM_CFG["io_retry_count"]})
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op, kwargs=w_args)
        proc_write_op.start()
        parallel_proc.append(proc_write_op)

        self.log.info("Step 3b: Start Read in new process")
        # Reads, validate and delete
        r_args = {'workload_info': workload_info_list[0], 'queue': que, 'skipread': False,
                  'validate': True, 'skipcleanup': True, 'retry': DTM_CFG["io_retry_count"]}
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops, kwargs=r_args)
        proc_read_op.start()
        parallel_proc.append(proc_read_op)

        self.log.info("Step 3c: Start Deletes in new process")
        # delete
        d_args = {'workload_info': workload_info_list[0], 'queue': que, 'skipread': True,
                  'validate': False, 'skipcleanup': False, 'retry': DTM_CFG["io_retry_count"]}
        proc_delete_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                                 kwargs=d_args)
        proc_delete_op.start()
        parallel_proc.append(proc_delete_op)

        self.log.info(
            "Step 4: Perform Single rgw Process Restart During Write/Read/Delete Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process,
                                            check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 5: Check if all the operations were successful")
        write_during_restart = None
        for each in parallel_proc:
            if each.is_alive():
                each.join()
            resp = que.get()
            assert_utils.assert_true(resp[0], resp[1])
            if isinstance(resp[1], list):
                write_during_restart = resp[1]

        if not write_during_restart:
            assert_utils.assert_true(False, 'No workload returned for writes performed during rgw '
                                            'restart')

        self.log.info("Step 6: Perform read, delete operation on object written during rgw restart "
                      "during step 3")
        self.dtm_obj.perform_ops(write_during_restart, que, False, True, False)

        self.test_completed = True
        self.log.info("ENDED: Verify WRITE, READ, DELETE during rgw restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42251")
    def test_overwrite_same_object_during_rgw_restart(self):
        """Overwrite same object during rgw restart."""
        self.log.info("STARTED: Overwrite same object during rgw restart.")
        overwrite_cnt = self.test_cfg['test_42251']['overwrite_cnt']
        max_object_size = self.test_cfg['test_42251']['max_object_size']
        que = multiprocessing.Queue()

        self.log.info("Step 1: Create bucket : %s", self.bucket_name)
        self.s3_test_obj.create_bucket(self.bucket_name)

        self.log.info("Step 2 : Start continuous overwrite on same object")
        proc_overwrite_op = multiprocessing.Process(target=self.dtm_obj.perform_object_overwrite,
                                                    args=(self.bucket_name, self.object_name,
                                                          overwrite_cnt,
                                                          max_object_size, que))
        proc_overwrite_op.start()

        self.log.info("Step 3 : Perform Single rgw Process Restart during overwrite ")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process,
                                            check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for Overwrite Operation to complete.")
        if proc_overwrite_op.is_alive():
            proc_overwrite_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        self.test_completed = True
        self.log.info("ENDED: Overwrite same object during rgw restart.")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42252")
    def test_io_operations_before_after_rgw_restart(self):
        """Verify IO operations work after rgw restart using pkill"""
        self.log.info("STARTED: Verify IO operations work after rgw restart using pkill")
        test_cfg = DTM_CFG['test_42252']
        test_prefix = 'test-42252-before-restart'

        self.log.info("Step 1: Perform WRITEs/READs-Verify/DELETEs with variable sizes objects.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix,
                                                    nclients=test_cfg['nclients'],
                                                    nsamples=test_cfg['nsamples'])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Successfully performed WRITEs/READs-Verify/DELETEs with variable "
                      "sizes objects.")

        self.log.info("Step 2: Perform Single rgw Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 2: rgw restarted and recovered successfully")

        test_prefix = 'test-42252-after-restart'
        self.log.info("Step 3: Perform WRITEs/READs-Verify/DELETEs with variable sizes objects.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix,
                                                    nclients=test_cfg['nclients'],
                                                    nsamples=test_cfg['nsamples'])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Successfully performed WRITEs/READs-Verify/DELETEs with variable "
                      "sizes objects.")

        self.log.info("ENDED: Verify IO operations work after rgw restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42256")
    def test_bkt_creation_ios_after_rgw_restart(self):
        """Verify bucket creation and IOs after rgw restart using pkill."""
        self.log.info("STARTED: Verify bucket creation and IOs after rgw restart using pkill")
        test_cfg = DTM_CFG['test_42256']
        test_prefix = 'test-42256'

        self.log.info("Step 1: Perform Single rgw Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 1: rgw restarted and recovered successfully")

        self.log.info("Step 2: Create buckets for IOs")
        workloads = HA_CFG["s3_bench_workloads"]
        if self.setup_type == "HW":
            workloads.extend(HA_CFG["s3_bench_large_workloads"])
        for workload in workloads:
            self.s3_test_obj.create_bucket(f"bucket-{workload.lower()}-{test_prefix}")
        self.log.info("Step 2: Created buckets for IOs")

        self.log.info("Step 3: Perform WRITEs/READs-Verify/DELETEs with variable sizes objects.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix,
                                                    nclients=test_cfg['nclients'],
                                                    nsamples=test_cfg['nsamples'])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Successfully performed WRITEs/READs-Verify/DELETEs with variable "
                      "sizes objects.")

        self.log.info("ENDED: Verify bucket creation and IOs after rgw restart using pkill")
