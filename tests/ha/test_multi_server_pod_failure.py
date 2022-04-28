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
HA test suite for Multiple (K) Server Pods Failure
"""

import logging
import os
import random
import threading
import time
from multiprocessing import Queue
from time import perf_counter_ns
import pytest

from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from commons import constants as const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# 4pylint: disable=R090
class TestMultiServerPodFailure:
    """
    Test suite for Multiple Server Pods Failure
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.username = []
        cls.password = []
        cls.host_master_list = []
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.pod_name_list = []
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = cls.random_time = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.deploy = cls.kvalue = None
        cls.pod_dict = dict()
        cls.mgnt_ops = ManagementOPs()

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
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.test_file = "ha-mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
        cls.multipart_obj_path = None

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.deploy = False
        self.s3_clean = dict()
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        LOGGER.info("Get the value of K for the given cluster.")
        resp = self.ha_obj.get_config_value(self.node_master_list[0])
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            LOGGER.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        LOGGER.info("The cluster has %s parity pods", self.kvalue)
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{self.random_time}"
        self.object_name = f"ha-mp-obj-{self.random_time}"
        self.restore_pod = self.restore_method = self.deployment_name = None
        self.deployment_backup = None
        if not os.path.exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created IAM users and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if self.restore_pod:
            for pod_name in self.pod_name_list:
                if len(self.pod_dict.get(pod_name)) == 2:
                    deployment_name = self.pod_dict.get(pod_name)[1]
                    deployment_backup = None
                else:
                    deployment_name = self.pod_dict.get(pod_name)[2]
                    deployment_backup = self.pod_dict.get(pod_name)[1]
                resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                               restore_method=self.restore_method,
                                               restore_params={"deployment_name": deployment_name,
                                                               "deployment_backup":
                                                                   deployment_backup})
                LOGGER.debug("Response: %s", resp)
                assert_utils.assert_true(resp[0], "Failed to restore pod by "
                                                  "{self.restore_method} way")
                LOGGER.info("Successfully restored pod %s by %s way",
                            pod_name, self.restore_method)
        if os.path.exists(self.test_dir_path):
            sysutils.remove_dirs(self.test_dir_path)
        # TODO: As cluster restart is not supported until F22A, Need to redeploy cluster after
        #  every test
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
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")

        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40567")
    @CTFailOn(error_handler)
    def test_reads_kserver_pods_fail(self):
        """
        Test to verify degraded READs after all K server pods down - unsafe shutdown.
        """
        LOGGER.info("Started: Test to verify degraded READs after all K server pods "
                    "down - unsafe shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40567'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed READs and verified DI on the written data")

        LOGGER.info("Step 3: Shutdown %s server pod by deleting deployment (unsafe)", self.kvalue)
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)

        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list

        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = []
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name} "
                                               " by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s server pod %s by deleting deployment (unsafe)", count,
                        pod_name)
        LOGGER.info("Step 3: Successfully deleted %s server pods", self.kvalue)

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster has some failures due to %s server pods has gone down.",
                    self.kvalue)

        LOGGER.info("Step 5: Check services status that were running on server pods"
                    " which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            server_data_pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some server pods not stopped.")
        LOGGER.info("Step 5: Services of server pods are in offline state")

        LOGGER.info("Step 6: Check services status on remaining pods %s", server_data_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of remaining pods %s are in "
                    "online state", server_data_pod_list)

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("Completed: Test to verify degraded READs after all K server pods "
                    "down - unsafe shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40568")
    @CTFailOn(error_handler)
    def test_reads_till_kserver_pods_fail(self):
        """
        Test to verify degraded READs after each pod failure till K server pods "
        "down - unsafe shutdown.
        """
        LOGGER.info("Started: Test to verify degraded READs after each pod failure till K "
                    "server pods down - unsafe shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40568'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed READs and verified DI on the written data")

        LOGGER.info("Shutdown %s (K) server pods one by one and verify read/verify "
                    "after each pod down", self.kvalue)
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Step 3: Shutdown %s server pod %s by deleting deployment (unsafe)",
                        count, pod_name)
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name} "
                                               "by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Step 3: Deleted %s server pod %s by deleting deployment (unsafe)",
                        count, pod_name)

            LOGGER.info("Step 4: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 4: Cluster has some failures due to %s server pods has gone down.",
                        count)

            LOGGER.info("Step 5: Check services status that were running on server pod %s which "
                        "is deleted", pod_name)
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            assert_utils.assert_true(resp[0], resp[1])
            server_data_pod_list.remove(pod_name)
            LOGGER.info("Step 5: Services of server pod %s are in offline state", pod_name)

            LOGGER.info("Step 6: Check services status on remaining pods %s", server_data_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 6: Services of remaining pods are in online state")

            LOGGER.info("Step 7: Perform READs and verify DI on the written data")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipwrite=True, skipcleanup=True,
                                                        nsamples=2, nclients=2)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("%s (K) server pods shutdown one by one successfully and read/verify "
                    "after each pod down verified", self.kvalue)

        LOGGER.info("Completed: Test to verify degraded READs after each pod failure till K "
                    "server pods down - unsafe shutdown.")

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40573")
    @CTFailOn(error_handler)
    def test_deletes_kserver_pods_down(self):
        """
        This test tests DELETEs after all K server pods down - unsafe shutdown
        """
        LOGGER.info("STARTED: Test to verify DELETEs after %s (K) server pods down - "
                    "unsafe shutdown", self.kvalue)
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        event = threading.Event()
        wr_output = Queue()
        del_output = Queue()
        LOGGER.info("Step 1: Create %s buckets & perform WRITEs with variable size objects.",
                    wr_bucket)
        LOGGER.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name, email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-40573'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)

        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains IAM user data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           "number of buckets")
        LOGGER.info("Step 1: Successfully created %s buckets & "
                    "perform WRITEs with variable size objects.", wr_bucket)

        LOGGER.info("Step 2: Shutdown %s (K) server pods one by one by deleting deployment ("
                    "unsafe)", self.kvalue)
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Shutdown %s server pod %s by deleting deployment "
                        "(unsafe)", count, pod_name)
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name} "
                                               "by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s server pod %s by deleting deployment "
                        "(unsafe)", count, pod_name)
        LOGGER.info("Step 2: Successfully shutdown %s (K) server pods one by one by deleting "
                    "deployment (unsafe)", self.kvalue)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster has some failures due to %s server pods has gone down.",
                    self.kvalue)

        LOGGER.info("Step 4: Check services status that were running on server pods "
                    "which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            server_data_pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some server pods not stopped.")
        LOGGER.info("Step 4: Services of server pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", server_data_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Perform DELETEs on random %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        remain_bkt = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(remain_bkt), wr_bucket - del_bucket,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(remain_bkt)} number of buckets")
        LOGGER.info("Step 6: Successfully performed DELETEs on random %s buckets", del_bucket)

        LOGGER.info("Step 7: Perform READs and verify DI on the remaining %s "
                    "buckets.", remain_bkt)
        rd_output = Queue()
        new_s3data = dict()
        for bkt in remain_bkt:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = tuple()
        while len(rd_resp) != 4:
            rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_bkt_get = rd_resp[0]
        fail_bkt_get = rd_resp[1]
        event_di_bkt = rd_resp[2]
        fail_di_bkt = rd_resp[3]

        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt), "Expected pass in read and di check "
                                                     "operations. Found failures in READ: "
                                                     f"{fail_bkt_get} {event_bkt_get}"
                                                     f"or DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 7: Successfully performed READs and verify DI on the remaining "
                    "%s buckets.", remain_bkt)

        LOGGER.info("ENDED: Test to verify DELETEs after %s (K) server pods down"
                    " - unsafe shutdown.", self.kvalue)

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40578")
    @CTFailOn(error_handler)
    def test_writes_till_kserver_pods_fail(self):
        """
        Test to verify degraded WRITEs after each pod failure till K server pods
        down - unsafe shutdown.
        """
        LOGGER.info("Started: Test to verify degraded Writes after each pod failure till K "
                    "server pods down - unsafe shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40578'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Shutdown %s (K) server pods one by one and verify WRITEs  "
                    "after each server pod down on new and existing buckets", self.kvalue)
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Step 2: Shutdown %s server pod %s by deleting deployment (unsafe)",
                        count, pod_name)
            pod_data = list()
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name}"
                                               "by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Step 2: Deleted %s server pod %s by deleting deployment (unsafe)",
                        count, pod_name)

            LOGGER.info("Step 3: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 3: Cluster has some failures due to %s server pods has gone down.",
                        count)

            LOGGER.info("Step 4: Check services status that were running on server pod %s which "
                        "is deleted", pod_name)
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            assert_utils.assert_true(resp[0], resp[1])
            server_data_pod_list.remove(pod_name)
            LOGGER.info("Step 4: Services of server pod %s are in offline state", pod_name)

            LOGGER.info("Step 5: Check services status on remaining pods %s", server_data_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 5: Services of remaining pods are in online state")

            LOGGER.info("Step 6: Perform WRITEs, READs and verify DI on the already created "
                        "bucket")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Successfully performed WRITEs, READs and verify DI on "
                        "already created bucket")

            LOGGER.info("Step 7: Perform WRITEs-READs-Verify with variable object sizes.")
            users_new = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_new = f'test-40578-{count}'
            self.s3_clean.update(users_new)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users_new.values())[0],
                                                        log_prefix=test_prefix_new,
                                                        skipcleanup=True,
                                                        nsamples=2, nclients=2)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("%s (K) server pods shutdown one by one successfully and WRITEs "
                    "after each server pod down on new and existing buckets "
                    "verified", self.kvalue)

        LOGGER.info("Completed: Test to verify degraded WRITEs after each pod failure till K "
                    "server pods down - unsafe shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40579")
    @CTFailOn(error_handler)
    def test_writes_kserver_pods_failure(self):
        """
        Test to verify degraded WRITEs after all K server pods down - unsafe shutdown.
        """
        LOGGER.info("Started: Test to verify degraded WRITEs after all K server pods "
                    "down - unsafe shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40579'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the server pod by deleting deployment (unsafe)")
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            LOGGER.info("Deleting %s server pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name}"
                                               " by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s server pod %s by deleting deployment "
                        "(unsafe)", count, pod_name)
        LOGGER.info("Step 2: Successfully deleted %s server pods", self.kvalue)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster has some failures due to %s server pods has gone down.",
                    self.kvalue)

        LOGGER.info("Step 4: Check services status that were running on server pods "
                    "which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            server_data_pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some server pods not stopped.")
        LOGGER.info("Step 4: Services of server pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", server_data_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Perform WRITEs-READs-Verify and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed WRITEs-READs-Verify and verified DI on the written data")

        LOGGER.info("Step 7: Perform WRITEs-READs-Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-40579-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed WRITEs-READs-Verify with variable sizes objects ")

        LOGGER.info("Completed: Test to verify degraded WRITEs after all K server pods "
                    "down - unsafe shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-40580")
    @CTFailOn(error_handler)
    def test_deletes_till_kserver_pods_fail(self):
        """
        Test to verify degraded DELETEs after each pod failure till K server pods
        down - unsafe shutdown.
        """
        LOGGER.info("Started: Test to verify degraded Deletes after each pod failure till "
                    "K server pods down - unsafe shutdown.")
        wr_bucket = self.kvalue * 5 + HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = 20
        event = threading.Event()
        wr_output = Queue()
        del_output = Queue()
        LOGGER.info("Step 1: Create %s buckets and perform WRITEs with variable size objects.",
                    wr_bucket)
        LOGGER.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-40580'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)

        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains IAM user data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number"
                                                           f" of buckets. Created {len(buckets)} "
                                                           "number of buckets")
        LOGGER.info("Step 1: Successfully created %s buckets & "
                    "perform WRITEs with variable size objects.", wr_bucket)

        LOGGER.info("Shutdown %s (K) server pods one by one and perform Delete on random %s"
                    " buckets and verify read on remaining bucket after each server pod down",
                    self.kvalue, del_bucket)
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Step 2: Shutdown %s server pod %s by deleting deployment (unsafe)",
                        count, pod_name)
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name} "
                                               f"by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Step 2: Deleted %s server pod %s by deleting deployment (unsafe)",
                        count, pod_name)

            LOGGER.info("Step 3: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 3: Cluster has some failures due to server pod %s has "
                        "gone down.", pod_name)

            LOGGER.info("Step 4: Check services status that were running "
                        "on server pod %s which is deleted", pod_name)
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            assert_utils.assert_true(resp[0], resp[1])
            server_data_pod_list.remove(pod_name)
            LOGGER.info("Step 4: Services of server pod %s are in offline state", pod_name)

            LOGGER.info("Step 5: Check services status on remaining "
                        "pods %s", server_data_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 5: Services of remaining pods are in online state")

            LOGGER.info("Step 6: Perform DELETEs on random %s buckets", del_bucket)
            args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                    'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket,
                    'output': del_output}

            self.ha_obj.put_get_delete(event, s3_test_obj, **args)
            del_resp = tuple()
            while len(del_resp) != 2:
                del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            remain_bkt = s3_test_obj.bucket_list()[1]
            assert_utils.assert_equal(len(remain_bkt), wr_bucket - del_bucket,
                                      f"Failed to delete {del_bucket} number of buckets from "
                                      f"{wr_bucket}. Remaining {len(remain_bkt)} number of "
                                      "buckets")
            LOGGER.info("Step 6: Successfully performed DELETEs on random %s buckets", del_bucket)
            wr_bucket = len(remain_bkt)

            LOGGER.info("Step 7: Perform READs and verify DI on the remaining %s "
                        "buckets", remain_bkt)
            rd_output = Queue()
            new_s3data = dict()
            for bkt in remain_bkt:
                new_s3data[bkt] = s3_data[bkt]

            args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                    'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                    'output': rd_output}
            self.ha_obj.put_get_delete(event, s3_test_obj, **args)
            rd_resp = tuple()
            while len(rd_resp) != 4:
                rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            event_bkt_get = rd_resp[0]
            fail_bkt_get = rd_resp[1]
            event_di_bkt = rd_resp[2]
            fail_di_bkt = rd_resp[3]

            # Above four lists are expected to be empty as all pass expected
            assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get)
                                      or len(event_di_bkt), "Expected pass in read and di check "
                                                            "operations. Found failures in READ: "
                                                            f"{fail_bkt_get} {event_bkt_get}"
                                                            f"or DI_CHECK: {fail_di_bkt} "
                                                            f"{event_di_bkt}")
            LOGGER.info("Step 7: Successfully performed READs and verify DI on the remaining"
                        " %s buckets.", remain_bkt)

        LOGGER.info("Shutdown %s (K) server pods one by one and performed Deletes "
                    "on random buckets and verified read on remaining bucket after"
                    " each server pod down", self.kvalue)

        LOGGER.info("Completed: Test to verify degraded DELETEs after each pod failure till K "
                    "server pods down - unsafe shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Not supported in RGW yet")
    @pytest.mark.tags("TEST-40581")
    @CTFailOn(error_handler)
    def test_copy_object_kserver_pods_fail(self):
        """
        Test to Verify copy object when all K server pods are down - unsafe shutdown.
        """
        LOGGER.info("STARTED: Test to Verify copy object when all K server pods "
                    "down - unsafe shutdown.")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{self.random_time}"] = \
                f"ha-obj{cnt}-{self.random_time}"
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
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 1: Create and list buckets and perform upload and copy "
                    "object from %s bucket to other buckets ", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Create Bucket copy "
                                          f"object failed with: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully created and listed buckets and performed upload and copy"
                    "object from %s bucket to other buckets", self.bucket_name)

        LOGGER.info("Step 2: Shutdown the %s (K) server pods by deleting deployment "
                    "(unsafe)", self.kvalue)
        LOGGER.info("Get server pod names to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        LOGGER.info("Get data pod names")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Combine data and server pods names")
        server_data_pod_list = pod_list + data_pod_list
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            LOGGER.info("Deleting %s server pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} server pod {pod_name}"
                                               " by deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s server pod %s by deleting deployment "
                        "(unsafe)", count, pod_name)
        LOGGER.info("Step 2: Successfully deleted %s server pods", self.kvalue)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster has some failures due to %s server pods has gone down.",
                    self.kvalue)

        LOGGER.info("Step 4: Check services status that were running on server pods"
                    " which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            server_data_pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some server pods not stopped.")
        LOGGER.info("Step 4: Services of server pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", server_data_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_data_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 6: Successfully download the uploaded objects & verify etags")

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.clear()
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 7: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        LOGGER.info("Step 7: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 8: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 8: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)

        LOGGER.info("COMPLETED: Test to Verify copy object when all K server pods "
                    "down - unsafe shutdown.")
