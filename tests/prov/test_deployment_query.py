#!/usr/bin/python
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

# pylint: disable=R0904

"""Failure Domain (k8s based Cortx) Test Suite."""
import logging
import os.path


from http import HTTPStatus
import os
import secrets
import time

from time import perf_counter_ns
import pytest
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from config import  PROV_CFG
from config import  DEPLOY_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from commons import configmanager, cortxlogging, constants as const
from libs.csm.csm_interface import csm_api_factory
from commons.helpers.health_helper import Health
from libs.ha.ha_common_libs_k8s import HAK8s
from commons.helpers.pods_helper import LogicalNode
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from config import CMN_CFG


LOGGER = logging.getLogger(__name__)

class TestQueryDeployment:
    """Query Deployment Testsuites"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_obj = ProvDeployK8sCortxLib()
        cls.deploy_conf = PROV_CFG['k8s_cortx_deploy']
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.node_master_list = list()
        cls.hlth_master_list = list()
        cls.node_worker_list = list()
        for node in range(cls.num_nodes):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
                cls.hlth_master_list.append(Health(hostname=CMN_CFG["nodes"][node]["hostname"],
                                                   username=CMN_CFG["nodes"][node]["username"],
                                                   password=CMN_CFG["nodes"][node]["password"]))
            else:
                cls.worker_node_list.append(node_obj)
        cls.log_disk_size = os.getenv('log_disk_size')
        cls.ha_obj = HAK8s()
        cls.csm_obj = csm_api_factory("rest")
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_query_deployment.yaml")
        cls.deploy_start_time = None
        cls.deploy_end_time = None
        cls.update_seconds = cls.csm_conf["update_seconds"]
        cls.collect_sb = True
        cls.destroy_flag = False
        cls.ha_obj = HAK8s()
        cls.num_replica = cls.delete_pod = cls.set_type = None
        cls.s3_clean = cls.test_prefix = cls.test_prefix_deg = cls.set_name = None
        cls.s3acc_name = cls.s3acc_email = cls.bucket_name = cls.object_name = cls.node_name = None
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "HATestMultipartUpload")
        cls.system_random = secrets.SystemRandom()

    def multiple_node_deployment(self, node, config, **kwargs):
        """
        This Method is used for deployment of various node count
        and its multiple SNS,DIX configs
        :param: nodes: Its the count of worker nodes in K8S cluster.
        :param: config: Its the config for each node defined
                        in deploy_config.yaml file
        """
        self.deploy_start_time = time.time()
        self.log.info("Start time for deployment %s: ", self.deploy_start_time)
        log_device = kwargs.get("log_device_flag", False)
        config = DEPLOY_CFG[f'nodes_{node}'][f'config_{config}']
        self.log.info("Running %s N with config %s+%s+%s",
                      node, config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_per_node'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            s3_instance=1, log_disk_flag=log_device, setup_k8s_cluster_flag = False,
            setup_client_config_flag = False, run_basic_s3_io_flag = False,
            run_s3bench_workload_flag = False )
        self.deploy_end_time = time.time()
        self.log.info("End time for deployment %s: ", self.deploy_end_time)
        self.collect_sb = False
        self.destroy_flag = True


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
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        if not resp[0]:
            resp = self.ha_obj.restart_cluster(self.master_node_list[0])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster status is online.")
        self.s3acc_name = f"ha_s3acc_{int(perf_counter_ns())}"
        self.s3acc_email = f"{self.s3acc_name}@seagate.com"
        self.bucket_name = f"ha-mp-bkt-{int(perf_counter_ns())}"
        self.object_name = f"ha-mp-obj-{int(perf_counter_ns())}"
        self.restore_pod = self.restore_method = self.deployment_name = self.set_name = None
        self.deployment_backup = None
        if not os.path.exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", resp)
        LOGGER.info("Done: Setup operations.")

    def teardown_method(self):
        """
        Teardown method
        """
        if self.s3_clean:
           LOGGER.info("Cleanup: Cleaning created s3 accounts and buckets.")
           resp = self.ha_obj.delete_s3_acc_buckets_objects(self.s3_clean)
           assert_utils.assert_true(resp[0], resp[1])
        if self.restore_pod:
           resp = self.ha_obj.restore_pod(pod_obj=self.master_node_list[0],
                                          restore_method=self.restore_method,
                                          restore_params={"deployment_name": self.deployment_name,
                                                          "deployment_backup":
                                                              self.deployment_backup,
                                                          "num_replica": self.num_replica,
                                                          "set_name": self.set_name})
           LOGGER.debug("Response: %s", resp)
           assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way")
           LOGGER.info("Successfully restored pod by %s way", self.restore_method)
        LOGGER.info("Cleanup: Check cluster status and start it if not up.")
        resp = self.ha_obj.check_cluster_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                            scripts_path=
                                                            self.deploy_conf['k8s_dir'])
        if self.destroy_flag:
            resp = self.deploy_obj.destroy_setup(self.master_node_list[0],
                                                 self.worker_node_list)
            assert_utils.assert_true(resp)
        self.deploy_obj.close_connections(self.master_node_list, self.worker_node_list)


    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-45743")
    def test_45743(self):
        """
        Test to verify query should be able to fetch standard 3 node configuration.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("Step 1 : Deploy cortx cluster ")
        self.multiple_node_deployment(3, 2)
        LOGGER.info("Step 2 : GET the cluster configuration ")
        self.log.info("Deploy start and end time: %s %s ", self.deploy_start_time,
                      self.deploy_end_time)
        result, err_msg = self.csm_obj.verify_system_topology(self.deploy_start_time,
                                                              self.deploy_end_time,
                                                              expected_response=HTTPStatus.OK)
        assert result, err_msg
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-45745")
    def test_45745(self):
        """
        Test to verify query should be able to fetch standard 5 node configuration.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("Step 1 : Deploy cortx cluster ")
        self.multiple_node_deployment(5, 1)
        LOGGER.info("Step 2 : GET the cluster configuration ")
        self.log.info("Send GET request for fetching system topology" )
        self.log.info("Deploy start and end time: %s %s ", self.deploy_start_time,
                      self.deploy_end_time)
        result, err_msg = self.csm_obj.verify_system_topology(self.deploy_start_time,
                                                              self.deploy_end_time,
                                                              expected_response=HTTPStatus.OK)
        assert result, err_msg
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-45744")
    def test_45744(self):
        """
        Test to verify query should be able to fetch standard 3 node configuration
            if cluster is in degraded state.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("Step 1 : Deploy cortx cluster ")
        self.multiple_node_deployment(3, 2)
        LOGGER.info("Step 2 : Make a cluster in degraded state")
        LOGGER.info("Get %s pod to be deleted", const.POD_NAME_PREFIX)
        sts_dict = self.master_node_list[0].get_sts_pods(pod_prefix=const.POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        LOGGER.debug("%s Statefulset: %s", const.POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        self.delete_pod = sts_dict[sts][-1]
        LOGGER.info("Pod to be deleted is %s", self.delete_pod)
        self.set_type, self.set_name = self.master_node_list[0].get_set_type_name(
            pod_name=self.delete_pod)
        resp = self.master_node_list[0].get_num_replicas(self.set_type, self.set_name)
        assert_utils.assert_true(resp[0], resp)
        self.num_replica = int(resp[1])
        LOGGER.info(" Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.master_node_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        self.log.info("Step 4: Verify GET system topology ")
        self.log.info("Deploy start and end time: %s %s ", self.deploy_start_time,
                      self.deploy_end_time)
        result, err_msg = self.csm_obj.verify_system_topology(self.deploy_start_time,
                                                              self.deploy_end_time,
                                                              expected_response=HTTPStatus.OK)
        assert result, err_msg
        # LOGGER.info("Step 5: Restore pod and check cluster status.")
        # resp = self.ha_obj.restore_pod(pod_obj=self.master_node_list[0],
        #                                restore_method=self.restore_method,
        #                                restore_params={"deployment_name": self.deployment_name,
        #                                                "deployment_backup":
        #                                                    self.deployment_backup,
        #                                                 "num_replica": self.num_replica,
        #                                                 "set_name": self.set_name},
        #                                clstr_status=True)
        # LOGGER.debug("Response: %s", resp)
        # assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way "
        #                                   "OR the cluster is not online")
        # self.restore_pod = False
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-45835")
    def test_45835(self):
        """
        Test to verify query should be able to fetch standard 5 node configuration
            if cluster is in degraded state.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("Step 1 : Deploy cortx cluster ")
        self.multiple_node_deployment(5, 1)
        LOGGER.info("Step 2 : Make a cluster in degraded state")
        LOGGER.info("Get %s pod to be deleted", const.POD_NAME_PREFIX)
        sts_dict = self.master_node_list[0].get_sts_pods(pod_prefix=const.POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        LOGGER.debug("%s Statefulset: %s", const.POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        self.delete_pod = sts_dict[sts][-1]
        LOGGER.info("Pod to be deleted is %s", self.delete_pod)
        self.set_type, self.set_name = self.master_node_list[0].get_set_type_name(
            pod_name=self.delete_pod)
        resp = self.master_node_list[0].get_num_replicas(self.set_type, self.set_name)
        assert_utils.assert_true(resp[0], resp)
        self.num_replica = int(resp[1])
        LOGGER.info(" Shutdown random data pod with replica method and "
                    "verify cluster & remaining pods status")
        num_replica = self.num_replica - 1
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.master_node_list[0], health_obj=self.hlth_master_list[0],
            delete_pod=[self.delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert_utils.assert_true(resp[1], "Failed to shutdown/delete pod")
        pod_name = list(resp[1].keys())[0]
        self.set_name = resp[1][pod_name]['deployment_name']
        self.restore_method = resp[1][pod_name]['method']
        pod_name = list(resp[1].keys())[0]
        assert_utils.assert_true(resp[0], "Cluster/Services status is not as expected")
        LOGGER.info("Step 3: Successfully shutdown data pod %s. Verified cluster and "
                    "services states are as expected & remaining pods status is online.", pod_name)
        self.restore_pod = True
        self.log.info("Step 4: Verify GET system topology ")
        self.log.info("Deploy start and end time: %s %s ", self.deploy_start_time,
                      self.deploy_end_time)
        result, err_msg = self.csm_obj.verify_system_topology(self.deploy_start_time,
                                                              self.deploy_end_time,
                                                              expected_response=HTTPStatus.OK)
        assert result, err_msg
        # LOGGER.info("Step 5: Restore pod and check cluster status.")
        # resp = self.ha_obj.restore_pod(pod_obj=self.master_node_list[0],
        #                                restore_method=self.restore_method,
        #                                restore_params={"deployment_name": self.deployment_name,
        #                                                "deployment_backup":
        #                                                    self.deployment_backup,
        #                                                 "num_replica": self.num_replica,
        #                                                 "set_name": self.set_name},
        #                                clstr_status=True)
        # LOGGER.debug("Response: %s", resp)
        # assert_utils.assert_true(resp[0], f"Failed to restore pod by {self.restore_method} way "
        #                                   "OR the cluster is not online")
        # self.restore_pod = False
        self.log.info("##### Test ended -  %s #####", test_case_name)

