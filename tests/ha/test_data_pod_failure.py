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
HA test suite for Data Pod Failure
"""

import logging
import os
import secrets
import threading
import time
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import commands as cmd
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
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=R0904
class TestDataPodFailure:
    """
    Test suite for Data Pod Failure
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
        cls.node_master_list = []
        cls.hlth_master_list = []
        cls.host_worker_list = []
        cls.node_worker_list = []
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.restore_node = cls.node_name = cls.deploy = cls.multipart_obj_path = None
        cls.restore_ip = cls.node_iface = cls.new_worker_obj = cls.node_ip = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.username.append(CMN_CFG["nodes"][node]["username"])
            cls.password.append(CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"] == "master":
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

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.restore_node = False
        self.restore_ip = False
        self.deploy = False
        self.s3_clean = dict()
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
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
            if CMN_CFG["dtm0_disabled"]:
                resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            else:
                resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean, obj_crud=True)
            assert_utils.assert_true(resp[0], resp[1])
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} "
                                              "way")
            LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        if self.restore_node:
            LOGGER.info("Cleanup: Power on the %s down node.", self.node_name)
            resp = self.ha_obj.host_power_on(host=self.node_name)
            assert_utils.assert_true(resp, "Host is not powered on")
            LOGGER.info("Cleanup: %s is Power on. Sleep for %s sec for pods to join back the"
                        " node", self.node_name, HA_CFG["common_params"]["pod_joinback_time"])
            time.sleep(HA_CFG["common_params"]["pod_joinback_time"])
        if self.restore_ip:
            LOGGER.info("Cleanup: Get the network interface up for %s ip", self.node_ip)
            self.new_worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(self.node_iface, "up"),
                                            read_lines=True)
            resp = sysutils.check_ping(host=self.node_ip)
            assert_utils.assert_true(resp, "Interface is still not up.")
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
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32443")
    @CTFailOn(error_handler)
    def test_reads_safe_pod_shutdown(self):
        """
        This test tests degraded reads before and after safe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded reads before and after safe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32443'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed READs and verified DI on the written data")

        LOGGER.info("Step 3: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 4: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded reads before and after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23553")
    @CTFailOn(error_handler)
    def test_reads_unsafe_pod_shutdown(self):
        """
        This test tests degraded reads before and after unsafe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded reads before and after unsafe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-23553'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed READs and verified DI on the written data")

        LOGGER.info("Step 3: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 4: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded reads before and after unsafe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-23552")
    @CTFailOn(error_handler)
    def test_writes_safe_pod_shutdown(self):
        """
        This test tests degraded writes before and after safe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded writes before and after safe pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-23552'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Perform WRITEs, READs and verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully performed WRITEs, READs & verify DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded writes before and after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26440")
    @CTFailOn(error_handler)
    def test_writes_unsafe_pod_shutdown(self):
        """
        This test tests degraded writes before and after unsafe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded writes before and after unsafe"
                    " pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-26440'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Perform WRITEs, READs and verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Successfully performed WRITEs, READs & verify DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded writes before and after unsafe pod shutdown.")

    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    @pytest.mark.tags("TEST-26444")
    @CTFailOn(error_handler)
    def test_deletes_safe_pod_shutdown(self):
        """
        This test tests degraded deletes before and after safe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded deletes before and after safe pod shutdown.")
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
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
        self.test_prefix = 'test-26444'
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
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Step 1: Successfully created %s buckets & "
                    "perform WRITEs with variable size objects.", wr_bucket)

        LOGGER.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Perform DELETEs on random %s buckets", del_bucket)
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
        LOGGER.info("Step 3: Successfully performed DELETEs on random %s buckets", del_bucket)

        LOGGER.info("Step 4: Perform READs on the remaining %s buckets and delete the same.",
                    remain_bkt)
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
        LOGGER.info("Step 4: Successfully performed READs on the remaining %s buckets.",
                    remain_bkt)
        LOGGER.info("COMPLETED: Test to verify degraded deletes before & after safe pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    @pytest.mark.tags("TEST-26644")
    @CTFailOn(error_handler)
    def test_deletes_unsafe_pod_shutdown(self):
        """
        This test tests degraded deletes before and after unsafe pod shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded deletes before and after unsafe pod "
                    "shutdown.")
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
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
        self.test_prefix = 'test-26644'
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
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Step 1: Successfully created %s buckets & "
                    "perform WRITEs with variable size objects.", wr_bucket)

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Perform DELETEs on random %s buckets", del_bucket)
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
        LOGGER.info("Step 3: Successfully performed DELETEs on random %s buckets", del_bucket)

        LOGGER.info("Step 4: Perform READs on the remaining %s buckets and delete the same.",
                    remain_bkt)
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
        LOGGER.info("Step 4: Successfully performed READs on the remaining %s buckets.",
                    remain_bkt)
        LOGGER.info("COMPLETED: Test to verify degraded deletes before and after unsafe "
                    "pod shutdown.")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32444")
    @CTFailOn(error_handler)
    def test_reads_during_pod_down(self):
        """
        This test tests degraded reads while pod is going down
        """
        LOGGER.info("STARTED: Test to verify degraded reads during pod is going down.")
        event = threading.Event()  # Event to be used to send intimation of data pod deletion

        LOGGER.info("Step 1: Perform WRITEs with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32444'
        self.s3_clean = users
        output = Queue()
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    nsamples=30, nclients=20,
                                                    log_prefix=self.test_prefix,
                                                    skipread=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs and verify DI on the written data in background")
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 5, 'nsamples': 30, 'skipwrite': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()

        LOGGER.info("Step 2: Successfully started READs/verified-DI on the written data in "
                    "background. ")
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 3: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        thread.join()
        LOGGER.info("Step 4: Verify READs & DI on the written data in background")
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        LOGGER.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses["fail_res"])
        LOGGER.debug("Fail logs list: %s", fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")

        LOGGER.info("Step 4: Verified READs and DI on the written data in background")

        LOGGER.info("Step 5: Run IOs with variable object sizes on a degraded cluster.")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-32444-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully ran IOs with variable object sizes.")
        LOGGER.info("ENDED: Test to verify degraded reads during pod is going down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32455")
    @CTFailOn(error_handler)
    def test_pod_shutdown_delete_deployment(self):
        """
        Verify IOs before and after data pod failure; pod shutdown by deleting deployment.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure; pod shutdown "
                    "by deleting deployment.")

        LOGGER.info("Step 1: Perform WRITEs-READs-Verify-DELETEs with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32455'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 3: Perform WRITEs-READs-Verify-DELETEs with variable object sizes "
                        "on degraded cluster with new user")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-32455-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2)
        else:
            LOGGER.info("Step 3: Perform WRITEs-READs-Verify with variable object "
                        "sizes on degraded cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed IOs with variable sizes objects.")

        LOGGER.info("Completed: Verify IOs before and after data pod failure; pod shutdown "
                    "by deleting deployment.")

    # pylint: disable=C0321
    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    @pytest.mark.tags("TEST-26445")
    @CTFailOn(error_handler)
    def test_deletes_during_pod_down(self):
        """
        This test tests DELETEs during data pod down by deleting deployment
        """
        LOGGER.info("STARTED: Test to verify DELETEs during data pod down by deleting deployment.")
        event = threading.Event()  # Event to be used to send intimation of data pod deletion
        LOGGER.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean = {'s3_acc': {'accesskey': resp[1]["access_key"],
                                    'secretkey': resp[1]["secret_key"],
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=resp[1]["access_key"], secret_key=resp[1]["secret_key"],
                                endpoint_url=S3_CFG["s3_url"])
        bucket_num = HA_CFG["s3_bucket_data"]["no_bck_background_deletes"]
        s3data = dict()
        workload = HA_CFG["s3_bucket_data"]["workload_sizes_mbs"]
        LOGGER.info("Step 1: Create %s buckets and put variable size object.", bucket_num)
        for count in range(bucket_num):
            # Workload size in Mb to be uploaded in each bucket
            size_mb = self.system_random.choice(workload)
            bucket_name = f"test-26445-bucket{count}-{size_mb}-{int(perf_counter_ns())}"
            object_name = f"obj_{bucket_name}_{size_mb}"
            file_path = os.path.join(self.test_dir_path, f"{bucket_name}.txt")
            resp = s3_test_obj.create_bucket_put_object(bucket_name, object_name, file_path,
                                                        self.system_random.choice(workload))
            assert_utils.assert_true(resp[0], resp[1])
            upload_chm = self.ha_obj.cal_compare_checksum(file_list=[file_path], compare=False)[0]
            s3data.update({bucket_name: (object_name, upload_chm)})
        LOGGER.info("Step 1: Created %s buckets and uploaded variable size object.", bucket_num)

        LOGGER.info("Step 2: Verify %s has %s buckets created",
                    self.s3_clean['s3_acc']["user_name"], bucket_num)
        buckets = s3_test_obj.bucket_list()
        assert_utils.assert_equal(bucket_num, len(buckets[1]), buckets)
        LOGGER.info("Step 2: Verified %s has %s buckets created",
                    self.s3_clean['s3_acc']["user_name"], bucket_num)
        output = Queue()
        bucket_list = list(s3data.keys())

        LOGGER.info("Step 3: Start Continuous DELETEs in background")
        get_random_buck = self.system_random.sample(bucket_list, (bucket_num - 10))
        remain_buck = list(set(bucket_list) - set(get_random_buck))
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': output}

        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 3: Successfully started DELETEs in background")

        LOGGER.info("Step 4: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 4: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        thread.join()
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt),
                                  f"Bucket deletion failed when cluster was online"
                                  f"{fail_del_bkt}")

        LOGGER.info("Step 5: Verify status for In-flight DELETEs while pod is going down "
                    "and Download and verify checksum on remaining/FailedToDelete buckets.")
        failed_buck = event_del_bkt
        LOGGER.info("Get the buckets from expected failed buckets list which FailedToDelete")
        remain_buck.extend(failed_buck)
        for bucket_name in remain_buck:
            download_file = self.test_file + str(s3data[bucket_name][0])
            download_path = os.path.join(self.test_dir_path, download_file)
            resp = s3_test_obj.object_download(
                bucket_name, s3data[bucket_name][0], download_path)
            LOGGER.info("Download object response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                                 compare=False)[0]
            assert_utils.assert_equal(s3data[bucket_name][1], download_checksum,
                                      f"Failed to match checksum: {s3data[bucket_name][1]},"
                                      f" {download_checksum}")
        LOGGER.info("Step 5: Verified status for In-flight DELETEs while pod is going down"
                    "and downloaded and verified checksum for remaining/FailedToDelete buckets.")

        LOGGER.info("Cleaning up s3 user data")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3_clean.pop('s3_acc')

        LOGGER.info("STEP 6: Create new user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes on degraded cluster")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-26445-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify DELETEs during data pod down by delete deployment.")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26441")
    @CTFailOn(error_handler)
    def test_writes_during_pod_down(self):
        """
        This test tests WRITEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify WRITEs during data pod down by delete deployment.")
        event = threading.Event()  # Event to be used to send intimation of data pod deletion
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes during data pod down by "
                    "delete deployment.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-26441'
        self.s3_clean = users
        output = Queue()

        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 20, 'skipread': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started WRITES in background")
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        thread.join()
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        LOGGER.info("Step 3: Verify status for In-flight WRITEs while pod going down is failed.")
        pass_logs = list(x[1] for x in responses["pass_res"])
        LOGGER.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses["fail_res"])
        LOGGER.debug("Fail logs list: %s", fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"Expected Pass, But Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")
        LOGGER.info("Step 3: Verified status for In-flight WRITEs while pod going down is failed.")

        LOGGER.info("STEP 4: Perform IOs with variable object sizes on degraded cluster")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-26441-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed IOs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify WRITEs during data pod down by delete deployment.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32454")
    @CTFailOn(error_handler)
    def test_pod_shutdown_scale_replicas(self):
        """
        Verify IOs before and after data pod failure; pod shutdown by making replicas=0
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure; pod shutdown "
                    "by making replicas=0")

        LOGGER.info("Step 1: Perform WRITEs-READs-Verify-DELETEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32454'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 3: Perform WRITEs-READs-Verify-DELETEs with variable object sizes "
                        "on degraded cluster with new user")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-32454-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2)
        else:
            LOGGER.info("Step 3: Perform WRITEs-READs-Verify with variable object sizes on "
                        "degraded cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed IOs with variable sizes objects.")

        LOGGER.info("Completed: Verify IOs before and after data pod failure; pod shutdown "
                    "by making replicas 0")

    # pylint: disable=C0321
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-26442")
    @CTFailOn(error_handler)
    def test_reads_writes_during_pod_down(self):
        """
        This test tests READs and WRITEs during data pod down (delete deployment)
        """

        LOGGER.info("STARTED: Test to verify READs/WRITEs during data pod down by "
                    "delete deployment.")
        event = threading.Event()  # Event to be used to send intimation of data pod deletion
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = users

        LOGGER.info("Step 1: Perform READs/WRITEs with variable object sizes during "
                    "data pod down by delete deployment.")
        LOGGER.info("Step 1.1: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = 'test-read-26442'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1.1: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Step 1.2: Start WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-26442'
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 1.2: Successfully started WRITEs with variable sizes objects"
                    " in background")

        LOGGER.info("Step 1.3: Start READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, 'setup_s3bench': False}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 1.3: Successfully started READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 1: Successfully started READs & WRITES in background.")
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        thread_rd.join()
        thread_wri.join()
        LOGGER.debug("Threads has joined")

        LOGGER.info("Step 3: Verify responses from WRITEs & READs/VerifyDI background processes")
        LOGGER.info("Step 3.1: Verify status for In-flight WRITEs while %s data pod going "
                    "down should be failed/error.", pod_name)
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        LOGGER.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        LOGGER.debug("Fail logs list: %s", fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"WRITEs logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"WRITEs logs which contain pass: {resp[1]}")
        LOGGER.info("Step 3.1: Verified status for In-flight WRITEs while %s data pod "
                    "going down.", pod_name)

        LOGGER.info("Step 3.2: Verify status for In-flight READs/Verify DI while %s"
                    " data pod going down should be failed/error.", pod_name)
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        LOGGER.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        LOGGER.debug("Fail logs list: %s", fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"READs/VerifyDI logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"READs/VerifyDI logs which contain pass: {resp[1]}")
        LOGGER.info("Step 3.2: Verified status for In-flight READs/VerifyDI while %s "
                    " data pod going down.", pod_name)
        LOGGER.info("Step 3: Verified responses from WRITEs & READs/VerifyDI background processes")

        LOGGER.info("Step 4: Run IOs with variable object sizes on a degraded cluster.")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-26442-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Successfully ran IOs with variable object sizes.")
        LOGGER.info("ENDED: Test to verify READs/WRITEs during data pod down by delete deployment.")

    # pylint: disable=C0321
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    @pytest.mark.tags("TEST-26446")
    @CTFailOn(error_handler)
    def test_writes_deletes_during_pod_down(self):
        """
        This test tests WRITEs and DELETEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify WRITEs and DELETEs during data pod down "
                    "by delete deployment.")
        event = threading.Event()  # Event to be used to send intimation of data pod deletion
        del_total_bkt = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        wr_bucket = HA_CFG["s3_bucket_data"]["no_bck_writes"]
        del_bucket = HA_CFG["bg_bucket_ops"]["no_del_buckets"]
        wr_output = Queue()
        del_output = Queue()

        LOGGER.info("Creating IAM user")
        users = self.mgnt_ops.create_account_users(nusers=1)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        self.test_prefix = 'test-26446'
        self.s3_clean = users
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])

        LOGGER.info("Step 1: Start WRITEs and DELETEs with variable object sizes "
                    "during data pod down by delete deployment.")

        LOGGER.info("Perform WRITEs on %s buckets for background DELETEs", del_total_bkt)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': del_total_bkt, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains IAM user data for passed buckets
        written_bck = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(written_bck), del_total_bkt,
                                  f"Failed to create {del_total_bkt} number of buckets."
                                  f"Created {len(written_bck)} number of buckets")
        LOGGER.info("Performed WRITEs on %s buckets for background DELETEs", del_total_bkt)

        LOGGER.info("Starting WRITEs on %s buckets in background", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}
        thread1 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj,), kwargs=args)

        LOGGER.info("Starting DELETEs of %s buckets in background", del_bucket)
        get_random_buck = self.system_random.sample(written_bck, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck,
                'bkts_to_del': del_bucket, 'output': del_output}
        thread2 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj,), kwargs=args)
        thread2.daemon = True  # Daemonize thread
        thread1.daemon = True  # Daemonize thread
        thread2.start()
        thread1.start()
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["20sec_delay"])
        time.sleep(HA_CFG["common_params"]["20sec_delay"])
        LOGGER.info("Step 1: Started WRITEs and DELETEs with variable object sizes "
                    "during data pod down by delete deployment.")

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        thread1.join()
        thread2.join()

        LOGGER.info("Step 3: Verify responses from WRITEs and DELETEs background processes")
        LOGGER.info("Step 3.1: Verifying responses from WRITEs background process")
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not wr_resp:
            assert_utils.assert_true(False, "Background process failed to do WRITEs")
        event_put_bkt = wr_resp[1]  # Contains buckets when event was set
        fail_put_bkt = wr_resp[2]  # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_put_bkt), "No WRITEs failure expected when event was "
                                                     f"clear {fail_put_bkt}.")
        LOGGER.info("Failed buckets while in-flight WRITEs operation : %s", event_put_bkt)
        LOGGER.info("Step 3.1: Verified responses from WRITEs background process")

        LOGGER.info("Step 3.2: Verifying responses from DELETEs background process")
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do DELETEs")
        event_del_bkt = del_resp[0]  # Contains buckets when event was set
        fail_del_bkt = del_resp[1]  # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_del_bkt), "No DELETEs failure expected when event was "
                                                     f"clear {fail_del_bkt}.")
        LOGGER.info("Failed buckets while in-flight DELETEs operation : %s", event_del_bkt)
        LOGGER.info("Step 3.2: Verified responses from DELETEs background process")
        LOGGER.info("Step 3: Verified responses from WRITEs and DELETEs background processes")

        rd_output = Queue()
        remain_bkts = list(set(written_bck) - set(get_random_buck))
        LOGGER.info("Step 4: Verify READs and DI check for remaining buckets: %s", len(remain_bkts))

        new_s3data = dict()
        for bkt in remain_bkts:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = tuple()
        while len(rd_resp) != 4:
            rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not rd_resp:
            assert_utils.assert_true(False, "Failed to READ/Verify remaining buckets.")
        event_bkt_get = rd_resp[0]
        fail_bkt_get = rd_resp[1]
        event_di_bkt = rd_resp[2]
        fail_di_bkt = rd_resp[3]

        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt),
                                  "Expected pass in READs and di check operations. Found failures "
                                  f"in READ: {fail_bkt_get} {event_bkt_get} OR in "
                                  f"DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 4: Successfully verified READs and DI check for remaining buckets: %s",
                    len(remain_bkts))

        LOGGER.info("Step 5: Deleting remaining %s buckets.", len(remain_bkts))
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Failed to DELETE remaining buckets.")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(event_del_bkt) or len(fail_del_bkt),
                                  f"Failed to DELETE buckets: {event_del_bkt} and {fail_del_bkt}")

        LOGGER.info("Step 5: Successfully deleted remaining buckets.")

        LOGGER.info("Step 6: Create multiple buckets and run IOs")
        self.test_prefix = 'test-26446-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify WRITEs and DELETEs during data pod down by "
                    "delete deployment.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    @pytest.mark.tags("TEST-26447")
    @CTFailOn(error_handler)
    def test_reads_deletes_during_pod_down(self):
        """
        This test tests READs and DELETEs during data pod down (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify READs and DELETEs during data pod down "
                    "by delete deployment.")
        event = threading.Event()  # Event to be used to send intimation of data pod deletion
        del_total_bkt = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        rd_bucket = HA_CFG["s3_bucket_data"]["no_bck_writes"]
        del_bucket = HA_CFG["bg_bucket_ops"]["no_del_buckets"]
        rd_output = Queue()
        wr_output = Queue()
        del_output = Queue()

        LOGGER.info("Creating IAM user")
        users = self.mgnt_ops.create_account_users(nusers=1)
        access_key = list(users.values())[0]["accesskey"]
        secret_key = list(users.values())[0]["secretkey"]
        self.test_prefix = 'test-26447'
        self.s3_clean = users
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])

        LOGGER.info("Step 1: Performing READs and DELETEs with variable object sizes during data "
                    "pod down by delete deployment.")

        LOGGER.info("Perform WRITEs on %s buckets for background DELETEs", del_total_bkt)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': del_total_bkt, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data_del = wr_resp[0]  # Contains IAM user data for passed buckets
        written_bck = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(written_bck), del_total_bkt,
                                  f"Failed to create {del_total_bkt} number of buckets."
                                  f"Created {len(written_bck)} number of buckets")
        LOGGER.info("Performed WRITEs on %s buckets for background DELETEs", del_total_bkt)

        LOGGER.info("Perform WRITEs on %s buckets for background READs", rd_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': rd_bucket, 'output': wr_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = tuple()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data_rd = wr_resp[0]  # Contains IAM user data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), rd_bucket,
                                  f"Failed to create {rd_bucket} number of buckets."
                                  f"Created {len(buckets)} number of buckets")
        LOGGER.info("Performed WRITEs on %s buckets for background READs", rd_bucket)

        LOGGER.info("Starting READs on %s buckets in background", rd_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': s3_data_rd,
                'di_check': True, 'output': rd_output}
        thread1 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj,), kwargs=args)

        LOGGER.info("Starting DELETEs of %s buckets in background", del_bucket)
        get_random_buck = self.system_random.sample(written_bck, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck,
                'bkts_to_del': del_bucket, 'output': del_output}
        thread2 = threading.Thread(target=self.ha_obj.put_get_delete,
                                   args=(event, s3_test_obj,), kwargs=args)
        thread1.daemon = True   # Daemonize thread
        thread2.daemon = True  # Daemonize thread
        thread2.start()
        thread1.start()
        LOGGER.info("Step 1: Started READs and DELETEs with variable object sizes "
                    "during server pod down by delete deployment.")
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 2: Shutdown random server pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown server pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        thread1.join()
        thread2.join()

        LOGGER.info("Background READs and DELETEs threads joined successfully.")
        LOGGER.info("Step 3: Verify responses from READs and DELETEs background processes")
        LOGGER.info("Step 3.1: Verifying responses from READs background process")
        rd_resp = tuple()
        LOGGER.info("Waiting for READ process output from Queue. Sleeping for %s",
                    HA_CFG["common_params"]["60sec_delay"])
        while len(rd_resp) != 4:
            rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not rd_resp:
            assert_utils.assert_true(False, "Background process failed to do READs")
        event_bkt_get = rd_resp[0]  # Contains buckets when event was set
        fail_bkt_get = rd_resp[1]  # Contains buckets which failed when event was clear
        event_di_bkt = rd_resp[2]  # Contains buckets when event was set
        fail_di_bkt = rd_resp[3]  # Contains buckets which failed when event was clear

        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt),
                                  "Expected PASS when event was clear, but buckets which failed in "
                                  f"READs : {fail_bkt_get} OR DI check : {fail_di_bkt}")

        LOGGER.info("Failed buckets while in-flight READs operation : %s", event_bkt_get)
        LOGGER.info("Failed buckets while in-flight DI check operation : %s", event_di_bkt)
        LOGGER.info("Step 3.1: Verified responses from READs background process")

        LOGGER.info("Step 3.2: Verifying responses from DELETEs background process")
        del_resp = tuple()
        LOGGER.info("Waiting for DELETE process output from Queue. Sleeping for %s",
                    HA_CFG["common_params"]["60sec_delay"])
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do DELETEs")
        event_del_bkt = del_resp[0]  # Contains buckets when event was set
        fail_del_bkt = del_resp[1]  # Contains buckets which failed when event was clear
        assert_utils.assert_false(len(fail_del_bkt), "Expected pass, buckets which failed in "
                                                     f"DELETEs: {fail_del_bkt}.")
        LOGGER.info("Failed buckets while in-flight DELETEs operation : %s", event_del_bkt)
        LOGGER.info("Step 3.2: Verified responses from DELETEs background process")
        LOGGER.info("Step 3: Verified responses from READs and DELETEs background processes")

        remain_bkts = list(set(written_bck) - set(get_random_buck))
        LOGGER.info(
            "Step 4: Check READs-DI on remaining buckets of DELETEs operation: %s", remain_bkts)
        new_s3data = dict()
        for bkt in remain_bkts:
            new_s3data[bkt] = s3_data_del[bkt]

        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = tuple()
        while len(rd_resp) != 4:
            rd_resp = rd_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not rd_resp:
            assert_utils.assert_true(False,
                                     "Failed to get READ/Verify response on remaining buckets.")
        event_bkt_get = rd_resp[0]
        fail_bkt_get = rd_resp[1]
        event_di_bkt = rd_resp[2]
        fail_di_bkt = rd_resp[3]

        # Above four lists are expected to be empty as all pass expected
        assert_utils.assert_false(len(fail_bkt_get) or len(fail_di_bkt) or len(event_bkt_get) or
                                  len(event_di_bkt),
                                  "Expected pass in READs & DI_CHECK operations. Found failures in"
                                  f"READ: {fail_bkt_get} {event_bkt_get} OR in "
                                  f"DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 4: Successfully checked READs and DI_CHECK for remaining buckets.")

        LOGGER.info("Step 5: Deleting remaining %s buckets.", len(remain_bkts))
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'output': del_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Failed to DELETE remaining buckets.")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(event_del_bkt) or len(fail_del_bkt),
                                  f"Failed to DELETE buckets: {event_del_bkt} and {fail_del_bkt}")

        LOGGER.info("Step 5: Successfully deleted remaining buckets.")

        LOGGER.info("Step 6: Create multiple buckets and run IOs")
        self.test_prefix = 'test-26447-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify READs and DELETEs during data pod down by "
                    "delete deployment.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32445")
    @CTFailOn(error_handler)
    def test_mpu_after_safe_pod_shutdown(self):
        """
        This test tests degraded multipart upload after data pod safe shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded multipart upload after data pod "
                    "safe shutdown.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 1: Create and list buckets and perform multipart upload for size 5GB.")
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
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

        LOGGER.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 3: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        sysutils.remove_file(self.multipart_obj_path)
        sysutils.remove_file(download_path)

        LOGGER.info("Step 4: Do Multipart upload and then download 5GB object")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Creating new bucket for new upload")
            bucket_name = f"mp-bkt-{perf_counter_ns()}"
        else:
            bucket_name = self.bucket_name
        object_name = f"mp-obj-{perf_counter_ns()}"
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
        LOGGER.info("Step 4: Did multipart upload and download with 5GB object")

        LOGGER.info("COMPLETED: Test to verify degraded multipart upload after data pod"
                    " safe shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32446")
    @CTFailOn(error_handler)
    def test_mpu_after_unsafe_pod_shutdown(self):
        """
        This test tests degraded multipart upload after data pod unsafe shutdown
        """
        LOGGER.info("STARTED: Test to verify degraded multipart upload after data pod"
                    " unsafe shutdown.")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 1: Create and list buckets and perform multipart upload for size 5GB.")
        LOGGER.info("Creating IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
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

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 3: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        sysutils.remove_file(self.multipart_obj_path)
        sysutils.remove_file(download_path)

        LOGGER.info("Step 4: Do Multipart upload and then download 5GB object")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Creating new bucket for new upload")
            bucket_name = f"mp-bkt-{perf_counter_ns()}"
        else:
            bucket_name = self.bucket_name
        object_name = f"mp-obj-{perf_counter_ns()}"
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
        LOGGER.info("Step 4: Did multipart upload and download with 5GB object")
        LOGGER.info("COMPLETED: Test to verify degraded multipart upload after data pod"
                    " unsafe shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Functionality not Available")
    @pytest.mark.tags("TEST-32460")
    @CTFailOn(error_handler)
    def test_ha_pod_failover(self):
        """
        Verify IOs before and after ha pod failure, pod shutdown by making worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after HA pod failure, "
                    "pod shutdown by making worker node down.")

        LOGGER.info("STEP 1: Create IAM user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32460'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Check the node which has the ha pod running and shutdown"
                    "the node.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_list = \
            self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        ha_pods = self.node_master_list[0].get_pods_node_fqdn(const.HA_POD_NAME_PREFIX)
        ha_pod_name = list(ha_pods.keys())[0]
        node_fqdn = ha_pods.get(ha_pod_name)
        self.node_name = node_fqdn
        LOGGER.info("HA pod %s is hosted on %s node", ha_pod_name, node_fqdn)
        LOGGER.info("Get the data pod running on node %s", node_fqdn)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        server_pods = self.node_master_list[0].get_pods_node_fqdn(const.SERVER_POD_NAME_PREFIX)
        data_pod_name = serverpod_name = None
        for pod_name, node in data_pods.items():
            if node == node_fqdn:
                data_pod_name = pod_name
                break
        for pod_name, node in server_pods.items():
            if node == node_fqdn:
                serverpod_name = pod_name
                break
        LOGGER.info("%s node has data pod: %s server pod: %s", node_fqdn, data_pod_name,
                    serverpod_name)
        LOGGER.info("Shutdown the node: %s", node_fqdn)
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where HA pod was running.", node_fqdn)
        self.restore_node = self.deploy = True

        LOGGER.info("Step 3: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Checked cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data pod %s and server "
                    "pod %s", data_pod_name, serverpod_name)
        resp = \
            self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name, serverpod_name],
                                                        fail=True, hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on data pod %s and server "
                    "pod %s", data_pod_name, serverpod_name)

        pod_list.remove(data_pod_name)
        server_list.remove(serverpod_name)
        online_pods = pod_list + server_list
        LOGGER.info("Step 5: Check services status on remaining pods %s", online_pods)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=online_pods, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 6: Check for HA pod failed over node.")
        ha_pods_new = self.node_master_list[0].get_pods_node_fqdn(const.HA_POD_NAME_PREFIX)
        assert_utils.assert_true(ha_pods_new, "HA pod has not failed over to any other node.")
        ha_pod_name_new = list(ha_pods_new.keys())[0]
        node_fqdn_new = ha_pods_new.get(ha_pod_name_new)
        LOGGER.info("Step 6: %s pod has been failed over to %s node",
                    ha_pod_name_new, node_fqdn_new)

        LOGGER.info("COMPLETED: Verify IOs before and after HA pod failure, "
                    "pod shutdown by making worker node down.")

    # pylint: disable=C0321
    # pylint: disable-msg=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32447")
    @CTFailOn(error_handler)
    def test_mpu_during_pod_unsafe_shutdown(self):
        """
        This test tests multipart upload during data pod shutdown (delete deployment)
        """
        LOGGER.info("STARTED: Test to verify multipart upload during data pod shutdown by delete "
                    "deployment")
        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts + 1))
        self.system_random.shuffle(part_numbers)
        output = Queue()
        parts_etag = list()
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        event = threading.Event()  # Event to be used to send intimation of data pod shutdown

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
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size, 'total_parts': total_parts,
                'multipart_obj_path': self.multipart_obj_path, 'part_numbers': part_numbers,
                'parts_etag': parts_etag, 'output': output}
        thread = threading.Thread(target=self.ha_obj.start_random_mpu, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Started multipart upload of 5GB object in background. Sleeping for "
                    "%s sec", HA_CFG["common_params"]["60sec_delay"])
        time.sleep(HA_CFG["common_params"]["60sec_delay"])

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Checking response from background process")
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
        if len(exp_failed_parts) == 0 and len(failed_parts) == 0:
            LOGGER.info("All the parts are uploaded successfully")
        elif failed_parts:
            assert_utils.assert_true(False, "Failed to upload parts when cluster was in degraded "
                                            f"state. Failed parts: {failed_parts}")
        elif exp_failed_parts:
            LOGGER.info("Step 3.1: Upload remaining parts")
            resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                        bucket_name=self.bucket_name,
                                                        object_name=self.object_name,
                                                        part_numbers=exp_failed_parts,
                                                        remaining_upload=True,
                                                        multipart_obj_size=file_size,
                                                        total_parts=total_parts,
                                                        multipart_obj_path=self.multipart_obj_path,
                                                        mpu_id=mpu_id)
            assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
            parts_etag1 = resp[3]
            parts_etag = parts_etag + parts_etag1
            LOGGER.info("Step 3.1: Successfully uploaded remaining parts")
        LOGGER.info("Step 3: Successfully checked background process responses")

        parts_etag = sorted(parts_etag, key=lambda d: d['PartNumber'])

        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 4: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 4: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 5: Completing multipart upload and check upload size is %s",
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
        LOGGER.info("Step 5: Multipart upload completed and verified upload object size is %s",
                    obj_size)

        LOGGER.info("Step 6: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 6: Successfully downloaded the object and verified the checksum")

        LOGGER.info("COMPLETED: Test to verify multipart upload during data pod shutdown by delete"
                    " deployment")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32449")
    @CTFailOn(error_handler)
    def test_partial_mpu_after_pod_unsafe_shutdown(self):
        """
        This test tests degraded partial multipart upload after data pod unsafe shutdown
        by deleting deployment
        """
        LOGGER.info("STARTED: Test to verify degraded partial multipart upload after data "
                    "pod unsafe shutdown by deleting deployment")

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
        mpu_id = resp[1]
        object_path = resp[2]
        parts_etag1 = resp[3]
        assert_utils.assert_true(resp[0], f"Failed to upload parts. Response: {resp}")
        LOGGER.info("Step 1: Successfully completed partial multipart upload for %s parts out of "
                    "total %s", part_numbers, total_parts)

        LOGGER.info("Step 2: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 2: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 3: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 4: Upload remaining parts")
        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts + 1))))
        resp = self.ha_obj.partial_multipart_upload(s3_data=self.s3_clean,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    part_numbers=remaining_parts,
                                                    remaining_upload=True, mpu_id=mpu_id,
                                                    multipart_obj_size=file_size,
                                                    total_parts=total_parts,
                                                    multipart_obj_path=object_path)

        assert_utils.assert_true(resp[0], f"Failed to upload parts {resp[1]}")
        parts_etag2 = resp[3]
        LOGGER.info("Step 4: Successfully uploaded remaining parts")

        etag_list = parts_etag1 + parts_etag2
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])

        LOGGER.info("Step 5: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 5: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 6: Completing multipart upload Completing multipart upload and check "
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
        LOGGER.info("Step 6: Multipart upload completed and verified upload size is %s",
                    file_size * const.Sizes.MB)

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

        LOGGER.info("ENDED: Test to verify degraded partial multipart upload after data pod unsafe"
                    " shutdown by deleting deployment")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Functionality not available in RGW yet")
    @pytest.mark.tags("TEST-32450")
    @CTFailOn(error_handler)
    def test_copy_object_safe_pod_shutdown(self):
        """
        Verify degraded copy object after data pod down - pod shutdown (make replicas=0)
        """
        LOGGER.info("STARTED: Verify degraded copy object after data pod down - pod shutdown "
                    "(make replicas=0) ")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{int(perf_counter_ns())}"] = \
                f"ha-obj{cnt}-{int(perf_counter_ns())}"
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
                    "object from %s bucket to other buckets.", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully created and listed buckets. Performed upload and copy"
                    "object from %s bucket to other buckets.", self.bucket_name)

        LOGGER.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 3: Successfully downloaded the uploaded objects & verified etags")

        if CMN_CFG["dtm0_disabled"]:
            bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
            object3 = f"ha-obj3-{int((perf_counter_ns()))}"
            bkt_obj_dict.clear()
            bkt_obj_dict[bucket3] = object3
            LOGGER.info("Step 4: Perform copy of %s from already created/uploaded %s to %s "
                        "and verify copy object etags",
                        self.object_name, self.bucket_name, bucket3)
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=bkt_obj_dict, put_etag=put_etag,
                                                      bkt_op=False)
            assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
            LOGGER.info("Step 4: Performed copy of %s from already created/uploaded %s to %s and "
                        "verified copy object etags", self.object_name, self.bucket_name, bucket3)

            LOGGER.info("Step 5: Download the uploaded %s on %s & verify etags.", object3, bucket3)
            resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {object3} of bucket {bucket3}.")
            LOGGER.info("Step 5: Downloaded the uploaded %s on %s & verified etags.",
                        object3, bucket3)

        LOGGER.info("COMPLETED: Verify degraded copy object after data pod down - pod shutdown "
                    "(make replicas=0) ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Functionality not available in RGW yet")
    @pytest.mark.tags("TEST-32451")
    @CTFailOn(error_handler)
    def test_copy_object_unsafe_pod_shutdown(self):
        """
        Verify degraded copy object after data pod down - pod unsafe
        shutdown (by deleting deployment)
        """
        LOGGER.info("STARTED: Verify degraded copy object after data pod down - "
                    "pod unsafe shutdown (by deleting deployment) ")

        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_cnt"]
        bkt_obj_dict = dict()
        for cnt in range(bkt_cnt):
            bkt_obj_dict[f"ha-bkt{cnt}-{int(perf_counter_ns())}"] = \
                f"ha-obj{cnt}-{int(perf_counter_ns())}"
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
                    "object from %s bucket to other bucket", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 1: successfully create and list buckets and perform upload and copy"
                    "object from %s bucket to other buckets", self.bucket_name)

        LOGGER.info("Step 2: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 3: Successfully download the uploaded objects & verify etags")

        if CMN_CFG["dtm0_disabled"]:
            bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
            object3 = f"ha-obj3-{int((perf_counter_ns()))}"
            bkt_obj_dict.clear()
            bkt_obj_dict[bucket3] = object3
            LOGGER.info("Step 4: Perform copy of %s from already created/uploaded %s to %s "
                        "and verify copy object etags",
                        self.object_name, self.bucket_name, bucket3)
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=bkt_obj_dict,
                                                      put_etag=put_etag,
                                                      bkt_op=False)
            assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
            LOGGER.info("Step 4: Performed copy of %s from already created/uploaded %s to %s and "
                        "verified copy object etags", self.object_name, self.bucket_name, bucket3)

            LOGGER.info("Step 5: Download the uploaded %s on %s & verify etags.", object3, bucket3)
            resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {object3} of bucket {bucket3}.")
            LOGGER.info("Step 5: Downloaded the uploaded %s on %s & verified etags.",
                        object3, bucket3)

        LOGGER.info("COMPLETED: Verify degraded copy object after data pod down - "
                    "pod unsafe shutdown (by deleting deployment) ")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-32458")
    @CTFailOn(error_handler)
    def test_pod_fail_node_down(self):
        """
        Verify IOs before and after data pod failure, pod shutdown by making worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node down.")

        LOGGER.info("STEP 1: Create IAM user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32458'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown data pod by shutting node on which its hosted.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        resp = self.ha_obj.get_data_pod_no_ha_control(data_pod_list, self.node_master_list[0])
        data_pod_name = resp[0]
        server_pod_name = resp[1]
        data_node_fqdn = resp[2]
        srv_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        self.node_name = data_node_fqdn
        LOGGER.info("Shutdown the node: %s", data_node_fqdn)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=data_node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered off")
        LOGGER.info("Step 2: %s Node is shutdown where data pod was running.", data_node_fqdn)
        self.restore_node = self.deploy = True
        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        running_pod = self.system_random.sample(remain_pod_list1, 1)[0]
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Sleep for pod-eviction-timeout of %s sec", HA_CFG["common_params"][
            "pod_eviction_time"])
        time.sleep(HA_CFG["common_params"]["pod_eviction_time"])

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0], pod_list=remain_pod_list1)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        LOGGER.info("Check services on %s data pod", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=pod_host, pod_name=running_pod)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Check services on %s server pod", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name], fail=True,
                                                           hostname=srv_pod_host,
                                                           pod_name=running_pod)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of data and server pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False,
                                                           pod_name=running_pod)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("STEP 6: Create IAM user and perform WRITEs-READs-Verify-DELETEs with "
                        "variable object sizes on degraded cluster")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-32458-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2)
        else:
            LOGGER.info("STEP 6: Perform WRITEs-READs-Verify with variable object sizes on "
                        "degraded cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed IOs with variable sizes objects.")

        LOGGER.info("COMPLETED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until 'EOS-27549' resolve")
    @pytest.mark.tags("TEST-32457")
    @CTFailOn(error_handler)
    def test_pod_fail_node_nw_down(self):
        """
        Verify IOs before and after data pod failure, pod shutdown
        by making worker node network down.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node network down.")

        LOGGER.info("STEP 1: Create IAM user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-32457'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown data pod by making network down of node "
                    "on which its hosted.")
        data_pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        resp = self.ha_obj.get_data_pod_no_ha_control(data_pod_list, self.node_master_list[0])
        data_pod_name = resp[0]
        server_pod_name = resp[1]
        data_node_fqdn = resp[2]
        srv_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name)
        LOGGER.info("Get the ip of the host from the node %s", data_node_fqdn)
        resp = self.ha_obj.get_nw_iface_node_down(host_list=self.host_worker_list,
                                                  node_list=self.node_worker_list,
                                                  node_fqdn=data_node_fqdn)
        self.node_ip = resp[1]
        self.node_iface = resp[2]
        self.new_worker_obj = resp[3]
        assert_utils.assert_true(resp[0], "Node network is still up")
        LOGGER.info("Step 2: %s Node's network is down.", data_node_fqdn)
        self.restore_ip = self.deploy = True

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        LOGGER.info("Check services on %s data pod", data_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[data_pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Check services on %s server pod", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name], fail=True,
                                                           hostname=srv_pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of data and server pods are in offline state")

        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services status on remaining pod are in online state")

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("STEP 6: Create IAM user and perform WRITEs-READs-Verify-DELETEs with "
                        "variable object sizes on degraded cluster")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-32457-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2)
        else:
            LOGGER.info("STEP 6: Perform WRITEs-READs-Verify with variable object sizes "
                        "on degraded cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed IOs with variable sizes objects.")

        LOGGER.info("COMPLETED: Verify IOs before and after data pod failure, "
                    "pod shutdown by making worker node network down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Functionality not available in RGW yet")
    @pytest.mark.tags("TEST-32452")
    @CTFailOn(error_handler)
    def test_copy_object_during_pod_shutdown(self):
        """
        Verify copy object during data pod shutdown (delete deployment)
        """
        LOGGER.info("STARTED: Verify copy object during data pod shutdown (delete deployment) ")

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
        LOGGER.info("Successfully created IAM user with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Create bucket, upload an object to one of the bucket ")
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
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
                LOGGER.error("Bucket creation is taking longer than %s sec",
                             HA_CFG["common_params"]["bucket_creation_delay"])
                assert_utils.assert_true(False, "Please check background process logs")
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["20sec_delay"])
        time.sleep(HA_CFG["common_params"]["20sec_delay"])

        LOGGER.info("Step 3: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, event=event)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 4: Checking responses from background process")
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
        if len(exp_fail_bkt_obj_dict) == 0 and len(failed_bkts) == 0:
            LOGGER.info("Copy object operation for all the buckets completed successfully. ")
        elif failed_bkts:
            assert_utils.assert_true(False, "Failed to do copy object when cluster was in degraded"
                                            f" state. Failed buckets: {failed_bkts}")
        elif exp_fail_bkt_obj_dict:
            LOGGER.info("Step 4.1: Retrying copy object to buckets %s",
                        list(exp_fail_bkt_obj_dict.keys()))
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=exp_fail_bkt_obj_dict,
                                                      bkt_op=False, put_etag=put_etag)
            assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
            put_etag = resp[1]
        LOGGER.info("Step 4: Successfully checked responses from background process.")

        LOGGER.info("Step 5: Download the uploaded objects & verify etags")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {key} of bucket {val}.")
        LOGGER.info("Step 5: Successfully download the uploaded objects & verify etags")

        if CMN_CFG["dtm0_disabled"]:
            bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
            object3 = f"ha-obj3-{int((perf_counter_ns()))}"
            bkt_obj_dict.clear()
            bkt_obj_dict[bucket3] = object3
            LOGGER.info("Step 6: Perform copy of %s from already created/uploaded %s to %s "
                        "and verify copy object etags",
                        self.object_name, self.bucket_name, bucket3)
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=bkt_obj_dict, put_etag=put_etag,
                                                      bkt_op=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Performed copy of %s from already created/uploaded %s to %s and "
                        "verified copy object etags", self.object_name, self.bucket_name, bucket3)

            LOGGER.info("Step 7: Download the uploaded %s on %s & verify etags.", object3, bucket3)
            resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed to match GET-PUT ETAG for "
                                                          f"object {object3} of bucket {bucket3}.")
            LOGGER.info("Step 7: Downloaded the uploaded %s on %s & verified etags.",
                        object3, bucket3)

        LOGGER.info("COMPLETED: Verify copy object during data pod shutdown (delete deployment)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-33209")
    @CTFailOn(error_handler)
    def test_rc_pod_failover(self):
        """
        Verify IOs before and after pod failure by making RC node down
        """
        LOGGER.info("STARTED: Verify IOs before & after pod failure by making RC node down")

        LOGGER.info("Step 1: Perform WRITEs-READs-Verify-DELETEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-33209'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Get the RC node data pod and shutdown the same.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        rc_node = self.ha_obj.get_rc_node(self.node_master_list[0])
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        self.node_name = list(rc_info.values())[0]
        LOGGER.info("RC Node is running on %s node", self.node_name)
        LOGGER.info("Get the data pod running on %s node", self.node_name)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        rc_datapod = None
        for pod_name, node in data_pods.items():
            if node == self.node_name:
                rc_datapod = pod_name
                break
        LOGGER.info("RC node %s has data pod: %s ", self.node_name, rc_datapod)
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=rc_datapod)

        LOGGER.info("Deleting pod of RC node, pod name %s", rc_datapod)
        resp = self.node_master_list[0].delete_deployment(pod_name=rc_datapod)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {rc_datapod} by deleting"
                                           f" deployment")
        LOGGER.info("Successfully shutdown/deleted pod %s by deleting deployment ", rc_datapod)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Successfully shutdown RC node data pod %s.", rc_datapod)
        pod_list.remove(rc_datapod)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0], pod_list=pod_list)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on RC node %s's data pod %s "
                    " are in offline state", self.node_name, rc_datapod)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[rc_datapod],
                                                           fail=True, hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status that were running on RC node %s's data pod %s"
                    " are in offline state", self.node_name, rc_datapod)

        LOGGER.info("Step 5: Check services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 6: Check for RC node failed over node.")
        rc_node = self.ha_obj.get_rc_node(self.node_master_list[0])
        assert_utils.assert_true(len(rc_node), "Couldn't fine new RC failover node")
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        LOGGER.info("Step 6: RC node has been failed over to %s node", list(rc_info.values())[0])

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 7: Create new IAM user and Perform WRITEs-READs-Verify-DELETEs with "
                        "variable object sizes on degraded cluster")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-33209-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2)
        else:
            LOGGER.info("Step 7: Perform WRITEs-READs-Verify-DELETEs with variable object sizes "
                        "on degraded cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed IOs with variable sizes objects.")

        LOGGER.info("COMPLETED: Verify IOs before & after pod failure by making RC node down")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35297")
    @CTFailOn(error_handler)
    def test_chunk_upload_during_pod_down(self):
        """
        Test chunk upload during pod down (using jclient)
        """
        LOGGER.info("STARTED: Test chunk upload during pod down")
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
        self.test_prefix = 'test-35297'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])

        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'file_size': file_size, 'chunk_obj_path': chunk_obj_path, 'output': output}

        thread = threading.Thread(target=self.ha_obj.create_bucket_chunk_upload, kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()

        LOGGER.info("Step 2: Successfully started chuck upload in background")
        LOGGER.info("Sleep for %s sec", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 3: Shutdown random data pod by deleting deployment and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.deployment_backup = resp[1][pod_name]['deployment_backup']
        self.restore_pod = self.deploy = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 4: Verifying response of background process")
        thread.join()
        while True:
            resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
            if isinstance(resp, bool):
                break
        if resp is None:
            assert_utils.assert_true(False, "Background process of chunk upload failed")
        LOGGER.info("Step 4: Successfully verified response of background process")

        if not resp:
            LOGGER.info("Step 5: Chunk upload failed in between, trying chunk upload again")
            self.ha_obj.create_bucket_chunk_upload(s3_data=self.s3_clean,
                                                   bucket_name=self.bucket_name,
                                                   file_size=file_size,
                                                   chunk_obj_path=chunk_obj_path,
                                                   output=output,
                                                   bkt_op=False)

            while True:
                resp = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
                if isinstance(resp, bool):
                    break

            if not resp or resp is None:
                assert_utils.assert_true(False, "Retried chunk upload failed")
            LOGGER.info("Step 5: Retried chunk upload successfully")

        LOGGER.info("Calculating checksum of file %s", chunk_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[chunk_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Step 6: Download object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Step 6: Successfully downloaded object and verified checksum")

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 7: Create IAM user, buckets & upload objects on degraded cluster.")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-35297-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2)
        else:
            LOGGER.info("Perform IOs with variable object sizes on degraded cluster")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=self.s3_clean,
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully completed IOs.")

        LOGGER.info("ENDED: Test chunk upload during pod down")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.nightly_regression
    @pytest.mark.tags("TEST-39976")
    @CTFailOn(error_handler)
    def test_object_crud_pod_failure(self):
        """
        Verify object CRUDs before and after pod failure; pod shutdown by making replicas=0
        """
        LOGGER.info("STARTED: Verify object CRUDs before and after pod failure; pod shutdown "
                    "by making replicas=0")

        LOGGER.info("Step 1: Perform WRITEs-READs-Verify with variable object sizes")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-39976'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random data pod by making replicas=0 and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)

        LOGGER.info("Step 3: Perform READs-Verify with variable object sizes on already "
                    "written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs-Verify on already written data.")

        LOGGER.info("Step 4: Create new objects and run IOs")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("IOs completed, delete objects.")
        resp = self.ha_obj.delete_s3_acc_buckets_objects(s3_data=users, obj_crud=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: IOs ran successfully and objects deleted.")

        LOGGER.info("Completed: Verify object CRUDs before and after pod failure; pod shutdown "
                    "by making replicas=0")
