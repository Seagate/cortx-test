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

"""New R2 Support Bundle test suit."""
from __future__ import absolute_import

import os
import logging
from multiprocessing import Process
import pytest

from commons import constants
from commons.params import LOG_DIR
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils import support_bundle_utils as sb
from config import CMN_CFG


class TestR2SupportBundle:
    """Class for R2 Support Bundle testing"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.LOGGER = logging.getLogger(__name__)
        cls.LOGGER.info("TestR2SupportBundle  Test setup started...")

        cls.bundle_dir = os.path.join(LOG_DIR, "latest", "support_bundle")

    def setup_method(self):
        """Create test data directory"""
        self.LOGGER.info("STARTED: Test Setup")

        if system_utils.path_exists(self.bundle_dir):
            self.LOGGER.info("Removing existing directory %s", self.bundle_dir)
            system_utils.remove_dirs(self.bundle_dir)
        system_utils.make_dirs(self.bundle_dir)

    def teardown_method(self):
        """Delete test data file"""
        self.LOGGER.info("STARTED: Test Teardown")

        cleanup_dir = os.path.join(self.bundle_dir, "var")
        if system_utils.path_exists(cleanup_dir):
            self.LOGGER.info("Removing existing directory %s", cleanup_dir)
            system_utils.remove_dirs(cleanup_dir)
        self.LOGGER.info("ENDED : Teardown operations at test function level")

    def r2_extract_support_bundle(self, tar_file_name, dest_dir: str = None):
        """
        This function is used to extract support bundle files
        :param tar_file_name: Name of file to be extracted
        :param dest_dir: Name of directory to extract support bundle
        :rtype bool
        """
        self.LOGGER.info("Extracting support bundle files")
        # Check if file exists
        if not system_utils.path_exists(tar_file_name):
            self.LOGGER.error("File not found : %s", tar_file_name)
            return False
        # Check if folder exists
        if not system_utils.path_exists(dest_dir):
            system_utils.make_dirs(dest_dir)
        # Extract support bundle
        tar_sb_cmd = "tar -xvf {} -C {}".format(tar_file_name, dest_dir)
        system_utils.execute_cmd(tar_sb_cmd)
        return True

    def r2_verify_support_bundle(self, bundle_id, test_comp_list):
        """
        This function is used to verify support bundle content
        :param bundle_id: bundle id generated after support bundle generation command triggered
        :param test_comp_list: list of component expected in support bundle
        :rtype bool
        """
        self.LOGGER.debug("Verifying logs are generated on each node")

        num_nodes = len(CMN_CFG["nodes"])
        for node in range(num_nodes):
            host = CMN_CFG["nodes"][node]["hostname"]
            tar_file = "".join([bundle_id, ".srvnode{}"]).format(node)
            # extract generated tar file from create_support_bundle_single_cmd()
            tar_file_path = os.path.join(self.bundle_dir, tar_file + ".tar")
            self.r2_extract_support_bundle(tar_file_path, self.bundle_dir)
            # extract generated tar file from support_bundle generate command on node
            tar_file_path = os.path.join(self.bundle_dir, "var", "log", "cortx", "support_bundle",
                                         bundle_id, host, bundle_id + "_" + host + ".tar.gz")
            self.r2_extract_support_bundle(tar_file_path, self.bundle_dir)

            self.LOGGER.debug(
                "Verifying logs are generated for each component for this node")
            for component_dir in test_comp_list:
                component_dir_name = os.path.join(
                    self.bundle_dir, host, component_dir)
                self.LOGGER.info("new component_dir : %s ", component_dir_name)
                found = os.path.isdir(component_dir_name)
                if found:
                    self.LOGGER.debug(
                        "component_dir found %s", component_dir_name)
                else:
                    self.LOGGER.error(
                        "component_dir not found %s", component_dir_name)
                    assert_utils.assert_true(
                        found, 'Component Directory in support bundle not found')
            self.LOGGER.debug(
                "Verified logs are generated for each component for this node")

        self.LOGGER.debug("Verified logs are generated on each node")

    @pytest.mark.cluster_user_ops
    @pytest.mark.lr
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-20114")
    def test_20114_generate_support_bundle_single_command(self):
        """
        Validate support bundle is generated for all components single node/multi node setup
        """
        self.LOGGER.info("Step 1: Generating support bundle through cli")
        resp = sb.create_support_bundle_single_cmd(
            self.bundle_dir, bundle_name="test_20114")
        assert_utils.assert_true(resp[0], resp[1])
        self.LOGGER.info("Step 1: Generated support bundle through cli")

        test_comp_list = constants.SUPPORT_BUNDLE_COMPONENT_LIST
        self.LOGGER.info(
            "Step 2: Verifying logs are generated for each component on each node")
        self.r2_verify_support_bundle(resp[1], test_comp_list)
        self.LOGGER.info(
            "Step 2: Verified logs are generated for each component on each node")

    @pytest.mark.cluster_user_ops
    @pytest.mark.lr
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-20115")
    def test_20115_generate_support_bundle_component(self):
        """
        Validate status of support bundle collection for each of the components/nodes
        """
        self.LOGGER.info("Step 1: Generating support bundle through cli")
        resp = sb.create_support_bundle_single_cmd(
            self.bundle_dir, bundle_name="test_20115", comp_list="'s3server;csm;provisioner'")
        assert_utils.assert_true(resp[0], resp[1])
        self.LOGGER.info("Step 1: Generated support bundle through cli")

        test_comp_list = ["csm", "s3", "provisioner"]
        self.LOGGER.info(
            "Step 2: Verifying logs are generated for each component on each node")
        self.r2_verify_support_bundle(resp[1], test_comp_list)
        self.LOGGER.info(
            "Step 2: Verified logs are generated for each component on each node")

    @pytest.mark.cluster_user_ops
    @pytest.mark.lc
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-32752")
    def test_32752(self):
        """
        Validate status of support bundle for LC
        """
        self.LOGGER.info("Step 1: Generating support bundle ")
        dest_dir = "file:///var/log/cortx/support_bundle"
        sb_identifier = system_utils.random_string_generator(10)
        msg = "TEST-32752"
        self.LOGGER.info("Support Bundle identifier of : %s ", sb_identifier)
        generate_sb_process = Process(
            target=sb.generate_sb_LC,
            args=(dest_dir, sb_identifier, None, msg))

        generate_sb_process.start()
        self.LOGGER.info("Step 2: checking Inprogress status of support bundle")
        resp = sb.sb_status_LC(sb_identifier)
        if "In-Progress" in resp:
            self.LOGGER.info("support bundle generation is In-progress status")
        elif "Successfully generated" in resp:
            self.LOGGER.error(f"Support bundle got generated "
                              f"very quickly need to check manually: {resp}")
        else:
            self.LOGGER.error(f"Support bundle is not generated: {resp}")

        generate_sb_process.join()

        self.LOGGER.info("Step 3: checking completed status of support bundle")
        resp = sb.sb_status_LC(sb_identifier)
        if "Successfully generated" in resp:
            self.LOGGER.info("support bundle generation completed")
        elif "In-Progress" in resp:
            self.LOGGER.error(f"Support bundle is In-progress state, "
                              f"which is unexpected: {resp}")
        else:
            self.LOGGER.error(False, f"Support bundle is not generated: {resp}")
