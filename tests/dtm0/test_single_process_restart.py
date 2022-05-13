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
#

"""
Test suite for testing Single Process Restart with DTM enabled.
"""
import logging
import multiprocessing
import os

import pytest

from commons import configmanager
from commons.constants import K8S_SCRIPTS_PATH, POD_NAME_PREFIX, MOTR_CONTAINER_PREFIX
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import support_bundle_utils, assert_utils
from config import CMN_CFG
from conftest import LOG_DIR
from libs.dtm0.dtm0_lib import DTM0TestLib


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
        cls.test_cfg = configmanager.get_config_wrapper(fpath="config/test_dtm0_config.yaml")
        cls.m0d_process = 'm0d'
        cls.restart_wait_time_secs = 10
        cls.dtm0_obj = DTM0TestLib()

    def teardown_method(self):
        """Teardown class method."""
        if not self.test_completed:
            self.log.info("Test Failure observed, collecting support bundle")
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            resp = support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                                   scripts_path=K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp)
        # TODO : Redeploy setup after test completion.

    @pytest.mark.lc
    @pytest.mark.dtm0
    @pytest.mark.tags("TEST-41204")
    def test_read_during_m0d_restart(self):
        """Verify READ during m0d restart using pkill -9."""
        self.log.info("STARTED: Verify READ during m0d restart using pkill -9")
        bucket_name = 'bucket-test-41204'
        object_name = 'object-test-41204'
        test_41204_cfg = self.test_cfg['test_41204']
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform write Operations :")
        self.dtm0_obj.perform_write_op(bucket_prefix=bucket_name,
                                       object_name=object_name,
                                       clients=test_41204_cfg['clients'],
                                       samples=test_41204_cfg['samples'],
                                       size=test_41204_cfg['size'],
                                       log_file_prefix=test_41204_cfg['log_file_prefix'], queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 2: Perform Read Operations :")
        proc_read_op = multiprocessing.Process(target=self.dtm0_obj.perform_read_op,
                                               args=(workload_info, que,
                                                     True,
                                                     True,
                                                     True))
        proc_read_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Read Operations")
        self.dtm0_obj.process_restart(self.master_node_list[0],
                                      POD_NAME_PREFIX, MOTR_CONTAINER_PREFIX, self.m0d_process)

        self.log.info("Step 4: Check hctl status if all services are online")
        resp = self.health_obj.is_motr_online()
        assert_utils.assert_true(resp, 'All services are not online.')

        self.log.info("Step 5: Wait for Read Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify READ during m0d restart using pkill -9")

    @pytest.mark.lc
    @pytest.mark.dtm0
    @pytest.mark.tags("TEST-41219")
    def test_write_during_m0d_restart(self):
        """Verify WRITE during m0d restart using pkill -9."""
        self.log.info("STARTED: Verify WRITE during m0d restart using pkill -9")
        bucket_name = 'bucket-test-41219'
        object_name = 'object-test-41219'
        test_41219_cfg = self.test_cfg['test_41219']
        que = multiprocessing.Queue()

        self.log.info("Step 1: Start write Operations :")
        proc_write_op = multiprocessing.Process(target=self.dtm0_obj.perform_write_op,
                                                args=(bucket_name, object_name,
                                                      test_41219_cfg['clients'],
                                                      test_41219_cfg['samples'],
                                                      test_41219_cfg['size'],
                                                      test_41219_cfg['log_file_prefix'],
                                                      que))
        proc_write_op.start()

        self.log.info("Step 2 : Perform Single m0d Process Restart During Write Operations")
        self.dtm0_obj.process_restart(self.master_node_list[0],
                                      POD_NAME_PREFIX, MOTR_CONTAINER_PREFIX, self.m0d_process)

        self.log.info("Step 3: Check hctl status if all services are online")
        resp = self.health_obj.is_motr_online()
        assert_utils.assert_true(resp, 'All services are not online.')

        self.log.info("Step 4: Wait for Write Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 5: Perform Read Operations :")
        self.dtm0_obj.perform_read_op(workload_info, que, True, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify READ during m0d restart using pkill -9")
