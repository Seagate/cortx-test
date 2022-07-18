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
HA test suite for Multiple (K) Data & Server Pods Failure
"""

import logging
import os
import secrets
import threading
import time
from multiprocessing import Queue

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
from libs.di.di_mgmt_ops import ManagementOPs
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_test_lib import S3TestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestMultiDataServerPodFailure:
    """
    Test suite for Multiple (K) Data & Server Pods Failure
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations.")
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.username = list()
        cls.password = list()
        cls.node_master_list = list()
        cls.hlth_master_list = list()
        cls.host_worker_list = list()
        cls.node_worker_list = list()
        cls.pod_name_list = list()
        cls.node_name_list = list()
        cls.node_ip_list = list()
        cls.srv_pod_host_list = list()
        cls.data_pod_host_list = list()
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.s3_clean = cls.test_prefix = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.restore_node = cls.node_name = cls.deploy = cls.kvalue = cls.restore_ip = None
        cls.pod_dict = dict()
        cls.ip_dict = dict()
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
        LOGGER.info("Get the value of K for the given cluster.")
        resp = self.ha_obj.get_config_value(self.node_master_list[0])
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            LOGGER.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        LOGGER.info("The cluster has %s parity pods", self.kvalue)
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
        if self.restore_node:
            for node_name in self.node_name_list:
                LOGGER.info("Cleanup: Power on the %s down node.", node_name)
                resp = self.ha_obj.host_power_on(host=node_name)
                assert_utils.assert_true(resp, f"Host {node_name} is not powered on")
                LOGGER.info("Cleanup: %s is Power on. Sleep for %s sec for pods to join back the"
                            " node", node_name, HA_CFG["common_params"]["pod_joinback_time"])
                time.sleep(HA_CFG["common_params"]["pod_joinback_time"])
        if self.restore_ip:
            for node_ip in self.node_ip_list:
                LOGGER.info("Cleanup: Get the network interface up for %s ip", node_ip)
                node_iface = self.ip_dict.get(node_ip)[0]
                worker_obj = self.ip_dict.get(node_ip)[1]
                worker_obj.execute_cmd(cmd=cmd.IP_LINK_CMD.format(node_iface, "up"),
                                       read_lines=True)
                resp = sysutils.check_ping(host=node_ip)
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

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.tags("TEST-35792")
    @pytest.mark.skip(reason="Buckets cruds won't be supported with DTM0")
    def test_server_data_kpods_fail_during_ios(self):
        """
        Test to verify continuous IOs while k server and data pods are failing one by one by delete
        deployment
        """
        LOGGER.info("STARTED: Test to verify continuous IOs while k server and data pods are "
                    "failing one by one")

        event = threading.Event()  # Event to be used to send when pods going down
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
        test_prefix_del = 'test-delete-35792'
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
        test_prefix_read = 'test-read-35792'
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read, skipread=True,
                                                    skipcleanup=True, nclients=5, nsamples=5)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Performed WRITEs with variable sizes objects for parallel READs.")

        LOGGER.info("Starting three independent background threads for READs, WRITEs & DELETEs.")
        LOGGER.info("Step 3: Start Continuous DELETEs in background on random %s buckets",
                    del_bucket)
        bucket_list = list(s3_data.keys())
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
        test_prefix_write = 'test-write-35792'
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
        LOGGER.info("Waiting for %s seconds to perform some READs",
                    HA_CFG["common_params"]["30sec_delay"])
        time.sleep(HA_CFG["common_params"]["30sec_delay"])

        LOGGER.info("Step 6: Shutdown random %s (K) data & server pods by deleting deployment and "
                    "verify cluster & remaining pods status", self.kvalue)
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.node_master_list[0], health_obj=self.hlth_master_list[0],
            kvalue=self.kvalue, event=event, event_set_clr=event_set_clr,
            down_method=const.RESTORE_DEPLOYMENT_K8S, pod_prefix=[const.POD_NAME_PREFIX,
                                                                  const.SERVER_POD_NAME_PREFIX])
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        for pod_name in resp[1].keys():
            pod_data = list()
            pod_data.append(resp[1][pod_name]['hostname'])  # hostname
            pod_data.append(resp[1][pod_name]['deployment_backup'])  # deployment_backup
            pod_data.append(resp[1][pod_name]['deployment_name'])  # deployment_name
            self.pod_name_list.append(pod_name)
            self.pod_dict[pod_name] = pod_data
        self.restore_pod = self.deploy = True
        self.restore_method = const.RESTORE_DEPLOYMENT_K8S
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 6: Successfully shutdown %s (K) data & server pod %s. Verified cluster "
                    "and services states are as expected & remaining pods status is online.",
                    self.kvalue, self.pod_name_list)

        LOGGER.info("Step 7: Verify status for In-flight WRITEs/READs-verify/DELETEs while %s (K)"
                    "server & data pods were going down", self.kvalue)
        LOGGER.info("Waiting for background IOs thread to join")
        thread_wri.join()
        thread_rd.join()
        thread_del.join()
        LOGGER.info("Step 7.1: Verify status for In-flight DELETEs while %s (K) data & server pods "
                    "were going down", self.kvalue)
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
        LOGGER.info("Step 7.1: Verified status for In-flight DELETEs while %s (K) data & server "
                    "pods were going down", self.kvalue)

        LOGGER.info("Step 7.2: Verify status for In-flight WRITEs while %s (K) data & server pods "
                    "going down should be failed/error.", self.kvalue)
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
        LOGGER.info("Step 7.2: Verified status for In-flight WRITEs while %s (K) data & server "
                    "pods going down.", self.kvalue)

        LOGGER.info("Step 7.3: Verify status for In-flight READs/Verify DI while %s (K)"
                    " data & server pods going down should be failed/error.", self.kvalue)
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
                    " data & server pods were going down.", self.kvalue)
        LOGGER.info("Step 7: Verified status for In-flight READs/WRITEs/DELETEs while %s (K)"
                    " data and server pods were going down.", self.kvalue)

        LOGGER.info("Step 8: Perform IOs with variable sizes objects.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("Step 8: Perform WRITEs-READs-Verify with variable object sizes "
                        "on degraded cluster with new user")
            users = self.mgnt_ops.create_account_users(nusers=1)
            test_prefix_read = 'test-35792-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=test_prefix_read,
                                                    nsamples=2, nclients=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 8: Performed IOs with variable sizes objects.")
        LOGGER.info("ENDED: Test to verify continuous IOs while k server and data pods are failing "
                    "one by one")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="VM issue in after Restart(CORTX-32933). Need to be tested on HW.")
    @pytest.mark.tags("TEST-35787")
    def test_kpods_fail_node_down(self):
        """
        Test to Verify degraded IOs after multiple (max K) pods (data and server) failures with node
        hosting them going down.
        """
        LOGGER.info("Started: Test to Verify degraded IOs after multiple (max K) pods "
                    "(data and server) failures with node hosting them going down.")

        LOGGER.info("Step 1: Perform WRITE/READ/Verify/DELETEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35787'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, nsamples=2,
                                                    nclients=2)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITE/READ/Verify/DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Delete data & server pods by shutting down node they are hosted on.")
        count = 1
        data_pod_list = remain_pod_list1 = \
            self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = remain_pod_list2 = \
            self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        while count < self.kvalue:
            resp = self.ha_obj.get_data_pod_no_ha_control(remain_pod_list1,
                                                          self.node_master_list[0])
            data_pod_name = resp[0]
            server_pod_name = resp[1]
            data_node_fqdn = resp[2]
            self.srv_pod_host_list.append(
                self.node_master_list[0].get_pod_hostname(pod_name=server_pod_name))
            self.data_pod_host_list.append(self.node_master_list[0].get_pod_hostname
                                           (pod_name=data_pod_name))
            self.node_name_list.append(data_node_fqdn)
            self.pod_name_list.append(data_pod_name)
            self.pod_name_list.append(server_pod_name)
            LOGGER.info("Shutdown the node: %s", data_node_fqdn)
            resp = self.ha_obj.host_safe_unsafe_power_off(host=data_node_fqdn)
            assert_utils.assert_true(resp, f"Host f{data_node_fqdn} is not powered off")
            remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
            remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
            count += 1
            self.pod_dict[data_pod_name] = self.data_pod_host_list
            self.pod_dict[server_pod_name] = self.srv_pod_host_list
            LOGGER.info("Sleep for pod-eviction-timeout of %s sec", HA_CFG["common_params"][
                "pod_eviction_time"])
            time.sleep(HA_CFG["common_params"]["pod_eviction_time"])

        LOGGER.info("Step 2: Deleted %s data and server pods by shutting down the node"
                    "hosting them.", count)
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        self.restore_node = self.deploy = True
        running_pod = self.system_random.sample(remain_pod_list1, 1)[0]

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0],
                                                pod_list=remain_pod_list1)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname,
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

        LOGGER.info("Step 6: Perform IOs with variable sizes objects.")
        if CMN_CFG["dtm0_disabled"]:
            LOGGER.info("STEP 6: Create IAM user and perform WRITEs-READs-Verify-DELETEs with "
                        "variable object sizes on degraded cluster")
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-35787-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix, skipcleanup=True,
                                                    nsamples=2, nclients=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed IOs with variable sizes objects.")

        LOGGER.info("Completed: Test to Verify degraded IOs after multiple (max K) pods "
                    "(data and server) failures with node hosting them going down.")

    @pytest.mark.ha
    @pytest.mark.lc
    @pytest.mark.skip(reason="VM issue in after Restart(CORTX-32933). Need to be tested on HW.")
    @pytest.mark.tags("TEST-35788")
    def test_kpods_fail_node_nw_down(self):
        """
        Test to Verify degraded IOs after multiple (max K) pods (data and server) failures
        with network of node hosting them going down.
        """
        LOGGER.info("Started: Test to Verify degraded IOs after multiple (max K) pods "
                    "(data and server) failures with network of node hosting them going down.")

        LOGGER.info("Step 1: Perform WRITE/READ/Verify/DELETEs with variable object sizes.")
        users = self.mgnt_ops.create_account_users(nusers=1)
        self.test_prefix = 'test-35788'
        self.s3_clean = users
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Performed WRITE/READ/Verify/DELETEs with variable sizes objects.")

        LOGGER.info("Step 2: Delete data and server pods by shutting down network on node they "
                    "are hosted on.")
        count = 1
        data_pod_list = remain_pod_list1 = \
            self.node_master_list[0].get_all_pods(pod_prefix=const.POD_NAME_PREFIX)
        server_pod_list = remain_pod_list2 = \
            self.node_master_list[0].get_all_pods(pod_prefix=const.SERVER_POD_NAME_PREFIX)
        while count < self.kvalue:
            pod_data = list()
            ip_data = list()
            resp = self.ha_obj.get_data_pod_no_ha_control(remain_pod_list1,
                                                          self.node_master_list[0])
            data_pod_name = resp[0]
            server_pod_name = resp[1]
            data_node_fqdn = resp[2]
            self.pod_name_list.append(data_pod_name)
            self.pod_name_list.append(server_pod_name)
            pod_data.append(self.node_master_list[0].get_pod_hostname(pod_name=data_pod_name))
            LOGGER.info("Get the ip of the host from the node %s", data_node_fqdn)
            resp = self.ha_obj.get_nw_iface_node_down(host_list=self.host_worker_list,
                                                      node_list=self.node_worker_list,
                                                      node_fqdn=data_node_fqdn)
            node_ip = resp[1]
            ip_data.append(resp[2])     # node_iface
            ip_data.append(resp[3])     # new_worker_obj
            self.node_ip_list.append(node_ip)   # node_ip_list
            assert_utils.assert_true(resp[0], "Node network is still up")
            LOGGER.info("Step 2: %s Node's network is down.", data_node_fqdn)
            remain_pod_list1 = list(filter(lambda x: x != data_pod_name, data_pod_list))
            remain_pod_list2 = list(filter(lambda x: x != server_pod_name, server_pod_list))
            count += 1
            self.pod_dict[data_pod_name] = pod_data
            self.pod_dict[server_pod_name] = pod_data
            self.ip_dict[node_ip] = ip_data

        LOGGER.info("Step 2: Deleted %s data and server pods by shutting down network of "
                    "the node hosting them.", count)
        remain_pod_list = remain_pod_list1 + remain_pod_list2
        self.restore_ip = self.deploy = True
        running_pod = self.system_random.sample(remain_pod_list1, 1)[0]

        LOGGER.info("Step 3: Check cluster status")
        resp = self.ha_obj.check_cluster_status(self.node_master_list[0],
                                                pod_list=remain_pod_list1)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 3: Cluster is in degraded state")

        LOGGER.info("Step 4: Check services status that were running on data and server pod")
        for pod_name in self.pod_name_list:
            hostname = self.pod_dict.get(pod_name)[0]
            resp = self.hlth_master_list[0].get_pod_svc_status(pod_list=[pod_name], fail=True,
                                                               hostname=hostname,
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

        LOGGER.info("Step 6: Perform WRITE/READ/Verify/DELETEs with variable object sizes.")
        if CMN_CFG["dtm0_disabled"]:
            users = self.mgnt_ops.create_account_users(nusers=1)
            self.test_prefix = 'test-35788-1'
            self.s3_clean.update(users)
        resp = self.ha_obj.ha_s3_workload_operation(s3userinfo=list(users.values())[0],
                                                    log_prefix=self.test_prefix,
                                                    nclients=2, nsamples=2, setup_s3bench=False)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Performed WRITE/READ/Verify/DELETEs with variable sizes objects.")

        LOGGER.info("Completed: Test to Verify degraded IOs after multiple (max K) pods "
                    "(data and server) failures with network of node hosting them going down.")
