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
from time import perf_counter_ns

import pytest

from commons import commands as cmd
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.di.di_mgmt_ops import ManagementOPs
from libs.dtm.dtm_recovery import DTMRecoveryTestLib
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib
from libs.csm.csm_interface import csm_api_factory

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
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = cls.random_time = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_node = cls.deploy = cls.restore_pod = None
        cls.repl_num = cls.res_taint = cls.user_list = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()
        cls.rest_iam_user = RestIamUser()
        cls.csm_obj = csm_api_factory("rest")

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
                cls.host_master_list.append(cls.host)
                cls.node_master_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))
                cls.hlth_master_list.append(Health(hostname=cls.host,
                                                   username=cls.username[node],
                                                   password=cls.password[node]))
            else:
                cls.host_worker_list.append(cls.host)
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.test_file = "ha-test-file"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HAControlPod")
        cls.ctrl_pods = cls.node_master_list[0].get_all_pods(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        cls.container_name = cls.node_master_list[0].get_all_pods_containers(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[cls.ctrl_pods[0]][0]

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restore_node = False
        self.deploy = False
        self.res_taint = False
        self.s3_clean = dict()
        self.user_list = list()
        self.restore_pod = None
        self.ctrl_pod_list = list()
        self.change_proc_delay = False
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = f"ha_s3acc_{self.random_time}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{self.random_time}"
        self.object_name = f"ha-mp-obj-{self.random_time}"
        if not os.path.exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Create IAM user")
        self.users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = self.users
        self.uids = list(self.users.keys())
        self.access_key = list(self.users.values())[0]['accesskey']
        self.secret_key = list(self.users.values())[0]['secretkey']
        self.s3_obj = S3TestLib(access_key=self.access_key, secret_key=self.secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        self.header = self.csm_obj.get_headers(self.csm_user, self.csm_passwd)
        LOGGER.info("Successfully created IAM user")
        self.dtm_obj = DTMRecoveryTestLib(self.access_key, self.secret_key, max_attempts=0)
        self.repl_num = int(len(self.node_worker_list) / 2 + 1)
        LOGGER.info("Number of replicas can be scaled for this cluster are: %s", self.repl_num)
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
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Revert back to default single control pod per cluster if more replicas are "
                    "created.")
        if len(self.ctrl_pod_list) > 1:
            resp = self.node_master_list[0].create_pod_replicas(
                num_replica=1, deploy=const.CONTROL_POD_NAME_PREFIX)
            assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Changing control pod process delay to 0")
        self.add_proc_restart_delay()
        LOGGER.info("Changed control pod process delay to 0")

        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")

        LOGGER.info("Removing extra files")
        # sysutils.remove_file(self.modified_yaml)
        # self.node_master_list[0].remove_remote_file(self.modified_yaml)
        # self.node_master_list[0].remove_remote_file(self.backup_yaml)
        sysutils.remove_dirs(self.test_dir_path)
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
        Helper function to kill pid based on process name
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

        proc_restart_delay = HA_CFG["common_params"]["control_proc_restart_delay"]
        num_users = HA_CFG["s3_operation_data"]["no_csm_users"]
        LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                            deploy=const.CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        LOGGER.info("Adding %s delay in config files of all control pods", proc_restart_delay)
        self.add_proc_restart_delay(proc_restart_delay)
        LOGGER.info("Successfully added %s delay in config files of all control pods",
                    proc_restart_delay)
        self.change_proc_delay = True

        LOGGER.info("Step 1: Perform WRITE-READ-Verify on user %s", self.uids[0])
        self.test_prefix = 'test-45499'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Create %s iam users for deletion", num_users)
        del_users = self.mgnt_ops.create_account_users(nusers=num_users)

        LOGGER.info("Step 2: Create soft failures and perform IAM user creation")
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
        LOGGER.info("Step 2: Created soft failures and performed IAM user creation")

        LOGGER.info("Step 3: Checking cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 3: Cluster status should be bad as control pods are in failed state")

        LOGGER.info("Step 4: Perform WRITE-READ-Verify on user %s", self.uids[0])
        self.test_prefix = 'test-45499-new'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Waiting for %s time for all control pod containers to start",
                    proc_restart_delay)
        time.sleep(proc_restart_delay)

        LOGGER.info("Step 5: Checking cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=60)
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Step 5: Cluster status is good")

        LOGGER.info("Step 6: Create new IAM user and perform IOs")
        self.test_prefix = f'test-45499-1'
        new_user = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = new_user
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(new_user.values())[0],
                                                    log_prefix=self.test_prefix, nclients=2,
                                                    nsamples=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Created new IAM user and performed IOs")

        LOGGER.info("ENDED: Test IOs and IAM user CRUDs before and after csm-agent is down in all "
                    "control pods")

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
        proc_restart_delay = HA_CFG["common_params"]["min_control_proc_restart_delay"]
        LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                            deploy=const.CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)

        LOGGER.info("Adding %s delay in config files of all control pods", proc_restart_delay)
        self.add_proc_restart_delay(proc_restart_delay)
        LOGGER.info("Successfully added %s delay in config files of all control pods",
                    proc_restart_delay)
        self.change_proc_delay = True

        LOGGER.info("Step 1: Perform WRITE-READ-Verify on user %s", self.uids[0])
        self.test_prefix = 'test-45500'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(self.users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Create %s iam users for deletion", num_users)
        del_users = self.mgnt_ops.create_account_users(nusers=num_users)

        LOGGER.info("Step 2: Perform IAM user creation/deletion in background")
        args = {'user_crud': True, 'bkt_crud': False, 'num_users': num_users, 's3_obj': self.s3_obj,
                'output': iam_output, 'del_users_dict': del_users, 'header': self.header}
        thread1 = threading.Thread(target=self.ha_obj.iam_bucket_cruds, args=(event,), kwargs=args)
        thread1.daemon = True  # Daemonize thread

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
                    proc_restart_delay)
        time.sleep(proc_restart_delay)
        event.clear()

        LOGGER.info("Waiting for threads to join")
        thread1.join()
        thread2.join()

        LOGGER.info("Step 4: Checking cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
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
                                            f"user CRUD operations. \nFailed buckets: {failed}")
        elif exp_fail:
            LOGGER.info("In-Flight IAM user creation/deletion failed for users: %s", exp_fail)
            LOGGER.info("In-Flight IAM user deletion failed for users: %s", user_del_failed)
            for i_i in user_del_failed:
                self.s3_clean.update({i_i: del_users[i_i]})
                self.uids.append(del_users[i_i]["user_name"])
        else:
            assert_utils.assert_true(False, "IAM user CRUD operations are expected to be failed "
                                            "during control pod soft failures")

        assert_utils.assert_true(len(created_users), f"Few IAM user creation is expected during "
                                                     f"soft failures in loop")
        for i_i in created_users:
            self.s3_clean.update({i_i})
            self.uids.append(i_i["user_name"])

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

        LOGGER.info("Step 7: Create new IAM user and perform IOs")
        self.test_prefix = f'test-45500-1'
        new_user = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = new_user
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(new_user.values())[0],
                                                    log_prefix=self.test_prefix, nclients=2,
                                                    nsamples=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Created new IAM user and performed IOs")

        LOGGER.info("ENDED: Test IOs and IAM user CRUDs during soft failures in all control pods"
                    " (Negative Scenario)")
