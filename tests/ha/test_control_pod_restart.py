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
HA test suite for Control Pod Restart
"""

import logging
import os
import random
import secrets
import threading
import time
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import constants as const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
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
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=R0904
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
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
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
        self.restore_node = False
        self.deploy = False
        self.s3_clean = dict()
        self.restore_pod = None
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
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
        if self.restore_pod:
            LOGGER.info("Restoring control pod to its original state using yaml file %s",
                        self.original_backup)
            control_pod_name = self.node_master_list[0].get_all_pods(
                const.CONTROL_POD_NAME_PREFIX)[0]
            pod_yaml = {control_pod_name: self.original_backup}
            resp = self.ha_obj.failover_pod(pod_obj=self.node_master_list[0], pod_yaml=pod_yaml,
                                            failover_node=self.original_control_node)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], "Failed to restore control pod to original state")
            LOGGER.info("Successfully restored control pod to original state")
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
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32459")
    @CTFailOn(error_handler)
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
        self.restore_node = self.deploy = True

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
            assert_utils.assert_equal(resp.status_code, const.Rest.SUCCESS_STATUS,
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
    @CTFailOn(error_handler)
    def test_failover_control_pod_kubectl(self):
        """
        Verify IOs before and after control pod fails over, verify control pod failover. (using
        kubectl command)
        """
        LOGGER.info("STARTED: Verify IOs before and after control pod fails over, verify control "
                    "pod failover. (using kubectl command)")

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

        self.restore_pod = True
        LOGGER.info("Step 3: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(resp.status_code, const.Rest.SUCCESS_STATUS,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 3: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Step 4: Perform READ-Verify-DELETE on already written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed READ-Verify-DELETE on already written data")

        LOGGER.info("Step 5: Create new IAM user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40369-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("ENDED: Verify IOs before and after control pod fails over, verify control "
                    "pod failover. (using kubectl command)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40370")
    @CTFailOn(error_handler)
    def test_rd_wr_del_during_ctrl_pod_failover(self):
        """
        Verify READs, WRITEs and DELETEs during control pod failover.
        """
        LOGGER.info("STARTED: Verify READs, WRITEs and DELETEs during control pod failover.")

        event = threading.Event()  # Event to be used to send when data pods going down
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
        test_prefix_del = 'test-delete-40370'
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
        test_prefix_read = 'test-read-40370'
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
        test_prefix_write = 'test-write-40370'
        args = {'s3userinfo': list(users.values())[1], 'log_prefix': test_prefix_write,
                'nclients': 5, 'nsamples': 50, 'skipread': True, 'skipcleanup': True,
                'output': wr_output}
        thread_wr = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_wr.daemon = True  # Daemonize thread
        thread_wr.start()
        LOGGER.info("Step 4: Successfully started WRITEs with variable sizes objects in background")
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
        self.restore_pod = True
        LOGGER.info("Step 7: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(resp.status_code, const.Rest.SUCCESS_STATUS,
                                      f"Couldn't find user {user} after control pod failover")
            LOGGER.info("User %s is persistent: %s", user, resp)
        LOGGER.info("Step 7: Verified all IAM users %s are persistent across control pod "
                    "failover", uids)

        LOGGER.info("Waiting for background IOs thread to join")
        thread_wr.join()
        thread_rd.join()
        thread_del.join()
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
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
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
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8.3: Verified status for In-flight READs/Verify DI during control pod"
                    " failover to %s", failover_node)
        LOGGER.info("Step 8: Verified status for In-flight READs/WRITEs/DELETEs during control "
                    "pod failover to %s", failover_node)

        LOGGER.info("ENDED: Verify READs, WRITEs and DELETEs during control pod failover.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40375")
    @CTFailOn(error_handler)
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

        self.restore_pod = True
        LOGGER.info("Step 3: Verify if IAM users %s are persistent across control pod failover",
                    uids)
        for user in uids:
            resp = self.rest_iam_user.get_iam_user(user)
            assert_utils.assert_equal(resp.status_code, const.Rest.SUCCESS_STATUS,
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

        LOGGER.info("Step 5: Create new bucket and multipart upload and then download 5GB object")
        bucket_name = "mp-bkt-{}".format(self.random_time)
        object_name = "mp-obj-{}".format(self.random_time)
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
        LOGGER.info("Step 5: Successfully created bucket and did multipart upload and download "
                    "with 5GB object")

        LOGGER.info("ENDED: Verify multipart upload before and after control pod failover")
