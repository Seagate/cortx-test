# pylint: disable=too-many-lines
# !/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Tests Query Deployment scenarios using REST API
"""

import time
import logging

import random
import string
from http import HTTPStatus
import pytest

from commons import configmanager, cortxlogging
from commons.constants import K8S_SCRIPTS_PATH, K8S_PRE_DISK, POD_NAME_PREFIX
from libs.csm.csm_interface import csm_api_factory
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib


class TestQueryDeployment():
    """Query Deployment Testsuites"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.ha_obj = HAK8s()
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.csm_obj = csm_api_factory("rest")
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_query_deployment.yaml")
        cls.update_seconds = cls.csm_conf["update_seconds"]
        cls.failed_pod = None
        cls.kvalue = None
        cls.deploy_list = cls.csm_obj.master.get_deployment_name(POD_NAME_PREFIX)
        cls.random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        cls.random_number = cls.csm_obj.random_gen.randrange(1, 99999)
        cls.random_symbols = ''.join(random.choices(string.punctuation, k=10))

    def setup_method(self):
        """
        Setup method
        """
        '''self.log.info("Prerequisite: Deploy cortx cluster")
        deploy_start_time = time.time()
        self.log.info("Printing start time for deployment %s: ", deploy_start_time)
        self.log.info("Cleanup: Destroying the cluster ")
        resp = self.deploy_lc_obj.destroy_setup(self.csm_obj.master, self.csm_obj.worker_list,
                                                K8S_SCRIPTS_PATH)
        assert resp[0], resp[1]
        self.log.info("Cleanup: Cluster destroyed successfully")

        self.log.info("Cleanup: Setting prerequisite")
        self.deploy_lc_obj.execute_prereq_cortx(self.csm_obj.master,
                                                K8S_SCRIPTS_PATH,
                                                K8S_PRE_DISK)

        for node in self.csm_obj.worker_list:
            self.deploy_lc_obj.execute_prereq_cortx(node, K8S_SCRIPTS_PATH,
                                                    K8S_PRE_DISK)
        self.log.info("Cleanup: Prerequisite set successfully")

        self.log.info("Cleanup: Deploying the Cluster")
        resp_cls = self.deploy_lc_obj.deploy_cluster(self.csm_obj.master,
                                                     K8S_SCRIPTS_PATH)
        assert resp_cls[0], resp_cls[1]
        self.log.info("Cleanup: Cluster deployment successfully")

        self.log.info("[Start] Sleep %s", self.update_seconds)
        time.sleep(self.update_seconds)
        self.log.info("[Start] Sleep %s", self.update_seconds)

        self.log.info("Cleanup: Check cluster status")
        resp = self.ha_obj.poll_cluster_status(self.csm_obj.master)
        assert resp[0], resp[1]
        self.log.info("Cleanup: Cluster status checked successfully")
        deploy_end_time = time.time()
        self.log.info("Printing end time for deployment %s: ", deploy_end_time)

        self.log.info("Getting k value from config")
        resp = self.ha_obj.get_config_value(self.csm_obj.master)
        if resp[0]:
            self.kvalue = int(resp[1]['cluster']['storage_set'][0]['durability']['sns']['parity'])
        else:
            self.log.info("Failed to get parity value, will use 1.")
            self.kvalue = 1
        self.log.info("The cluster has %s parity pods", self.kvalue)'''

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-45675')
    def test_45675(self):
        """
        Verify GET cluster topology with valid storage id
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step 1: Send GET request for fetching system topology"
                      "without storage set id")
        self.log.info("Get cluster id from system topology response")
        get_topology = self.csm_obj.get_system_topology()
        for cluster in get_topology["topology"]["clusters"]:
            resp, result, err_msg = self.csm_obj.verify_storage_set(cluster_id = cluster['id'])
            assert result, err_msg
            self.log.info("Response : %s", resp)
            self.log.info("Step 2: Send GET request for fetching system topology"
                      "with storage set id")
            #need to revisit
            storage_sets = resp.json()["topology"]["clusters"][0]["storage_set"]
            for storage_set_id in storage_sets:
                self.log.info("Sending request for %s ", storage_set_id)
                resp, result, err_msg = self.csm_obj.verify_storage_set(cluster_id = cluster['id'],
                                                storage_set_id = storage_set_id['id'])
                assert result, err_msg
                self.log.info("Response : %s", resp)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-45671')
    def test_45671(self):
        """
        Verify GET cluster topology with invalid resource name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_45671"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_msg_index = test_cfg["message_index"]
        self.log.info("Step 1: Send GET request with invalid resource ID")
        invalid_ids = []
        invalid_ids = ['Clusters', self.random_string, self.random_number, self.random_symbols]
        for ids in invalid_ids:
            resp = self.csm_obj.get_system_topology(uri_param = str(ids))
            assert resp.status_code == HTTPStatus.NOT_FOUND, \
                               "Status code check failed for get system topology"
            resp = self.csm_obj.verify_error_message(resp, resp_error_code, resp_msg_id,
                                                     resp_msg_index)
            assert resp, "Error msg verify failed"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-45673')
    def test_45673(self):
        """
        Verify GET cluster topology with invalid cluster id
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_45673"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_msg_index = test_cfg["message_index"]
        self.log.info("Step 1: Send GET request with invalid cluster ID")
        invalid_ids = []
        invalid_ids = ['cluster', self.random_string, self.random_number, self.random_symbols, 0]
        for ids in invalid_ids:
            resp = self.csm_obj.get_cluster_topology(cluster_id = str(ids))
            #assert resp.status_code == HTTPStatus.NOT_FOUND, \
            #                   "Status code check failed for get cluster topology"
            #resp = self.csm_obj.verify_error_message(resp, resp_error_code, resp_msg_id,
            #                                         resp_msg_index)
            #assert resp, "Error msg verify failed"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-45676')
    def test_45676(self):
        """
        Verify GET cluster topology with invalid storage id
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_45676"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_msg_index = test_cfg["message_index"]
        invalid_ids = []
        invalid_ids = [self.random_string, self.random_number, self.random_symbols]
        self.log.info("Step 1: Send GET request with invalid storage ID")
        self.log.info("Get cluster id from system topology response")
        get_topology = self.csm_obj.get_system_topology()
        for cluster in get_topology["topology"]["clusters"]:
            for ids in invalid_ids:
                resp = self.csm_obj.get_storage_topology(cluster_id = cluster['id'],
                                                         storage_set_id = str(ids))
                assert resp.status_code == HTTPStatus.NOT_FOUND, \
                               "Status code check failed for get storage topology"
                result = self.csm_obj.verify_error_message(resp, resp_error_code, resp_msg_id,
                                                     resp_msg_index)
                assert result, "Error msg verify failed"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-45678')
    def test_45678(self):
        """
        Verify GET cluster topology with invalid node id
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_45678"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_msg_index = test_cfg["message_index"]
        invalid_ids = []
        invalid_ids = [self.random_string, self.random_number, self.random_symbols]
        self.log.info("Step 1: Send GET request with invalid storage ID")
        self.log.info("Get cluster id from system topology response")
        get_topology = self.csm_obj.get_system_topology()
        for cluster in get_topology["topology"]["clusters"]:
            for ids in invalid_ids:
                resp = self.csm_obj.get_node_topology(cluster_id = cluster['id'],
                                                      node_id = str(ids))
                assert resp.status_code == HTTPStatus.NOT_FOUND, \
                               "Status code check failed for get node topology"
                resp = self.csm_obj.verify_error_message(resp, resp_error_code, resp_msg_id,
                                                     resp_msg_index)
                assert resp, "Error msg verify failed"
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-45679')
    def test_45679(self):
        """
        Verify GET cluster topology in degraded mode
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Failure loop")
        for failure_cnt in range(1, self.kvalue + 2):
            self.log.info("Starting failure loop for iteration %s ", failure_cnt)
            self.log.info("Step 1: Send Get cluster topology")
            resp = self.csm_obj.get_cluster_topology()
            assert resp.status_code == HTTPStatus.OK, \
                               "Status code check failed for get cluster topology"
            self.log.info("Step 2: Shutdown data pod safely")
            deploy_name = self.deploy_list[failure_cnt]
            self.log.info("[Start] Shutdown the data pod safely")
            self.log.info("Deleting pod %s", deploy_name)
            resp = self.csm_obj.master.create_pod_replicas(num_replica=0, deploy=deploy_name)
            assert not resp[0], f"Failed to delete pod {deploy_name}"
            self.log.info("[End] Successfully deleted pod %s", deploy_name)

            self.failed_pod.append(deploy_name)

            self.log.info("Step 3: Send Get cluster topology")
            resp = self.csm_obj.get_cluster_topology()
            assert resp.status_code == HTTPStatus.OK, \
                               "Status code check failed for get cluster topology"
        self.log.info("[END] Failure loop")
        self.log.info("##### Test ended -  %s #####", test_case_name)
