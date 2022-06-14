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
Test suite for testing Single Process Restart with DTM enabled.
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
from commons.utils.system_utils import validate_checksum
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
class TestSingleProcessRestart:
    """Test Class for Single Process Restart."""

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
        cls.m0d_process = 'm0d'
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
            self.log.info("Cleanup: Deleting objects created during test.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.iam_user, True)
            assert_utils.assert_true(resp[0], resp[1])
        if os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        # TODO : Redeploy setup after test completion.

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41204")
    def test_read_during_m0d_restart(self):
        """Verify READ during m0d restart using pkill."""
        self.log.info("STARTED: Verify READ during m0d restart using pkill")
        log_file_prefix = 'test-41204'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix,
                                      queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 2: Perform Read Operations on the data written in step 1 in background")
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                               args=(workload_info, que, False, True, True))
        proc_read_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Read Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for Read Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify READ during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41219")
    def test_write_during_m0d_restart(self):
        """Verify WRITE during m0d restart using pkill."""
        self.log.info("STARTED: Verify WRITE during m0d restart using pkill")
        log_file_prefix = 'test-41219'

        que = multiprocessing.Queue()

        self.log.info("Step 1: Create bucket for IO operations")
        self.s3_test_obj.create_bucket(self.bucket_name)

        self.log.info("Step 2: Start write Operations in background:")
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                args=(self.bucket_name, self.object_name,
                                                      self.test_cfg['clients'],
                                                      self.test_cfg['samples'], log_file_prefix,
                                                      que, self.test_cfg['size'], 1,
                                                      [self.bucket_name]))
        proc_write_op.start()

        self.log.info("Step 2 : Perform Single m0d Process Restart During Write Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 3: Wait for Write Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 4: Perform Read Operations on data written in Step 1:")
        self.dtm_obj.perform_ops(workload_info, que, False, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify write during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41223")
    def test_delete_during_m0d_restart(self):
        """Verify DELETE during m0d restart."""
        self.log.info("STARTED: Verify DELETE during m0d restart.")
        log_file_prefix = 'test-41223'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 2: Perform Delete Operations in background:")
        proc_del_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                              args=(workload_info, que, True, False, False))
        proc_del_op.start()

        self.log.info("Step 3: Perform Single m0d Process Restart During Delete Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for Delete Operation to complete.")
        if proc_del_op.is_alive():
            proc_del_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify Delete during m0d restart using pkill -9")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41234")
    def test_ios_during_rc_m0d_restart(self):
        """Verify IOs during RC pod m0d restart using pkill."""
        self.log.info("STARTED: Verify IOs during RC pod m0d restart using pkill")
        test_cfg = DTM_CFG['test_41234']

        self.log.info("Step 1: Perform WRITEs/READs-Verify with variable object sizes in "
                      "background")
        event = threading.Event()  # Event to be used to send intimation of m0d restart
        output = Queue()

        test_prefix = 'test-41234'
        self.log.info("Create buckets for IOs")

        workloads = HA_CFG["s3_bench_workloads"]
        if self.setup_type == "HW":
            workloads.extend(HA_CFG["s3_bench_large_workloads"])
        for workload in workloads:
            self.s3_test_obj.create_bucket(f"bucket-{workload.lower()}-{test_prefix}")

        self.log.info("Perform WRITEs/READs-Verify with variable object sizes in background")
        args = {'s3userinfo': self.iam_user, 'log_prefix': test_prefix,
                'nclients': test_cfg['nclients'], 'nsamples': test_cfg['nsamples'],
                'skipcleanup': True, 'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()

        self.log.info("Step 1: Successfully created IAM user and started WRITEs/READs-Verify "
                      "with variable object sizes in background")
        self.log.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        self.log.info("Step 2: Perform single restart of m0d process on pod hosted on RC node and "
                      "check hctl status")
        self.log.info("Get RC node name")
        rc_node = self.ha_obj.get_rc_node(self.master_node_list[0])
        rc_info = self.master_node_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        rc_node_name = list(rc_info.values())[0]
        self.log.info("RC Node is running on %s node", rc_node_name)
        self.log.info("Get the data pod running on %s node", rc_node_name)
        data_pods = self.master_node_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        rc_datapod = None
        for pod_name, node in data_pods.items():
            if node == rc_node_name:
                rc_datapod = pod_name
                break
        self.log.info("RC node %s has data pod: %s ", rc_node_name, rc_datapod)
        event.set()
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=rc_datapod,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 2: Successfully performed single restart of m0d process on pod hosted "
                      "on RC node and checked hctl status is good")
        event.clear()
        thread.join()
        self.log.info("Thread has joined.")
        self.log.info("Step 3: Verify responses from background process")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        self.log.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses["fail_res"])
        self.log.debug("Fail logs list: %s", fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "Failed WRITEs/READs in background before and "
                                                "after m0d restart. Logs which contain failures: "
                                                f"{resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), "Failed WRITEs/READs in background during m0d"
                                                f"restart. Logs which contain failures: {resp[1]}")
        self.log.info("Step 3: Successfully completed WRITEs/READs in background")

        self.log.info("Step 4: Perform READs-Verify on already written data in Step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix, skipwrite=True,
                                                    skipcleanup=True, nclients=test_cfg['nclients'],
                                                    nsamples=test_cfg['nsamples'])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Successfully performed READs-Verify on already written data in "
                      "Step 1")

        self.log.info("ENDED: Verify IOs before and after RC pod m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41235")
    def test_bkt_creation_ios_after_m0d_restart(self):
        """Verify bucket creation and IOs after m0d restart using pkill."""
        self.log.info("STARTED: Verify bucket creation and IOs after m0d restart using pkill")
        test_cfg = DTM_CFG['test_41235']
        test_prefix = 'test-41235'

        self.log.info("Step 1: Perform Single m0d Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 1: m0d restarted and recovered successfully")

        self.log.info("Step 2: Perform WRITEs/READs-Verify/DELETEs with variable sizes objects.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix,
                                                    nclients=test_cfg['nclients'],
                                                    nsamples=test_cfg['nsamples'])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Successfully performed WRITEs/READs-Verify/DELETEs with variable "
                      "sizes objects.")

        self.log.info("ENDED: Verify bucket creation and IOs after m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41225")
    def test_continuous_read_during_m0d_restart(self):
        """Verify continuous READ during m0d restart using pkill."""
        self.log.info("STARTED: Verify continuous READ during m0d restart using pkill")
        log_file_prefix = 'test-41225'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Start write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]
        self.log.info("Step 2: Start READ Operations in loop in background:")
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                               args=(workload_info, que, False, True,
                                                     True, self.test_cfg['loop_count']))
        proc_read_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Read Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for READ Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify continuous READ during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41226")
    def test_continuous_write_during_m0d_restart(self):
        """Verify continuous WRITE during m0d restart using pkill."""
        self.log.info("STARTED: Verify continuous WRITE during m0d restart using pkill")
        log_file_prefix = 'test-41226'
        que = multiprocessing.Queue()
        bucket_list = []

        self.log.info("Step 1: Create %s buckets for write operation during m0d restart",
                      self.test_cfg['loop_count'])
        for each in self.test_cfg['loop_count']:
            bucket = f'{self.bucket_name}-{each}'
            self.s3_test_obj.create_bucket(bucket)
            bucket_list.append(bucket)

        self.log.info("Step 2: Start write Operations in loop in background:")
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                args=(self.bucket_name, self.object_name,
                                                      self.test_cfg['clients'],
                                                      self.test_cfg['samples'],
                                                      log_file_prefix,
                                                      que, self.test_cfg['loop_count'],
                                                      bucket_list))
        proc_write_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Write Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for Write Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 4: Perform Read-Validate on data written in Step 1")
        self.dtm_obj.perform_ops(workload_info, que, False, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True

        self.log.info("ENDED: Verify continuous WRITE during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41228")
    def test_continuous_delete_during_m0d_restart(self):
        """Verify continuous DELETE during m0d restart using pkill."""
        self.log.info("STARTED: Verify continuous DELETE during m0d restart using pkill")
        log_file_prefix = 'test-41228'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Start write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      log_file_prefix=log_file_prefix, queue=que,
                                      loop=self.test_cfg['loop_count'])
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]
        self.log.info("Step 2: Start DELETE Operations in background:")
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                               args=(workload_info, que, True, False, False))
        proc_read_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Delete Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for DELETE Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify continuous DELETE during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41244")
    def test_mpu_m0d_restart(self):
        """Verify multipart upload and download before/after m0d is restarted."""
        self.log.info("STARTED: Verify multipart upload and download before/after m0d is restarted")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts + 1))
        self.system_random.shuffle(part_numbers)
        multipart_obj_path = os.path.join(self.test_dir_path, "test_41244_file")
        download_path = os.path.join(self.test_dir_path, "test_41244_file_download")

        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.iam_user,
                                                         bucket_name=self.bucket_name,
                                                         object_name=self.object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = self.s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        self.log.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        self.log.info("Step 1: Successfully performed multipart upload for size 5GB.")

        self.log.info("Step 2: Download the uploaded object and verify checksum")
        resp = self.s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        self.log.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        self.log.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        self.log.info("Step 2: Successfully downloaded the object and verified the checksum")

        self.log.info("Step 3: Perform Single m0d Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 3: m0d restarted and recovered successfully")

        self.log.info("Step 4: Download the uploaded object after m0d recovery and verify checksum")
        resp = self.s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        self.log.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum1 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum1}")
        self.log.info("Matched checksum: %s, %s", upload_checksum, download_checksum1)
        self.log.info("Step 4: Successfully downloaded the object and verified the checksum after "
                      "m0d recovery")

        self.log.info("ENDED: Verify multipart upload and download before/after m0d is restarted")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41229")
    def test_write_read_delete_during_m0d_restart(self):
        """Verify WRITE, READ, DELETE during m0d restart using pkill."""
        self.log.info("STARTED: Verify WRITE, READ, DELETE during m0d restart using pkill")
        log_file_prefix = 'test-41219'

        que = multiprocessing.Queue()

        self.log.info("Step 1: Start Write Operations for parallel reads "
                      "and parallel deletes during m0d restart:")
        write_proc = []
        for _ in range(0, 2):
            proc = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                           args=(self.bucket_name, self.object_name,
                                                 self.test_cfg['clients'],
                                                 self.test_cfg['samples'],
                                                 self.test_cfg['size'],
                                                 log_file_prefix,
                                                 que))
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

        self.log.info("Step 3: Perform Write,Read,Delete Parallely during m0d restart")
        parallel_proc = []
        self.log.info("Step 3a: Start Write in new process")
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                args=(self.bucket_name, self.object_name,
                                                      self.test_cfg['clients'],
                                                      self.test_cfg['samples'],
                                                      self.test_cfg['size'],
                                                      log_file_prefix,
                                                      que))
        proc_write_op.start()
        parallel_proc.append(proc_write_op)
        self.log.info("Step 3b: Start Read in new process")
        # Reads, validate and delete
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                               args=(workload_info_list[0], que,
                                                     False,
                                                     True,
                                                     True))
        proc_read_op.start()
        parallel_proc.append(proc_read_op)
        self.log.info("Step 3c: Start Deletes in new process")
        # delete
        proc_delete_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                                 args=(workload_info_list[1], que,
                                                       True,
                                                       False,
                                                       False))
        proc_delete_op.start()
        parallel_proc.append(proc_delete_op)

        self.log.info(
            "Step 4: Perform Single m0d Process Restart During Write/Read/Delete Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process,
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
            assert_utils.assert_true(False, 'No workload returned for writes performed during m0d '
                                            'restart')

        self.log.info("Step 6: Perform read, delete operation on object written during m0d restart "
                      "during step 3")
        self.dtm_obj.perform_ops(write_during_restart, que, False, True, False)

        self.test_completed = True
        self.log.info("ENDED: Verify WRITE, READ, DELETE during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41230")
    def test_overwrite_same_object_during_m0d_restart(self):
        """Overwrite same object during m0d restart."""
        self.log.info("STARTED: Overwrite same object during m0d restart.")
        overwrite_cnt = self.test_cfg['test_41230']['overwrite_cnt']
        max_object_size = self.test_cfg['test_41230']['max_object_size']
        que = multiprocessing.Queue()

        self.log.info("Step 1: Create bucket : %s", self.bucket_name)
        self.s3_test_obj.create_bucket(self.bucket_name)

        self.log.info("Step 2 : Start continuous overwrite on same object")
        proc_overwrite_op = multiprocessing.Process(target=self.dtm_obj.perform_object_overwrite,
                                                    args=(self.bucket_name, self.object_name,
                                                          overwrite_cnt,
                                                          max_object_size, que))
        proc_overwrite_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart during overwrite ")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process,
                                            check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for Overwrite Operation to complete.")
        if proc_overwrite_op.is_alive():
            proc_overwrite_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        self.test_completed = True
        self.log.info("ENDED: Overwrite same object during m0d restart.")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41231")
    def test_io_operations_before_after_m0d_restart(self):
        """Verify IO operations work after m0d restart using pkill."""
        self.log.info("STARTED: Verify IO operations work after m0d restart using pkill.")
        log_file_prefix = 'test-41231'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform Write/Read Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.dtm_obj.perform_ops(workload_info, que, False, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 2: Create bucket for IO operation post m0d restart")
        bucket_post_m0d = f"{self.bucket_name}-post-m0d-restart"
        self.s3_test_obj.create_bucket(bucket_post_m0d)

        self.log.info("Step 3 : Perform Single m0d Process Restart ")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process,
                                            check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Read, validate, Delete data written in Step 1")
        self.dtm_obj.perform_ops(workload_info, que, False, True, False)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 5: Perform Write/Read/Delete Operations on new bucket %s",
                      bucket_post_m0d)
        self.dtm_obj.perform_write_op(bucket_prefix=self.bucket_name,
                                      object_prefix=self.object_name,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix, queue=que, loop=1,
                                      created_bucket=[bucket_post_m0d])
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.dtm_obj.perform_ops(workload_info, que, False, True, False)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify IO operations work after m0d restart using pkill.")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41232")
    def test_copy_object_after_m0d_restart(self):
        """Verify copy object after m0d restart using pkill."""
        self.log.info("STARTED: Verify copy object after m0d restart using pkill")
        object_name = 'object-test-41232'
        bucket_list = list()
        self.log.info("Step 1: Start write Operations :")
        for i in range(0, 2):
            bucket_name = f"bucket-test-41232-{i}"
            resp = self.s3_test_obj.create_bucket(bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            bucket_list.append(bucket_name)
        for size in self.test_cfg["size_list"]:
            file_name = "{}{}".format("dtm-test-41232", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            system_utils.create_file(file_path, size)
            resp = self.s3_test_obj.put_object(bucket_list[0], f"{object_name}_{size}", file_path)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Single m0d Process Restart")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")
        self.log.info("Step 3: Perform Copy Object to bucket-2, download and verify on copied "
                      "Objects")
        for size in self.test_cfg["size_list"]:
            resp = self.s3_test_obj.copy_object(source_bucket=bucket_list[0],
                                                source_object=f"{object_name}_{size}",
                                                dest_bucket=bucket_list[1],
                                                dest_object=f"{object_name}_{size}")
            assert_utils.assert_true(resp[0], resp[1])
            file_name_copy = "{}{}".format("dtm-test-41232-copy", size)
            file_path_copy = os.path.join(self.test_dir_path, file_name_copy)
            resp = self.s3_test_obj.object_download(bucket_name=bucket_list[1],
                                                    obj_name=f"{object_name}_{size}",
                                                    file_path=file_path_copy)
            assert_utils.assert_true(resp[0], resp[1])
            file_name = "{}{}".format("dtm-test-41232-", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            resp = validate_checksum(file_path_1=file_path, file_path_2=file_path_copy)
            assert_utils.assert_true(resp, "Checksum validation Failed.")
        self.test_completed = True
        self.log.info("ENDED: Verify copy object after m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41233")
    def test_copy_object_during_m0d_restart(self):
        """Verify copy object during m0d restart using pkill."""
        self.log.info("STARTED: Verify copy object during m0d restart using pkill")
        object_name = 'object-test-41233'
        workload = dict()
        obj_list = list()
        bucket_list = list()
        que = multiprocessing.Queue()

        self.log.info("Step 1: Start write Operations :")
        for i in range(0, 2):
            bucket_name = f"bucket-test-41233-{i}"
            resp = self.s3_test_obj.create_bucket(bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            bucket_list.append(bucket_name)
        for size in self.test_cfg["size_list"]:
            file_name = "{}{}".format("dtm-test-41233-", size)
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

        self.log.info("Step 3: Perform Single m0d Process Restart During Copy Object Operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Wait for copy object to finish")
        if proc_cp_op.is_alive():
            proc_cp_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Perform Download and verify on copied Objects")
        for size in self.test_cfg["size_list"]:
            file_name_copy = "{}{}".format("dtm-test-41233-copy", size)
            file_path_copy = os.path.join(self.test_dir_path, file_name_copy)
            resp = self.s3_test_obj.object_download(bucket_name=bucket_list[1],
                                                    obj_name=f"{object_name}_{size}",
                                                    file_path=file_path_copy)
            assert_utils.assert_true(resp[0], resp[1])
            file_name = "{}{}".format("dtm-test-41233-", size)
            file_path = os.path.join(self.test_dir_path, file_name)
            resp = validate_checksum(file_path_1=file_path, file_path_2=file_path_copy)
            assert_utils.assert_true(resp, "Checksum validation Failed.")
        self.test_completed = True
        self.log.info("ENDED: Verify copy object during m0d restart using pkill.")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-41245")
    def test_multiple_rgw_single_m0d_restart(self):
        """Verify IO operations work during multiple rgw restarts, single m0d restart
        and multiple rgw restarts."""
        self.log.info("STARTED: Verify IO operations work during multiple rgw restarts,"
                      " single m0d restart and multiple rgw restarts.")
        log_file_prefix = 'test-41245'
        que = multiprocessing.Queue()
        num_loops = num_buckets = self.test_cfg["test_41245"]["num_loop"]
        rgw_restarts = self.test_cfg["test_41245"]["rgw_restarts"]

        self.log.info("Step 1: Create %s buckets for IO operation during restarts", num_buckets)
        resp = self.s3_test_obj.create_multiple_buckets(num_buckets, 'test-41245')
        bucket_list = resp[1]
        self.log.info("Step 1: Bucket created in healthy mode ")

        self.log.info("Step 2: Perform Writes,Reads and Validate operation for %s iterations:",
                      num_loops)
        args = {'bucket_prefix': self.bucket_name, 'object_prefix': self.object_name,
                'no_of_clients': self.test_cfg['clients'],
                'no_of_samples': self.test_cfg['samples'],
                'log_file_prefix': log_file_prefix, 'queue': que, 'loop': num_loops,
                'retry': DTM_CFG["io_retry_count"], 'skip_read': False, 'skip_cleanup': True,
                'validate': True, 'created_bucket': bucket_list}
        proc_ios = multiprocessing.Process(target=self.dtm_obj.perform_write_op, kwargs=args)
        proc_ios.start()

        self.log.info("Step 3 : Perform RGW Process Restarts for %s iteration during IO operations",
                      rgw_restarts)
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process,
                                            check_proc_state=True,
                                            restart_cnt=rgw_restarts)
        assert_utils.assert_true(resp, "Failure observed during rgw process restart/recovery")

        self.log.info("Step 4 : Perform single m0d Process Restarts during IO operations")
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.POD_NAME_PREFIX,
                                            container_prefix=const.MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process,
                                            check_proc_state=True)
        assert_utils.assert_true(resp, "Failure observed during m0d process restart/recovery")

        self.log.info("Step 5 : Perform RGW Process Restarts for %s iteration during IO operations",
                      rgw_restarts)
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process,
                                            check_proc_state=True,
                                            restart_cnt=rgw_restarts)
        assert_utils.assert_true(resp, "Failure observed during rgw process restart/recovery")

        self.log.info("Step 6: Check if IO operations triggered in step 2 completed successfully")
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 7: Read, validate, Delete data written in Step 2")
        self.dtm_obj.perform_ops(workload_info, que, False, True, False)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify IO operations work during multiple rgw restarts,"
                      " single m0d restart and multiple rgw restarts.")
