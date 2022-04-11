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

"""HA test suite for Server Pod Failure."""

import logging
import os
import random
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
from libs.motr.motr_core_k8s_lib import MotrCoreK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=R0904
class TestServerPodFailure:

    """Test suite for Server Pod Failure."""

    @classmethod
    def setup_class(cls):
        """Setup operations for the test file."""
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
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = cls.random_time = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.restore_node = cls.node_name = cls.deploy = None
        cls.restore_ip = cls.node_iface = cls.new_worker_obj = cls.node_ip = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()
        cls.motr_obj = MotrCoreK8s()

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
        """Following function steps will be invoked prior to each test case."""
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restore_node = False
        self.restore_ip = False
        self.deploy = False
        self.s3_clean = {}
        LOGGER.info("Check the overall status of the cluster.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
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
        """Following function steps will be invoked after each test function in the module."""
        LOGGER.info("STARTED: Teardown Operations.")
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
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
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cleanup: Cluster status checked successfully")
        LOGGER.info("Done: Teardown completed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-39902")
    @CTFailOn(error_handler)
    def test_degraded_reads_safe_server_pod_shutdown(self):
        """Following test steps tests degraded READs after server pod down -safe pod shutdown."""
        LOGGER.info("STARTED: Test to verify degraded reads after safe server pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-39902'
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

        LOGGER.info("Step 3: Shutdown the server pod safely by making replicas=0")
        LOGGER.info("Get server pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting server pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 3: Successfully shutdown/deleted server pod %s by making replicas=0",
                    pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster has some failures due to server pod %s has gone down.",
                    pod_name)

        LOGGER.info("Step 5: Check services status that were running on server pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of server pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services on the remaining pods are in online state")

        LOGGER.info("Step 7: Perform READs & verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs & verified DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded reads after safe server pod shutdown.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-39903")
    @CTFailOn(error_handler)
    def test_degraded_reads_unsafe_server_pod_shutdown(self):
        """Following test steps tests degraded READs after server pod down - unsafe shutdown."""
        LOGGER.info("STARTED: Test to verify degraded reads after unsafe server pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-39903'
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

        LOGGER.info("Step 3: Shutdown the server pod by deleting deployment (unsafe)")
        LOGGER.info("Get server pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting server pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0],
                                  f"Failed to delete server pod {pod_name} by deleting deployment")
        LOGGER.info(
            "Step 3: Successfully shutdown/deleted server pod %s by deleting deployment", pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster has some failures due to server pod %s has gone down.",
                    pod_name)

        LOGGER.info("Step 5: Check services status that were running on server pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of server pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services on the remaining pods are in online state")

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify degraded reads after unsafe server pod shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-39904")
    @CTFailOn(error_handler)
    def test_reads_during_server_pod_down(self):
        """Following test steps tests degraded reads while server pod is going down."""
        LOGGER.info("STARTED: Test to verify degraded reads during server pod is going down.")
        event = threading.Event()  # Event to be used to send intimation of server pod deletion

        LOGGER.info("Step 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-39904'
        self.s3_clean = users
        output = Queue()
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    nsamples=30, nclients=20,
                                                    log_prefix=self.test_prefix,
                                                    skipread=True, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs & verify DI on the written data in background")
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 5, 'nsamples': 30, 'skipwrite': True, 'skipcleanup': True,
                'output': output}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started READs & verified DI on the written data in "
                    "background")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 3: Shutdown the server pod by deleting deployment (unsafe)")
        LOGGER.info("Get server pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting server pod %s", pod_name)
        LOGGER.debug("Setting the Thread event")
        event.set()
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0],
                                  f"Failed to delete server pod {pod_name} by deleting deployment")
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        LOGGER.info(
            "Step 3: Successfully shutdown/deleted server pod %s by deleting deployment", pod_name)

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster has some failures due to server pod %s has gone down.",
                    pod_name)

        LOGGER.info("Step 5: Check services status that were running on serve pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of server pod %s are in offline state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pods %s are in online state", pod_list)

        event.clear()
        thread.join()
        LOGGER.info("Event is cleared and Thread has joined back.")
        responses = {}
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

        LOGGER.info("Step 2: Successfully completed READs & verified DI on the written data in "
                    "background")

        LOGGER.info("Step 7: Create IAM user with multiple buckets and run IOs when cluster has "
                    "some failures due to server pod %s going down.", pod_name)
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-39904-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully created IAM user with multiple buckets and ran IOs "
                    "when cluster has some failures due to server pod %s has gone down.", pod_name)
        LOGGER.info("ENDED: Test to verify degraded reads during server pod is going down.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-39905")
    @CTFailOn(error_handler)
    def test_degraded_writes_safe_server_pod_shutdown(self):
        """Following test steps tests degraded writes after safe server pod shutdown."""
        LOGGER.info("STARTED: Test to verify degraded writes after safe server pod shutdown.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes. 0B + (1KB - "
                    "512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-39905'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the server pod safely by making replicas=0")
        LOGGER.info("Get server pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        hostname = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting server pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0],
                                  f"Failed to delete server pod {pod_name} by making replicas=0")
        self.deployment_name = resp[1]
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS
        LOGGER.info(
            "Step 2: Successfully shutdown/deleted server pod %s by making replicas=0", pod_name)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster has some failures due to server pod %s has gone down.",
                    pod_name)

        LOGGER.info("Step 4: Check services status that were running on server pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=hostname)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of server pod %s are in offline state.", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services on remaining pods are in online state")

        LOGGER.info("Step 6: Perform WRITEs, READs & verify DI on the already created bucket")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Successfully performed WRITEs, READs & verify DI on the already "
                    "created bucket")

        LOGGER.info("ENDED: Test to verify degraded writes after safe server pod shutdown.")
