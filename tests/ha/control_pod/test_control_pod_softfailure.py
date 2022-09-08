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
HA test suite for Control Pod Soft Failure
"""

import logging
import os
import secrets
import threading
import time
from multiprocessing import Queue

import pytest

from commons import constants as const
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestControlPodSoftFailure:
    """
    Test suite for Control Pod Soft Failure
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.username = []
        cls.password = []
        cls.node_master_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = cls.deply_name = cls.repl_num = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
        cls.csm_obj = csm_api_factory("rest")

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
            else:
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.s3_clean = dict()
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        set_type, set_name = self.node_master_list[0].get_set_type_name(
            pod_name=pod_list[0])
        LOGGER.info("Got set_type = %s and set_name = %s.", set_type, set_name)
        resp = self.node_master_list[0].get_num_replicas(set_type, set_name)
        assert_utils.assert_true(resp[0], resp)
        self.def_replica = int(resp[1])
        self.repl_num = int(len(self.node_worker_list) / 2 + 1)
        self.deply_name = self.node_master_list[0].get_deployment_name(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[0]
        LOGGER.info("Default replicas for %s is %s and can be scaled to: %s",
                    const.CONTROL_POD_NAME_PREFIX, self.def_replica, self.repl_num)
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Revert back to default single control pod per cluster if more replicas are "
                    "created.")
        resp = self.node_master_list[0].create_pod_replicas(num_replica=self.def_replica,
                                                            deploy=self.deply_name)
        assert_utils.assert_true(resp[0], resp[1])
        if os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45498")
    def test_45498(self):
        """
        Verify IAM user creation and IOs on already created IAM user while performing
        control pod soft-failure in loop one by one for N control pods.
        """
        LOGGER.info("STARTED: Verify IAM user creation and IOs on already created IAM user while "
                    "performing control pod soft-failure in loop one by one for N control pods.")

        LOGGER.info("Step 1: Create IAM user and perform IOs before soft-failure.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-45498'
        self.s3_clean = users
        access_key = list(users.values())[0]['accesskey']
        secret_key = list(users.values())[0]['secretkey']
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Created IAM user and performed IOs before soft-failure.")

        num_users = HA_CFG["s3_operation_data"]["iam_users"] + 50
        header = self.csm_obj.get_headers(self.csm_user, self.csm_passwd)
        LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                            deploy=self.deply_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        LOGGER.info("Step 2: Perform WRITEs for background READs and DELETEs")
        wr_bucket = HA_CFG["s3_bucket_data"]["degraded_bucket"]
        LOGGER.info("Step 2.1: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        iam_output = Queue()
        event = threading.Event()
        test_prefix_del = 'test-45498-delete'
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        existing_bkt = len(s3_test_obj.bucket_list()[1])
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets = len(s3_test_obj.bucket_list()[1]) - existing_bkt
        assert_utils.assert_equal(buckets, wr_bucket, f"Failed to create {wr_bucket} number "
                                                      f"of buckets. Created {buckets} buckets")
        s3_data = wr_resp[0]
        LOGGER.info("Step 2.1: Successfully performed WRITEs with variable object sizes on %s "
                    "buckets for parallel DELETEs.", wr_bucket)
        LOGGER.info("Step 2.2: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = 'test-45498-read'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2.2: Performed WRITEs with variable sizes objects for parallel READs.")
        LOGGER.info("Step 2: Performed WRITEs for background READs and DELETEs")

        LOGGER.info("Step 3: Starting independent background threads for IOs on already created "
                    "user and IAM user creation.")
        LOGGER.info("Step 3.1: Start IAM user creation in background during control pod "
                    "soft-failure.")
        args = {'user_crud': True, 'num_users': num_users, 'output': iam_output, 'header': header}
        thr_iam = threading.Thread(target=self.ha_obj.iam_bucket_cruds, args=(event,), kwargs=args)
        thr_iam.daemon = True  # Daemonize thread
        thr_iam.start()
        LOGGER.info("Step 3.1: Start continuous DELETEs in background on random %s buckets",
                    wr_bucket)
        bucket_list = s3_data.keys()
        get_random_buck = self.system_random.sample(bucket_list, wr_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 3.1: Started DELETEs in background for %s buckets", wr_bucket)
        LOGGER.info("Step 3.2: Start WRITEs with variable object sizes in background")
        test_prefix_write = 'test-45498-write'
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 3.2: Started WRITEs with variable sizes objects in background")
        LOGGER.info("Step 3.3: Start READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True	 # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 3.3: Started READs and verify on the written data in background")
        LOGGER.info("Step 3: Started independent background threads for IOs on already created "
                    "user and IAM user creation.")
        LOGGER.info("Wait for %s seconds for all background operations to start",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 4: Perform soft-failure of %s control pods in loop and check cluster "
                    "has failures", self.repl_num - 1)
        LOGGER.info("Get the list of control pods")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        event.set()
        for pod in pod_list:
            self.node_master_list[0].kill_process_in_container(pod_name=pod,
                                                               container_name=const.CORTX_CSM_POD,
                                                               process_name=const.CSM_AGENT_PRC,
                                                               safe_kill=True)
            LOGGER.info("Step 4.1: Check cluster has failures.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 4.1: Checked cluster has failures.")
        LOGGER.info("Step 4: Performed soft-failure of %s control pods in loop and checked cluster "
                    "has failures", self.repl_num - 1)

        time.sleep(15)
        event.clear()
        LOGGER.info("Waiting for background threads to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        thr_iam.join()
        LOGGER.info("Step 5: Verifying responses from background processes")
        LOGGER.info("Step 5.1: Verify background process for IAM user creation")
        iam_resp = tuple()
        while len(iam_resp) != 4:
            iam_resp = iam_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not iam_resp:
            assert_utils.assert_true(False, "Background process failed to do IAM user CRUD "
                                            "operations")
        failed = iam_resp[1]
        created_users = iam_resp[3]
        if failed:
            assert_utils.assert_true(False, "No IAM user creation expected before or after "
                                            f"soft-failure: {failed}")
        if created_users:
            for i_i in created_users:
                self.s3_clean.update(i_i)
        LOGGER.info("Step 5.1: Verified background process for IAM user creation")
        LOGGER.info("Step 5.2: Verify status for In-flight DELETEs")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  "Bucket deletion failed in control pod soft-failure process "
                                  f"{fail_del_bkt} {event_del_bkt}")
        LOGGER.info("Step 5.2: Verified status for In-flight DELETEs")
        LOGGER.info("Step 5.3: Verify status for In-flight WRITEs")
        wr_resp = dict()
        while len(wr_resp) != 2:
            wr_resp = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in wr_resp["pass_res"])
        fail_logs = list(x[1] for x in wr_resp["fail_res"])
        LOGGER.debug("Logs during control pod soft-failure: %s\nLogs after "
                     "control pod soft-failure: %s", pass_logs, fail_logs)
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), f"WRITEs which contain failures: {resp[1]}")

        LOGGER.info("Step 5.3: Verified status for In-flight WRITEs")
        LOGGER.info("Step 5.4: Verify status for In-flight READs/Verify DI")
        rd_resp = dict()
        while len(rd_resp) != 2:
            rd_resp = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in rd_resp["pass_res"])
        fail_logs = list(x[1] for x in rd_resp["fail_res"])
        LOGGER.debug("Logs during control pod soft-failure: %s\nLogs after "
                     "control pod soft-failure: %s", pass_logs, fail_logs)
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), f"READs/VerifyDI which contain failures: {resp[1]}")
        LOGGER.info("Step 5.4: Verified status for In-flight READs/Verify DI")
        LOGGER.info("Step 5: Verifying responses from background processes")

        LOGGER.info("Step 6: Create IAM user and perform IOs after soft-failure.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-45498-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nclients=2, nsamples=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Created IAM user and performed IOs after soft-failure.")

        LOGGER.info("ENDED: Verify IAM user creation and IOs on already created IAM user while "
                    "performing control pod soft-failure in loop one by one for N control pods.")
