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

import pytest

from commons import configmanager, cortxlogging
from commons.constants import K8S_SCRIPTS_PATH, K8S_PRE_DISK
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
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        cls.update_seconds = cls.csm_conf["update_seconds"]

    def setup_method(self):
        """
        Setup method
        """
        self.log.info("Prerequisite: Deploy cortx cluster")
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
        for cluster in get_topology["topology"]["cluster"]:
            resp, result, err_msg = self.csm_obj.verify_storage_set(cluster_id = cluster['id'])
            assert result, err_msg
            self.log.info("Response : %s", resp)
            self.log.info("Step 2: Send GET request for fetching system topology"
                      "with storage set id")
            #need to revisit
            storage_sets = resp.json()["topology"]["cluster"][0]["storage_set"]
            for storage_set_id in storage_sets:
                self.log.info("Sending request for %s ", storage_set_id)
                resp, result, err_msg = self.csm_obj.verify_storage_set(cluster_id = cluster['id'],
                                                storage_set_id = storage_set_id['id'])
                assert result, err_msg
                self.log.info("Response : %s", resp)
        self.log.info("##### Test ended -  %s #####", test_case_name)