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
HA test suite for Multiple (K) Pods Failure
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
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=R0904
class TestMultiPodFailure:
    """
    Test suite for Multiple (K) Pods Failure
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
        cls.restore_node = cls.node_name = cls.deploy = cls.kvalue = None
        cls.restore_ip = cls.node_iface = cls.new_worker_obj = cls.node_ip = None
        cls.pod_dict = {}
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
        """
        This function will be invoked prior to each test case.
        """
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
        LOGGER.info("Get the value of K for the given cluster.")
        resp = self.ha_obj.get_config_value(self.node_master_list[0])
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            LOGGER.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        LOGGER.info("The cluster has %s parity pods", self.kvalue)
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
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
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if self.restore_pod:
            for pod_name in self.pod_name_list:
                deployment_name = self.pod_dict.get(pod_name)[2]
                deployment_backup = self.pod_dict.get(pod_name)[1]
                resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                               restore_method=self.restore_method,
                                               restore_params={"deployment_name": deployment_name,
                                                               "deployment_backup":
                                                                   deployment_backup})
                LOGGER.debug("Response: %s", resp)
                assert_utils.assert_true(resp[0], "Failed to restore pod by "
                                                  f"{self.restore_method} way")
                LOGGER.info("Successfully restored pod %s by %s way",
                            pod_name, self.restore_method)
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

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35772")
    @CTFailOn(error_handler)
    def test_degraded_reads_kpods_failure(self):
        """
        Test to verify degraded READs after all K data pods are failed.
        """
        LOGGER.info("Started: Test to verify degraded READs after all K data pods are failed.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35772'
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

        LOGGER.info("Step 3: Shutdown the data pod by deleting deployment (unsafe)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
                                               "deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
        LOGGER.info("Step 3: Successfully deleted %s data pods", self.kvalue)

        LOGGER.info("Step 4: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 4: Cluster is in degraded state")

        LOGGER.info("Step 5: Check services status that were running on pods which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some pods not stopped.")
        LOGGER.info("Step 5: Services of pods are in offline state")

        LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Services of pod are in online state")

        LOGGER.info("Step 7: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("Completed: Test to verify degraded READs after all K data pods are failed.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35771")
    @CTFailOn(error_handler)
    def test_degraded_reads_till_kpods_fail(self):
        """
        Test to verify degraded READs after each pod failure till K data pods fail.
        """
        LOGGER.info("Started: Test to verify degraded READs after each pod failure till K "
                    "data pods fail.")

        LOGGER.info("STEP 1: Perform WRITEs with variable object sizes. 0B + (1KB - 512MB)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35771'
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

        LOGGER.info("Shutdown %s (K) data pods one by one and verify read/verify "
                    "after each pod down.", self.kvalue)
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Step 3: Shutdown %s data pod %s by deleting deployment (unsafe)",
                        count, pod_name)
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
                                               "deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Step 3: Deleted %s pod %s by deleting deployment (unsafe)",
                        count, pod_name)

            LOGGER.info("Step 4: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 4: Cluster is in degraded state")

            LOGGER.info("Step 5: Check services status that were running on pods which are deleted")
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            assert_utils.assert_true(resp[0], resp[1])
            pod_list.remove(pod_name)
            LOGGER.info("Step 5: Services of pods are in offline state")

            LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 6: Services of pod are in online state")

            LOGGER.info("Step 7: Perform READs and verify DI on the written data")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix, skipwrite=True,
                                                        skipcleanup=True, nsamples=2, nclients=2)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: Performed READs and verified DI on the written data")

        LOGGER.info("%s (K) data pods shutdown one by one successfully and read/verify "
                    "after each pod down verified", self.kvalue)

        LOGGER.info("Completed: Test to verify degraded READs after each pod failure till K "
                    "data pods fail.")

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35790")
    @CTFailOn(error_handler)
    def test_cont_ios_during_data_kpods_down_safe(self):
        """
        Test to verify continuous IOs while k data pods are failing one by one by scale replicas
        method
        """
        LOGGER.info("STARTED: Test to verify continuous IOs while k data pods are failing one "
                    "by one")

        LOGGER.info("Step 1: Perform Continuous WRITEs-READs-verify during k data pods are "
                    "going down")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35790'
        self.s3_clean = users
        event = threading.Event()
        output = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 3, 'skipcleanup': False, 'output': output}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started WRITEs-READs-verify in background")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 2: Shutdown the data pods by making replicas=0 (safe)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            event.set()
            resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to shutdown pod {pod_name} by making "
                                               "replicas=0")
            pod_data.append(resp[1])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_SCALE_REPLICAS
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by making replicas=0 (safe)", count, pod_name)
            event.clear()
        LOGGER.info("Step 2: Successfully deleted %s data pods", self.kvalue)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pods which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some pods not stopped.")
        LOGGER.info("Step 4: Services of pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Verify status for In-flight WRITEs-READs-verify while data pods are "
                    "down")
        thread.join()
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "Expected all pass, But Logs which contain "
                                                f"failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")

        LOGGER.info("Step 6: Successfully completed WRITEs-READs-verify running in background")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        self.test_prefix = 'test-35790-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, nsamples=2,
                                                    nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous IOs while k data pods are failing one by one")

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35791")
    @CTFailOn(error_handler)
    def test_cont_ios_during_server_kpods_down(self):
        """
        Test to verify continuous IOs while k server pods are failing one by one by delete
        deployment
        """
        LOGGER.info("STARTED: Test to verify continuous IOs while k server pods are failing one "
                    "by one")

        LOGGER.info("Step 1: Perform Continuous WRITEs-READs-verify during k server pods are "
                    "going down")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35791'
        self.s3_clean = users
        event = threading.Event()
        output = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 5, 'skipcleanup': False, 'output': output}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started WRITEs-READs-verify in background")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 2: Shutdown the server pods by deleting deployment (unsafe)")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            LOGGER.info("Deleting %s pod %s", count, pod_name)
            event.set()
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
                                               "deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
            event.clear()
        LOGGER.info("Step 2: Successfully deleted %s data pods", self.kvalue)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pods which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some pods not stopped.")
        LOGGER.info("Step 4: Services of pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Verify status for In-flight WRITEs-READs-verify while server pods are "
                    "down")
        thread.join()
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), "Expected all pass, But Logs which contain "
                                                f"failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")

        LOGGER.info("Step 6: Successfully completed WRITEs-READs-verify in background")

        LOGGER.info("Step 7: Create multiple buckets and run IOs")
        self.test_prefix = 'test-35791-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, nsamples=2,
                                                    nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous IOs while k server pods are failing one "
                    "by one")

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35777")
    @CTFailOn(error_handler)
    def test_reads_writes_during_kpods_down(self):
        """
        This test tests continuous READs/WRITEs while pods are failing till K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify continuous READs/WRITEs while %s (K) pods "
                    "were going down.", self.kvalue)

        LOGGER.info("Step 1: Start continuous IOs with variable object sizes in background")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35777'
        self.s3_clean = users
        output = Queue()
        event = threading.Event()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 2, 'nsamples': 30, 'skipcleanup': True, 'output': output}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 1: Successfully started continuous IOs with variable object sizes in "
                    "background")

        LOGGER.info("Step 2: Shutdown %s (K) data pods one by one while continuous IOs"
                    "in background", self.kvalue)
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        event.set()
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Shutdown %s data pod %s by deleting deployment (unsafe)", count, pod_name)
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
                                               f"deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
        LOGGER.info("Step 2: Shutdown %s (K) data pods one by one while continuous IOs in "
                    "background", self.kvalue)
        event.clear()

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pods which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some pods not stopped.")
        LOGGER.info("Step 4: Services of pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Joining background thread. Waiting for %s seconds to "
                    "collect the queue logs", HA_CFG["common_params"]["60sec_delay"])
        thread.join()
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        LOGGER.info("Step 6: Verify status for In-flight IOs while %s (K) pods going "
                    "down should be failed/error.", self.kvalue)
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"Expected all pass, But Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain passed IOs: {resp[1]}")
        LOGGER.info("Step 6: Verified status for In-flight IOs while %s (K) pods going "
                    "down should be failed/error.", self.kvalue)

        LOGGER.info("ENDED: Test to verify continuous READs/WRITEs while %s (K) pods "
                    "were going down.", self.kvalue)

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35779")
    @CTFailOn(error_handler)
    def test_deletes_after_kpods_down(self):
        """
        This test tests DELETEs after all K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify DELETEs after %s (K) data pods down", self.kvalue)
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        event = threading.Event()
        wr_output = Queue()
        del_output = Queue()
        LOGGER.info("Step 1: Create %s buckets & perform WRITEs with variable size objects.",
                    wr_bucket)
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-35779'
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)

        LOGGER.info("Create %s buckets and put variable size objects.", wr_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Step 1: Successfully created %s buckets & "
                    "perform WRITEs with variable size objects.", wr_bucket)

        LOGGER.info("Step 2: Shutdown %s (K) data pods one by one by deleting deployment ("
                    "unsafe)", self.kvalue)
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = random.sample(pod_list, self.kvalue)
        for count, pod_name in enumerate(self.pod_name_list):
            count += 1
            LOGGER.info("Shutdown %s data pod %s by deleting deployment (unsafe)", count, pod_name)
            pod_data = list()
            pod_data.append(
                self.node_master_list[0].get_pod_hostname(pod_name=pod_name))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {pod_name} by "
                                               f"deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[pod_name] = pod_data
            LOGGER.info("Deleted %s pod %s by deleting deployment (unsafe)", count, pod_name)
        LOGGER.info("Step 2: Successfully shutdown %s (K) data pods one by one by deleting "
                    "deployment (unsafe)", self.kvalue)

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pods which are deleted.")
        counter = 0
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname)
            LOGGER.debug("Services status on %s : %s", pod_name, resp)
            if not resp[0]:
                counter += 1
            pod_list.remove(pod_name)
        assert_utils.assert_equal(counter, 0, "Services on some pods not stopped.")
        LOGGER.info("Step 4: Services of pods are in offline state")

        LOGGER.info("Step 5: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of remaining pods are in online state")

        LOGGER.info("Step 6: Perform DELETEs on random %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        remain_bkt = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(remain_bkt), wr_bucket - del_bucket,
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(remain_bkt)} number of buckets")
        LOGGER.info("Step 6: Successfully performed DELETEs on random %s buckets", del_bucket)

        LOGGER.info("Step 7: Perform READs on the remaining %s buckets.", remain_bkt)
        rd_output = Queue()
        new_s3data = {}
        for bkt in remain_bkt:
            new_s3data[bkt] = s3_data[bkt]
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 's3_data': new_s3data, 'di_check': True,
                'output': rd_output}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        rd_resp = ()
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
        LOGGER.info("Step 7: Successfully performed READs on the remaining %s buckets.", remain_bkt)

        LOGGER.info("ENDED: Test to verify DELETEs after %s (K) data pods down.", self.kvalue)
