#!/usr/bin/python  # pylint: disable=R0902
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
HA test suite for Pod restart
"""

import logging
import os
import random
import threading
import time
from multiprocessing import Queue
from time import perf_counter_ns

import pytest

from commons import constants as const
from commons import commands as cmd
from commons.utils import system_utils as sysutils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import HA_CFG
from config.s3 import S3_CFG
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.motr.motr_core_k8s_lib import MotrCoreK8s
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=R0902
# pylint: disable=C0302
# pylint: disable=R0904
class TestPodRestart:
    """
    Test suite for Pod Restart
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
        cls.random_time = cls.s3_clean = cls.test_prefix = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.restore_node = cls.multipart_obj_path = None
        cls.restore_ip = cls.node_iface = cls.new_worker_obj = cls.node_ip = None
        cls.mgnt_ops = ManagementOPs()
        cls.system_random = random.SystemRandom()

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
        cls.motr_obj = MotrCoreK8s()

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.random_time = int(time.time())
        self.restore_node = False
        self.restore_ip = False
        self.s3_clean = {}
        self.s3acc_name = "{}_{}".format("ha_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.bucket_name = "ha-mp-bkt-{}".format(self.random_time)
        self.object_name = "ha-mp-obj-{}".format(self.random_time)
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        self.multipart_obj_path = os.path.join(self.test_dir_path, self.test_file)
        LOGGER.info("Precondition: Verify cluster is up and running and all pods are online.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Precondition: Verified cluster is up and running and all pods are online.")
        LOGGER.info("Precondition: Run IOs on healthy cluster & Verify DI on the same.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = f'ha-pod-restart-{int(perf_counter_ns())}'
        io_resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                       log_prefix=self.test_prefix,
                                                       skipcleanup=True)
        resp = self.ha_obj.delete_s3_acc_buckets_objects(users)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_true(io_resp[0], io_resp[1])
        LOGGER.info("Precondition: Ran IOs on healthy cluster & Verified DI on the same.")
        LOGGER.info("COMPLETED: Setup operations. ")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        if self.s3_clean:
            LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
            resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
            assert_utils.assert_true(resp[0], resp[1])
        if os.path.exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        LOGGER.info("STARTED: Teardown Operations.")
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
            assert_utils.assert_true(resp, f"Host {self.node_name} is not powered on")
        if self.restore_ip:
            LOGGER.info("Cleanup: Get the network interface up for %s ip", self.node_ip)
            self.new_worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(self.node_iface, "up"),
                                            read_lines=True)
            resp = sysutils.check_ping(host=self.node_ip)
            assert_utils.assert_true(resp, "Interface is still not up.")
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.node_master_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Teardown completed.")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34072")
    @CTFailOn(error_handler)
    def test_reads_after_pod_restart(self):
        """
        This test tests READs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify READs after data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 512MB(VM)/5GB(HW))")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34072'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed READs and verified DI on the written data")

        LOGGER.info("ENDED: Test to verify READs after data pod restart.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34074")
    @CTFailOn(error_handler)
    def test_write_after_pod_restart(self):
        """
        This test tests WRITEs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify WRITEs after data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs-READs-Verify with variable object sizes. 0B - 512MB("
                    "VM)/5GB(HW)")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34074'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Perform READs and verify DI on the written data")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed READs and verified DI on the written data")

        LOGGER.info("Step 9: Perform WRITEs-READs-Verify with variable object sizes. (0B - 512MB("
                    "VM)/5GB(HW))")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34074-1'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Performed WRITEs-READs-Verify with variable sizes objects.")

        LOGGER.info("ENDED: Test to verify WRITEs after data pod restart.")

    # pylint: disable=C0321
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34077")
    @CTFailOn(error_handler)
    def test_deletes_after_pod_restart(self):
        """
        This test tests DELETEs after data pod restart
        """
        LOGGER.info("STARTED: Test to verify DELETEs after data pod restart.")
        wr_output = Queue()
        del_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        event = threading.Event()

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 128MB)")
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-34077'
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

        LOGGER.info("Step 5: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB)")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Perform DELETEs on %s buckets", del_bucket)
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

        LOGGER.info("Step 8: Successfully Performed DELETEs on %s buckets", del_bucket)

        LOGGER.info("Step 9: Perform READs and verify on remaining buckets")
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
        LOGGER.info("Step 9: Successfully verified READs and DI check for remaining buckets: %s",
                    remain_bkt)

        LOGGER.info("Step 10: Again create %s buckets and put variable size objects and perform "
                    "delete on %s buckets", wr_bucket, del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipget': True, 'skipdel': True, 'bkts_to_wr': wr_bucket, 'output': wr_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        wr_resp = ()
        while len(wr_resp) != 3:
            wr_resp = wr_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        s3_data = wr_resp[0]  # Contains s3 data for passed buckets
        new_bkts = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(new_bkts) - len(remain_bkt), wr_bucket,
                                  f"Failed to create {wr_bucket} number of buckets. Created "
                                  f"{len(new_bkts) - len(remain_bkt)} number of buckets")

        LOGGER.info("Perform DELETEs on %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}

        self.ha_obj.put_get_delete(event, s3_test_obj, **args)
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        buckets1 = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets1), wr_bucket - del_bucket + len(remain_bkt),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket + len(remain_bkt)}. Remaining {len(buckets1)} number"
                                  " of buckets")

        LOGGER.info("Step 10: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB) and DELETEs on %s buckets", del_bucket)

        LOGGER.info("Step 11: Perform READs and verify on remaining buckets")
        for bkt in buckets1:
            if bkt in s3_data:
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
        LOGGER.info("Step 11: Successfully verified READs and DI check for remaining buckets: %s",
                    buckets1)

        LOGGER.info("ENDED: Test to verify DELETEs after data pod restart.")

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34080")
    @CTFailOn(error_handler)
    def test_mpu_after_pod_restart(self):
        """
        This test tests multipart upload after data pod restart.
        """
        LOGGER.info("STARTED: Test to verify multipart upload after data pod restart.")
        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)

        LOGGER.info("Step 5: Create and list buckets. Perform multipart upload for size %s MB in "
                    "total %s parts.", file_size, total_parts)
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.debug("Response: %s", resp)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
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
        LOGGER.info("Step 5: Sucessfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)

        LOGGER.info("Step 6: Start pod again by creating deployment.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.restore_pod = False
        LOGGER.info("Step 6: Successfully started pod again by creating deployment.")

        LOGGER.info("Step 7: Verify cluster status is in online state")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 8: Download the uploaded object %s & verify checksum", self.object_name)
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 8: Successfully downloaded the object %s & verified the checksum",
                    self.object_name)
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        system_utils.remove_file(self.multipart_obj_path)
        system_utils.remove_file(download_path)

        LOGGER.info("Step 9: Create and list buckets. Perform multipart upload for size %s MB in "
                    "total %s parts.", file_size, total_parts)
        test_bucket = f"ha-mp-bkt-{int(perf_counter_ns())}"
        test_object = f"ha-mp-obj-{int(perf_counter_ns())}"
        resp = self.ha_obj.create_bucket_to_complete_mpu(s3_data=self.s3_clean,
                                                         bucket_name=test_bucket,
                                                         object_name=test_object,
                                                         file_size=file_size,
                                                         total_parts=total_parts,
                                                         multipart_obj_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], resp)
        result = s3_test_obj.object_info(test_bucket, test_object)
        obj_size = result[1]["ContentLength"]
        LOGGER.debug("Uploaded object info for %s is %s", test_bucket, result)
        assert_utils.assert_equal(obj_size, file_size * const.Sizes.MB)
        upload_checksum = str(resp[2])
        LOGGER.info("Step 9: Sucessfully performed multipart upload for  size %s MB in "
                    "total %s parts.", file_size, total_parts)

        LOGGER.info("Step 10: Download the uploaded object %s & verify checksum", test_object)
        resp = s3_test_obj.object_download(test_bucket, test_object, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 10: Successfully downloaded the object %s & verified the checksum",
                    test_object)
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        system_utils.remove_file(self.multipart_obj_path)
        system_utils.remove_file(download_path)
        LOGGER.info("COMPLETED: Test to verify multipart upload after data pod restart.")

    # pylint: disable=too-many-locals
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34082")
    @CTFailOn(error_handler)
    def test_partial_mpu_after_pod_restart(self):
        """
        This test tests partial multipart upload after data pod restart
        """
        LOGGER.info("STARTED: Test to verify partial multipart upload after data pod restart.")
        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = random.sample(list(range(1, total_parts + 1)), total_parts // 2)
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        if os.path.exists(self.multipart_obj_path):
            os.remove(self.multipart_obj_path)
        system_utils.create_file(self.multipart_obj_path, file_size)
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]

        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
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
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 5: Start multipart upload for 5GB object in multiple parts and complete "
                    "partially for %s part out of %s", part_numbers, total_parts)
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
        LOGGER.info("Step 5: Successfully completed partial multipart upload for %s part out of "
                    "%s", part_numbers, total_parts)

        LOGGER.info("Step 6: Listing parts of partial multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        for part_n in res[1]["Parts"]:
            assert_utils.assert_list_item(part_numbers, part_n["PartNumber"])
        LOGGER.info("Step 6: Listed parts of partial multipart upload: %s", res[1])

        LOGGER.info("Step 7: Start pod again by creating deployment.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.restore_pod = False
        LOGGER.info("Step 7: Successfully started pod again by creating deployment.")

        LOGGER.info("Step 8: Verify cluster status is in online state")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Verified cluster is in online state. All services are up & running")

        remaining_parts = list(filter(lambda i: i not in part_numbers,
                                      list(range(1, total_parts + 1))))
        LOGGER.info("Step 9: Upload remaining %s parts out of %s", remaining_parts, total_parts)
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
        LOGGER.info("Step 9: Successfully uploaded remaining %s parts out of %s",
                    remaining_parts, total_parts)

        etag_list = parts_etag1 + parts_etag2
        parts_etag = sorted(etag_list, key=lambda d: d['PartNumber'])

        LOGGER.info("Step 10: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 10: Listed parts of multipart upload, Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 11: Completing multipart upload & check upload size is %s", file_size *
                    const.Sizes.MB)
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
        LOGGER.info("Step 11: Multipart upload completed and verified upload size is %s",
                    file_size * const.Sizes.MB)

        LOGGER.info("Step 12: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 12: Successfully downloaded the object and verified the checksum")
        LOGGER.info("Removing files %s and %s", self.multipart_obj_path, download_path)
        system_utils.remove_file(self.multipart_obj_path)
        system_utils.remove_file(download_path)
        LOGGER.info("COMPLETED: Test to verify partial multipart upload after data pod restart.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34083")
    @CTFailOn(error_handler)
    def test_copy_obj_after_pod_restart(self):
        """
        This test tests copy object after data pod restart
        """
        LOGGER.info("STARTED: Test to verify copy object after data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        event = threading.Event()
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        bkt_obj_dict = {}
        bucket2 = f"ha-bkt2-{int((perf_counter_ns()))}"
        object2 = f"ha-obj2-{int((perf_counter_ns()))}"
        bkt_obj_dict[bucket2] = object2
        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account with name %s", self.s3acc_name)
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}
        LOGGER.info("Step 5: Create and list buckets. Upload object to %s & copy object from the"
                    " same bucket to %s and verify copy object etags",
                    self.bucket_name, bucket2)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 5: Successfully created multiple buckets and uploaded object to %s "
                    "and copied to %s and verified copy object etags", self.bucket_name, bucket2)

        LOGGER.info("Step 6: Start pod again by creating deployment.")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        self.restore_pod = False
        LOGGER.info("Step 6: Successfully started pod again by creating deployment.")

        LOGGER.info("Step 7: Verify cluster status is in online state")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 8: Download the uploaded %s on %s & verify etags.", object2, bucket2)
        resp = s3_test_obj.get_object(bucket=bucket2, key=object2)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object2} of bucket {bucket2}.")
        LOGGER.info("Step 8: Downloaded the uploaded %s on %s & verified etags.", object2, bucket2)

        bucket3 = f"ha-bkt3-{int((perf_counter_ns()))}"
        object3 = f"ha-obj3-{int((perf_counter_ns()))}"
        bkt_obj_dict.pop(bucket2)
        bkt_obj_dict[bucket3] = object3
        LOGGER.info("Step 9: Perform copy of %s from already created/uploaded %s to %s and verify "
                    "copy object etags", self.object_name, self.bucket_name, bucket3)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  put_etag=put_etag,
                                                  bkt_op=False)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        LOGGER.info("Step 9: Performed copy of %s from already created/uploaded %s to %s and "
                    "verified copy object etags", self.object_name, self.bucket_name, bucket3)

        LOGGER.info("Step 10: Download the uploaded %s on %s & verify etags.", object3, bucket3)
        resp = s3_test_obj.get_object(bucket=bucket3, key=object3)
        LOGGER.info("Get object response: %s", resp)
        get_etag = resp[1]["ETag"]
        assert_utils.assert_equal(put_etag, get_etag, "Failed in verification of Put & Get Etag "
                                                      f"for object {object3} of bucket {bucket3}.")
        LOGGER.info("Step 10: Downloaded the uploaded %s on %s & verified etags.", object3, bucket3)
        LOGGER.info("COMPLETED: Test to verify copy object after data pod restart.")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34073")
    @CTFailOn(error_handler)
    def test_continuous_reads_during_pod_restart(self):
        """
        This test tests continuous reads during pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous READs during data pod restart.")

        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)

        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in online state")

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 512MB(VM)/5GB(HW))")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34073'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipread=True,
                                                    skipcleanup=True, nclients=10, nsamples=10)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Performed WRITEs with variable sizes objects.")

        LOGGER.info("Step 6: Perform READs and verify DI on the written data in background")
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 10, 'skipwrite': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()

        LOGGER.info("Step 6: Successfully started READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 7: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 7: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        event.clear()
        thread.join()

        LOGGER.info("Verifying responses from background process")
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 6: Successfully completed READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        self.test_prefix = 'test-34073-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous READs during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34086")
    @CTFailOn(error_handler)
    def test_pod_restart_node_down(self):
        """
        Verify IOs before and after data pod restart (pod shutdown by making worker node down).
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making worker node down.")

        LOGGER.info("Step 1: Shutdown data pod by shutting node on which its hosted.")
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
        LOGGER.info("Step 1: %s Node is shutdown where data pod was running.", data_node_fqdn)
        self.restore_node = True

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on data and server pod")
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
        LOGGER.info("Step 3: Services of data and server pods are in offline state")

        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(
            pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services status on remaining pod are in online state")

        LOGGER.info("Step 5: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34086'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: IOs completed successfully.")

        LOGGER.info("Step 6: Start the pod %s back by restarting the node %s",
                    data_pod_name, data_node_fqdn)
        LOGGER.info("Power on the %s down node.", )
        resp = self.ha_obj.host_power_on(host=data_node_fqdn)
        assert_utils.assert_true(resp, "Host is not powered on")
        LOGGER.info("Step 6: Node %s is restarted", data_node_fqdn)
        self.restore_node = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34086-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: IOs completed successfully.")

        LOGGER.info("COMPLETED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making worker node down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34085")
    @CTFailOn(error_handler)
    def test_pod_restart_node_nw_down(self):
        """
        Verify IOs before and after data pod restart,
        pod shutdown by making mgmt ip of worker node down.
        """
        LOGGER.info("STARTED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making mgmt ip of worker node down")

        LOGGER.info("Step 1: Shutdown data pod by making network down of node "
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
        LOGGER.info("Step 1: %s Node's network is down.", data_node_fqdn)
        self.restore_ip = True

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on data and server pod")
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
        LOGGER.info("Step 3: Services of data and server pods are in offline state")

        remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
        remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(
            pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services status on remaining pod are in online state")

        LOGGER.info("Step 5: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34085'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: IOs completed successfully.")

        LOGGER.info("Step 6: Get the network back up for node %s", data_node_fqdn)
        LOGGER.info("Get the network interface up for %s ip", self.node_ip)
        self.new_worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(self.node_iface, "up"),
                                        read_lines=True)
        resp = sysutils.execute_cmd(cmd.CMD_PING.format(self.node_ip),
                                    read_lines=True, exc=False)
        assert_utils.assert_not_in(b"100% packet loss", resp[1][0],
                                   f"Node interface still down. {resp}")
        LOGGER.info("Step 6: Network interface is back up for %s node", data_node_fqdn)
        self.restore_ip = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 8: Start IOs (create s3 acc, buckets and upload objects).")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34085-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: IOs completed successfully.")

        LOGGER.info("COMPLETED: Verify IOs before and after data pod restart, "
                    "pod shutdown by making mgmt ip of worker node down")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34091")
    @CTFailOn(error_handler)
    def test_different_data_pods_restart_loop(self):
        """
        This test tests IOs in degraded mode and after data pod restart in loop
        (different data pod down every time)
        """
        LOGGER.info("STARTED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (different data pod down every time)")

        LOGGER.info("Get data pod list to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)

        for pod in pod_list:
            LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
            pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod)
            LOGGER.info("Deleting pod %s", pod)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod} by deleting deployment"
                                               " (unsafe)")
            LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment "
                        "(unsafe)", pod)
            self.deployment_backup = resp[1]
            self.deployment_name = resp[2]
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S

            LOGGER.info("Step 2: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 2: Cluster is in degraded state")

            LOGGER.info("Step 3: Check services status that were running on pod %s", pod)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod], fail=True,
                                                               hostname=pod_host)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 3: Services of pod are in offline state")

            remain_pod_list = list(filter(lambda x: x != pod, pod_list))
            LOGGER.info("Step 4: Check services status on remaining pods %s", remain_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 4: Services of pod are in online state")

            LOGGER.info("Step 5: Create s3 account, create multiple buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34091'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 5: Successfully created s3 account and multiple buckets and ran IOs")

            LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Step 6: Successfully started the pod")
            self.restore_pod = False

            LOGGER.info("Step 7: Check cluster status")
            resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

            LOGGER.info("Step 8: Create s3 account, create multiple buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34091-1'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 8: Successfully created s3 account and multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (different data pod down every time)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34090")
    @CTFailOn(error_handler)
    def test_same_data_pod_restart_loop(self):
        """
        This test tests IOs in degraded mode and after data pod restart in loop
        (same pod down every time)
        """
        LOGGER.info("STARTED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (same pod down every time)")

        LOGGER.info("Get data pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod)

        loop_count = HA_CFG["common_params"]["loop_count"]
        for loop in range(1, loop_count):
            LOGGER.info("Running loop %s", loop)

            LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
            LOGGER.info("Deleting pod %s", pod)
            resp = self.node_master_list[0].delete_deployment(pod_name=pod)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], f"Failed to delete pod {pod} by deleting deployment"
                                               " (unsafe)")
            LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment "
                        "(unsafe)", pod)
            self.deployment_backup = resp[1]
            self.deployment_name = resp[2]
            self.restore_pod = True
            self.restore_method = const.RESTORE_DEPLOYMENT_K8S

            LOGGER.info("Step 2: Check cluster status")
            resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_false(resp[0], resp)
            LOGGER.info("Step 2: Cluster is in degraded state")

            LOGGER.info("Step 3: Check services status that were running on pod %s", pod)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod], fail=True,
                                                               hostname=pod_host)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 3: Services of pod are in offline state")

            remain_pod_list = list(filter(lambda x: x != pod, pod_list))
            LOGGER.info("Step 4: Check services status on remaining pods %s",
                        remain_pod_list)
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                               fail=False)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 4: Services of pod are in online state")

            LOGGER.info("Step 5: Create s3 account, create multiple buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34090'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 5: Successfully created s3 account and multiple buckets and ran IOs")

            LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
            resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
            LOGGER.info("Step 6: Successfully started the pod")
            self.restore_pod = False

            LOGGER.info("Step 7: Check cluster status")
            resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp)
            LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

            LOGGER.info("Step 8: Create s3 account, create multiple buckets and run IOs")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.s3_clean.update(users)
            self.test_prefix = 'test-34090-1'
            resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                        log_prefix=self.test_prefix,
                                                        skipcleanup=True)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 8: Successfully created s3 account and multiple buckets and ran IOs")

            LOGGER.info("Get recently created data pod name using deployment %s",
                        self.deployment_name)
            pod = self.node_master_list[0].get_recent_pod_name(deployment_name=self.deployment_name)
            pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)

        LOGGER.info("ENDED: Test to verify IOs in degraded mode and after data pod restart in "
                    "loop (same pod down every time)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34081")
    @CTFailOn(error_handler)
    def test_mpu_during_pod_restart(self):
        """
        This test tests multipart upload during data pod restart
        """
        LOGGER.info("STARTED: Test to verify multipart upload during data pod restart")

        file_size = HA_CFG["5gb_mpu_data"]["file_size"]
        total_parts = HA_CFG["5gb_mpu_data"]["total_parts"]
        part_numbers = list(range(1, total_parts + 1))
        random.shuffle(part_numbers)
        output = Queue()
        parts_etag = []
        download_file = self.test_file + "_download"
        download_path = os.path.join(self.test_dir_path, download_file)
        event = threading.Event()  # Event to be used to send intimation of pod restart

        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
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
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pods %s are in online state", remain_pod_list)

        LOGGER.info("Step 5: Start multipart upload of 5GB object in background")
        args = {'s3_data': self.s3_clean, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'file_size': file_size, 'total_parts': total_parts,
                'multipart_obj_path': self.multipart_obj_path, 'part_numbers': part_numbers,
                'parts_etag': parts_etag, 'output': output}
        thread = threading.Thread(target=self.ha_obj.start_random_mpu, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 5: Started multipart upload of 5GB object in background")

        time.sleep(HA_CFG["common_params"]["60sec_delay"])

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 5: Checking responses from background process")
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
        elif exp_failed_parts or failed_parts:
            assert_utils.assert_true(False, "Failed to upload parts when cluster was in good "
                                            f"state. Failed parts: {failed_parts} and "
                                            f"{exp_failed_parts}")
        LOGGER.info("Step 5: Successfully checked background process responses")

        parts_etag = sorted(parts_etag, key=lambda d: d['PartNumber'])
        LOGGER.info("Calculating checksum of file %s", self.multipart_obj_path)
        upload_checksum = self.ha_obj.cal_compare_checksum(file_list=[self.multipart_obj_path],
                                                           compare=False)[0]
        LOGGER.info("Step 5: Successfully uploaded all the parts of multipart upload.")

        LOGGER.info("Step 8: Listing parts of multipart upload")
        res = s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res)
        assert_utils.assert_equal(len(res[1]["Parts"]), total_parts)
        LOGGER.info("Step 8: Listed parts of multipart upload. Count: %s", len(res[1]["Parts"]))

        LOGGER.info("Step 9: Completing multipart upload")
        res = s3_mp_test_obj.complete_multipart_upload(mpu_id, parts_etag, self.bucket_name,
                                                       self.object_name)
        assert_utils.assert_true(res[0], res)
        res = s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res)
        LOGGER.info("Step 9: Multipart upload completed")

        LOGGER.info("Step 10: Download the uploaded object and verify checksum")
        resp = s3_test_obj.object_download(self.bucket_name, self.object_name, download_path)
        LOGGER.info("Download object response: %s", resp)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = self.ha_obj.cal_compare_checksum(file_list=[download_path],
                                                             compare=False)[0]
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match checksum: {upload_checksum},"
                                  f" {download_checksum}")
        LOGGER.info("Matched checksum: %s, %s", upload_checksum, download_checksum)
        LOGGER.info("Step 10: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 11: Create s3 account, create multiple buckets and run IOs")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34081-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 11: Successfully created s3 account and multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify multipart upload during data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34084")
    @CTFailOn(error_handler)
    def test_copy_object_during_pod_restart(self):
        """
        This test tests copy object during data pod restart
        """
        LOGGER.info("STARTED: Test to verify copy object during data pod restart")

        bkt_obj_dict = dict()
        bkt_obj_dict["ha-bkt-{}".format(self.random_time)] = "ha-obj-{}".format(self.random_time)
        output = Queue()
        event = threading.Event()

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pods %s are in online state", remain_pod_list)

        LOGGER.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        s3_test_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                endpoint_url=S3_CFG["s3_url"])
        LOGGER.info("Successfully created s3 account")
        self.s3_clean = {'s3_acc': {'accesskey': access_key, 'secretkey': secret_key,
                                    'user_name': self.s3acc_name}}

        LOGGER.info("Step 5: Create multiple buckets and upload object to %s and copy to other "
                    "bucket", self.bucket_name)
        resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  bkt_obj_dict=bkt_obj_dict,
                                                  file_path=self.multipart_obj_path)
        assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
        put_etag = resp[1]
        LOGGER.info("Step 5: Successfully Created multiple buckets and uploaded object to %s "
                    "and copied to other bucket", self.bucket_name)

        bkt_obj_dict1 = {}
        bkt_cnt = HA_CFG["copy_obj_data"]["bkt_multi"]
        for cnt in range(bkt_cnt):
            rd_time = perf_counter_ns()
            s3_test_obj.create_bucket(f"ha-bkt{cnt}-{rd_time}")
            bkt_obj_dict1[f"ha-bkt{cnt}-{rd_time}"] = f"ha-obj{cnt}-{rd_time}"
        bkt_obj_dict.update(bkt_obj_dict1)
        LOGGER.info("Step 6: Create multiple buckets and copy object from %s to other buckets in "
                    "background", self.bucket_name)
        args = {'s3_test_obj': s3_test_obj, 'bucket_name': self.bucket_name,
                'object_name': self.object_name, 'bkt_obj_dict': bkt_obj_dict1, 'output': output,
                'file_path': self.multipart_obj_path, 'background': True, 'bkt_op': False,
                'put_etag': put_etag}
        thread = threading.Thread(target=self.ha_obj.create_bucket_copy_obj, args=(event,),
                                  kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 6: Successfully started background process for copy object")
        # While loop to sync this operation with background thread to achieve expected scenario
        LOGGER.info("Waiting for creation of %s buckets", bkt_cnt)
        bkt_list = list()
        timeout = time.time() + 60 * 3
        while len(bkt_list) < bkt_cnt:
            time.sleep(HA_CFG["common_params"]["20sec_delay"])
            bkt_list = s3_test_obj.bucket_list()[1]
            if timeout < time.time():
                LOGGER.error("Bucket creation is taking longer than 3 mins")
                assert_utils.assert_true(False, "Please check background process logs")
        time.sleep(HA_CFG["common_params"]["20sec_delay"])

        LOGGER.info("Step 7: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 7: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        event.clear()

        LOGGER.info("Step 9: Checking responses from background process")
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
            assert_utils.assert_true(False, "Failed to do copy object when cluster was in degraded "
                                            f"state. Failed buckets: {failed_bkts}")
        elif exp_fail_bkt_obj_dict:
            LOGGER.info("Step 9.1: Retrying copy object to buckets %s",
                        list(exp_fail_bkt_obj_dict.keys()))
            resp = self.ha_obj.create_bucket_copy_obj(event, s3_test_obj=s3_test_obj,
                                                      bucket_name=self.bucket_name,
                                                      object_name=self.object_name,
                                                      bkt_obj_dict=exp_fail_bkt_obj_dict,
                                                      bkt_op=False, put_etag=put_etag)
            assert_utils.assert_true(resp[0], f"Failed buckets are: {resp[1]}")
            put_etag = resp[1]

        LOGGER.info("Step 10: Download the uploaded object and verify checksum")
        for key, val in bkt_obj_dict.items():
            resp = s3_test_obj.get_object(bucket=key, key=val)
            LOGGER.info("Get object response: %s", resp)
            get_etag = resp[1]["ETag"]
            assert_utils.assert_equal(put_etag, get_etag, "Failed in Etag verification of "
                                                          f"object {val} of bucket {key}. Put and "
                                                          f"Get Etag mismatch")
        LOGGER.info("Step 10: Successfully downloaded the object and verified the checksum")

        LOGGER.info("Step 11: Create s3 account, create multiple buckets and run IOs")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34084-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 11: Successfully created s3 account and multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify copy object during data pod restart")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34079")
    @CTFailOn(error_handler)
    def test_ios_during_pod_restart(self):
        """
        This test tests continuous READs/WRITEs/DELETEs in loop during data pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous READs/WRITEs/DELETEs in loop during data "
                    "pod restart")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)
        pod_list.remove(pod_name)
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state", pod_list)

        event = threading.Event()  # Event to be used to send when data pod restart start
        LOGGER.info("Step 5: Perform Continuous READs/WRITEs/DELETEs with variable object sizes. "
                    "0b + - 512Mb) during data pod restart.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34079'
        self.s3_clean.update(users)
        output = Queue()

        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 30, 'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 5: Successfully started READs/WRITEs/DELETEs in background")
        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod again by creating deployment")
        self.restore_pod = False

        LOGGER.info("Step 7: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")
        event.clear()
        thread.join()

        LOGGER.info("Step 8: Verify status for In-flight READs/WRITEs/DELETEs while pod was"
                    "restarting are successful without any failures.")
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"IOs during no pod restart contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]),
                                  f"IOs during pod restart contain failures: {resp[1]}")
        LOGGER.info("Step 8: Verified status for In-flight READs/WRITEs/DELETEs while pod was"
                    "restarting are successful without any failures.")

        LOGGER.info("COMPLETED: Test to verify continuous READs/WRITEs/DELETEs in loop during data "
                    "pod restart")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34078")
    @CTFailOn(error_handler)
    def test_continuous_deletes_during_pod_restart(self):
        """
        This test tests continuous DELETEs during pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous DELETEs during data pod restart.")

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Verify cluster status is in degraded state")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Verified cluster status is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)
        pod_list.remove(pod_name)
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state", pod_list)

        event = threading.Event()  # Event to be used to send when data pod restart start
        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 128MB)")
        wr_output = Queue()
        del_output = Queue()
        wr_bucket = HA_CFG["s3_bucket_data"]["no_buckets_for_deg_deletes"]
        del_bucket = wr_bucket - 10
        LOGGER.info("Create s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email,
                                               passwd=S3_CFG["CliConfig"]["s3_account"]["password"])
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.test_prefix = 'test-34078'
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
        s3_data = wr_resp[0]           # Contains s3 data for passed buckets
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(len(buckets), wr_bucket, f"Failed to create {wr_bucket} number "
                                                           f"of buckets. Created {len(buckets)} "
                                                           f"number of buckets")
        LOGGER.info("Step 5: Successfully performed WRITEs with variable object sizes. (0B - "
                    "128MB)")

        LOGGER.info("Step 6: Verify %s has %s buckets created", self.s3acc_name, wr_bucket)
        buckets = s3_test_obj.bucket_list()
        assert_utils.assert_equal(wr_bucket, len(buckets[1]), buckets)
        LOGGER.info("Step 6: Verified %s has %s buckets created", self.s3acc_name, wr_bucket)

        LOGGER.info("Step 7: Start Continuous DELETEs in background on %s buckets", del_bucket)
        args = {'test_prefix': self.test_prefix, 'test_dir_path': self.test_dir_path,
                'skipput': True, 'skipget': True, 'bkts_to_del': del_bucket, 'output': del_output}
        thread = threading.Thread(target=self.ha_obj.put_get_delete,
                                  args=(event, s3_test_obj,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 7: Successfully started continuous DELETEs in background on %s buckets",
                    del_bucket)

        LOGGER.info("Step 8: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 8: Successfully started the pod again by creating deployment")
        self.restore_pod = False

        LOGGER.info("Step 9: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 9: Verified cluster is in online state. All services are up & running")
        event.clear()
        thread.join()

        LOGGER.info("Step 10: Verify status for In-flight DELETEs while pod was"
                    "restarting are successful & check the remaining buckets.")
        del_resp = ()
        while len(del_resp) != 2:
            del_resp = del_output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        event_del_bkt = del_resp[0]
        fail_del_bkt = del_resp[1]
        assert_utils.assert_false(len(fail_del_bkt) or len(event_del_bkt),
                                  f"Bucket deletion failed {fail_del_bkt} {event_del_bkt}")
        buckets = s3_test_obj.bucket_list()[1]
        assert_utils.assert_equal(wr_bucket - del_bucket, len(buckets),
                                  f"Failed to delete {del_bucket} number of buckets from "
                                  f"{wr_bucket}. Remaining {len(buckets)} number of buckets")
        LOGGER.info("Step 10: Verified status for In-flight DELETEs while pod was"
                    "restarting are successful & remaining buckets count is %s", len(buckets))

        LOGGER.info("Step 11: Verify read on the remaining %s buckets.", buckets)
        rd_output = Queue()
        new_s3data = {}
        for bkt in buckets:
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
        LOGGER.info("Step 11: Successfully verified READs & DI check for remaining buckets: %s",
                    buckets)
        LOGGER.info("COMPLETED: Test to verify continuous DELETEs during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34075")
    @CTFailOn(error_handler)
    def test_continuous_writes_during_pod_restart(self):
        """
        Verify continuous WRITEs during data pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous Writes during data pod restart.")

        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        LOGGER.info("Step 5: Perform WRITEs with variable object sizes. (0B - 512MB(VM)/5GB(HW)) "
                    "in background")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34075'
        self.s3_clean.update(users)
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'skipread': True, 'skipcleanup': True, 'nclients': 1, 'nsamples': 30}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 5: Performed WRITEs with variable sizes objects in background.")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")
        event.clear()
        thread.join()

        LOGGER.info("Step 8: Verifying writes from background process")
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8: Successfully completed Writes in background")

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34075-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous Writes during data pod restart.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34076")
    @CTFailOn(error_handler)
    def test_continuous_read_write_during_pod_restart(self):
        """
        Verify continuous READ/WRITEs during data pod restart
        """
        LOGGER.info("STARTED: Test to verify continuous READ/WRITE during data pod restart.")

        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart

        LOGGER.info("Step 1: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 4: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services on remaining pods %s are in online state",
                    remain_pod_list)

        LOGGER.info("Step 5: Perform READ/WRITEs/VERIFY with variable object sizes in background")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-34076'
        self.s3_clean.update(users)
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'skipcleanup': True, 'nclients': 1, 'nsamples': 30}
        thread = threading.Thread(target=self.ha_obj.event_s3_operation, args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        LOGGER.info("Step 5: Performed READ/WRITEs/VERIFY with variable sizes objects in "
                    "background.")

        LOGGER.info("Step 6: Starting pod again by creating deployment using K8s command")
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 7: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Cluster is in good state. All the services are up and running")
        event.clear()
        thread.join()

        LOGGER.info("Step 8: Verifying read/writes from background process")
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        pass_logs = list(x[1] for x in responses["pass_res"])
        fail_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=pass_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=fail_logs)
        assert_utils.assert_false(len(resp[1]), f"Logs which contain failures: {resp[1]}")
        LOGGER.info("Step 8: Successfully completed Read/Writes in background")

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34076-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous READs/WRITE during data pod restart.")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34088")
    @CTFailOn(error_handler)
    def test_ios_rc_node_restart(self):
        """
        This test tests IOs before and after pod restart by making RC node down
        """
        LOGGER.info("STARTED: Test to verify IOs before & after pod restart by making RC node "
                    "down.")

        LOGGER.info("Step 1: Get the RC node and shutdown the same.")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)

        rc_node = self.motr_obj.get_primary_cortx_node().split("svc-")[1]
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        self.node_name = list(rc_info.values())[0]
        LOGGER.info("RC Node is running on %s node", self.node_name)
        LOGGER.info("Get the data pod running on %s node", self.node_name)
        data_pods = self.node_master_list[0].get_pods_node_fqdn(const.POD_NAME_PREFIX)
        server_pods = self.node_master_list[0].get_pods_node_fqdn(const.SERVER_POD_NAME_PREFIX)
        rc_datapod = rc_serverpod = None
        for pod_name, node in data_pods.items():
            if node == self.node_name:
                rc_datapod = pod_name
                break
        for server_pod, node in server_pods.items():
            if node == self.node_name:
                rc_serverpod = server_pod
                break

        LOGGER.info("RC node %s has data pod: %s and server pod : %s", self.node_name,
                    rc_datapod, rc_serverpod)
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=rc_datapod)
        LOGGER.info("Shutdown the RC node: %s", self.node_name)
        resp = self.ha_obj.host_safe_unsafe_power_off(host=self.node_name)
        assert_utils.assert_true(resp, f"{self.node_name} is not powered off")
        LOGGER.info("Step 1: Sucessfully shutdown RC node %s.", self.node_name)
        self.restore_node = True

        LOGGER.info("Step 2: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Checked cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on RC node %s's data pod %s "
                    "and server pod %s are in offline state", self.node_name, rc_datapod,
                    rc_serverpod)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[rc_datapod, rc_serverpod],
                                                           fail=True, hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Checked services status that were running on RC node %s's data pod %s "
                    "and server pod %s are in offline state", self.node_name, rc_datapod,
                    rc_serverpod)

        pod_list.remove(rc_datapod)
        server_list.remove(rc_serverpod)
        online_pods = pod_list + server_list
        LOGGER.info("Step 4: Check services status on remaining pods %s are in online state",
                    online_pods)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=online_pods, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 5: Check for RC node failed over node.")
        rc_node = self.motr_obj.get_primary_cortx_node()
        assert_utils.assert_true(len(rc_node), "Couldn't find new RC failover node")
        rc_info = self.node_master_list[0].get_pods_node_fqdn(pod_prefix=rc_node.split("svc-")[1])
        LOGGER.info("Step 5: RC node has been failed over to %s node", list(rc_info.values())[0])

        LOGGER.info("Step 6: Start IOs (create s3 acc, buckets and upload objects) after RC node %s"
                    "shutdown.", rc_node)
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34088'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: IOs completed Successfully after RC node %s shutdown.", rc_node)

        LOGGER.info("Step 7: Start pod %s again by bringing RC node %s up.", rc_datapod, rc_node)
        resp = self.ha_obj.host_power_on(host=rc_node)
        assert_utils.assert_true(resp, f"Host {rc_node} is not powered on")
        LOGGER.info("Step 7: Sucessfully started pod %s again by bringing RC node %s up.",
                    rc_datapod, rc_node)
        self.restore_node = False

        LOGGER.info("Step 8: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 9: Start IOs (create s3 acc, buckets and upload objects) after RC node %s"
                    "restart.", rc_node)
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34088-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: IOs completed Successfully after RC node %s restart.", rc_node)

        LOGGER.info("COMPLETED: Test to verify IOs before & after pod restart by making RC node "
                    "down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34087")
    @CTFailOn(error_handler)
    def test_ios_safe_shutdown_pod_restart(self):
        """
        This test tests IOs before and after data pod restart (pod shutdown by making replicas=0)
        """
        LOGGER.info("STARTED: Test to verify IOs before and after data pod restart (pod shutdown "
                    "by making replicas=0).")

        LOGGER.info("Step 1: Shutdown/Delete the data pod safely by making replicas=0")
        LOGGER.info("Get pod name to be Shutdown/Deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Shutdown/Delete pod %s", pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=pod_name)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by making replicas=0")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by making replicas=0", pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 2: Check cluster status is in degraded state.")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Checked cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Checked services status that were running on pod %s are in offline "
                    "state", pod_name)

        pod_list.remove(pod_name)
        LOGGER.info("Step 4: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Checked services status on remaining pods are in online state")

        LOGGER.info("Step 5: Start IOs (create s3 acc, buckets and upload objects) after pod "
                    "shutdown by making replicas=0.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34087'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully IOs completed after pod shutdown by making replicas=0.")

        LOGGER.info("Step 6: Starting pod again by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod again by making replicas=1")
        self.restore_pod = False

        LOGGER.info("Step 7: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 8: Start IOs again after data pod restart by making replicas=1.")
        self.test_prefix = 'test-34087-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully IOs completed after data pod restart by making "
                    "replicas=1.")

        LOGGER.info("COMPLETED: Test to verify IOs before and after data pod restart (pod shutdown "
                    "by making replicas=0).")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34089")
    @CTFailOn(error_handler)
    def test_io_server_pod_restart(self):
        """
        Verify IOs before and after server pod restart (setting replica=0 and 1)
        """
        LOGGER.info("STARTED: Verify IOs before and after server pod restart "
                    "(setting replica=0 and 1)")

        LOGGER.info("Step 1: Shutdown the server pod safely by making replicas=0")
        LOGGER.info("Get server pod name to be shutdown")
        server_pod_list = self.node_master_list[0].get_all_pods(
            pod_prefix=const.SERVER_POD_NAME_PREFIX)
        server_pod_name = random.sample(server_pod_list, 1)[0]
        server_pod_host = self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name)
        LOGGER.info("Shutdown pod %s", server_pod_name)
        resp = self.node_master_list[0].create_pod_replicas(num_replica=0, pod_name=server_pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to shutdown Server pod {server_pod_name} "
                                           "by making replicas=0")
        LOGGER.info("Step 1: Successfully shutdown pod %s by making replicas=0", server_pod_name)
        self.deployment_name = resp[1]
        self.restore_pod = True
        self.restore_method = const.RESTORE_SCALE_REPLICAS

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", server_pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[server_pod_name],
                                                           fail=True, hostname=server_pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of %s are in offline state", server_pod_name)

        server_pod_list.remove(server_pod_name)
        LOGGER.info("Step 4: Check services status on remaining pods %s", server_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=server_pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of remaining pods are in online state")

        LOGGER.info("Step 5: Start IOs (create s3 acc, buckets and upload objects) after server "
                    "pod shutdown by making replicas=0")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34089'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: IOs are completed successfully after server pod shutdown by making "
                    "replicas=0")

        LOGGER.info("Step 6: Starting pod again by making replicas=1")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 6: Successfully started the pod again by making replicas=1")
        self.restore_pod = False

        LOGGER.info("Step 7: Verify cluster status is in online state.")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: Verified cluster is in online state. All services are up & running")

        LOGGER.info("Step 8: Start IOs again after server pod restart by making replicas=1.")
        self.test_prefix = 'test-34089-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Successfully IOs completed after server pod restart by making "
                    "replicas=1.")

        LOGGER.info("COMPLETED: Verify IOs before and after server pod restart "
                    "(setting replica=0 and 1)")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="Blocked until F-22A is available")
    @pytest.mark.tags("TEST-34261")
    @CTFailOn(error_handler)
    def test_server_pod_restart_kubectl_delete(self):
        """
        Verify IOs after pod restart (kubectl delete)
        """
        LOGGER.info("STARTED: Verify IOs after server pod restart (kubectl delete)")

        LOGGER.info("Step 1: Shutdown the server pod by kubectl delete.")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)
        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_pod(pod_name=pod_name, force=True)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by kubectl delete")
        LOGGER.info("Step 1: Successfully shutdown/deleted pod %s by kubectl delete", pod_name)

        LOGGER.info("Step 2: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 2: Cluster is in degraded state")

        LOGGER.info("Step 3: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Services of pod are in offline state")

        pod_list.remove(pod_name)
        LOGGER.info("Step 4: Check services status on remaining pods %s", pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=pod_list, fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of remaining pods are in online state")

        LOGGER.info("Step 5: Start IOs (create s3 acc, buckets and upload objects) after pod "
                    "shutdown by kubectl delete")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34261'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Successfully IOs completed after pod shutdown by kubectl delete")

        LOGGER.info("Step 6: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 7: Start IOs (create s3 acc, buckets and upload objects) after "
                    "starting the pod ")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.s3_clean.update(users)
        self.test_prefix = 'test-34261-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 7: Successfully IOs completed after starting the pod")

        LOGGER.info("COMPLETED: Verify IOs after server pod restart (kubectl delete)")

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36003")
    @CTFailOn(error_handler)
    def test_reads_after_pod_restart_ros(self):
        """
        This test tests READs after data pod restart (F-26A Read Only Scope)
        """
        LOGGER.info("STARTED: Test to verify READs after data pod restart.")

        LOGGER.info("Step 1: Perform WRITEs/READs/Verify with variable object sizes. (0B - 512MB("
                    "VM)/5GB(HW))")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-36003'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], f"Failed to delete pod {pod_name} by deleting deployment"
                                           " (unsafe)")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on pod %s", pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Services of pod are in offline state")

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 5: Check services status on remaining pods %s", remain_pod_list)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in online state")

        LOGGER.info("Step 6: Perform READs & Verify DI on written variable object sizes. "
                    "(0B - 512MB(VM)/5GB(HW)), on degraded cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed READs & Verify DI on written variable object sizes. "
                    "(0B - 512MB(VM)/5GB(HW)), on degraded cluster")

        LOGGER.info("Step 7: Starting pod again by creating deployment using K8s command")
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 7: Successfully started the pod")
        self.restore_pod = False

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")

        LOGGER.info("Step 9: Perform READs & verify DI on written variable object sizes. "
                    "(0B - 512MB(VM)/5GB(HW)), after pod restart on online cluster")
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipwrite=True,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Performed READs & verified DI on written variable object sizes. "
                    "(0B - 512MB(VM)/5GB(HW)), after pod restart on online cluster")

        LOGGER.info("Step 10: Perform WRITEs/READs/Verify with variable object sizes. (0B - "
                    "512MB(VM)/5GB(HW))")
        self.test_prefix = 'test-36003-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 10: Performed WRITEs/READs/Verify with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify READs after data pod restart.")

    # pylint: disable=C0321
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-36004")
    @CTFailOn(error_handler)
    def test_continuous_reads_during_pod_restart_ros(self):
        """
        This test tests continuous reads during pod restart (F-26A Read Only Scope)
        """
        LOGGER.info("STARTED: Test to verify continuous READs during data pod restart.")

        output = Queue()
        event = threading.Event()  # Event to be used to send intimation of pod restart

        LOGGER.info("Step 1: Perform WRITEs/READs/Verify with variable object sizes. (0B - 512MB("
                    "VM)/5GB(HW))")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-36004'
        self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True, nclients=20, nsamples=20)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITEs/READs/Verify with variable sizes objects.")

        LOGGER.info("Step 2: Shutdown the data pod by deleting deployment (unsafe)")
        LOGGER.info("Get pod name to be deleted")
        pod_list = self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        pod_name = random.sample(pod_list, 1)[0]
        pod_host = self.node_master_list[0].get_pod_hostname(pod_name=pod_name)

        LOGGER.info("Deleting pod %s", pod_name)
        resp = self.node_master_list[0].delete_deployment(pod_name=pod_name)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0],
                                  f"Failed to delete pod {pod_name} by deleting deployment"
                                  " (unsafe)")
        LOGGER.info("Step 2: Successfully shutdown/deleted pod %s by deleting deployment (unsafe)",
                    pod_name)
        self.deployment_backup = resp[1]
        self.deployment_name = resp[2]
        self.restore_pod = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0])
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Verify services that were running on pod %s are in offline state",
                    pod_name)
        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                           hostname=pod_host)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Verified services of %s are in offline state", pod_name)

        remain_pod_list = list(filter(lambda x: x != pod_name, pod_list))
        LOGGER.info("Step 5: Verify services status on remaining pods %s are in online state",
                    remain_pod_list)

        resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=remain_pod_list,
                                                           fail=False)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Services of pod are in online state")

        LOGGER.info(
            "Step 6: Perform READs and verify DI on the written data in background during "
            "pod restart using %s method", self.restore_method)
        args = {'s3userinfo': list(users.values())[0], 'log_prefix': self.test_prefix,
                'nclients': 1, 'nsamples': 20, 'skipwrite': True, 'skipcleanup': True,
                'output': output}

        thread = threading.Thread(target=self.ha_obj.event_s3_operation,
                                  args=(event,), kwargs=args)
        thread.daemon = True  # Daemonize thread
        thread.start()
        # TODO Need to update timing once we get stability in degraded IOs performance
        time.sleep(HA_CFG["common_params"]["degraded_wait_delay"])
        LOGGER.info("Step 6: Successfully started READs and verified DI on the written data in "
                    "background")

        LOGGER.info("Step 7: Starting pod again by creating deployment using %s method",
                    self.restore_method)
        event.set()
        resp = self.ha_obj.restore_pod(pod_obj=self.node_master_list[0],
                                       restore_method=self.restore_method,
                                       restore_params={"deployment_name": self.deployment_name,
                                                       "deployment_backup":
                                                           self.deployment_backup})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
        LOGGER.info("Step 7: Successfully started the pod using %s method", self.restore_method)
        self.restore_pod = False

        LOGGER.info("Step 8: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.node_master_list[0], timeout=180)
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 8: Cluster is in good state. All the services are up and running")
        event.clear()
        thread.join()
        LOGGER.debug("Event is cleared and thread has joined.")
        LOGGER.info("Verifying responses from background process")
        responses = {}
        while len(responses) != 2:
            responses = output.get(timeout=HA_CFG["common_params"]["60sec_delay"])
        if not responses:
            assert_utils.assert_true(False, "Background S3bench Failures")
        LOGGER.debug("Background S3bench responses : %s", responses)
        if not responses["pass_res"]:
            assert_utils.assert_true(False,
                                     "No background IOs response while event was cleared")
        nonbkgrd_logs = list(x[1] for x in responses["pass_res"])
        if not responses["fail_res"]:
            assert_utils.assert_true(False,
                                     "No background IOs response while event was set")
        bkgrd_logs = list(x[1] for x in responses["fail_res"])
        resp = self.ha_obj.check_s3bench_log(file_paths=nonbkgrd_logs)
        assert_utils.assert_false(len(resp[1]), "Non Background Logs which contain failures"
                                                f": {resp[1]}")
        resp = self.ha_obj.check_s3bench_log(file_paths=bkgrd_logs)
        assert_utils.assert_false(len(resp[1]), "Background Logs which contain failures:"
                                                f" {resp[1]}")
        LOGGER.info(
            "Step 6: Successfully completed READs and verified DI on the written data in "
            "background during pod restart using %s method", self.restore_method)

        LOGGER.info("Step 9: Create multiple buckets and run IOs")
        self.test_prefix = 'test-36004-1'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    skipcleanup=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 9: Successfully created multiple buckets and ran IOs")

        LOGGER.info("ENDED: Test to verify continuous READs during data pod restart.")
