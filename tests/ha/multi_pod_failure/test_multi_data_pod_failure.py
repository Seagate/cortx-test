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
HA test suite for Multiple (K) Data Pods Failure
"""

import logging
import os
import secrets
import threading
import time
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import constants as const
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
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class TestMultiDataPodFailure:
    """
    Test suite for Multiple (K) Data Pods Failure
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.username = list()
        cls.password = list()
        cls.node_master_list = list()
        cls.hlth_master_list = list()
        cls.node_worker_list = list()
        cls.pod_name_list = list()
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.node_name = cls.deploy = cls.kvalue = None
        cls.pod_dict = dict()
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = secrets.SystemRandom()

        for node in range(len(CMN_CFG["nodes"])):
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
                cls.node_worker_list.append(LogicalNode(hostname=cls.host,
                                                        username=cls.username[node],
                                                        password=cls.password[node]))

        cls.rest_obj = S3AccountOperations()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
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
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.restore_pod = self.restore_method = self.deployment_name = None
        self.deployment_backup = None
        if not os.path.exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
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
                                                  f"{self.restore_method} way")
                LOGGER.info("Successfully restored pod %s by %s way",
                            pod_name, self.restore_method)
        if os.path.exists(self.test_dir_path):
            sysutils.remove_dirs(self.test_dir_path)
        # TODO: Will need DTM support for pod restart and recovery so need to redeploy
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
    @pytest.mark.tags("TEST-35772")
    def test_degraded_reads_kpods_failure(self):
        """
        Test to verify degraded READs after all K data pods are failed.
        """
        LOGGER.info("Started: Test to verify degraded READs after all K data pods are failed.")

        LOGGER.info("STEP 1: Perform WRITEs/READs/verify DI with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35772'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, kvalue=self.kvalue)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 3: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True, nsamples=2, nclients=2,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed READs and verified DI on the written data")

        LOGGER.info("Completed: Test to verify degraded READs after all K data pods are failed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35771")
    def test_degraded_reads_till_kpods_fail(self):
        """
        Test to verify degraded READs after each pod failure till K data pods fail.
        """
        LOGGER.info("Started: Test to verify degraded READs after each pod failure till K "
                    "data pods fail.")

        LOGGER.info("STEP 1: Perform WRITEs/READs/Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35771'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown %s (K) data pods one by one and verify read/verify "
                    "after each pod down.", self.kvalue)
        for count in range(1, self.kvalue+1):
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                down_method=const.RESTORE_DEPLOYMENT_K8S)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1])[0]
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_dict[pod_name] = pod_data
            self.pod_name_list.append(pod_name)
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("Deleted %s data pod %s by deleting deployment (unsafe)", count, pod_name)

            LOGGER.info("Step 3: Perform READs and verify DI on the written data")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix, skipwrite=True,
                                                        skipcleanup=True, nsamples=2, nclients=2,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: Performed READs and verified DI on the written data")
        LOGGER.info("Step 2: %s (K) %s data pods shutdown one by one successfully and read/verify "
                    "after each pod down verified", self.kvalue, self.pod_name_list)

        LOGGER.info("Completed: Test to verify degraded READs after each pod failure till K "
                    "data pods fail.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35789")
    def test_k_rc_pod_fail(self):
        """
        Test to Verify degraded IOs after RC pod is taken down in loop till K pod failures.
        """
        LOGGER.info("Started: Test to Verify degraded IOs after RC pod is taken down in loop "
                    "till K pod failures.")

        LOGGER.info("STEP 1: Perform WRITE/READ/Verify/DELETEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35789'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITE/READ/Verify/DELETEs with variable sizes objects.")

        LOGGER.info("Shutdown RC node pod in loop and check IOs.")
        count = 1
        while self.kvalue > 0:
            LOGGER.info("Step 2: Get the RC node pod details.")
            pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
            rc_node = self.ha_obj.get_rc_node(self.node_master_list[0])
            rc_info = \
                self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
            self.node_name = list(rc_info.values())[0]
            LOGGER.info("RC Node is running on %s node", self.node_name)
            LOGGER.info("Get the data pod running on %s node", self.node_name)
            data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
            rc_datapod = None
            for pod_name, node in data_pods.items():
                if node == self.node_name:
                    rc_datapod = pod_name
                    break
            self.pod_name_list.append(rc_datapod)
            LOGGER.info("Step 2: RC node %s has data pod: %s ", self.node_name, rc_datapod)

            LOGGER.info("Step 3: Shutdown %s data pod %s by deleting deployment (unsafe)",
                        count, rc_datapod)
            pod_data = list()
            pod_data.append(self.node_master_list[0].get_pod_hostname
                            (pod_name=rc_datapod))  # hostname
            resp = self.node_master_list[0].delete_deployment(pod_name=rc_datapod)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete {count} pod {rc_datapod} by "
                                               f"deleting deployment (unsafe)")
            pod_data.append(resp[1])  # deployment_backup
            pod_data.append(resp[2])  # deployment_name
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            self.pod_dict[rc_datapod] = pod_data
            LOGGER.info("Step 3: Deleted %s pod %s by deleting deployment (unsafe)",
                        count, rc_datapod)

            LOGGER.info("Step 4: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 4: Cluster is in degraded state")

            LOGGER.info("Step 5: Check services status that were running on pods which are deleted")
            hostname = self.pod_dict.get(rc_datapod)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[rc_datapod], fail=True,
                                                               hostname=hostname)
            assert_utils.assert_true(resp[0], resp[1])
            pod_list.remove(rc_datapod)
            LOGGER.info("Step 5: Services of pods are in offline state")

            LOGGER.info("Step 6: Check services status on remaining pods %s", pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 6: Services of pods are in online state")

            LOGGER.info("STEP 7: Perform WRITE/READ/Verify/DELETEs with variable object sizes.")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = f'test-35789-{count}'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        nsamples=2, nclients=2, setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 7: Performed WRITE/READ/Verify/DELETEs with variable sizes objects.")
            count += 1
            self.kvalue -= 1
        LOGGER.info("Shutdown %s RC node pods in loop and ran IOs", (count - 1))

        LOGGER.info("Completed: Test to Verify degraded IOs after RC pod is taken down in loop "
                    "till K pod failures.")

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35790")
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    def test_ios_during_data_kpods_down_safe(self):
        """
        Test to verify continuous IOs while k data pods are failing one by one by scale replicas
        method
        """
        LOGGER.info("STARTED: Test to verify IOs during k data pods are failing one by one")
        event = threading.Event()  # Event to be used to send when server pods going down
        wr_bucket = self.kvalue * 5 + HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        remaining_bkt = 10
        del_bucket = wr_bucket - remaining_bkt
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]['accesskey']
        secret_key = list(users.values())[0]['secretkey']
        test_prefix_del = 'test-delete-35790'
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Create %s buckets and put variable size objects for parallel DELETEs",
                    wr_bucket)
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
        test_prefix_read = 'test-read-35790'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Starting three independent background threads for READs, WRITEs & DELETEs.")
        LOGGER.info("Step 3: Start Continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = list(s3_data)
        get_random_buck = self.system_random.sample(bucket_list, del_bucket)
        del_random_buck = get_random_buck.copy()
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': del_random_buck,
                'output': del_output, 'bkts_to_del': del_bucket}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 3: Successfully started DELETEs in background for %s buckets",
                    del_bucket)

        LOGGER.info("Step 4: Perform WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-35790'
        output_wr = Queue()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'event_set_clr': event_set_clr, 'setup_s3bench': False}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 4: Successfully started WRITEs with variable sizes objects"
                    " in background")

        LOGGER.info("Waiting for %s seconds to perform some WRITEs",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])
        LOGGER.info("Step 5: Perform READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd, "setup_s3bench": False, 'event_set_clr': event_set_clr}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 5: Successfully started READs and verified DI on the written data in "
                    "background")
        LOGGER.info("Waiting for %s seconds to perform READs",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 6: Shutdown random %s (K) data pods by making replicas=0 and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            kvalue=self.kvalue, event=event, event_set_clr=event_set_clr)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 6: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 7: Verify status for In-flight READs/WRITEs/DELETEs while "
                    "%s (K) data pods were going down.", self.kvalue)
        LOGGER.info("Waiting for background IOs thread to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 7.1: Verify status for In-flight DELETEs while %s (K) data pods were"
                    "going down", self.kvalue)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        fail_del_bkt = del_resp[1]
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        # event_del_bkt = del_resp[0]
        # assert_utils.assert_true(len(event_del_bkt), "Expected DELETEs failures during data "
        #                                              f"pod down {event_del_bkt}")
        assert_utils.assert_false(len(fail_del_bkt), "Expected pass, buckets which failed in "
                                                     f"DELETEs: {fail_del_bkt}.")
        LOGGER.info("Step 7.1: Verified status for In-flight DELETEs while %s (K) data"
                    " pods were going down", self.kvalue)

        LOGGER.info("Step 7.2: Verify status for In-flight WRITEs while %s (K) data pods going "
                    "down should be failed/error.", self.kvalue)
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
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"WRITEs logs which contain pass: {resp[1]}")
        LOGGER.info("Step 7.2: Verified status for In-flight WRITEs while %s (K) data pods "
                    "going down.", self.kvalue)

        LOGGER.info("Step 7.3: Verify status for In-flight READs/Verify DI while %s (K)"
                    " data pods going down should be failed/error.", self.kvalue)
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        LOGGER.debug("Pass logs list: %s", pass_logs)
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        LOGGER.debug("Fail logs list: %s", fail_logs)
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Reads logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Reads logs which contain pass: {resp[1]}")
        LOGGER.info("Step 7.3: Verified status for In-flight READs/Verify DI while %s (K)"
                    " data pods going down.", self.kvalue)
        LOGGER.info("Step 7: Verified status for In-flight READs/WRITEs/DELETEs while %s (K)"
                    " data pods were going down.", self.kvalue)

        LOGGER.info("Step 8: Perform IOs with variable sizes objects.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 8: Perform WRITEs-READs-Verify with variable object sizes "
                        "on degraded cluster with new user")
            users = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_read = 'test-35790-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read,
                                                    nsamples=2, nclients=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed IOs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify continuous IOs while k data pods are failing one by one")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35777")
    def test_reads_writes_during_kpods_down(self):
        """
        This test tests continuous READs/WRITEs while pods are failing till K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify continuous READs/WRITEs while %s (K) data pods "
                    "were going down.", self.kvalue)

        event = threading.Event()  # Event to be used to send intimation of data pod deletion
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean = users

        LOGGER.info("Step 1: Perform READs/WRITEs with variable object sizes during "
                    "data pod down by delete deployment.")
        LOGGER.info("Step 1.1: Perform WRITEs with variable object sizes for parallel READs")
        test_prefix_read = 'test-read-35777'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1.1: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Step 1.2: Start WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-35777'
        output_wr = Queue()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr, 'setup_s3bench': False, 'event_set_clr': event_set_clr}
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
                'output': output_rd, 'setup_s3bench': False, 'event_set_clr': event_set_clr}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 1.3: Successfully started READs and verified DI on the written data in "
                    "background")
        LOGGER.info("Step 1: Successfully started READs & WRITES in background.")
        LOGGER.info("Sleep for %s sec for some IOs", HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 2: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            kvalue=self.kvalue, event=event, down_method=const.RESTORE_DEPLOYMENT_K8S,
            event_set_clr=event_set_clr)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Joining background thread. Waiting for %s seconds to "
                    "collect the queue logs", HA_CFG["common_params"]["60sec_delay"])
        thread_rd.join()
        thread_wri.join()
        LOGGER.debug("Threads has joined")

        LOGGER.info("Step 3: Verify responses from WRITEs & READs/VerifyDI background processes")
        LOGGER.info("Step 3.1: Verify status for In-flight WRITEs while %s (K) data pods going "
                    "down should be failed/error.", self.kvalue)
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
        LOGGER.info("Step 3.1: Verified status for In-flight WRITEs while %s (K) data pods "
                    "going down.", self.kvalue)

        LOGGER.info("Step 3.2: Verify status for In-flight READs/Verify DI while %s"
                    " (K) data pods going down should be failed/error.", self.kvalue)
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
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"READs/VerifyDI logs which contain pass: {resp[1]}")
        LOGGER.info("Step 3.2: Verified status for In-flight READs/VerifyDI while %s (K)"
                    " data pods going down.", self.kvalue)
        LOGGER.info("Step 3: Verified responses from WRITEs & READs/VerifyDI background processes")

        LOGGER.info("STEP 4: Perform IOs with variable object sizes on degraded cluster")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_write = 'test-35777-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_write,
                                                    skipcleanup=True, nsamples=2, nclients=2,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed IOs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify continuous READs/WRITEs while %s (K) data pods "
                    "were going down.", self.kvalue)

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35779")
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    def test_deletes_after_kpods_failure(self):
        """
        This test tests Degraded DELETEs after all K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify DELETEs after %s (K) data pods down", self.kvalue)
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        event = threading.Event()
        wr_output = Queue()
        del_output = Queue()
        LOGGER.info("Step 1: Create %s buckets & perform WRITEs with variable size objects.",
                    wr_bucket)
        LOGGER.info("Create IAM user with name %s", self.s3acc_name)
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
        LOGGER.info("Step 1: Successfully created %s buckets & perform WRITEs with variable size "
                    "objects.", wr_bucket)

        LOGGER.info("Step 2: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, kvalue=self.kvalue)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

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

        LOGGER.info("Step 4: Perform READs on the remaining %s buckets.", remain_bkt)
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
        LOGGER.info("Step 4: Successfully performed READs on the remaining %s buckets.", remain_bkt)

        LOGGER.info("ENDED: Test to verify DELETEs after %s (K) data pods down.", self.kvalue)

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35773")
    def test_reads_during_kpods_down(self):
        """
        This test tests READs while pods are failing till K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify READs during %s (K) data pods down", self.kvalue)
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35773'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 2: Perform READs/VerifyDI on written data in background")
        output = Queue()
        event = threading.Event()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output, 'event_set_clr': event_set_clr, 'setup_s3bench': False}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started READs/VerifyDI on written data in background")

        LOGGER.info("Step 3: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            kvalue=self.kvalue, event=event, down_method=const.RESTORE_DEPLOYMENT_K8S,
            event_set_clr=event_set_clr)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 4: Verify status for In-flight READs/Verify DI while %s (K) data pods "
                    "going down should be failed/error.", self.kvalue)
        thread.join()
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain pass: {resp[1]}")
        LOGGER.info("Step 4: Verified status for In-flight READs/Verify DI while %s (K) data pods "
                    "going down.", self.kvalue)

        LOGGER.info("STEP 5: Perform IOs with variable object sizes on degraded cluster")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-35773-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed IOs with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify continuous READs during %s (K) data pods down",
                    self.kvalue)

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35776")
    def test_writes_during_kpods_down(self):
        """
        This test tests WRITEs while pods are failing till K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify WRITEs during %s (K) data pods down", self.kvalue)
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes in background")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35776'
        self.s3_clean.update(users)
        output = Queue()
        event = threading.Event()
        event_set_clr = [False]
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output, 'event_set_clr': event_set_clr}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 1: Successfully started WRITEs with variable sizes objects in background")

        LOGGER.info("Step 2: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            kvalue=self.kvalue, event=event, down_method=const.RESTORE_DEPLOYMENT_K8S,
            event_set_clr=event_set_clr)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 3: Verify status for In-flight WRITEs while %s (K) data pods going "
                    "down should be failed/error.", self.kvalue)
        thread.join()
        responses = dict()
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain pass: {resp[1]}")
        LOGGER.info("Step 3: Verified status for In-flight WRITEs while %s (K) data pods "
                    "going down.", self.kvalue)

        LOGGER.info("STEP 4: Perform IOs with variable object sizes on degraded cluster")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-35776-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Performed IOs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify WRITEs during %s (K) data pods down", self.kvalue)

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    @pytest.mark.tags("TEST-35780")
    def test_deletes_during_kpods_down(self):
        """
        This test tests DELETEs while pods are failing till K data pods are failed
        """
        LOGGER.info("STARTED: Test to verify DELETEs while pods are failing till K "
                    "data pods are failed.")
        event = threading.Event()  # Event to be used to send intimation of pod deletion
        wr_output = Queue()
        del_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        remaining_bkt = 10
        del_bucket = wr_bucket - remaining_bkt
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes. (0B - 128MB) on %s "
                    "buckets", wr_bucket)
        LOGGER.info("Create IAM user with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-35780'
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
        s3_data_del = wr_resp[0]  # Contains IAM user data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           "number of buckets")
        LOGGER.info("Step 1: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB) on %s buckets", wr_bucket)
        LOGGER.info("Step 2: Start Continuous DELETEs in background on random %s buckets",
                    del_bucket)
        get_random_buck = self.system_random.sample(buckets, del_bucket)
        del_random_buck = get_random_buck.copy()
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': del_random_buck,
                'output': del_output, 'bkts_to_del': del_bucket}
        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 2: Successfully started DELETEs in background for %s buckets", del_bucket)

        LOGGER.info("Step 3: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            kvalue=self.kvalue, event=event, down_method=const.RESTORE_DEPLOYMENT_K8S)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 4: Verify status for In-flight DELETEs while %s (K) pods data were"
                    "going down", self.kvalue)
        LOGGER.info("Waiting for background DELETEs thread to join. Waiting for %s seconds to "
                    "collect the queue logs", HA_CFG["common_params"]["60sec_delay"])
        thread.join()
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt), "Expected pass, buckets which failed in "
                                                     f"DELETEs: {fail_del_bkt}.")
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        # assert_utils.assert_true(len(event_del_bkt), "No bucket DELETEs failed during "
        #                                              f"data pod down {event_del_bkt}")
        LOGGER.info("Failed buckets while in-flight DELETEs operation : %s", event_del_bkt)
        LOGGER.info("Step 4: Verified status for In-flight DELETEs while %s (K) data pods were"
                    "going down", self.kvalue)

        LOGGER.info("Step 5: Perform DELETEs on remaining FailedToDelete buckets when pods were "
                    "going down, on degraded cluster.")
        rem_bkts_after_del = list(set(buckets) - set(get_random_buck))
        new_s3data = dict()
        for bkt in rem_bkts_after_del:
            new_s3data[bkt] = s3_data_del[bkt]
        fail_del_op = Queue()
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': event_del_bkt, 'output': fail_del_op}
        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = fail_del_op.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(event_del_bkt) or len(fail_del_bkt),
                                  f"Failed to delete buckets: either {event_del_bkt} or"
                                  f" {fail_del_bkt}")
        LOGGER.info("Step 5: Successfully performed DELETEs on remaining FailedToDelete buckets "
                    "when pods were going down, on degraded cluster.")

        LOGGER.info("Step 6: Verify read on the remaining %s buckets.", len(rem_bkts_after_del))
        rd_output = Queue()
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipdel': True, 'bkt_list': rem_bkts_after_del, 'di_check': True,
                'output': rd_output, 's3_data': new_s3data}
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
                                  len(event_di_bkt),
                                  "Expected pass in read and di check operations. Found failures "
                                  f"in READ: {fail_bkt_get} {event_bkt_get}"
                                  f"or DI_CHECK: {fail_di_bkt} {event_di_bkt}")
        LOGGER.info("Step 6: Successfully verified READs & DI check for remaining buckets")

        LOGGER.info("STEP 7: Create new user and perform WRITEs-READs-Verify-DELETEs with "
                    "variable object sizes on degraded cluster")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35780-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, nsamples=2,
                                                    nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Performed WRITEs-READs-Verify-DELETEs with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify DELETEs while pods are failing till K "
                    "data pods are failed.")

    # pylint: disable=multiple-statements
    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35781")
    def test_ios_during_kpods_down(self):
        """
        This test tests continuous READs/WRITEs/DELETEs while pods are failing till K
        data pods are failed
        """
        LOGGER.info("STARTED: Test to verify continuous READs/WRITEs/DELETEs while pods are "
                    "failing till K data pods are failed.")

        event = threading.Event()  # Event to be used to send when data pods going down
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        LOGGER.info("Step 1: Perform WRITEs with variable object sizes on %s buckets "
                    "for parallel DELETEs.", wr_bucket)
        wr_output = Queue()
        del_output = Queue()
        remaining_bkt = 10
        del_bucket = wr_bucket - remaining_bkt
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        access_key = list(users.values())[0]['accesskey']
        secret_key = list(users.values())[0]['secretkey']
        test_prefix_del = 'test-delete-35781'
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
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
        test_prefix_read = 'test-read-35781'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Starting three independent background threads for READs, WRITEs & DELETEs.")
        LOGGER.info("Step 3: Start Continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = list(s3_data)
        get_random_buck = self.system_random.sample(bucket_list, del_bucket)
        args = {'test_prefix': test_prefix_del, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkt_list': get_random_buck, 'output': del_output}
        thread_del = threading.Thread(target=self.ha_obj.put_get_delete,
                                      args=(event, s3_test_obj,), kwargs=args)
        thread_del.daemon = True  # Daemonize thread
        thread_del.start()
        LOGGER.info("Step 3: Successfully started DELETEs in background for %s buckets", del_bucket)

        LOGGER.info("Step 4: Perform WRITEs with variable object sizes in background")
        test_prefix_write = 'test-write-35781'
        output_wr = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_write,
                'nclients': 1, 'nsamples': 5, 'skipread': True, 'skipcleanup': True,
                'output': output_wr}
        thread_wri = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                      kwargs=args)
        thread_wri.daemon = True  # Daemonize thread
        thread_wri.start()
        LOGGER.info("Step 4: Successfully started WRITEs with variable sizes objects in background")

        LOGGER.info("Step 5: Perform READs and verify DI on the written data in background")
        output_rd = Queue()
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': test_prefix_read,
                'nclients': 1, 'nsamples': 5, 'skipwrite': True, 'skipcleanup': True,
                'output': output_rd}
        thread_rd = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,),
                                     kwargs=args)
        thread_rd.daemon = True  # Daemonize thread
        thread_rd.start()
        LOGGER.info("Step 5: Successfully started READs and verified DI on the written data in "
                    "background")
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 6: Shutdown %s (K) data pods one by one while continuous IOs in "
                    "background", self.kvalue)
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        LOGGER.info("Get pod names to be deleted")
        self.pod_name_list = self.system_random.sample(pod_list, self.kvalue)
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
            LOGGER.info("Deleted %s data pod %s by deleting deployment (unsafe)", count, pod_name)
        LOGGER.info("Step 6: Successfully shutdown %s (K) data pods one by one while continuous "
                    "IOs in background", self.kvalue)
        event.clear()

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in degraded state")

        LOGGER.info("Step 8: Check services status that were running on pods which are deleted.")
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
        LOGGER.info("Step 8: Services of pods are in offline state")

        LOGGER.info("Step 9: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 9: Services of remaining pods are in online state")

        LOGGER.info("Step 10: Verify status for In-flight READs/WRITEs/DELETEs while %s (K) "
                    "data pods were going down.", self.kvalue)
        LOGGER.info("Waiting for background IOs thread to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 10.1: Verify status for In-flight DELETEs while %s (K) data pods were"
                    "going down", self.kvalue)
        del_resp = tuple()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not del_resp:
            assert_utils.assert_true(False, "Background process failed to do deletes")
        fail_del_bkt = del_resp[1]
        rem_bkts_aftr_del = s3_test_obj.bucket_list()[1]
        assert_utils.assert_false(len(fail_del_bkt),
                                  f"Bucket deletion failed when cluster was online {fail_del_bkt}")
        assert_utils.assert_true(len(rem_bkts_aftr_del) < del_bucket,
                                 "Some bucket deletion expected during pods going down")
        LOGGER.info("Step 10.1: Verified status for In-flight DELETEs while %s (K) data pods were"
                    "going down", self.kvalue)

        LOGGER.info("Step 10.2: Verify status for In-flight WRITEs while %s (K) data pods going "
                    "down should be failed/error.", self.kvalue)
        responses_wr = dict()
        while len(responses_wr) != 2:
            responses_wr = output_wr.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_wr["pass_res"])
        fail_logs = list(x[1] for x in responses_wr["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain pass: {resp[1]}")
        LOGGER.info("Step 10.2: Verified status for In-flight WRITEs while %s (K) data pods "
                    "going down.", self.kvalue)

        LOGGER.info("Step 10.3: Verify status for In-flight READs/Verify DI while %s (K) data pods "
                    "going down should be failed/error.", self.kvalue)
        responses_rd = dict()
        while len(responses_rd) != 2:
            responses_rd = output_rd.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses_rd["pass_res"])
        fail_logs = list(x[1] for x in responses_rd["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs, pass_logs=False)
        # TODO: Expecting Failures when data pods going down. Re-test once CORTX-28541 is Resolved
        assert_utils.assert_true(len(resp[1]) <= len(fail_logs),
                                 f"Logs which contain pass: {resp[1]}")
        LOGGER.info("Step 10.3: Verified status for In-flight READs/Verify DI while %s (K) pods "
                    "going down.", self.kvalue)
        LOGGER.info("Step 10: Verified status for In-flight READs/WRITEs/DELETEs while %s (K) pods "
                    "were going down.", self.kvalue)

        LOGGER.info("Step 11: Perform IOs with variable sizes objects.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 11: Perform WRITEs-READs-Verify with variable object sizes "
                        "on degraded cluster with new user")
            users = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_read = 'test-35781-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read,
                                                    nsamples=2, nclients=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 11: Performed IOs with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify continuous READs/WRITEs/DELETEs while %s (K) pods "
                    "were going down.", self.kvalue)

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35774")
    def test_degraded_writes_till_kpods_fail(self):
        """
        Test to verify degraded WRITEs after each pod failure till K data pods fail.
        """
        LOGGER.info("Started: Test to verify degraded Writes after each pod failure till K "
                    "data pods fail.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35774'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown %s (K) data pods one by one and verify write/read/verify "
                    "after each pod down on new and existing buckets", self.kvalue)
        for count in range(1, self.kvalue+1):
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                down_method=const.RESTORE_DEPLOYMENT_K8S)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1])[0]
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_dict[pod_name] = pod_data
            self.pod_name_list.append(pod_name)
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("Deleted %s data pod %s by deleting deployment (unsafe)", count, pod_name)

            LOGGER.info("Step 3: Perform WRITEs, READs and verify DI on the already created "
                        "bucket")
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: Successfully performed WRITEs, READs and verify DI on the "
                        "written data")

            if CMN_CFG["dtm0_disabled"]:
                LOGGER.info("STEP 4: Create IAM user and perform WRITEs-READs-Verify with "
                            "variable object sizes on degraded cluster")
                users = self.mgnt_ops.create_account_users(nusers=1)
                test_prefix_new = f'test-35774-{count}'
                self.s3_clean.update(users)
                resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                            log_prefix=test_prefix_new, nclients=2,
                                                            skipcleanup=True, nsamples=2,
                                                            setup_s3bench=False)
                assert_utils.assert_true(resp[0], resp[1])
                LOGGER.info("Step 4: Performed IOs with variable sizes objects.")

        LOGGER.info("%s (K) %s data pods shutdown one by one successfully and write/read/verify "
                    "after each pod down on new and existing buckets verified", self.kvalue,
                    self.pod_name_list)

        LOGGER.info("Completed: Test to verify degraded WRITEs after each pod failure till K "
                    "data pods fail.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35775")
    def test_degraded_writes_kpods_failure(self):
        """
        Test to verify degraded WRITEs after all K data pods are failed.
        """
        LOGGER.info("Started: Test to verify degraded WRITEs after all K data pods are failed.")

        LOGGER.info("STEP 1: Perform WRITEs-READs-Verify with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35775'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown random %s (K) data pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            down_method=const.RESTORE_DEPLOYMENT_K8S, kvalue=self.kvalue)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1]:
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 2: Successfully shutdown %s (K) data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 3: Perform WRITEs-READs-Verify and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nsamples=2, nclients=2,
                                                    setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Performed WRITEs-READs-Verify and verified DI on the written data")

        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("STEP 4: Create IAM user and perform WRITEs-READs-Verify with "
                        "variable object sizes on degraded cluster")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-35775-1'
            self.s3_clean.update(users)
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True, nsamples=2, nclients=2,
                                                        setup_s3bench=False)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 4: Performed IOs with variable sizes objects.")

        LOGGER.info("Completed: Test to verify degraded WRITEs after all K data pods are failed.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35778")
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    def test_degraded_deletes_till_kpods_fail(self):
        """
        Test to verify degraded DELETEs after each pod failure till K data pods fail.
        """
        LOGGER.info("Started: Test to verify degraded Deletes after each pod failure till K "
                    "data pods fail.")
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
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
        self.test_prefix = 'test-35778'
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
                                                           "number of buckets")
        LOGGER.info("Step 1: Successfully created %s buckets & "
                    "perform WRITEs with variable size objects.", wr_bucket)

        LOGGER.info("Step 2: Shutdown %s (K) data pods one by one and perform Delete on random %s"
                    " buckets and verify read on remaining bucket after each pod down",
                    self.kvalue, del_bucket)
        for count in range(1, self.kvalue+1):
            resp = self.ha_obj.delete_kpod_with_shutdown_methods(
                master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
                down_method=const.RESTORE_DEPLOYMENT_K8S)
            assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
            pod_name = list(resp[1])[0]
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_dict[pod_name] = pod_data
            self.pod_name_list.append(pod_name)
            self.restore_pod = self.deploy = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S
            assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
            LOGGER.info("Deleted %s data pod %s by deleting deployment (unsafe)", count, pod_name)

            LOGGER.info("Step 3: Perform DELETEs on random %s buckets", del_bucket)
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
            LOGGER.info("Step 3: Successfully performed DELETEs on random %s buckets", del_bucket)
            wr_bucket = len(remain_bkt)

            LOGGER.info("Step 4: Perform READs on the remaining %s buckets", remain_bkt)
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
            LOGGER.info("Step 4: Successfully performed READs on the remaining %s buckets.",
                        remain_bkt)

        LOGGER.info("Shutdown %s (K) %s data pods one by one and performed Deletes on random "
                    "buckets and verified read on remaining bucket after each pod down",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Completed: Test to verify degraded DELETEs after each pod failure till K "
                    "data pods fail.")
