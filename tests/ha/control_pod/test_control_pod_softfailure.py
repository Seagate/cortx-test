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
from libs.csm.csm_interface import csm_api_factory
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

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
        cls.s3_clean = cls.test_prefix = cls.deply_name = cls.repl_num = cls.test_io_prefix = None
        cls.def_replica = cls.del_users = cls.header = cls.scale_req = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
        cls.csm_obj = csm_api_factory("rest")
        cls.csm_soft_delay = HA_CFG["common_params"]["15sec_delay"]
        cls.num_users = HA_CFG["s3_operation_data"]["iam_users"] + 50

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
        self.scale_req = True if self.def_replica < self.repl_num else False
        self.deply_name = self.node_master_list[0].get_deployment_name(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[0]
        LOGGER.info("Default replicas for %s is %s and can be scaled to: %s",
                    const.CONTROL_POD_NAME_PREFIX, self.def_replica, self.repl_num)
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        LOGGER.info("Precondition: Create IAM user before soft-failure.")
        user = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(user)
        LOGGER.info("Precondition: Get header token before soft-failure")
        self.header = self.csm_obj.get_headers(self.csm_user, self.csm_passwd)
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created IAM users & buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            LOGGER.error("Cleanup: Failed to perform clean up of created IAM users & buckets")
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Cleanup: Successfully cleaned created IAM users & buckets.")

        if self.scale_req:
            LOGGER.info(
                "Cleanup: Revert back to default replica %s for control pod per cluster.",
                self.def_replica)
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
        Verify IAM user creation/deletion and IOs on already created IAM user while performing
        control pod soft-failure in loop one by one for N control pods.
        """
        LOGGER.info("STARTED: Verify IAM user creation/deletion & IOs on already created IAM user "
                    "while performing control pod soft-failure in loop 1 by 1 for N control pods.")

        LOGGER.info("Precondition: Create %s iam users for deletion", self.num_users)
        del_users = self.mgnt_ops.create_account_users(nusers=self.num_users)

        LOGGER.info("Step 1: Perform IOs before soft-failure.")
        self.test_prefix = 'test-45498'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.s3_clean.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed IOs before soft-failure.")

        if self.scale_req:
            LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                                deploy=self.deply_name)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        iam_output = Queue()
        io_output = Queue()
        event = threading.Event()

        LOGGER.info("Step 2: Starting independent background threads for IOs on already created "
                    "user and IAM user creation/deletion.")
        LOGGER.info("Step 2.1: Start IAM user creation/deletion in background during control pod "
                    "soft-failure.")

        args = {'user_crud': True, 'num_users': self.num_users,
                'output': iam_output, 'del_users_dict': del_users, 'header': self.header}
        thr_iam = threading.Thread(target=self.ha_obj.iam_bucket_cruds,
                                   args=(event, ), kwargs=args)
        thr_iam.daemon = True  # Daemonize thread
        self.test_io_prefix = 'test-45498-io'
        args = {'s3userinfo': list(self.s3_clean.values())[0], 'log_prefix': self.test_io_prefix,
                'nclients': 1, 'nsamples': 8, 'output': io_output, 'setup_s3bench': False}
        LOGGER.info("Step 2.2: Start IOs in background during control pod soft-failure.")
        io_thread = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        io_thread.daemon = True  # Daemonize thread
        io_thread.start()
        thr_iam.start()
        LOGGER.info("Step 2: Started independent background threads for IOs on already created "
                    "user and IAM user creation/deletion.")

        LOGGER.info("Step 3: Perform soft-failure of %s control pods in loop and check cluster "
                    "has failures", self.repl_num)
        LOGGER.info("Get the list of control pods")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        event.set()
        for pod in pod_list:
            self.node_master_list[0].kill_process_in_container(pod_name=pod,
                                                               container_name=const.CORTX_CSM_POD,
                                                               process_name=const.CSM_AGENT_PRC,
                                                               safe_kill=True)
            LOGGER.info("Step 3.1: Check cluster has failures.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 3.1: Checked cluster has failures.")
        LOGGER.info("Step 3: Performed soft-failure of %s control pods in loop and checked cluster "
                    "has failures", self.repl_num)

        time.sleep(self.csm_soft_delay)
        event.clear()
        LOGGER.info("Waiting for background threads to join")
        thr_iam.join()
        io_thread.join()
        LOGGER.info("Step 4: Verifying responses from background processes")
        LOGGER.info("Step 4.1: Verify background process for IAM user creation")
        iam_resp = tuple()
        while len(iam_resp) != 4:
            iam_resp = iam_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not iam_resp:
            assert_utils.assert_true(False, "Background process failed to do IAM user CRUD "
                                            "operations")
        failed = iam_resp[1]
        exp_failed = iam_resp[0]
        user_del_failed = iam_resp[2]
        created_users = iam_resp[3]
        assert_utils.assert_false(failed, "No IAM user creation/deletion expected to fail before "
                                          f"or after soft-failure: {failed}")
        assert_utils.assert_true(exp_failed, "IAM user creation/deletion expected to fail during "
                                             f"soft-failure: {exp_failed}")
        if created_users:
            for i_i in created_users:
                self.s3_clean.update(i_i)
        LOGGER.info("Updating dict for clean up with remaining users")
        for i_i in user_del_failed:
            self.s3_clean.update({i_i: del_users[i_i]})
        LOGGER.info("Step 4.1: Verified background process for IAM user creation/deletion")

        LOGGER.info("Step 4.2: Verify background process of IOs")
        responses = {}
        while len(responses) != 2:
            responses = io_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 4.2: Verified background process of IOs")
        LOGGER.info("Step 4: Verified responses from background processes")

        LOGGER.info("Step 5: Create IAM user and perform IOs after soft-failure.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-45498-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nclients=2, nsamples=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Created IAM user and performed IOs after soft-failure.")

        LOGGER.info("ENDED: Verify IAM user creation/deletion and IOs on already created IAM user "
                    "while performing control pod soft-failure in loop 1 by 1 for N control pods.")
