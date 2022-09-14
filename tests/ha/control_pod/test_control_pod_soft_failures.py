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
HA test suite for Control Pod Restart
"""

import logging
import os
import secrets
import threading
import time
from http import HTTPStatus
from multiprocessing import Queue

import pytest

from commons import commands as cmd
from commons import constants as const
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.csm.csm_interface import csm_api_factory
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.di.di_mgmt_ops import ManagementOPs
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestControlPodSoftFailure:
    """
    Test suite for Control Pod Restart
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
        cls.host_master_list = []
        cls.node_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.s3_clean = cls.test_prefix = cls.repl_num = cls.test_io_prefix = cls.header = None
        cls.ctrl_pod_list = cls.change_proc_delay = cls.multipart_obj_path = cls.users = None
        cls.uids = cls.s3_obj = cls.dtm_obj = cls.pid = None
        cls.mgnt_ops = ManagementOPs()
        cls.rest_iam_user = RestIamUser()
        cls.csm_obj = csm_api_factory("rest")
        cls.system_random = secrets.SystemRandom()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.host_master_list.append(cls.host)
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
            else:
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.test_file = "ha-test-file"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HAControlPod")
        cls.ctrl_pods = cls.node_master_list[0].get_all_pods(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        cls.container_name = cls.node_master_list[0].get_all_pods_containers(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[cls.ctrl_pods[0]][0]
        set_type, set_name = cls.node_master_list[0].get_set_type_name(pod_name=cls.ctrl_pods[0])
        LOGGER.info("Got set_type = %s and set_name = %s.", set_type, set_name)
        resp = cls.node_master_list[0].get_num_replicas(set_type, set_name)
        assert_utils.assert_true(resp[0], resp)
        cls.default_replica = int(resp[1])
        cls.repl_num = int(len(cls.node_worker_list) / 2 + 1)
        cls.scale_req = True if cls.default_replica < cls.repl_num else False
        cls.deploy_name = cls.node_master_list[0].get_deployment_name(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[0]
        LOGGER.info("Default replicas for %s is %s and can be scaled to: %s",
                    const.CONTROL_POD_NAME_PREFIX, cls.default_replica, cls.repl_num)
        cls.num_users = HA_CFG["s3_operation_data"]["200_iam_users"]
        cls.csm_soft_delay = HA_CFG["common_params"]["15sec_delay"]
        cls.max_proc_restart_delay = HA_CFG["common_params"]["60sec_delay"]
        cls.min_proc_restart_delay = HA_CFG["common_params"]["20sec_delay"]

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.s3_clean = dict()
        self.ctrl_pod_list = list()
        self.change_proc_delay = False
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        if not os.path.exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Precondition: Create IAM user before soft-failure.")
        self.users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = self.users
        self.uids = list(self.users.keys())
        access_key = list(self.users.values())[0]['accesskey']
        secret_key = list(self.users.values())[0]['secretkey']
        self.s3_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        self.header = self.csm_obj.get_headers(self.csm_user, self.csm_passwd)
        LOGGER.info("Successfully created IAM user")
        self.dtm_obj = DTMRecoveryTestLib(access_key, secret_key, max_attempts=0)
        self.pid = self.get_pid(pod_name=self.ctrl_pods[0], container_name=self.container_name,
                                proc_name=const.CONTROL_POD_SVC_NAME)
        LOGGER.debug("PID of cortx-csm-agent process is: %s", self.pid)
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            if not resp[0]:
                LOGGER.error("Cleanup: Failed to perform clean up of created IAM users & buckets")
            LOGGER.info("Cleanup: Successfully cleaned created IAM users & buckets.")
        if self.scale_req:
            LOGGER.info(
                "Cleanup: Revert back to default replica %s for control pod per cluster.",
                self.default_replica)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.default_replica,
                                                                deploy=self.deploy_name)
            assert_utils.assert_true(resp[0], resp[1])

        if self.change_proc_delay:
            LOGGER.info("Changing control pod process delay to 0")
            self.add_proc_restart_delay()
            LOGGER.info("Changed control pod process delay to 0")

        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")

        LOGGER.info("Removing extra files")
        sysutils.cleanup_dir(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    def add_proc_restart_delay(self, proc_restart_delay=0):
        """
        Helper function to add delay in control pod container to delay the process restart operation
        :param proc_restart_delay: Delay in seconds
        :return: None
        """
        self.ctrl_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        for pod in self.ctrl_pod_list:
            self.dtm_obj.set_proc_restart_duration(self.node_master_list[0], pod,
                                                   self.container_name, proc_restart_delay)

    def get_pid(self, pod_name, container_name, proc_name):
        """
        Helper function to get pid based on process name
        :param pod_name: Name of the pod
        :param container_name: Name of the container
        :param proc_name: Name of the process
        :return: tuple
        """
        command = cmd.GET_PID_INIT_PROCESS.format(proc_name)
        resp = self.node_master_list[0].send_k8s_cmd(operation="exec", pod=pod_name,
                                                     namespace=const.NAMESPACE,
                                                     command_suffix=f"-c {container_name} "
                                                                    f"-- {command}",
                                                     decode=True)
        return resp

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45498")
    def test_iam_cruds_during_soft_failure_all_pods(self):
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
                                                                deploy=self.deploy_name)
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
                'nclients': 1, 'nsamples': 5, 'output': io_output, 'setup_s3bench': False}
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
            resp = self.node_master_list[0].kill_process_in_container(
                pod_name=pod, container_name=self.container_name, pid=self.pid, safe_kill=True)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Step 3.1: Check cluster has failures.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 3.1: Checked cluster has failures.")
        LOGGER.info("Step 3: Performed soft-failure of %s control pods in loop and checked cluster "
                    "has failures", self.repl_num)

        LOGGER.info("Waiting for %s sec for successful container restart",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        event.clear()
        LOGGER.info("Step 4: Check cluster status is online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked cluster status is online.")

        LOGGER.info("Waiting for background threads to join")
        thr_iam.join()
        io_thread.join()
        LOGGER.info("Step 5: Verifying responses from background processes")
        LOGGER.info("Step 5.1: Verify background process for IAM user creation")
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
        if failed:
            assert_utils.assert_true(False, "Failures observed in background process for IAM "
                                            "user CRUD operations before and after soft failures. "
                                            f"\nFailed users: {failed}")
        elif exp_failed:
            LOGGER.info("In-Flight IAM user creation/deletion failed for users: %s", exp_failed)
            LOGGER.info("In-Flight IAM user deletion failed for users: %s", user_del_failed)
            for i_i in user_del_failed:
                self.s3_clean.update({i_i: del_users[i_i]})
        else:
            assert_utils.assert_true(False, "Some IAM user CRUD operations are expected to be "
                                            "failed during control pod soft failures")

        assert_utils.assert_true(len(created_users), "Few IAM user creation is expected during "
                                                     "soft failures in loop")
        for i_i in created_users:
            self.s3_clean.update(i_i)
        LOGGER.info("Step 5.1: Verified background process for IAM user creation/deletion")

        LOGGER.info("Step 5.2: Verify background process of IOs")
        responses = {}
        while len(responses) != 2:
            responses = io_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 5.2: Verified background process of IOs")
        LOGGER.info("Step 5: Verified responses from background processes")

        LOGGER.info("Step 6: Create multiple IAM user after soft-failure.")
        users = self.mgnt_ops.create_account_users()
        new_users_list = list(users.keys())
        resp = self.csm_obj.list_iam_users_rgw()
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "List IAM user failed.")
        user_data_new = resp.json()
        fetched_users = user_data_new['users']
        assert_utils.assert_true(
            (set(new_users_list).issubset(set(fetched_users)),
             "Failed to create IAM users after soft-failure"))
        self.s3_clean.update(users)
        LOGGER.info("Step 6: Created multiple IAM user after soft-failure.")

        LOGGER.info("ENDED: Verify IAM user creation/deletion and IOs on already created IAM user "
                    "while performing control pod soft-failure in loop 1 by 1 for N control pods.")

    # pylint: disable-msg=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45499")
    def test_iam_cruds_soft_failure_all_pods(self):
        """
        Test IOs and IAM user CRUDs before and after csm-agent is down in all control pods.
        (Negative Scenario)
        """
        LOGGER.info("STARTED: Test IOs and IAM user CRUDs before and after csm-agent is down in"
                    " all control pods")

        num_users = HA_CFG["s3_operation_data"]["no_csm_users"]

        if self.scale_req:
            LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                                deploy=self.deploy_name)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        LOGGER.info("Adding %s delay in config files of all control pods",
                    self.max_proc_restart_delay)
        self.add_proc_restart_delay(self.max_proc_restart_delay)
        LOGGER.info("Successfully added %s delay in config files of all control pods",
                    self.max_proc_restart_delay)
        self.change_proc_delay = True

        LOGGER.info("Step 1: Perform WRITE-READ-Verify on user %s", self.uids[0])
        self.test_prefix = 'test-45499'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Create %s iam users for deletion", num_users)
        del_users = self.mgnt_ops.create_account_users(nusers=num_users)

        LOGGER.info("Step 2: Create soft failures and perform IAM user CRUDs")
        for pod in self.ctrl_pod_list:
            LOGGER.info("Step 2.1: Create soft failure on pod %s", pod)
            resp = self.node_master_list[0].kill_process_in_container(
                pod_name=pod, container_name=self.container_name, pid=self.pid, safe_kill=True)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Step 2.1: Created soft failure")
            LOGGER.info("Step 2.2: Create an IAM user")
            user = self.ha_obj.create_iam_user_with_header(num_users=1, header=self.header)
            LOGGER.debug("Created user: %s", user)
            if pod == self.ctrl_pod_list[-1]:
                assert_utils.assert_equal(user, None, "Expected failure in IAM user creation")
                LOGGER.info("Step 2.2: Failed IAM user creation as expected")
            else:
                assert_utils.assert_not_equal(user, None, "Expected successful IAM user creation")
                self.s3_clean.update(user)
                self.uids.append(user[list(user.keys())[0]]["user_name"])
                LOGGER.info("Step 2.2: Successfully created IAM user")
            d_user = del_users.pop(list(del_users.keys())[0])
            LOGGER.info("Step 2.3: Delete iam user %s", d_user["user_name"])
            d_user_dict = {d_user["user_name"]: d_user}
            resp = self.ha_obj.delete_iam_user_with_header(user=d_user_dict, header=self.header)
            if pod == self.ctrl_pod_list[-1]:
                assert_utils.assert_false(resp[0], "Expected failure in IAM user deletion")
                LOGGER.info("Step 2.3: Failed IAM user deletion as expected")
                self.uids.append(d_user["user_name"])
                self.s3_clean.update(d_user_dict)
            else:
                assert_utils.assert_true(resp[0], "Expected successful IAM user deletion")
                LOGGER.info("Step 2.3: Successfully deleted IAM user")

            LOGGER.info("Step 2.4: Verify if %s IAM users are persistent across control pod "
                        "soft failures", self.uids)
            for user in self.uids:
                resp = self.rest_iam_user.get_iam_user(user)
                assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                          f"Couldn't find user {user} after control pod "
                                          "failover")
                LOGGER.info("Step 2.4: User %s is persistent: %s", user, resp)
        LOGGER.info("Step 2: Created soft failures and performed IAM user CRUDs")

        LOGGER.info("Step 3: Checking cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster status should be bad as control pods are in failed state")

        LOGGER.info("Step 4: Perform WRITE-READ-Verify on user %s", self.uids[0])
        self.test_prefix = 'test-45499-new'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=5, nclients=5,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Waiting for %s time for all control pod containers to start",
                    self.max_proc_restart_delay)
        time.sleep(self.max_proc_restart_delay)

        LOGGER.info("Step 5: Checking cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Cluster status is good")

        LOGGER.info("Step 6: Create multiple IAM user after soft-failure.")
        new_user = self.mgnt_ops.create_account_users()
        new_users_list = list(new_user.keys())
        resp = self.csm_obj.list_iam_users_rgw()
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "List IAM user failed.")
        user_data_new = resp.json()
        fetched_users = user_data_new['users']
        assert_utils.assert_true(
            (set(new_users_list).issubset(set(fetched_users)),
             "Failed to create IAM users after soft-failure"))
        self.s3_clean.update(new_user)
        LOGGER.info("Step 6: Created multiple IAM user after soft-failure.")

        LOGGER.info("ENDED: Test IOs and IAM user CRUDs before and after csm-agent is down in all "
                    "control pods")

    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45500")
    def test_iam_cruds_ios_during_soft_failure_all_pods(self):
        """
        Test IOs and IAM user CRUDs during soft failures in all control pods (Negative Scenario)
        """
        LOGGER.info("STARTED: Test IOs and IAM user CRUDs during soft failures in all control pods"
                    " (Negative Scenario)")

        event = threading.Event()
        iam_output = Queue()
        bkt_output = Queue()
        num_users = HA_CFG["s3_operation_data"]["iam_users"]
        num_bkts = HA_CFG["s3_operation_data"]["no_bkt_del_ctrl_pod"]
        if self.scale_req:
            LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                                deploy=self.deploy_name)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        LOGGER.info("Adding %s delay in config files of all control pods",
                    self.min_proc_restart_delay)
        self.add_proc_restart_delay(self.min_proc_restart_delay)
        LOGGER.info("Successfully added %s delay in config files of all control pods",
                    self.min_proc_restart_delay)
        self.change_proc_delay = True

        LOGGER.info("Step 1: Perform WRITE-READ-Verify on user %s", self.uids[0])
        self.test_prefix = 'test-45500'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Create %s iam users for deletion", num_users)
        del_users = self.mgnt_ops.create_account_users(nusers=num_users)

        LOGGER.info("Step 2: Perform IAM user and bucket creation/deletion in background")
        LOGGER.info("Step 2.1: Starting IAM CRUDs in background")
        args = {'user_crud': True, 'num_users': num_users, 'output': iam_output,
                'del_users_dict': del_users, 'header': self.header}
        thread1 = threading.Thread(target=self.ha_obj.iam_bucket_cruds, args=(event,), kwargs=args)
        thread1.daemon = True  # Daemonize thread

        LOGGER.info("Step 2.2: Starting bucket CRUDs in background")
        args = {'user_crud': False, 'bkt_crud': True, 'num_bkts': num_bkts, 's3_obj': self.s3_obj,
                'output': bkt_output}
        thread2 = threading.Thread(target=self.ha_obj.iam_bucket_cruds, args=(event,), kwargs=args)
        thread2.daemon = True  # Daemonize thread
        thread1.start()
        thread2.start()
        LOGGER.info("Step 2: Successfully started IAM user and bucket creation/deletion in "
                    "background")
        LOGGER.info("Waiting for %s sec for background operations to start",
                    HA_CFG["common_params"]["10sec_delay"])
        time.sleep(HA_CFG["common_params"]["10sec_delay"])

        LOGGER.info("Step 3: Create soft failures")
        event.set()
        for pod in self.ctrl_pod_list:
            LOGGER.info("Creating soft failure on pod %s", pod)
            resp = self.node_master_list[0].kill_process_in_container(
                pod_name=pod, container_name=self.container_name, pid=self.pid, safe_kill=True)
            LOGGER.info("Response: %s", resp)
        LOGGER.info("Step 3: Created soft failures")

        LOGGER.info("Waiting for %s time for all control pod containers to start",
                    self.min_proc_restart_delay)
        time.sleep(self.min_proc_restart_delay)
        event.clear()

        LOGGER.info("Waiting for threads to join")
        thread1.join()
        thread2.join()

        LOGGER.info("Step 4: Checking cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Cluster status is good")

        LOGGER.info("Step 5: Verifying responses from background processes")
        LOGGER.info("Checking background process for IAM user CRUDs")
        iam_resp = tuple()
        while len(iam_resp) != 4:
            iam_resp = iam_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not iam_resp:
            assert_utils.assert_true(False, "Background process failed to do IAM user CRUD "
                                            "operations")
        exp_fail = iam_resp[0]
        failed = iam_resp[1]
        user_del_failed = iam_resp[2]
        created_users = iam_resp[3]
        if failed:
            assert_utils.assert_true(False, "Failures observed in background process for IAM "
                                            "user CRUD operations before and after soft failures. "
                                            f"\nFailed users: {failed}")
        elif exp_fail:
            LOGGER.info("In-Flight IAM user creation/deletion failed for users: %s", exp_fail)
            LOGGER.info("In-Flight IAM user deletion failed for users: %s", user_del_failed)
            for i_i in user_del_failed:
                self.s3_clean.update({i_i: del_users[i_i]})
                self.uids.append(del_users[i_i]["user_name"])
        else:
            assert_utils.assert_true(False, "Some IAM user CRUD operations are expected to be "
                                            "failed during control pod soft failures")

        assert_utils.assert_true(len(created_users), "Few IAM user creation is expected during "
                                                     "soft failures in loop")
        for i_i in created_users:
            self.s3_clean.update(i_i)
            self.uids.append(list(i_i.keys())[0])

        LOGGER.info("Checking background process for bucket CRUD operations")
        bkt_resp = tuple()
        while len(bkt_resp) != 2:
            bkt_resp = bkt_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not bkt_resp:
            assert_utils.assert_true(False, "Background process failed to do bucket CRUD "
                                            "operations")
        exp_fail = bkt_resp[0]
        failed = bkt_resp[1]
        assert_utils.assert_false(len(exp_fail) or len(failed),
                                  "Failures observed in background process for bucket "
                                  f"CRUD operations. \nIn-flight Failed buckets: {exp_fail}"
                                  f"\nFailed buckets: {failed}")
        LOGGER.info("Step 5: Successfully verified responses from background processes")

        LOGGER.info("Step 6: Verify if IAM users %s are persistent across control pods restart",
                    self.uids)
        for user in self.uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pods restart")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 6: Verified all IAM users %s are persistent across control pods "
                    "restart", self.uids)

        LOGGER.info("Step 7: Create multiple IAM user after soft-failure.")
        new_user = self.mgnt_ops.create_account_users()
        new_users_list = list(new_user.keys())
        resp = self.csm_obj.list_iam_users_rgw()
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "List IAM user failed.")
        user_data_new = resp.json()
        fetched_users = user_data_new['users']
        assert_utils.assert_true(
            (set(new_users_list).issubset(set(fetched_users)),
             "Failed to create IAM users after soft-failure"))
        self.s3_clean.update(new_user)
        LOGGER.info("Step 7: Created multiple IAM user after soft-failure.")

        LOGGER.info("ENDED: Test IOs and IAM user CRUDs during soft failures in all control pods"
                    " (Negative Scenario)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45501")
    def test_iam_cruds_bfr_aftr_soft_failure(self):
        """
        Verify IAM user creation and IOs before and after soft-failures
        """
        LOGGER.info("STARTED: Verify IAM user creation & IOs before and after soft-failures.")

        LOGGER.info("Step 1: Perform IOs before soft-failure.")
        self.test_prefix = 'test-45501'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.s3_clean.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed IOs before soft-failure.")

        LOGGER.info("Step 2: Perform soft-failure of control pod and check cluster status.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        pod_name = self.system_random.sample(pod_list, 1)[0]
        self.node_master_list[0].kill_process_in_container(pod_name=pod_name,
                                                           container_name=const.CORTX_CSM_POD,
                                                           process_name=const.CSM_AGENT_PRC,
                                                           safe_kill=True, pid=self.pid)
        LOGGER.info("Waiting for %s sec for successful container restart",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 2.1: Check cluster is online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2.1: Verified cluster is online.")
        LOGGER.info("Step 2: Performed soft-failure of control pod & checked cluster is online.")

        LOGGER.info("Step 3: Perform IOs on already created buckets.")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.s3_clean.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    setup_s3bench=False, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed IOs on already created buckets.")

        LOGGER.info("Step 4: Create multiple IAM user after soft-failure.")
        users = self.mgnt_ops.create_account_users()
        new_users_list = list(users.keys())
        resp = self.csm_obj.list_iam_users_rgw()
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "List IAM user failed.")
        user_data_new = resp.json()
        fetched_users = user_data_new['users']
        assert_utils.assert_true(
            (set(new_users_list).issubset(set(fetched_users)),
             "Failed to create IAM users after soft-failure"))
        self.s3_clean.update(users)
        LOGGER.info("Step 4: Created multiple IAM user after soft-failure.")
        LOGGER.info("ENDED: Verify IAM user creation & IOs before and after soft-failures.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-45502")
    def test_iam_cruds_during_soft_failure_random_n_pods(self):
        """
        Verify IAM user creation/deletion and get IAM user list while soft-failure in loop.
        """
        LOGGER.info("STARTED: Verify IAM user creation/deletion and get IAM user list while "
                    "soft-failure in loop.")
        LOGGER.info("Precondition: Create %s iam users for deletion", self.num_users)
        del_users = self.mgnt_ops.create_account_users(nusers=self.num_users)

        if self.scale_req:
            LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                                deploy=self.deploy_name)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        LOGGER.info("Step 1: Create multiple IAM users.")
        new_users = self.mgnt_ops.create_account_users()
        new_users_list = list(new_users.keys())
        LOGGER.info("Step 1: Created multiple IAM users.")

        LOGGER.info("Step 2: Start IAM user CRUD operations while performing soft failure on "
                    "random control pods in loop. Verify existing IAM users persist.")
        LOGGER.info("Get the list of control pods")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)

        iam_output = Queue()
        event = threading.Event()
        args = {'user_crud': True, 'num_users': self.num_users,
                'output': iam_output, 'del_users_dict': del_users, 'header': self.header}
        thr_iam = threading.Thread(target=self.ha_obj.iam_bucket_cruds,
                                   args=(event,), kwargs=args)
        thr_iam.daemon = True  # Daemonize thread
        LOGGER.info("Starting background threads for IAM user creation/deletion.")
        thr_iam.start()
        for failure in range(HA_CFG["common_params"]["short_loop"]):
            pod = self.system_random.choice(pod_list)
            LOGGER.info("Creating soft failure of %s for % loop", pod, failure)
            self.node_master_list[0].kill_process_in_container(pod_name=pod,
                                                               container_name=const.CORTX_CSM_POD,
                                                               process_name=const.CSM_AGENT_PRC,
                                                               safe_kill=True, pid=self.pid)
            LOGGER.info("Step 2.1: Check cluster has failures.")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 2.1: Checked cluster has failures.")
        LOGGER.info("Step 2: Started IAM user CRUD operations while performing soft failure on "
                    "random control pods in loop. Verified existing IAM users persisted.")

        LOGGER.info("Waiting for %s sec for successful container restart",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        event.clear()
        LOGGER.info("Step 3: Check cluster status is online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster status is online.")

        LOGGER.info("Step 4: Verify background process for IAM user creation/deletion")
        LOGGER.info("Waiting for background threads to join")
        thr_iam.join()
        iam_resp = tuple()
        while len(iam_resp) != 4:
            iam_resp = iam_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not iam_resp:
            assert_utils.assert_true(False, "Background process failed to do IAM user "
                                            "creation/deletion operations")
        failed = iam_resp[1]
        exp_failed = iam_resp[0]
        user_del_failed = iam_resp[2]
        created_users = iam_resp[3]
        if failed:
            assert_utils.assert_true(False, "Failures observed in background process for IAM "
                                            "user CRUD operations before and after soft failures. "
                                            f"\nFailed users: {failed}")
        elif exp_failed:
            LOGGER.info("In-Flight IAM user creation/deletion failed for users: %s", exp_failed)
            LOGGER.info("In-Flight IAM user deletion failed for users: %s", user_del_failed)
            for i_i in user_del_failed:
                self.s3_clean.update({i_i: del_users[i_i]})
        else:
            assert_utils.assert_true(False, "Some IAM user CRUD operations are expected to be "
                                            "failed during control pod soft failures")

        assert_utils.assert_true(len(created_users), "Few IAM user creation is expected during "
                                                     "soft failures in loop")
        for i_i in created_users:
            self.s3_clean.update(i_i)
        LOGGER.info("Step 4: Verified background process for IAM user creation/deletion")

        LOGGER.info("Step 5: Get IAM user list and check created IAM users are persistent.")
        resp = self.csm_obj.list_iam_users_rgw()
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "List IAM user failed.")
        user_data_new = resp.json()
        fetched_users = user_data_new['users']
        assert_utils.assert_true(
            (set(new_users_list).issubset(set(fetched_users)),
             "Created IAM user list is not persisted in fetched IAM user list"))
        self.s3_clean.update(new_users)
        LOGGER.info("Step 5: Got IAM user list & checked created IAM users are persisted.")

        LOGGER.info("Step 6: Create IAM user after soft-failure.")
        users = self.mgnt_ops.create_account_users()
        new_users_list = list(users.keys())
        resp = self.csm_obj.list_iam_users_rgw()
        assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "List IAM user failed.")
        user_data_new = resp.json()
        fetched_users = user_data_new['users']
        assert_utils.assert_true(
            (set(new_users_list).issubset(set(fetched_users)),
             "Failed to create IAM users after soft-failure"))
        self.s3_clean.update(users)
        LOGGER.info("Step 6: Created IAM user after soft-failure.")
        LOGGER.info("ENDED: Verify IAM user creation/deletion and get IAM user list while "
                    "soft-failure in loop.")
