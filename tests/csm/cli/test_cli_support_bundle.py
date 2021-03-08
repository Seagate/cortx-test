#!/usr/bin/python
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
#
"""Test suite for support bundle operations"""

import logging
import time
import pytest
from commons.utils import assert_utils
from commons.helpers.node_helper import Node
from commons.helpers import s3_helper
from commons.utils import system_utils
from commons import constants
from commons import commands
from config import CMN_CFG
from libs.csm.cli.cortx_cli_support_bundle import CortxCliSupportBundle


class TestCliSupportBundle:
    """CORTX CLI Test suite for support bundle operations"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        cls.LOGGER = logging.getLogger(__name__)
        cls.LOGGER.info("STARTED : Setup operations at test suit level")
        cls.support_bundle_obj = CortxCliSupportBundle()
        cls.LOGGER.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        self.LOGGER.info("STARTED : Setup operations at test function level")
        login = self.support_bundle_obj.login_cortx_cli(cmd="sudo cortxcli")
        assert_utils.assert_equals(True, login[0], login[1])
        self.node_list = []
        self.LOGGER.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Deleting files which are created while executing tests
            - Log out from CORTX CLI console.
        """
        self.LOGGER.info(
            "STARTED : Teardown operations at test function level")
        remove_cmd = commands.CMD_REMOVE_DIR.format("/tmp/csm_support_bundle/")
        for each_node in self.node_list:
            resp = s3_helper.S3Helper.is_s3_server_path_exists(
                "/tmp/csm_support_bundle/",
                each_node,
                CMN_CFG["csm"]["admin_user"],
                CMN_CFG["csm"]["admin_pass"])
            if resp[0]:
                system_utils.run_remote_cmd(
                    cmd=remove_cmd,
                    hostname=each_node,
                    username=CMN_CFG["csm"]["admin_user"],
                    password=CMN_CFG["csm"]["admin_pass"])
        self.support_bundle_obj.logout_cortx_cli()
        self.LOGGER.info("ENDED : Teardown operations at test function level")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12845")
    def test_4487_generate_support_bundle(self):
        """
        Test that when each node-wise tar file is unzipped,
        it should contain logs for each registered components
        """
        self.LOGGER.info("Step 1: Generating support bundle through cli")
        new_dict = {}
        resp = self.support_bundle_obj.generate_support_bundle(comment="test_4487")
        assert_utils.assert_equals(True, resp[0], resp[1])
        bundle_id = resp[1].split("|")[1].strip()
        time.sleep(2000)
        self.LOGGER.info("Step 1: Generated support bundle through cli")
        self.LOGGER.info("Step 2: Verifying status of support bundle")
        resp = self.support_bundle_obj.support_bundle_status(
            bundle_id=bundle_id, output_format="json")
        self.LOGGER.debug(resp)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.node_list = list(set([each["node_name"] for each in resp[1][
            "status"] if constants.SUPPORT_BUNDLE_MSG in each["message"]]))
        self.LOGGER.info("Step 2: Verified status of support bundle")
        self.LOGGER.info("Step 2: Verifying logs are generated on each node")
        for each_node in self.node_list:
            resp = self.support_bundle_obj.extract_support_bundle(
                bundle_id, each_node, "/tmp/csm_support_bundle/", host=each_node)
            assert_utils.assert_equals(True, resp[0], resp[1])
            new_dict[each_node] = resp[1]
        time.sleep(1000)
        self.LOGGER.info("Step 2: Verified logs are generated on each node")
        self.LOGGER.info(
            "Step 3: Verifying logs are generated for each component")
        for each in new_dict:
            for each_dir in new_dict[each]:
                path = "{0}{1}/{2}/".format("/tmp/csm_support_bundle/",
                                            bundle_id, each_dir)
                obj = Node(hostname=each,
                           username=CMN_CFG["csm"]["admin_user"],
                           password=CMN_CFG["csm"]["admin_pass"])
                resp = obj.list_dir(path)
                self.LOGGER.info(resp)
                assert_utils.assert_equals(True, any([resp[0].endswith("gz") or resp[0].endswith(
                    "xz") or resp[0].endswith("zip") or resp[0].endswith("tar")]))
        self.LOGGER.info(
            "Step 3: Verified logs are generated for each component")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12843")
    def test_10367_generate_support_bundle_os(self):
        """
        Test that user can generate support bundle logs for OS
        """
        self.LOGGER.info("Step 1: Generating support bundle through cli")
        new_dict = {}
        resp = self.support_bundle_obj.generate_support_bundle_for_os(
            comment="test_10367")
        assert_utils.assert_equals(True, resp[0], resp[1])
        bundle_id = resp[1].split("|")[1].strip()
        time.sleep(700)
        self.LOGGER.info("Step 1: Generated support bundle through cli")
        self.LOGGER.info("Step 2: Verifying status of support bundle")
        resp = self.support_bundle_obj.support_bundle_status(
            bundle_id=bundle_id, output_format="json")
        self.LOGGER.debug(resp)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.node_list = list(set([each["node_name"] for each in resp[1][
            "status"] if constants.SUPPORT_BUNDLE_MSG in each["message"]]))
        self.LOGGER.info("Step 2: Verified status of support bundle")
        self.LOGGER.info(
            "Step 2: Verifying os logs are generated on each node")
        for each_node in self.node_list:
            resp = self.support_bundle_obj.extract_support_bundle(
                bundle_id, each_node, "/tmp/csm_support_bundle/", host=each_node)
            assert_utils.assert_equals(True, resp[0], resp[1])
            new_dict[each_node] = resp[1]
        time.sleep(1000)
        self.LOGGER.info("Step 2: Verified os logs are generated on each node")
        self.LOGGER.info(
            "Step 3: Verifying os logs are generated for each component")
        for each in new_dict:
            for each_dir in new_dict[each]:
                path = "{0}{1}/{2}/".format("/tmp/csm_support_bundle/",
                                            bundle_id, each_dir)
                obj = Node(hostname=each,
                           username=CMN_CFG["csm"]["admin_user"],
                           password=CMN_CFG["csm"]["admin_pass"])
                resp = obj.list_dir(path)
                self.LOGGER.info(resp)
                assert_utils.assert_equals(True, any([resp[0].endswith("gz") or resp[0].endswith(
                    "xz") or resp[0].endswith("zip") or resp[0].endswith("tar")]))
        self.LOGGER.info(
            "Step 3: Verified os logs are generated for each component")
