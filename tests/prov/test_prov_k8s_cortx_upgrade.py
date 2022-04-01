#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""Test cases for K8s CORTX Software Upgrade."""

import logging
import os
import time
import pytest
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from config import CMN_CFG, PROV_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestK8CortxUpgrade:
    """This class contains test cases for K8s CORTX Software Upgrade."""

    @classmethod
    def setup_class(cls):
        """Setup class."""
        LOGGER.info("STARTED: Setup Module operations")
        cls.repo_clone_path = "root"
        cls.deployment_version = os.getenv("DEPLOYMENT_VERSION")
        cls.upgrade_image = os.getenv("UPGRADE_IMAGE", None)
        cls.current_image = os.getenv("CURRENT_IMAGE", None)
        cls.deploy_conf = PROV_CFG["k8s_cortx_deploy"]
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.remote_path = cons.CLUSTER_CONF_PATH
        cls.local_path = cons.LOCAL_CONF_PATH
        cls.collect_sb = True
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            cls.host_list.append(node_obj)
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        resp = cls.deploy_lc_obj.check_s3_status(cls.master_node_obj,
                                                 pod_prefix=cons.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Setup operations finished.")

    def teardown_class(self):
        """Teardown method."""
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                            scripts_path=
                                                            self.deploy_conf['k8s_dir'])

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade_disruptive
    @pytest.mark.tags("TEST-33660")
    def test_33660(self):
        """Verify CORTX Software upgrade."""
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        resp = HAK8s.get_config_value(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        current_version = resp[1]['cortx']['common']['release']['version']
        LOGGER.info("Current version: %s", current_version)
        installed_version = current_version.split("-")[1]
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 2: Done.")
        LOGGER.info("Step 3: Check if installing version is higher than installed version.")
        LOGGER.info("upgrade_image: %s", self.upgrade_image)
        upgrade_image_version = self.upgrade_image.split(":")[1]
        upgrade_version = upgrade_image_version.split("-")[1]
        LOGGER.info("Installing CORTX image version: %s", upgrade_version)
        if int(upgrade_version) <= int(installed_version):
            assert False, "Installed version is same or higher than installing version."
        else:
            LOGGER.info("Installed version is lower than installing version.")
        LOGGER.info("Step 4: Check cluster health.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj,
                                                  pod_prefix=cons.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Start upgrade.")
        resp = self.deploy_lc_obj.service_upgrade_software(self.master_node_obj, self.upgrade_image)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Check if installed version is equals to installing version.")
        resp = HAK8s.get_config_value(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        new_installed_version = resp[1]['cortx']['common']['release']['version'].split("-")[1]
        LOGGER.info("New CORTX image version: %s", new_installed_version)
        assert_utils.assert_equals(new_installed_version, upgrade_version,
                                   "new_installed version is equal to upgrade_version.")
        LOGGER.info("Step 7 : Check PODs are up and running.")
        resp = self.deploy_lc_obj.check_pods_status(self.master_node_obj)
        assert_utils.assert_true(resp)
        LOGGER.info("All PODs are up and running.")
        LOGGER.info("Step 8 : Check Cluster health and services.")
        time.sleep(PROV_CFG["deploy_ff"]["per_step_delay"])
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj,
                                                  pod_prefix=cons.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        pod_name = self.master_node_obj.get_pod_name(pod_prefix=cons.POD_NAME_PREFIX)
        assert_utils.assert_true(pod_name[0], pod_name[1])
        resp = self.deploy_lc_obj.get_hctl_status(self.master_node_obj, pod_name[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and all services are started.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade_disruptive
    @pytest.mark.tags("TEST-33669")
    def test_33669(self):
        """Verify Hotfix upgrade for same or lower version."""
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        resp = HAK8s.get_config_value(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        current_version = resp[1]['cortx']['common']['release']['version']
        LOGGER.info("Current version: %s", current_version)
        installed_version = current_version.split("-")[1]
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 2: Done.")
        LOGGER.info("Step 3: Check if installing version is higher than installed version.")
        LOGGER.info("upgrade_image: %s", self.upgrade_image)
        upgrade_image_version = self.upgrade_image.split(":")[1]
        upgrade_version = upgrade_image_version.split("-")[1]
        LOGGER.info("Installing CORTX image version: %s", upgrade_version)
        # TO DO BUG #CORTX-29184
        LOGGER.info("Step 3: Start upgrade.")
        resp = self.deploy_lc_obj.service_upgrade_software(self.master_node_obj, self.upgrade_image)
        assert_utils.assert_false(resp[0], resp[1])
        if int(upgrade_version) <= int(installed_version):
            assert_utils.assert_true(resp[0],
                                     "Installed version is same or higher than installing version.")
        LOGGER.info("Test Completed.")
