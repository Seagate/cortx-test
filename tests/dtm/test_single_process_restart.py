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
import threading
from multiprocessing import Queue
from time import perf_counter_ns
import time

import pytest

from commons import configmanager
from commons import constants as const
from commons.constants import K8S_SCRIPTS_PATH, POD_NAME_PREFIX, MOTR_CONTAINER_PREFIX
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import LATEST_LOG_FOLDER
from commons.utils import support_bundle_utils, assert_utils
from config import CMN_CFG, HA_CFG
from config.s3 import S3_CFG
from conftest import LOG_DIR
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from scripts.s3_bench import s3bench


# pylint: disable=R0902
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
        cls.dtm_obj = DTMRecoveryTestLib()
        cls.log.info("Setup S3bench")
        resp = s3bench.setup_s3bench()
        assert_utils.assert_true(resp)
        cls.ha_obj = HAK8s()
        cls.rest_obj = S3AccountOperations()

    def setup_method(self):
        """Setup Method"""
        self.log.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.master_node_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Cluster status is online.")
        self.random_time = int(perf_counter_ns())
        self.s3acc_name = f"dps_s3acc_{self.random_time}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"dps-bkt-{self.random_time}"
        self.object_name = f"dps-obj-{self.random_time}"
        self.deploy = False
        self.iam_user = dict()

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
        """Verify READ during m0d restart using pkill."""
        self.log.info("STARTED: Verify READ during m0d restart using pkill")
        bucket_name = 'bucket-test-41204'
        object_prefix = 'object-test-41204'
        log_file_prefix = 'test-41204'
        que = multiprocessing.Queue()

        self.log.info("Step 1: Perform write Operations :")
        self.dtm_obj.perform_write_op(bucket_prefix=bucket_name,
                                      object_prefix=object_prefix,
                                      no_of_clients=self.test_cfg['clients'],
                                      no_of_samples=self.test_cfg['samples'],
                                      obj_size=self.test_cfg['size'],
                                      log_file_prefix=log_file_prefix, queue=que)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 2: Perform Read Operations on the data written in step 1 in background")
        proc_read_op = multiprocessing.Process(target=self.dtm_obj.perform_ops,
                                               args=(workload_info, que,
                                                     True,
                                                     True,
                                                     True))
        proc_read_op.start()

        self.log.info("Step 3 : Perform Single m0d Process Restart During Read Operations")
        self.log.debug("Get IDs of all m0d processes")
        resp, fids = self.health_obj.hctl_status_get_svc_fids()
        assert_utils.assert_true(resp, "Failed to get services fids")
        fids = fids['ioservice']
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj, pod_prefix=POD_NAME_PREFIX,
                                            container_prefix=MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, process_ids=fids)
        assert_utils.assert_true(resp, f"Response: {resp} \nhctl status is not as expected")

        self.log.info("Step 4: Wait for Read Operation to complete.")
        if proc_read_op.is_alive():
            proc_read_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify READ during m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm0
    @pytest.mark.tags("TEST-41219")
    def test_write_during_m0d_restart(self):
        """Verify WRITE during m0d restart using pkill."""
        self.log.info("STARTED: Verify WRITE during m0d restart using pkill")
        bucket_name = 'bucket-test-41219'
        object_prefix = 'object-test-41219'
        log_file_prefix = 'test-41219'

        que = multiprocessing.Queue()

        self.log.info("Step 1: Start write Operations :")
        proc_write_op = multiprocessing.Process(target=self.dtm_obj.perform_write_op,
                                                args=(bucket_name, object_prefix,
                                                      self.test_cfg['clients'],
                                                      self.test_cfg['samples'],
                                                      self.test_cfg['size'],
                                                      log_file_prefix,
                                                      que))
        proc_write_op.start()

        self.log.info("Step 2 : Perform Single m0d Process Restart During Write Operations")
        self.log.debug("Get IDs of all m0d processes")
        resp, fids = self.health_obj.hctl_status_get_svc_fids()
        assert_utils.assert_true(resp, "Failed to get services fids")
        fids = fids['ioservice']
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj, pod_prefix=POD_NAME_PREFIX,
                                            container_prefix=MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, process_ids=fids)
        assert_utils.assert_true(resp, f"Response: {resp} \nhctl status is not as expected")

        self.log.info("Step 3: Wait for Write Operation to complete.")
        if proc_write_op.is_alive():
            proc_write_op.join()
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])
        workload_info = resp[1]

        self.log.info("Step 4: Perform Read Operations on data written in Step 1:")
        self.dtm_obj.perform_ops(workload_info, que, True, True, True)
        resp = que.get()
        assert_utils.assert_true(resp[0], resp[1])

        self.test_completed = True
        self.log.info("ENDED: Verify READ during m0d restart using pkill")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.dtm0
    @pytest.mark.tags("TEST-41234")
    def test_ios_during_rc_m0d_restart(self):
        """Verify IOs during RC pod m0d restart using pkill."""
        self.log.info("STARTED: Verify IOs before and after RC pod m0d restart using pkill")

        self.log.info("Step 1: Create IAM user and perform WRITEs/READs-Verify with variable "
                      "object sizes in background")
        event = threading.Event()  # Event to be used to send intimation of m0d restart
        output = Queue()

        self.log.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.iam_user = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        test_prefix = 'test-41234'
        self.log.info("Perform WRITEs/READs-Verify with variable object sizes in background")
        args = {'s3userinfo': self.iam_user, 'log_prefix': test_prefix,
                'nclients': 10, 'nsamples': 30, 'skipcleanup': True, 'output': output}

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
        self.log.debug("Get IDs of all m0d processes")
        resp, fids = self.health_obj.hctl_status_get_svc_fids()
        assert_utils.assert_true(resp, "Failed to get services fids")
        fids = fids['ioservice']
        event.set()
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj, pod_prefix=rc_datapod,
                                            container_prefix=MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, process_ids=fids)
        assert_utils.assert_true(resp, f"Response: {resp} \nhctl status is not as expected")
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
        assert_utils.assert_false(len(resp[1]), "Failed WRITEs/READs in background before/after m0d"
                                                f"restart. Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_false(len(resp[1]) <= len(fail_logs),
                                  "Expected failures in WRITEs/READs in background during m0d "
                                  f"restart. Logs collected during m0d restart: {resp[1]}")
        self.log.info("Step 3: Successfully completed WRITEs/READs in background")

        self.log.info("Step 4: Perform READs-Verify on already written data in Step 1")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix, skipwrite=True,
                                                    skipcleanup=True, nclients=10, nsamples=30)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Successfully performed READs-Verify on already written data in "
                      "Step 1")

        self.log.info("ENDED: Verify IOs before and after RC pod m0d restart using pkill")

    @pytest.mark.lc
    @pytest.mark.dtm0
    @pytest.mark.tags("TEST-41235")
    def test_bkt_creation_ios_after_m0d_restart(self):
        """Verify bucket creation and IOs after m0d restart using pkill."""
        self.log.info("STARTED: Verify bucket creation and IOs after m0d restart using pkill")

        self.log.info("Step 1: Perform Single m0d Process Restart")
        self.log.debug("Get IDs of all m0d processes")
        resp, fids = self.health_obj.hctl_status_get_svc_fids()
        assert_utils.assert_true(resp, "Failed to get services fids")
        fids = fids['ioservice']
        resp = self.dtm_obj.process_restart(master_node=self.master_node_list[0],
                                            health_obj=self.health_obj, pod_prefix=POD_NAME_PREFIX,
                                            container_prefix=MOTR_CONTAINER_PREFIX,
                                            process=self.m0d_process, process_ids=fids)
        assert_utils.assert_true(resp, f"Response: {resp} \nhctl status is not as expected")
        self.log.info("Step 1: m0d restarted and recovered successfully")

        self.log.info("Step 2: Create IAM user and perform WRITEs/READs-Verify/DELETEs with "
                      "variable object sizes")
        self.log.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.iam_user = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        test_prefix = 'test-41235'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.iam_user,
                                                    log_prefix=test_prefix,
                                                    nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Successfully created IAM user and performed "
                      "WRITEs/READs-Verify/DELETEs with variable sizes objects.")

        self.log.info("ENDED: Verify IOs after m0d restart using pkill")
