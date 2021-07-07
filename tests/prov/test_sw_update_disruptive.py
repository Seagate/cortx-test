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

"""
Prov test file for all the Prov tests scenarios for SW update disruptive.
"""

import os
import logging
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons.utils import assert_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, PROV_CFG
from libs.prov.prov_upgrade import ProvSWUpgrade
from libs.di.di_run_man import RunDataCheckManager
from libs.di.di_mgmt_ops import ManagementOPs

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestSWUpdateDisruptive:
    """
    Test suite for prov tests scenarios for SW update disruptive.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.prov_obj = ProvSWUpgrade()
        cls.mgnt_ops = ManagementOPs()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.build_up1 = os.getenv("Build_update1", None)
        cls.build_up2 = os.getenv("Build_update2", None)
        cls.build_update1 = "{}/{}".format(cls.build_up1,
                                   "prod") if cls.build_up1 else PROV_CFG["build_def"]
        cls.build_update2 = "{}/{}".format(cls.build_up2,
                                           "prod") if cls.build_up2 else PROV_CFG["build_def"]
        cls.build_branch = os.getenv("Build_Branch", "stable")
        cls.build_iso1 = PROV_CFG["build_iso"].format(
            cls.build_branch, cls.build_update1, cls.build_up1)
        cls.build_sig1 = PROV_CFG["build_sig"].format(
            cls.build_branch, cls.build_update1, cls.build_up1)
        cls.build_key1 = PROV_CFG["build_key"].format(
            cls.build_branch, cls.build_update1)
        cls.build_iso2 = PROV_CFG["build_iso"].format(
            cls.build_branch, cls.build_update2, cls.build_update2)
        cls.build_sig2 = PROV_CFG["build_sig"].format(
            cls.build_branch, cls.build_update2, cls.build_update2)
        cls.build_key2 = PROV_CFG["build_key"].format(
            cls.build_branch, cls.build_update2)
        cls.iso1_list = [cls.build_iso1, cls.build_sig1, cls.build_key1]
        cls.iso2_list = [cls.build_iso2, cls.build_sig2, cls.build_key2]
        cls.repo1_list = [PROV_CFG["iso_repo"].format(cls.build_up1),
                          PROV_CFG["sig_repo"].format(cls.build_up1),
                          PROV_CFG["key_repo"]]
        cls.repo2_list = [PROV_CFG["iso_repo"].format(cls.build_up2),
                          PROV_CFG["sig_repo"].format(cls.build_up2),
                          PROV_CFG["key_repo"]]
        cls.node_list = []
        cls.host_list = []
        cls.hlt_list = []
        cls.srvnode_list = []

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.uname, password=cls.passwd))
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname,
                                       password=cls.passwd))

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        LOGGER.info("Checking if all nodes online and PCS clean.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")
        LOGGER.info("ENDED: Setup Operations")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-23175")
    @CTFailOn(error_handler)
    def test_sw_upgrade(self):
        """
        This test will trigger SW upgrade with correct ISO and on healthy system to check
        if SW upgrade command works fine. Also once process is complete, it will check if new
        version is shown on provisioner and check system health and Run IOs.
        """
        LOGGER.info("Started: SW upgrade disruptive for CORTX sw components.")

        build = self.prov_obj.get_build_version(self.node_list[0])
        LOGGER.info("Current cortx build: {} and version on system: {}".format(build[0], build[1]))

        LOGGER.info("Check that update builds are different.")
        assert_utils.assert_not_equal(build[0], self.build_up1,
                                      "SW upgrade from same build to same build not supported.")

        LOGGER.info("Start IOs on the current SW version.")
        users = self.mgnt_ops.create_account_users(nusers=2, use_cortx_cli=False)
        data = self.mgnt_ops.create_buckets(nbuckets=10, users=users)
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'TEST-23175-{}'.format(self.build_up1)}
        run_data_chk_obj.start_io(
            users=data, buckets=None, files_count=8, prefs=pref_dir)

        LOGGER.info("Download the upgrade ISO, SIG file and GPG key")
        for dnld in self.iso1_list:
            self.node_list[0].execute_cmd(common_cmds.CMD_WGET.format(dnld),
                                          read_lines=True)
        LOGGER.info("Set the update repo.")
        resp = self.prov_obj.set_validate_repo(self.repo1_list, self.node_list[0])
        assert_utils.assert_true(resp[0], "Given sw upgrade version is not compatible.")
        assert_utils.assert_equal(resp[1], self.build_up1,
                                  "Set ISO version doesn't match with desired one.")
        LOGGER.info("Start the SW upgrade operation in offline mode.")
        resp = self.prov_obj.check_sw_upgrade(self.node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.build_up1,
                                  "SW build version on system doesn't match with desired one.")
        LOGGER.info("SW upgrade process completed and SW version updated from {} to {}"
                    .format(build[0], resp[1]))

        LOGGER.info("Checking the overall cluster and nodes status.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes online and all services in cluster up and running.")

        LOGGER.info("Checking DI for IOs run before upgrade.")
        run_data_chk_obj.stop_io(users=data, di_check=True)
        #TODO: Need to add validation of IOs run from DI framework.
        LOGGER.info("IOs working fine with latest build {} upgraded.".format(self.build_up1))

        LOGGER.info("Completed: SW upgrade disruptive for CORTX sw components.")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-23206")
    @CTFailOn(error_handler)
    def test_sw_upgrade_multiple(self):
        """
        This test will trigger SW upgrade with correct ISO and on healthy system to check
        if SW upgrade command works fine in succession. Also once process is complete, it
        will check if new version is shown on provisioner and check system health and Run IOs.
        """
        LOGGER.info("Started: SW upgrade disruptive for CORTX sw components in succession.")

        LOGGER.info("Check that update builds are different.")
        assert_utils.assert_not_equal(self.build_up1, self.build_up2,
                                      "SW upgrade from same build to same build not supported.")

        iso_list = [self.iso1_list, self.iso2_list]
        repo_list = [self.repo1_list, self.repo2_list]
        build_list = [self.build_up1, self.build_up2]
        for iso, repo, build in zip(iso_list, repo_list, build_list):
            build_cur = self.prov_obj.get_build_version(self.node_list[0])
            LOGGER.info("Current cortx build: {} and version on system: {}"
                        .format(build_cur[0], build_cur[1]))

            LOGGER.info("Start IOs on the current SW version.")
            users = self.mgnt_ops.create_account_users(nusers=2, use_cortx_cli=False)
            data = self.mgnt_ops.create_buckets(nbuckets=10, users=users)
            run_data_chk_obj = RunDataCheckManager(users=data)
            pref_dir = {"prefix_dir": 'TEST-23206-{}'.format(build)}
            run_data_chk_obj.start_io(
                users=data, buckets=None, files_count=8, prefs=pref_dir)

            LOGGER.info("Download the upgrade ISO, SIG file and GPG key for build: {}"
                        .format(build))
            for dnld in iso:
                self.node_list[0].execute_cmd(common_cmds.CMD_WGET.format(dnld),
                                              read_lines=True)
            LOGGER.info("Set the update repo.")
            resp = self.prov_obj.set_validate_repo(repo, self.node_list[0])
            assert_utils.assert_true(resp[0], "Given sw upgrade version is not compatible.")
            assert_utils.assert_equal(resp[1], build,
                                      "Set ISO version doesn't match with desired one.")
            LOGGER.info("Start the SW upgrade operation in offline mode.")
            resp = self.prov_obj.check_sw_upgrade(self.node_list[0])
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_equal(resp[1], build,
                                      "SW build version on system doesn't match with desired one.")
            LOGGER.info("SW upgrade process completed and SW version updated from {} to {}"
                        .format(build_cur[0], resp[1]))

            LOGGER.info("Checking the overall cluster and nodes status.")
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes online and all services in cluster up and running.")

            LOGGER.info("Checking DI for IOs run before upgrade.")
            run_data_chk_obj.stop_io(users=data, di_check=True)
            # TODO: Need to add validation of IOs run from DI framework.
            LOGGER.info("IOs working fine with latest build {} upgraded.".format(build))

            LOGGER.info("Removing KEY file to avoid conflicts.")
            self.node_list[0].remove_file(filename=PROV_CFG["key_repo"])
            self.node_list[0].remove_file(filename=PROV_CFG["key1_repo"])

        LOGGER.info("Completed: SW upgrade disruptive for CORTX sw components in succession.")
