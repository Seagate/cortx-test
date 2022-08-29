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

from commons import constants as const
from commons import commands as cmd
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
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestControlPodRestart:
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
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestData")
        control_pods = cls.node_master_list[0].get_pods_node_fqdn(const.CONTROL_POD_NAME_PREFIX)
        ctrl_pod = list(control_pods.keys())[0]
        backup_path = cls.node_master_list[0].backup_deployment(
            deployment_name=cls.node_master_list[0].get_deploy_replicaset(ctrl_pod)[1])[1]
        cls.original_backup = backup_path.split(".")[0] + "_original.yaml"
        cls.node_master_list[0].rename_file(old_filename=backup_path,
                                            new_filename=cls.original_backup)
        cls.original_control_node = control_pods.get(ctrl_pod)

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
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = f"ha_s3acc_{self.random_time}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{self.random_time}"
        self.object_name = f"ha-mp-obj-{self.random_time}"
        if not os.path.exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Updating control pod deployment yaml")
        self.control_pods = self.node_master_list[0].get_pods_node_fqdn(
            const.CONTROL_POD_NAME_PREFIX)
        self.control_pod_name = list(self.control_pods.keys())[0]
        self.control_node = self.control_pods.get(self.control_pod_name)
        resp = self.ha_obj.update_deployment_yaml(pod_obj=self.node_master_list[0],
                                                  pod_name=self.control_pod_name,
                                                  find_key="persistentVolumeClaim",
                                                  replace_key="emptyDir", replace_val=dict())
        assert_utils.assert_true(resp[0], resp)
        self.modified_yaml = resp[1]
        self.backup_yaml = resp[2]
        self.repl_num = int(len(self.node_worker_list) / 2 + 1)
        LOGGER.info("Number of replicas can be scaled for this cluster are: %s", self.repl_num)
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
        if self.res_taint:
            LOGGER.info("Untaint the node back which was tainted: %s", self.control_node)
            self.node_master_list[0].execute_cmd(cmd=cmd.K8S_UNTAINT_CTRL.format(self.control_node))
        LOGGER.info("Revert back to default single control pod per cluster if more replicas are "
                    "created.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        if len(pod_list) > 1:
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                                pod_name=pod_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        # TODO: Uncomment following code after getting confirmation from Rick on control pod
        #  restoration
        # if self.restore_pod:
            # LOGGER.info("Restoring control pod to its original state using yaml file %s",
            #             self.original_backup)
            # control_pod_name = self.node_master_list[0].get_all_pods(
            #     const.CONTROL_POD_NAME_PREFIX)[0]
            # pod_yaml = {control_pod_name: self.original_backup}
            # resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
            #                                 failover_node=self.original_control_node)
            # LOGGER.debug("Response: %s", resp)
            # assert_utils.assert_true(resp[0], "Failed to restore control pod to original state")
            # LOGGER.info("Successfully restored control pod to original state")
        if self.restore_node:
            LOGGER.info("Cleanup: Power on the %s down node.", self.control_node)
            resp = self.ha_obj.host_power_on(host=self.control_node)
            assert_utils.assert_true(resp, "Host is not powered on")
            LOGGER.info("Cleanup: %s is Power on. Sleep for %s sec for pods to join back the"
                        " node", self.control_node, HA_CFG["common_params"]["pod_joinback_time"])
            time.sleep(HA_CFG["common_params"]["pod_joinback_time"])
        # TODO: As control node is restarted, Need to redeploy cluster after every test (We may
        #  need this after control pod deployment file is changed)
        if self.deploy:
            LOGGER.info("Cleanup: Destroying the cluster ")
            resp = self.deploy_lc_obj.destroy_setup(self.node_master_list[0],
                                                    self.node_worker_list,
                                                    const.K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Cleanup: Cluster destroyed successfully")

            LOGGER.info("Cleanup: Setting prerequisite")
            self.deploy_lc_obj.execute_prereq_cortx(self.node_master_list[0],
                                                    const.K8S_SCRIPTS_PATH,
                                                    const.K8S_PRE_DISK)
            for node in self.node_worker_list:
                self.deploy_lc_obj.execute_prereq_cortx(node, const.K8S_SCRIPTS_PATH,
                                                        const.K8S_PRE_DISK)
            LOGGER.info("Cleanup: Prerequisite set successfully")

            LOGGER.info("Cleanup: Deploying the Cluster")
            resp_cls = self.deploy_lc_obj.deploy_cluster(self.node_master_list[0],
                                                         const.K8S_SCRIPTS_PATH)
            assert_utils.assert_true(resp_cls[0], resp_cls[1])
            LOGGER.info("Cleanup: Cluster deployment successfully")

        LOGGER.info("Cleanup: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")

        LOGGER.info("Removing extra files")
        sysutils.remove_file(self.modified_yaml)
        self.node_master_list[0].remove_remote_file(self.modified_yaml)
        self.node_master_list[0].remove_remote_file(self.backup_yaml)
        sysutils.remove_dirs(self.test_dir_path)
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32459")
    @pytest.mark.skip(reason="VM issue in after Restart(CORTX-32933). Need to be tested on HW")
    def test_restart_control_node(self):
        """
        Verify IOs before and after control pod fails over after restarting node hosting control
        pod.
        """
        LOGGER.info("STARTED: Verify IOs before and after control pod fails over after restarting"
                    " node hosting control pod")

        LOGGER.info("Step 1: Create IAM user and perform WRITEs-READs-Verify with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32459'
        self.s3_clean = users
        uids = list(users.keys())
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Check the node which has the control pod running and shutdown "
                    "the node.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name, self.control_node)
        LOGGER.info("Get the data and server pod running on %s node", self.control_node)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        server_pods = self.node_master_list[0].get_pods_node_fqdn(const.SERVER_POD_NAME_PREFIX)
        data_pod_name = serverpod_name = None
        for pod_name, node in data_pods.items():
            if node == self.control_node:
                data_pod_name = pod_name
                break
        for server_pod, node in server_pods.items():
            if node == self.control_node:
                serverpod_name = server_pod
                break
        LOGGER.info("%s node has data pod %s and server pod %s", self.control_node, data_pod_name,
                    serverpod_name)
        LOGGER.info("Shutdown the node: %s", self.control_node)
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=self.control_node)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where control pod was running.", self.control_node)

        LOGGER.info("Sleep for pod-eviction-timeout of %s sec", HA_CFG["common_params"][
            "pod_eviction_time"])
        time.sleep(HA_CFG["common_params"]["pod_eviction_time"])
        data_pod_list.remove(data_pod_name)
        running_pod = self.system_random.sample(data_pod_list, 1)[0]
        server_list.remove(serverpod_name)

        LOGGER.info("Step 3: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0], pod_list=data_pod_list)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data pod %s and server "
                    "pod %s", data_pod_name, serverpod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name, serverpod_name],
                                                           fail=True, hostname=hostname,
                                                           pod_name=running_pod)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on data pod %s and server "
                    "pod %s are in offline state", data_pod_name, serverpod_name)

        online_pods = data_pod_list + server_list
        LOGGER.info("Step 5: Check services status on remaining pods %s", online_pods)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=online_pods, fail=False,
                                                           pod_name=running_pod)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 6: Check for control pod failed over node.")
        control_pods_new = self.node_master_list[0].get_pods_node_fqdn(
            const.CONTROL_POD_NAME_PREFIX)
        control_pod_name_new = list(control_pods_new.keys())[0]
        node_fqdn_new = control_pods_new.get(control_pod_name_new)
        assert_utils.assert_not_equal(node_fqdn_new, self.control_node,
                                      "Control pod has not failed over to any other node.")
        LOGGER.info("Step 6: %s pod has been failed over to %s node",
                    control_pod_name_new, node_fqdn_new)

        LOGGER.info("Step 7: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 7: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 8: Perform READ-Verify-DELETE on already written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed READ-Verify-DELETE on already written data")

        LOGGER.info("Step 9: Create new IAM user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32459-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("COMPLETED: Verify IOs before and after control pod failure, "
                    "pod shutdown by making worker node down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40369")
    def test_taint_ctrl_pod_failover(self):
        """
        Verify IAM users/IOs before and after control pod fails over when tainting control node
        with no schedule option (using kubectl command)
        """
        LOGGER.info("STARTED: Verify IAM users/IOs before and after control pod fails over when "
                    "tainting control node with no schedule option (using kubectl command)")
        LOGGER.info("Step 1: Create IAM user and perform WRITEs-READs-Verify with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40369'
        self.s3_clean = users
        uids = list(users.keys())
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")
        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name, self.control_node)
        LOGGER.info("Step 2: Taint the control node %s and delete control pod %s",
                    self.control_node, self.control_pod_name)
        self.node_master_list[0].execute_cmd(cmd=cmd.K8S_TAINT_CTRL.format(self.control_node))
        self.res_taint = True
        LOGGER.info("Restart the control pod by kubectl delete.")
        resp = self.node_master_list[0].delete_pod(pod_name=self.control_pod_name, force=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to delete pod {self.control_pod_name} by "
                                          "kubectl delete")
        LOGGER.info("Step 2: Tainted the control node %s and deleted control pod %s",
                    self.control_node, self.control_pod_name)
        LOGGER.info("Sep 3: Check cluster status and new control node hosting control pod")
        delay = HA_CFG["common_params"]["60sec_delay"]
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=delay)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Cluster is in healthy state.")
        LOGGER.info("Check new control node hosting failed over control pod")
        control_pods = self.node_master_list[0].get_pods_node_fqdn(
            const.CONTROL_POD_NAME_PREFIX)
        control_pod_name = list(control_pods.keys())[0]
        control_node = control_pods.get(control_pod_name)
        assert_utils.assert_not_equal(self.control_node, control_node, "Control pod did not fail "
                                                                       "over to new node")
        LOGGER.info("Step 3: Control pod %s failed over to new node %s from old node %s",
                    control_pod_name, control_node, self.control_node)
        LOGGER.info("Step 4: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 4: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)
        LOGGER.info("Step 5: Perform READ-Verify-DELETE on already written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed READ-Verify-DELETE on already written data")
        LOGGER.info("Step 6: Create new IAM user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40369-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")
        LOGGER.info("Untaint the node back which was tainted in step 2: %s", self.control_node)
        self.node_master_list[0].execute_cmd(cmd=cmd.K8S_UNTAINT_CTRL.format(self.control_node))
        self.res_taint = False
        LOGGER.info("ENDED: Verify IAM users/IOs before and after control pod fails over when "
                    "tainting control node with no schedule option (using kubectl command)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-34827")
    def test_rd_wr_del_during_ctrl_pod_failover(self):
        """
        Verify READs, WRITEs and DELETEs during control pod failover.
        """
        LOGGER.info("STARTED: Verify READs, WRITEs and DELETEs during control pod failover.")

        event = threading.Event()  # Event to be used to send when control pod failing over
        wr_bucket = HA_CFG["s3_bucket_data"]["no_bck_background_deletes"]
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        remaining_bkt = 10
        del_bucket = wr_bucket - remaining_bkt
        users = self.mgnt_ops.create_account_users(nusers=2)
        self.s3_clean.update(users)
        uids = list(users.keys())
        del_access_key = list(users.values())[0]['accesskey']
        del_secret_key = list(users.values())[0]['secretkey']
        test_prefix_del = 'test-delete-34827'
        s3_test_obj = S3TestLib(access_key=del_access_key, secret_key=del_secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           "number of buckets")
        s3_data = wr_resp[0]
        LOGGER.info("Step 1: Successfully performed WRITEs with variable object sizes on %s "
                    "buckets for parallel DELETEs.", wr_bucket)

        LOGGER.info("Step 2: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = 'test-read-34827'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[1],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=50, nsamples=50)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Starting three independent background threads for READs, WRITEs & DELETEs.")
        LOGGER.info("Step 3: Start Continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = list(s3_data.keys())
        get_random_buck = self.system_random.sample(bucket_list, del_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 3: Successfully started DELETEs in background for %s buckets", del_bucket)

        LOGGER.info("Step 4: Perform WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-34827'
        args = {'s3userinfo': list(users.values())[1], 'log_prefix': test_prefix_write,
                'nclients': 5, 'nsamples': 50, 'skipread': True, 'skipcleanup': True,
                'output': wr_output, 'setup_s3bench': False}
        thread_wr = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_wr.daemon = True  # Daemonize thread
        thread_wr.start()
        LOGGER.info("Step 4: Successfully started WRITEs with variable sizes objects in "
                    "background")
        LOGGER.info("Waiting for %s seconds to allow s3bench installation ",
                    HA_CFG["common_params"]["20sec_delay"])
        time.sleep(HA_CFG["common_params"]["20sec_delay"])    # delay to allow s3bench installation

        LOGGER.info("Step 5: Perform READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[1], 'log_prefix': test_prefix_read,
                'nclients': 5, 'nsamples': 50, 'skipwrite': True, 'skipcleanup': True,
                'setup_s3bench': False, 'output': output_rd}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 5: Successfully started READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name, self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)

        event.set()
        LOGGER.info("Step 6: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)

        event.clear()
        self.restore_pod = self.deploy = True
        LOGGER.info("Step 7: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 7: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Waiting for background IOs thread to join")
        thread_wr.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 8: Verify status for In-flight READs/WRITEs/DELETEs during control "
                    "pod failover to %s", failover_node)
        LOGGER.info("Step 8.1: Verify status for In-flight DELETEs during control pod "
                    "failover to %s", failover_node)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        fail_del_bkt = del_resp[1]
        rem_bkts_aftr_del = s3_test_obj.bucket_list()[1]
        assert_utils.assert_false(len(fail_del_bkt),
                                  f"Bucket deletion failed when cluster was online {fail_del_bkt}")
        assert_utils.assert_equal(len(rem_bkts_aftr_del), remaining_bkt,
                                  f"{del_bucket} buckets should get deleted, only "
                                  f"{wr_bucket - len(rem_bkts_aftr_del)} were deleted")
        LOGGER.info("Step 8.1: Verified status for In-flight DELETEs during control pod "
                    "failover to %s", failover_node)

        LOGGER.info("Step 8.2: Verify status for In-flight WRITEs during control pod "
                    "failover to %s", failover_node)
        wr_resp = dict()
        while len(wr_resp) != 2:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in wr_resp["pass_res"])
        fail_logs = list(x[1] for x in wr_resp["fail_res"])
        LOGGER.debug("Logs during control pod failover: %s\nLogs after control pod failover: %s",
                     pass_logs, fail_logs)
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8.2: Verified status for In-flight WRITEs during control pod %s "
                    "failover", failover_node)

        LOGGER.info("Step 8.3: Verify status for In-flight READs/Verify DI during control pod "
                    "failover to %s", failover_node)
        rd_resp = dict()
        while len(rd_resp) != 2:
            rd_resp = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in rd_resp["pass_res"])
        fail_logs = list(x[1] for x in rd_resp["fail_res"])
        LOGGER.debug("Logs during control pod failover: %s\nLogs after control pod failover: %s",
                     pass_logs, fail_logs)
        all_logs = pass_logs + fail_logs
        resp = self.ha_obj.check_s3bench_log(file_paths=all_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8.3: Verified status for In-flight READs/Verify DI during control pod"
                    " failover to %s", failover_node)
        LOGGER.info("Step 8: Verified status for In-flight READs/WRITEs/DELETEs during control "
                    "pod failover to %s", failover_node)

        LOGGER.info("ENDED: Verify READs, WRITEs and DELETEs during control pod failover.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40375")
    def test_mpu_after_ctrl_pod_failover(self):
        """
        Verify multipart upload before and after control pod failover.
        """
        LOGGER.info("STARTED: Verify multipart upload before and after control pod failover")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 1: Create and list buckets and perform multipart upload for size 5GB.")
        LOGGER.info("Creating IAM user...")
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        uids = [self.s3acc_name]
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=self.bucket_name,
                                                         object_name=self.object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 1: Successfully performed multipart upload for size 5GB.")

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name, self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)

        LOGGER.info("Step 2: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)

        self.restore_pod = self.deploy = True
        LOGGER.info("Step 3: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 3: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 4: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 4: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        sysutils.remove_file(self.multipart_obj_path)
        sysutils.remove_file(download_path)

        LOGGER.info("Step 5: Create new bucket and do multipart upload and download 5GB object")
        bucket_name = f"mp-bkt-{self.random_time}"
        object_name = f"mp-obj-{self.random_time}"
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        upload_checksum1 = resp[2]
        result = s3_test_obj.object_info(bucket_name, object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)

        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum1 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum1, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum1},"
                                  f" {download_checksum1}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum1, download_checksum1)
        LOGGER.info("Step 5: Successfully created bucket, did multipart upload and downloaded "
                    "5GB object")

        LOGGER.info("Step 6: Create new user and perform multipart upload and download for size "
                    "5GB.")
        LOGGER.info("Step 6.1: Creating IAM user...")
        users = self.mgnt_ops.create_account_users(nusers=1)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        user_name = list(users.values())[0]['user_name']
        self.s3_clean.update(users)
        new_user = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                               'user_name': user_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        bucket_name = f"new-bkt-{self.random_time}"
        object_name = f"new_obj_{self.random_time}"
        LOGGER.info("Step 6.1: Successfully created IAM user")
        LOGGER.info("Step 6.2: Perform multipart upload for size 5GB.")
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=new_user,
                                                         bucket_name=bucket_name,
                                                         object_name=object_name,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(bucket_name, object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", object_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum2 = str(resp[2])
        LOGGER.info("Step 6.2: Successfully performed multipart upload for size 5GB.")
        LOGGER.info("Step 6.3: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(bucket_name, object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum2 = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                              compare=False)[0]
        assert_utils.assert_equal(upload_checksum1, download_checksum1,
                                  f"Failed to match checksum: {upload_checksum1},"
                                  f" {download_checksum1}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum2, download_checksum2)
        LOGGER.info("Step 6.3: Successfully downloaded the uploaded object and verify checksum")
        LOGGER.info("Step 6: Successfully created new user, created bucket, did multipart upload "
                    "and downloaded 5GB object")

        LOGGER.info("ENDED: Verify multipart upload before and after control pod failover")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40387")
    def test_ctrl_pod_shutdown_loop(self):
        """
        Verify N-1 control pods shutdown in loop
        """
        LOGGER.info("STARTED: Verify N-1 control pods shutdown in loop")
        num_users = HA_CFG["s3_operation_data"]["no_csm_users"]
        LOGGER.info("Scale replicas for control pod to %s", self.repl_num)
        pod_name = self.node_master_list[0].get_all_pods(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[0]
        resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                            pod_name=pod_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Total number of control pods in the cluster are: %s", self.repl_num)
        LOGGER.info("Step 1: Create %s IAM user and perform WRITEs-READs-Verify with "
                    "variable object sizes.", num_users)
        users = self.mgnt_ops.create_account_users(nusers=num_users)
        self.s3_clean = users
        uids = list(users.keys())
        for count in range(num_users):
            self.test_prefix = f'test-40387-{count}'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[count],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects for %s IAM "
                    "users created.", num_users)
        LOGGER.info("Step 2: Shutdown %s control pods in loop", self.repl_num - 1)
        LOGGER.info("Get the list of control pods")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        pod_left = None
        for loop in range(len(pod_list)):
            LOGGER.info("Shutting down %s control pods for loop: %s", self.repl_num - 1, loop)
            delete_pods = list()
            while pod_left not in delete_pods:
                delete_pods.extend(self.system_random.sample(pod_list, self.repl_num - 1))
            for pod in delete_pods:
                resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Check cluster status")
            delay = HA_CFG["common_params"]["60sec_delay"]
            resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=delay)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Cluster status is online")
            LOGGER.info("Step 2.2: Create multiple IAM users and delete randomly selected IAM "
                        "users")
            users_loop = self.mgnt_ops.create_account_users(nusers=num_users)
            self.s3_clean = users_loop
            created_list = list(users_loop.keys())
            num = self.system_random.randint(1, num_users)
            delete_list = self.system_random.sample(created_list, num)
            for buck in range(num):
                resp = self.ha_obj.delete_s3_acc_buckets_objects(delete_list[buck])
                assert_utils.assert_true(resp[0], resp[1])
                created_list.remove(delete_list[buck])
            self.user_list.extend(created_list)
            for user in self.user_list:
                resp = self.rest_iam_user.get_iam_user(user)
                assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                          f"Couldn't find user {user}")
            LOGGER.info("Step 2.2: Created %s and randomly deleted %s IAM users and verified",
                        num_users, num)
            pod_left = self.node_master_list[0].get_all_pods(
                pod_prefix=const.CONTROL_POD_NAME_PREFIX)[0]
            LOGGER.info("Starting all shutdown pods again")
            resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                                pod_name=pod_left)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Control pods are shutdown in loop successfully.")
        LOGGER.info("Step 3: Check if users created in step 1 are persistent and Perform "
                    "READs-Verify-Deletes with variable object sizes on data written in step 1.")
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user}")
        LOGGER.info("IAM users created in step 1 are persistent.")
        LOGGER.info("Run READ-Verify-Deletes on data")
        for count in range(num_users):
            self.test_prefix = f'test-40387-{count}'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[count],
                                                        log_prefix=self.test_prefix, skipwrite=True,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: IAM users created in step 1 are persistent and Performed "
                    "READs-Verify-Deletes with variable sizes objects for data written in step 1")
        LOGGER.info("Step 4: Create New IAM user and perform WRITEs-READs-Verify-Deletes with "
                    "variable object sizes.")
        users_new = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40387-new'
        self.s3_clean = users_new
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_new.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed WRITEs-READs-Verify-Deletes with variable sizes objects")
        LOGGER.info("ENDED: Verify N-1 control pods shutdown in loop")

    # pylint: disable=too-many-branches
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40389")
    def test_iam_bkt_cruds_during_ctrl_pod_rst(self):
        """
        Verify IAM user and bucket operations while N-1 control pods are restarted
        """
        LOGGER.info("STARTED: Verify IAM user and bucket operations while N-1 control pods "
                    "are restarted")
        LOGGER.info("Prereq: Scale replicas for control pod to %s", self.repl_num)
        pod_name = self.node_master_list[0].get_all_pods(
            pod_prefix=const.CONTROL_POD_NAME_PREFIX)[0]
        resp = self.node_master_list[0].create_pod_replicas(num_replica=self.repl_num,
                                                            pod_name=pod_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Prereq: Total number of control pods in the cluster are: %s", self.repl_num)
        LOGGER.info("Get the control pod list")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.CONTROL_POD_NAME_PREFIX)
        event = threading.Event()
        iam_output = Queue()
        bkt_output = Queue()
        num_users = HA_CFG["s3_operation_data"]["iam_users"]
        num_bkts = HA_CFG["s3_operation_data"]["no_bkt_del_ctrl_pod"]
        LOGGER.info("Step 1: Create IAM user.")
        users_org = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = users_org
        uids = list(users_org.keys())
        access_key = list(users_org.values())[0]["accesskey"]
        secret_key = list(users_org.values())[0]["secretkey"]
        s3_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                           endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Step 1: Created IAM user successfully")
        LOGGER.info("Create %s iam users for deletion", num_users)
        users = self.mgnt_ops.create_account_users(nusers=num_users)
        LOGGER.info("Step 2: Perform IAM user creation/deletion in background")
        args = {'user_crud': True, 'bkt_crud': False, 'num_users': num_users, 's3_obj': s3_obj,
                'output': iam_output, 'del_users_dict': users}
        thread1 = threading.Thread(target=self.ha_obj.iam_bucket_cruds,
                                   args=(event, ), kwargs=args)
        thread1.daemon = True  # Daemonize thread
        thread1.start()
        LOGGER.info("Start buckets creation/deletion in background")
        args = {'user_crud': False, 'bkt_crud': True, 'num_bkts': num_bkts, 's3_obj': s3_obj,
                'output': bkt_output}
        thread2 = threading.Thread(target=self.ha_obj.iam_bucket_cruds,
                                   args=(event, ), kwargs=args)
        thread2.daemon = True  # Daemonize thread
        thread2.start()
        LOGGER.info("Step 2: Successfully started IAM user and bucket creation/deletion in "
                    "background")
        LOGGER.info("Waiting for %s sec for background operations to start",
                    HA_CFG["common_params"]["10sec_delay"])
        time.sleep(HA_CFG["common_params"]["10sec_delay"])
        LOGGER.info("Step 3: Restart %s control pods while creation/deletion of IAM users and "
                    "buckets is running in background.", self.repl_num - 1)
        for count in range(HA_CFG["common_params"]["short_loop"]):
            LOGGER.info("Restarting %s control pods for loop : %s", self.repl_num - 1, count + 1)
            ctrl_pod_list = self.system_random.sample(pod_list, self.repl_num - 1)
            for pod in ctrl_pod_list:
                resp = self.node_master_list[0].delete_pod(pod)
                assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3.1: Check cluster status")
            delay = HA_CFG["common_params"]["60sec_delay"]
            resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=delay)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3.1: Cluster status is online")
        LOGGER.info("%s pod are restarted successfully in loop of %s", self.repl_num - 1,
                    HA_CFG["common_params"]["short_loop"])
        event.clear()
        LOGGER.info("Waiting for threads to join")
        thread1.join()
        thread2.join()
        LOGGER.info("Step 4: Verify if IAM users %s are persistent across control pods restart",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pods restart")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 4: Verified all IAM users %s are persistent across control pods "
                    "restart", uids)
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
                self.s3_clean.update({i_i: users[i_i]})
        else:
            assert_utils.assert_true(False, "IAM user CRUD operations are expected to be failed "
                                            "during control pod failover")

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
        LOGGER.info("Step 6: Perform new IAM users(%s) and buckets(%s) creation/deletion in loop",
                    num_users, num_bkts)
        users_dict = dict()
        for i_i in created_users:
            users_dict.update(i_i)
        output = Queue()
        args = {'user_crud': True, 'bkt_crud': True, 'num_users': 10,
                'del_users_dict': users_dict, 'num_bkts': 10, 's3_obj': s3_obj,
                'output': output}
        self.ha_obj.iam_bucket_cruds(event, **args)
        LOGGER.info("Checking responses for IAM user CRUD operations")
        iam_resp = tuple()
        while len(iam_resp) != 4:
            iam_resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not iam_resp:
            assert_utils.assert_true(False, "Failed to do IAM user CRUD operations")
        exp_fail = iam_resp[0]
        failed = iam_resp[1]
        user_del_failed = iam_resp[2]
        new_created_users = iam_resp[3]
        if user_del_failed:
            for i_i in created_users:
                if list(i_i.keys())[0] in user_del_failed:
                    self.s3_clean.update(i_i)
        if new_created_users:
            for i_i in new_created_users:
                self.s3_clean.update(i_i)
        assert_utils.assert_false(len(exp_fail) or len(failed), "Failure in IAM user CRUD "
                                                                "operations. \nFailed users: "
                                                                f"\nexp_fail: {exp_fail} and "
                                                                f"\nfailed: {failed}")

        LOGGER.info("Checking responses for bucket CRUD operations")
        bkt_resp = tuple()
        while len(bkt_resp) != 2:
            bkt_resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not bkt_resp:
            assert_utils.assert_true(False, "Failed to do bucket CRUD operations")
        exp_fail = bkt_resp[0]
        failed = bkt_resp[1]
        assert_utils.assert_false(len(exp_fail) or len(failed),
                                  "Failures observed in bucket CRUD operations. "
                                  f"\nFailed buckets: \nexp_fail: {exp_fail} and "
                                  f"\nfailed: {failed}")
        LOGGER.info("Step 6: Successfully created/deleted %s new IAM users and %s buckets in loop",
                    num_users, num_bkts)
        LOGGER.info("ENDED: Verify IAM user and bucket operations while N-1 control pods "
                    "are restarted")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40377")
    def test_part_mpu_after_ctrl_pod_failover(self):
        """
        Verify partial multipart upload before and after control pod restart.
        """
        LOGGER.info("STARTED: Verify partial multipart upload before and after control "
                    "pod failover")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = self.system_random.sample(list(range(1, total_parts + 1)), total_parts // 2)
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        sysutils.create_file(self.multipart_obj_path, file_size)
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 1: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially for %s parts out of total %s", part_numbers, total_parts)
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                            endpoint_url=S3_CFG["s3_url"])
        uids = [self.s3acc_name]
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=part_numbers,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        mpu_id = resp[1]
        object_path = resp[2]
        parts_etag1 = resp[3]
        LOGGER.info("Step 1: Successfully completed partial multipart upload for %s parts out of "
                    "total %s", part_numbers, total_parts)

        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name,
                    self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)

        LOGGER.info("Step 3: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)

        self.restore_pod = self.deploy = True
        LOGGER.info("Step 4: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 4: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 5: Upload remaining parts")
        remaining_parts = list(filter(lambda i_i: i_i not in part_numbers,
                                      list(range(1, total_parts + 1))))
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=remaining_parts,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)

        assert_utils.assert_true(resp[0], f"Failed to upload remaining parts {resp[1]}")
        parts_etag2 = resp[3]
        LOGGER.info("Step 5: Successfully uploaded remaining parts")

        etag_list = parts_etag1 + parts_etag2
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])

        LOGGER.info("Step 6: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 6: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 7: Completing multipart upload and check "
                    "upload size is %s", file_size * const.Sizes.MB)
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        if self.object_name not in res[1]:
            assert_utils.assert_true(False, res)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        LOGGER.info("Step 7: Multipart upload completed and verified upload size is %s",
                    file_size * const.Sizes.MB)

        LOGGER.info("Step 8: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 8: Successfully downloaded the object and verified the checksum")

        LOGGER.info("ENDED: Verify partial multipart upload before and after control pod failover")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Functionality not available in RGW yet")
    @pytest.mark.tags("TEST-40376")
    def test_copy_obj_after_ctrl_pod_failover(self):
        """
        Verify copy object before and after control pod restart.
        """
        LOGGER.info("STARTED: Verify copy object before and after control pod restart")
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{self.random_time}"] = f"ha-obj{cnt}-{self.random_time}"
        event = threading.Event()

        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        uids = [self.s3acc_name]
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Create and list buckets and perform upload and copy "
                    "object from %s bucket to other buckets, ", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Create Bucket copy object failed with: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully create and list buckets and perform upload and copy"
                    "object from %s bucket to other buckets, ", self.bucket_name)

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name,
                    self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)

        LOGGER.info("Step 2: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)

        self.restore_pod = self.deploy = True
        LOGGER.info("Step 3: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 3: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 4: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 4: Successfully download the uploaded objects & verify etags")

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 5: Perform copy of %s from already created/uploaded %s to %s "
                    "and verify copy object etags",
                    self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict, put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        LOGGER.info("Step 5: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 6: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get"
                                                      f" Etag for object {object3} of "
                                                      f"bucket {bucket3}.")
        LOGGER.info("Step 6: Downloaded the uploaded %s on %s & verified etags.",
                    object3, bucket3)

        LOGGER.info("ENDED: Verify copy object before and after control pod restart")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40381")
    def test_mpu_during_ctrl_pod_failover(self):
        """
        This test tests multipart upload during control pod restart
        """
        LOGGER.info("STARTED: Test to verify multipart upload during control pod restart ")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts + 1))
        self.system_random.shuffle(part_numbers)
        output = Queue()
        parts_etag = list()
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        event = threading.Event()  # Event to be used to send intimation of control pod restart

        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        uids = [self.s3acc_name]
        s3_mp_test_obj = S3MultipartTestLib(access_key=access_key, secret_key=secret_key,
                                            endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size,
                'total_parts': total_parts, 'multipart_obj_path': self.multipart_obj_path,
                'part_numbers': part_numbers, 'parts_etag': parts_etag, 'output': output}
        thread = threading.Thread(target=self.ha_obj.start_random_mpu, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Started multipart upload of 5GB object in background")
        LOGGER.info("Waiting for %s seconds to perform multipart upload ",
                    HA_CFG["common_params"]["60sec_delay"])
        time.sleep(HA_CFG["common_params"]["60sec_delay"])

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name,
                    self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)
        event.set()
        LOGGER.info("Step 2: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)
        event.clear()

        self.restore_pod = self.deploy = True
        LOGGER.info("Step 3: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 3: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 4: Checking response from background process")
        thread.join()
        responses = tuple()
        while len(responses) < 4:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])

        if not responses:
            assert_utils.assert_true(False, "Background process failed to do multipart upload")

        exp_failed_parts = responses[0]
        failed_parts = responses[1]
        parts_etag = responses[2]
        mpu_id = responses[3]
        LOGGER.debug("Responses received from background process:\nexp_failed_parts: "
                     "%s\nfailed_parts: %s\nparts_etag: %s\nmpu_id: %s", exp_failed_parts,
                     failed_parts, parts_etag, mpu_id)
        assert_utils.assert_false(len(failed_parts), "Failed to upload parts before or after "
                                                     "control pod failover/restart "
                                                     f"Failed parts: {failed_parts}")
        assert_utils.assert_false(len(exp_failed_parts), "Failed to upload parts during"
                                                         "control pod failover. Failed"
                                                         f"parts {exp_failed_parts}")
        LOGGER.info("All the parts are uploaded successfully")
        LOGGER.info("Step 4: Successfully checked background process responses")

        parts_etag = sorted(parts_etag, key=lambda d: d['PartNumber'])

        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 5: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 5: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 6: Completing multipart upload and check upload size is %s",
                    file_size * const.Sizes.MB)
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res)
        result = s3_test_obj.object_info(self.bucket_name, self.object_name)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", self.bucket_name, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        LOGGER.info("Step 6: Multipart upload completed and verified upload object size is %s",
                    obj_size)

        LOGGER.info("Step 7: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 7: Successfully downloaded the object and verified the checksum")

        LOGGER.info("ENDED: Test to verify multipart upload during control pod restart ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Functionality not available in RGW yet")
    @pytest.mark.tags("TEST-40382")
    def test_copy_obj_during_ctrl_pod_failover(self):
        """
        Verify copy object during control pod restart
        """
        LOGGER.info("STARTED: Verify copy object during control pod restart ")

        bkt_obj_dict = dict()
        output = Queue()
        event = threading.Event()

        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        uids = [self.s3acc_name]
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Create bucket, upload an object to %s bucket ", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Create Bucket copy object failed with: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: Successfully created bucket, uploaded an object to the bucket")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_multi"]
        for cnt in range(bkt_cnt):
            rd_time = perf_counter_ns()
            s3_test_obj.create_bucket(f"ha-bkt{cnt}-{rd_time}")
            bkt_obj_dict[f"ha-bkt{cnt}-{rd_time}"] = f"ha-obj{cnt}-{rd_time}"
        LOGGER.info("Step 2: Create multiple buckets and copy object from %s to other buckets in "
                    "background", self.bucket_name)
        args = {'s3_test_obj': s3_test_obj, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': False,
                'put_etag': put_etag}
        thread = threading.Thread(target=self.ha_obj.create_bucket_copy_obj, args=(event,),
                                  kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started background process for copy object")
        # While loop to sync this operation with background thread to achieve expected scenario
        LOGGER.info("Waiting for creation of %s buckets", bkt_cnt)
        bkt_list = list()
        timeout = time.time() + HA_CFG["common_params"]["bucket_creation_delay"]
        while len(bkt_list) < bkt_cnt:
            time.sleep(HA_CFG["common_params"]["20sec_delay"])
            bkt_list = s3_test_obj.bucket_list()[1]
            if timeout < time.time():
                LOGGER.error("Bucket creation is taking longer than 3 mins")
                assert_utils.assert_true(False, "Please check background process logs")
        LOGGER.info("Waiting for %s seconds to perform copy object ",
                    HA_CFG["common_params"]["20sec_delay"])
        time.sleep(HA_CFG["common_params"]["20sec_delay"])

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name,
                    self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)
        event.set()
        LOGGER.info("Step 3: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)
        event.clear()

        self.restore_pod = self.deploy = True
        LOGGER.info("Step 4: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 4: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 5: Checking responses from background process")
        thread.join()
        responses = tuple()
        while len(responses) < 3:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])

        if not responses:
            assert_utils.assert_true(False, "Background process failed to do copy object")

        put_etag = responses[0]
        exp_fail_bkt_obj_dict = responses[1]
        failed_bkts = responses[2]
        LOGGER.debug("Responses received from background process:\nput_etag: "
                     "%s\nexp_fail_bkt_obj_dict: %s\nfailed_bkts: %s", put_etag,
                     exp_fail_bkt_obj_dict, failed_bkts)
        assert_utils.assert_true(len(failed_bkts) != 0, "Failed to do copy object before or after"
                                                        " control pod failover/restart"
                                                        f" Failed buckets: {failed_bkts}")
        assert_utils.assert_true(len(exp_fail_bkt_obj_dict) != 0, "Failed to do copy object when "
                                                                  "control pod restart. Failed "
                                                                  "buckets are:"
                                                                  f" {exp_fail_bkt_obj_dict}")
        LOGGER.info("Copy object operation for all the buckets completed successfully. ")
        LOGGER.info("Step 5: Successfully checked responses from background process.")

        LOGGER.info("Step 6: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {key} of bucket {val}. "
                                                          "Put and Get Etag mismatch")
        LOGGER.info("Step 6: Successfully download the uploaded objects & verify etags")

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 7: Perform copy of %s from already created/uploaded %s to %s "
                    "and verify copy object etags",
                    self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict, put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 8: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get "
                                                      f"Etag for object {object3} of "
                                                      f"bucket {bucket3}.")
        LOGGER.info("Step 8: Downloaded the uploaded %s on %s & verified etags.",
                    object3, bucket3)

        LOGGER.info("ENDED: Verify copy object during control pod restart ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40386")
    def test_chunk_upload_during_ctrl_pod_failover(self):
        """
        Test chunk upload during control pod restart (using jclient)
        """
        LOGGER.info("STARTED: Test chunk upload during control pod restart")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        download_file = "test_chunk_upload" + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        chunk_obj_path = os.path.join(self.test_dir_path, self.object_name)
        output = Queue()

        LOGGER.info("Step 1: Perform setup steps for jclient")
        jc_obj = JCloudClient()
        resp = self.ha_obj.setup_jclient(jc_obj)
        assert_utils.assert_true(resp, "Failed in setting up jclient")
        LOGGER.info("Step 1: Successfully setup jcloud/jclient on runner")

        LOGGER.info("Step 2: Create IAM user with name %s, bucket %s and start chunk upload in "
                    "background", self.s3acc_name, self.bucket_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-40386'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        uids = [self.s3acc_name]
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'file_size': file_size, 'chunk_obj_path': chunk_obj_path, 'output': output}
        thread = threading.Thread(target=self.ha_obj.create_bucket_chunk_upload, kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started chuck upload in background")
        LOGGER.info("Waiting for %s seconds to perform chunk upload ",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Control pod %s is hosted on %s node", self.control_pod_name,
                    self.control_node)

        failover_node = self.system_random.choice([ele for ele in self.host_worker_list if ele !=
                                                   self.control_node])
        LOGGER.debug("Fail over node is: %s", failover_node)

        LOGGER.info("Step 3: Failover control pod %s to node %s and check cluster status",
                    self.control_pod_name, failover_node)
        pod_yaml = {self.control_pod_name: self.modified_yaml}
        resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                        failover_node=failover_node)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Successfully failed over control pod to %s. Cluster is in good state",
                    failover_node)

        self.restore_pod = self.deploy = True
        LOGGER.info("Step 4: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(int(resp.status_code), HTTPStatus.OK.value,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 4: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 5: Verifying response of background process")
        thread.join()
        while True:
            resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            if isinstance(resp, bool):
                break

        if resp is None and not resp:
            assert_utils.assert_true(False, "Background process of chunk upload failed")
        LOGGER.info("Step 5: Successfully verified response of background process")

        LOGGER.info("Calculating checksum of file %s", chunk_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[chunk_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 6: Download object and verify checksum")
        resp = self.ha_obj.object_download_jclient(s3_data=self.s3_clean,
                                                   bucket_name=self.bucket_name,
                                                   object_name=self.object_name,
                                                   obj_download_path=download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Step 6: Successfully downloaded object and verified checksum")

        LOGGER.info("Step 7: Create IAM user, buckets and upload objects after"
                    " control pod restart ")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40386-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully completed IOs.")

        LOGGER.info("ENDED: Test chunk upload during control pod restart")
