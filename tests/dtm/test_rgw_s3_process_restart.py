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
        cls.rgw_process = 'rgw'
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
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]
        self.log.info("Step 2: Perform Read Operations on the data written in step 1 in background")
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                               args=(workload_info, que, False, True, True))
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

        self.log.info("Step 4: Wait for READ operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
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
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                args=(self.bucket_name, self.object_name,
                                                      self.test_cfg['clients'],
                                                      self.test_cfg['samples'], log_file_prefix,
                                                      que, self.test_cfg['size']))
        proc_write_op.start()

        self.log.info("Step 3: Perform rgw_s3 Process Restart for %s times During Read "
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

        self.log.info("ENDED: Verify WRITEs during rgw_s3 restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm
    @pytest.mark.tags("TEST-42246")
    def test_delete_during_rgw_svc_restart(self):
        """Verify DELETEs during rgw_s3 service restart using pkill."""
        self.log.info("STARTED: Verify DELETEs during rgw_s3 service restart using pkill")
        test_prefix = 'test-42246'
        wr_output = Queue()

        event = threading.Event()  # Event to be used to send intimation of rgw_s3 process restart

        self.log.info("Step 1: Perform write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=f"bucket-{test_prefix}",
                                      object_prefix=f"object-{test_prefix}",
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=test_prefix, queue=wr_output)
        resp = wr_output.get()
        assert_utils.assert_true(resp[0], resp[1])

        buckets = self.s3_test_obj.bucket_list()[1]
        self.log.info("Step 1: Successfully created %s buckets & performed WRITEs with variable "
                      "size objects.", len(buckets))

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
        self.log.info("Step 3: Perform rgw_s3 Process Restart for %s times During Read "
                      "Operations", DTM_CFG["rgw_restart_cnt"])
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj,
                                            pod_prefix=const.SERVER_POD_NAME_PREFIX,
                                            container_prefix=const.RGW_CONTAINER_NAME,
                                            process=self.rgw_process, check_proc_state=False,
                                            restart_cnt=DTM_CFG["rgw_restart_cnt"])
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
