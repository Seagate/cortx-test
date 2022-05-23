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

"""Provisioner Component level test cases for Data only pod deployment in k8s environment."""

import logging
import os
from string import Template
import pytest

from commons import commands
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG, PROV_TEST_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestProvK8DataOnlyDeploy:
    """
    This class contains Provisioner Component level test cases for
    Data only pod deployment in k8s environment.
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        cls.cortx_data_image = os.getenv("CORTX_DATA_IMAGE", None)
        cls.cortx_image = os.getenv("CORTX_IMAGE", None)
        cls.deployment_type = os.getenv("DEPLOYMENT_TYPE", cls.deploy_cfg["deployment_type"])
        cls.server_only_list = ["server-only", "standard"]
        cls.script_remote_branch = os.getenv("SCRIPT_REMOTE_BRANCH", "cortx-test")
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.local_sol_path = cons.LOCAL_SOLUTION_PATH
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
        LOGGER.info("Done: Setup operations finished.")

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-35766")
    def test_35766(self):
        """
        Verify N-Node data only pod deployment in K8s environment.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Clone cortx-k8s script repo on setup.")
        template = Template('cd $HA_TMP; $CMD_GIT_CLONE $PATH $REPO')
        cmd = template.substitute(HA_TMP=cons.HA_TMP,CMD_GIT_CLONE=commands.CMD_GIT_CLONE_TEMPLATE,
                                    PATH=self.prov_deploy_cfg["git_prov_k8_repo_template"],
                                    REPO=self.script_remote_branch)
        LOGGER.info(cmd)
        for node_obj in self.host_list:
            node_obj.execute_cmd(cmd)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Update solution.yaml with default data only deploy config.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.example.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        resp = self.deploy_lc_obj.update_sol_for_granular_deploy(file_path=self.local_sol_path,
                                                            host_list=self.host_list,
                                            master_node_list=self.master_node_obj,
                                            image=self.cortx_data_image,
                                        deployment_type=self.deploy_cfg["deployment_type_data"])

        assert_utils.assert_true(resp[0])
        for node_obj in self.host_list:
            res = node_obj.copy_file_to_remote(local_path=resp[1],
                                               remote_path=self.prov_deploy_cfg[
                                    "git_remote_path"] + self.deploy_cfg["solution_file"])
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Run prereq script on setup nodes.")
        for node_obj in self.host_list:
            self.deploy_lc_obj.execute_prereq_cortx(node_obj,
                                                    self.prov_deploy_cfg["git_remote_path"],
                                                    self.prov_deploy_cfg["pre_req"])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Start data only cortx cluster.")
        resp = self.deploy_lc_obj.deploy_cluster(self.master_node_obj,
                                                 self.prov_deploy_cfg["git_remote_path"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-39370")
    def test_39370(self):
        """
        Verify pods status for data only pod deployment.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check PODs are up and running.")
        resp = self.deploy_lc_obj.check_pods_status(self.master_node_obj)
        assert_utils.assert_true(resp)
        LOGGER.info("All PODs are up and running.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-39333")
    def test_39333(self):
        """
        Verify S3 status for data pods.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check Cluster status for data pods")
        resp = self.deploy_lc_obj.check_service_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and all services are started for data pods.")
        LOGGER.info("Test Completed.")
