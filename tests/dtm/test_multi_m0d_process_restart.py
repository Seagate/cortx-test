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
import time
from time import perf_counter_ns

import pytest

from commons import configmanager
from commons import constants as const
from commons.constants import POD_NAME_PREFIX, M0D_SVC
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from commons.utils import system_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from conftest import LOG_DIR
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestMultiProcessRestart:
    """Test Class for Multi Process Restart."""

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
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/dtm/test_dtm_config.yaml")
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
        cls.delay = cls.test_cfg['delay']

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
                                     endpoint_url=S3_CFG["s3_url"], max_attempts=0)
        self.dtm_obj = DTMRecoveryTestLib(self.access_key, self.secret_key, max_attempts=0)
        self.log.info("Created IAM user with name %s", self.s3acc_name)
        if not os.path.exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)

        self.log.info("Edit deployment file to append conditional sleep command to m0d setup "
                      "command of all data pods.")
        resp = self.master_node_list[0].get_deployment_name(POD_NAME_PREFIX)
        for each in resp:
            self.log.info("Editing Deployment for %s", each)
            resp = self.dtm_obj.edit_deployments_for_delay(self.master_node_list[0], each, M0D_SVC)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Edit deployment done for all data pods")
        self.log.info("Sleep of %s secs", self.test_cfg['edit_deployment_delay'])
        time.sleep(self.test_cfg['edit_deployment_delay'])
        self.log.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Cluster status is online.")
        self.log.info("Get the value of K for the given cluster.")
        resp = self.ha_obj.get_config_value(self.master_node_list[0])
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            self.log.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        self.log.info("The cluster has %s parity pods", self.kvalue)

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
    def test_write_during_multi_m0d_restart(self):
        """Verify write during multiple m0d restart using pkill."""
        self.log.info("STARTED: Verify write during multiple m0d restart using pkill")
        log_file_prefix = 'test-XXXXX'
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

        time.sleep(self.delay)
        self.log.info("Step 2 : Perform multiple m0d Process Restarts During Write Operations")
        resp_proc = self.dtm_obj.multi_process_restart_with_delay(
            master_node=self.master_node_list[0],
            health_obj=self.health_obj,
            pod_prefix=const.POD_NAME_PREFIX,
            container_prefix=const.MOTR_CONTAINER_PREFIX,
            process=self.m0d_process,
            check_proc_state=True,
            k_value=self.kvalue)

        self.log.info("Step 3: Wait for Write Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        # Assert if process restart failed
        assert_utils.assert_true(resp_proc, "Failure observed during process restart/recovery")

        self.log.info("Step 4: Perform Read Operations on data written in Step 1:")
        self.dtm_obj.perform_ops(workload_info, que, False, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify write during multiple m0d restart using pkill")
