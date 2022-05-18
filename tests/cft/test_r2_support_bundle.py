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

"""New R2 Support Bundle test suit."""
from __future__ import absolute_import

import os
import logging
import shutil
import time
from multiprocessing import Process
import pytest

from commons import constants
from commons.constants import const
from commons import commands as comm
from commons.params import LOG_DIR
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils import support_bundle_utils as sb
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG


def size_verify(component_dir_name):
    """
    This function which is used to verify component directory has specific size limit logs
    """
    files = os.listdir(component_dir_name)
    number = len(files)
    count = 0
    flg = False
    for file in files:
        if os.path.getsize(file)>=constants.MIN and os.path.getsize(file)<=constants.MAX:
            count+= 1
    if count == number:
        flg = True
    return flg


# pylint: disable-msg=too-many-public-methods
class TestR2SupportBundle:
    """Class for R2 Support Bundle testing"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.LOGGER = logging.getLogger(__name__)
        cls.LOGGER.info("TestR2SupportBundle  Test setup started...")

        cls.bundle_dir = os.path.join(LOG_DIR, "latest", "support_bundle")
        for node in CMN_CFG["nodes"]:
            if node["node_type"] == "master":
                host = node["hostname"]
                username = node["username"]
                password = node["password"]
                cls.node_obj = LogicalNode(hostname=host, username=username, password=password)

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

    def r2_verify_support_bundle(self, bundle_id, test_comp_list, size=None, services=None):
        """
        This function is used to verify support bundle content
        :param bundle_id: bundle id generated after support bundle generation command triggered
        :param test_comp_list: list of component expected in support bundle
        :param size : size of the log files expected in support bundle
        :param services: services of the components should be generated
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
                if size is not None:
                    resp = size_verify(component_dir_name)
                    if resp:
                        self.LOGGER.info("Component dir %s is with limited size logs",
                                         component_dir_name)
                    else:
                        self.LOGGER.error("Component dir %s is not with limited size logs",
                                          component_dir_name)
                if services is not None:
                    auth_services = os.path.isfile(const.AUTHSERVER_LOG_PATH)
                    if auth_services:
                        self.LOGGER.info("specified Authserver files are generated")
                    else:
                        self.LOGGER.info("specified Autthserver files are not generated")
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
        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)

        output = self.node_obj.execute_cmd(cmd=comm.KUBECTL_GET_POD_CONTAINERS.format(pod_list[0]),
                                           read_lines=True)
        container_list = output[0].split()

        generate_sb_process = Process(target=sb.generate_sb_lc,
                                      args=(dest_dir, sb_identifier, pod_list[0],
                                            msg, container_list[0]))

        generate_sb_process.start()
        time.sleep(2)
        self.LOGGER.info("Step 2: checking In progress status of support bundle")
        resp = sb.sb_status_lc(sb_identifier)
        if "In-Progress" in resp:
            self.LOGGER.info("support bundle generation is In-progress status")
        elif "Successfully generated" in resp:
            assert_utils.assert_true(False, f"Support bundle got generated "
                              f"very quickly need to check manually: {resp}")
        else:
            assert_utils.assert_true(False, f"Support bundle is not generated: {resp}")

        generate_sb_process.join()

        self.LOGGER.info("Step 3: checking completed status of support bundle")
        resp = sb.sb_status_lc(sb_identifier)
        if "Successfully generated" in resp:
            self.LOGGER.info("support bundle generation completed")
        elif "In-Progress" in resp:
            assert_utils.assert_true(False, f"Support bundle is In-progress state, "
                                            f"which is unexpected: {resp}")
        else:
            assert_utils.assert_true(False, f"Support bundle is not generated: {resp}")

    @pytest.mark.cluster_user_ops
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-32603")
    def test_32603_generate_support_bundle_size_limit(self):
        """
        Validate  support bundle size limit filter for each log
        """
        self.LOGGER.info("Step 1: Generating support bundle through cli")
        resp = sb.create_support_bundle_single_cmd(self.bundle_dir, bundle_name="test_32603",
                                                   comp_list="'s3server;csm;provisioner'",
                                                   size='1M')
        assert_utils.assert_true(resp[0], resp[1])
        self.LOGGER.info("Step 1: Generated support bundle through cli")
        size='1M'
        test_comp_list = ["csm", "s3", "provisioner"]
        self.LOGGER.info(
            "Step 2: Verifying logs are generated with specified size limit")
        self.r2_verify_support_bundle(resp[1], test_comp_list,size)
        self.LOGGER.info(
            "Step 2: Verified logs are generated with specific size limit")

    @pytest.mark.cluster_user_ops
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-32606")
    def test_32606_generate_support_bundle_service_filter(self):
        """
        Validate  support bundle service filter
        """
        self.LOGGER.info("Step 1: Generating support bundle through cli")
        resp = sb.create_support_bundle_single_cmd(
            self.bundle_dir, bundle_name="test_32606", comp_list="'s3server'",
            services="S3:Authserver")
        assert_utils.assert_true(resp[0], resp[1])
        self.LOGGER.info("Step 1: Generated support bundle through cli")
        services = ['Authserver']
        test_comp_list = ["s3"]
        self.LOGGER.info(
            "Step 2: Verifying logs are generated with specified services")
        self.r2_verify_support_bundle(resp[1], test_comp_list, services)
        self.LOGGER.info(
            "Step 2: Verified logs are generated with specified services")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31246")
    def test_31246(self):
        """
        Validate CSM log path exists
        """
        self.LOGGER.info("Checking log path for CSM")
        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.CONTROL_POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            resp = sb.log_file_size_on_path(pod, constants.LOG_PATH_CSM)
            if "No such file" in resp:
                assert_utils.assert_true(False, f"Log path {constants.LOG_PATH_CSM} "
                                                f"does not exist on pod: {pod} resp: {resp}")
            self.LOGGER.info("CSM log files: %s", resp)
        self.LOGGER.info("Successfully validated CSM log path")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31258")
    def test_31258(self):
        """
        Validate CSM log files size are within defined max limit
        """
        self.LOGGER.info("Checking log file size for CSM")
        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.CONTROL_POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            resp = sb.log_file_size_on_path(pod, constants.LOG_PATH_CSM)
            if "No such file" in resp:
                assert_utils.assert_true(False, f"Log path {constants.LOG_PATH_CSM} "
                                                f"does not exist on pod: {pod} resp: {resp}")
            lines = resp.splitlines()
            for count in range(1,len(lines)):
                line = lines[count].split()
                file_size = int(line[4][:-2])
                if file_size > constants.MAX_LOG_FILE_SIZE_CSM_MB:
                    assert_utils.assert_true(False, f"CSM max file size is: "
                        f"{constants.MAX_LOG_FILE_SIZE_CSM_MB}MB and actual file size is:"
                            f"{file_size}MB for file:{line[-1]}")
        self.LOGGER.info("Successfully validated CSM log files size, "
                         "all files are within max limit")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31252")
    def test_31252(self):
        """
        Validate CSM rotating log files are as per frequency configured
        """
        self.LOGGER.info("Checking CSM rotating log files are as per frequency configured")
        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.CONTROL_POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            resp = sb.log_file_size_on_path(pod, constants.LOG_PATH_CSM)
            if "No such file" in resp:
                assert_utils.assert_true(False, f"Log path {constants.LOG_PATH_CSM} "
                                                f"does not exist on pod: {pod} resp: {resp}")
            lines = resp.splitlines()
            self.LOGGER.info("CSM log files on path %s: %s", constants.LOG_PATH_CSM, resp)
            if constants.MAX_NO_OF_ROTATED_LOG_FILES['CSM'] < (len(lines) - 1):
                assert_utils.assert_true(False, f"Max rotating CSM log files "
                                        f"are:{constants.MAX_NO_OF_ROTATED_LOG_FILES['CSM']} "
                                        f"and actual no of files are: {len(lines) - 1}")
        self.LOGGER.info("Successfully validated CSM rotating log files are as per "
                         "frequency configured for all pods")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31247")
    def test_31247(self):
        """
        Validate S3 log path exists
        """
        self.LOGGER.info("Checking s3 log file paths")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for log_path in constants.LOG_PATH_FILE_SIZE_MB_S3:
                log_path = log_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                self.LOGGER.info("S3 log files: %s", resp)
        self.LOGGER.info("Successfully validated S3 log file paths for all pods")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31259")
    def test_31259(self):
        """
        Validate S3 log files size are within defined max limit
        """
        self.LOGGER.info("Checking log file size for S3")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_S3:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                lines = resp.splitlines()
                self.LOGGER.info("S3 log files on path %s: %s", log_path, resp)
                for count in range(1, len(lines)):
                    line = lines[count].split()
                    file_size = int(line[4][:-2])
                    if file_size > constants.LOG_PATH_FILE_SIZE_MB_S3[file_path]:
                        assert_utils.assert_true(False, f"S3 max file size is: "
                                    f"{constants.LOG_PATH_FILE_SIZE_MB_S3[file_path]}MB"
                                    f" and actual file size is: {file_size}MB for file:{line[-1]}")
        self.LOGGER.info("Successfully validated S3 log files size, "
                         "all files are within max limit")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31249")
    def test_31249(self):
        """
        Validate Utils log path exists
        """
        self.LOGGER.info("Checking Utils log file paths")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for log_path in constants.LOG_PATH_FILE_SIZE_MB_UTILS:
                log_path = log_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} does not exist "
                                                    f"on pod: {pod} resp: {resp}")
                self.LOGGER.info("Utils log files: %s", resp)
        self.LOGGER.info("Successfully validated Utils log file paths for all pods")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31261")
    def test_31261(self):
        """
        Validate Utils log files size are within defined max limit
        """
        self.LOGGER.info("Checking log file size for Utils")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_UTILS:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                lines = resp.splitlines()
                self.LOGGER.info("Utils log files on path %s: %s", log_path, resp)
                for count in range(1, len(lines)):
                    line = lines[count].split()
                    file_size = int(line[4][:-2])
                    if file_size > constants.LOG_PATH_FILE_SIZE_MB_UTILS[file_path]:
                        assert_utils.assert_true(False, f"Utils max file size is: "
                            f"{constants.LOG_PATH_FILE_SIZE_MB_UTILS[file_path]}MB "
                                f"and actual file size is: {file_size}MB for file:{line[-1]}")
        self.LOGGER.info("Successfully validated Utils log files size, "
                             "all files are within max limit")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31255")
    def test_31255(self):
        """
        Validate Utils rotating log files are as per frequency configured
        """
        self.LOGGER.info("Checking Utils rotating log files are as per frequency configured")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_UTILS:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                lines = resp.splitlines()
                self.LOGGER.info("Utils log files on path %s: %s", log_path, resp)
                if constants.MAX_NO_OF_ROTATED_LOG_FILES['Utils'] < (len(lines) - 1):
                    assert_utils.assert_true(False, f"Max rotating Utils log files "
                                        f"are:{constants.MAX_NO_OF_ROTATED_LOG_FILES['Utils']}"
                                        f"and actual no of files are: {len(lines) - 1}")
        self.LOGGER.info("Successfully validated Utils rotating log files are as per "
                         "frequency configured for all pods")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31248")
    def test_31248(self):
        """
        Validate HARE log path exists
        """
        self.LOGGER.info("Checking HARE log file paths")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for log_path in constants.LOG_PATH_FILE_SIZE_MB_HARE:
                log_path = log_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                self.LOGGER.info("HARE log files: %s", resp)
        self.LOGGER.info("Successfully validated HARE log file paths for all pods")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31260")
    def test_31260(self):
        """
        Validate HARE log files size are within defined max limit
        """
        self.LOGGER.info("Checking log file size for HARE")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_HARE:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                lines = resp.splitlines()
                self.LOGGER.info("HARE log files on path %s: %s", log_path, resp)
                for count in range(1, len(lines)):
                    line = lines[count].split()
                    file_size = int(line[4][:-2])
                    if file_size > constants.LOG_PATH_FILE_SIZE_MB_HARE[file_path]:
                        assert_utils.assert_true(False, f"HARE max file size is: "
                            f"{constants.LOG_PATH_FILE_SIZE_MB_HARE[file_path]}MB "
                                f"and actual file size is: {file_size}MB for file:{line[-1]}")
        self.LOGGER.info("Successfully validated HARE log files size, "
                         "all files are within max limit")

    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31254")
    def test_31254(self):
        """
        Validate HARE rotating log files are as per frequency configured
        """
        self.LOGGER.info("Checking HARE rotating log files are as per frequency configured")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_HARE:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                if "No such file" in resp:
                    assert_utils.assert_true(False, f"Log path {log_path} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                lines = resp.splitlines()
                self.LOGGER.info("HARE log files on path %s: %s", log_path, resp)
                if constants.MAX_NO_OF_ROTATED_LOG_FILES['Hare'] < (len(lines) - 1):
                    assert_utils.assert_true(False, f"Max rotating HARE log files "
                                        f"are:{constants.MAX_NO_OF_ROTATED_LOG_FILES['Hare']} "
                                        f"and actual no of files are: {len(lines) - 1}")
        self.LOGGER.info("Successfully validated HARE rotating log files are as per "
                         "frequency configured for all pods")

    # pylint: disable-msg=too-many-nested-blocks
    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31250")
    def test_31250(self):
        """
        Validate Motr log path exists
        """
        self.LOGGER.info("Checking Motr log file paths")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_MOTR:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                lines = resp.splitlines()
                self.LOGGER.info("Motr log files on path %s: %s", log_path, resp)
                for count in range(1, len(lines)):
                    line = lines[count].split()
                    log_path_m0d = log_path + line[-1] + "/"
                    resp = sb.log_file_size_on_path(pod, log_path_m0d)
                    lines_m0d = resp.splitlines()
                    if "trace" in log_path_m0d:
                        if "No such file" in resp:
                            assert_utils.assert_true(False, f"Log path {log_path_m0d} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                        self.LOGGER.info("Motr trace log files on path %s: %s", log_path_m0d, resp)
                    elif "addb" in log_path_m0d:
                        for counter in range(1, len(lines_m0d)):
                            addb_stobs_dir = lines_m0d[counter].split()
                            log_path_addb_stobs = log_path_m0d + addb_stobs_dir[-1] + "/o"
                            resp = sb.log_file_size_on_path(pod, log_path_addb_stobs)

                            if "No such file" in resp:
                                assert_utils.assert_true(False, f"Log path {log_path_addb_stobs}"
                                                    f"does not exist on pod: {pod} resp:{resp}")
                            self.LOGGER.info("Motr addb log files on path %s: %s",
                                             log_path_addb_stobs, resp)
                    else:
                        assert_utils.assert_true(False, f"No addb or trace directory found "
                                                        f"on path: {log_path_m0d}")

        self.LOGGER.info("Successfully validated Motr log file paths for all pods")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31262")
    def test_31262(self):
        """
        Validate Motr log file size
        """
        self.LOGGER.info("Checking Motr log file size")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_MOTR:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                lines = resp.splitlines()
                self.LOGGER.info("Motr log files on path %s: %s", log_path, resp)
                for count in range(1, len(lines)):
                    line = lines[count].split()
                    log_path_m0d = log_path + line[-1] + "/"
                    resp = sb.log_file_size_on_path(pod, log_path_m0d)
                    lines_m0d = resp.splitlines()
                    if "trace" in log_path_m0d:
                        if "No such file" in resp:
                            assert_utils.assert_true(False, f"Log path {log_path_m0d} "
                                                f"does not exist on pod: {pod} resp: {resp}")
                        self.LOGGER.info("Motr trace log files on path %s: %s",
                                         log_path_m0d, resp)
                        for counter in range(1, len(lines_m0d)):
                            line = lines_m0d[counter].split()
                            file_size = int(line[4][:-2])
                            if file_size > constants.LOG_PATH_FILE_SIZE_MB_MOTR[file_path]:
                                assert_utils.assert_true(False, f"Motr trace max file size is: "
                                    f"{constants.LOG_PATH_FILE_SIZE_MB_MOTR[file_path]}MB "
                                    f"and actual file size: {file_size}MB for file:{line[-1]}")
                    elif "addb" in log_path_m0d:
                        for counter in range(1, len(lines_m0d)):
                            addb_stobs_dir = lines_m0d[counter].split()
                            log_path_addb_stobs = log_path_m0d + addb_stobs_dir[-1] + "/o"
                            resp = sb.log_file_size_on_path(pod, log_path_addb_stobs)
                            act_files = resp.splitlines()
                            if "No such file" in resp:
                                assert_utils.assert_true(False, f"Log path {log_path_addb_stobs}"
                                                    f"does not exist on pod: {pod} resp:{resp}")
                            self.LOGGER.info("Motr addb log files on path %s: %s",
                                             log_path_addb_stobs, resp)
                            for ctr in range(1, len(act_files)):
                                line = act_files[ctr].split()
                                file_size = int(line[4][:-2])
                                if file_size > constants.LOG_PATH_FILE_SIZE_MB_MOTR[file_path]:
                                    assert_utils.assert_true(False, f"Motr addb max file size is: "
                                        f"{constants.LOG_PATH_FILE_SIZE_MB_MOTR[file_path]}MB "
                                        f"and actual file size: {file_size}MB for file:{line[-1]}")
                    else:
                        assert_utils.assert_true(False, f"No addb or trace directory found "
                                                        f"on path: {log_path_m0d}")

        self.LOGGER.info("Successfully validated Motr log file size for all pods")

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.log_rotation
    @pytest.mark.tags("TEST-31256")
    def test_31256(self):
        """
        Validate Motr rotating log files are as per frequency configured
        """
        self.LOGGER.info("Motr rotating log files are as per frequency configured")

        pod_list = self.node_obj.get_all_pods(pod_prefix=constants.POD_NAME_PREFIX)
        for pod in pod_list:
            self.LOGGER.info("Checking log path of %s pod", pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod)
            for file_path in constants.LOG_PATH_FILE_SIZE_MB_MOTR:
                log_path = file_path.format(machine_id)
                self.LOGGER.info("log path: %s", log_path)
                resp = sb.log_file_size_on_path(pod, log_path)
                lines = resp.splitlines()
                self.LOGGER.info("Motr log files on path %s: %s", log_path, resp)
                for count in range(1, len(lines)):
                    line = lines[count].split()
                    log_path_m0d = log_path + line[-1] + "/"
                    resp = sb.log_file_size_on_path(pod, log_path_m0d)
                    lines_m0d = resp.splitlines()
                    if "trace" in log_path_m0d:
                        if "No such file" in resp:
                            assert_utils.assert_true(False, f"Log path {log_path_m0d} "
                                                    f"does not exist on pod: {pod} resp: {resp}")
                        self.LOGGER.info("Motr trace log files on path %s: %s",
                                         log_path_m0d, resp)
                        if constants.MAX_NO_OF_ROTATED_LOG_FILES['Motr'] < (len(lines_m0d) - 1):
                            assert_utils.assert_true(False, f"Max rotating trace log files "
                                    f"are:{constants.MAX_NO_OF_ROTATED_LOG_FILES['Motr']} "
                                    f"and actual no of files are: {len(lines_m0d) - 1}")
                    elif "addb" in log_path_m0d:
                        for counter in range(1, len(lines_m0d)):
                            addb_stobs_dir = lines_m0d[counter].split()
                            log_path_addb_stobs = log_path_m0d + addb_stobs_dir[-1] + "/o"
                            resp = sb.log_file_size_on_path(pod, log_path_addb_stobs)
                            act_files = resp.splitlines()
                            if "No such file" in resp:
                                assert_utils.assert_true(False, f"Log path {log_path_addb_stobs}"
                                                    f"does not exist on pod: {pod} resp:{resp}")
                            self.LOGGER.info("Motr addb log files on path %s: %s",
                                             log_path_addb_stobs, resp)
                            if constants.MAX_NO_OF_ROTATED_LOG_FILES['Motr'] < (len(act_files)-1):
                                assert_utils.assert_true(False, f"Max rotating addb log files "
                                        f"are:{constants.MAX_NO_OF_ROTATED_LOG_FILES['Motr']} "
                                        f"and actual no of files are: {len(lines_m0d) - 1}")
                    else:
                        assert_utils.assert_true(False, f"No addb or trace directory found "
                                                        f"on path: {log_path_m0d}")

        self.LOGGER.info("Successfully validated Motr rotating log files are as per "
                         "frequency configured for all pods")

    # pylint: disable-msg=too-many-branches
    # pylint: disable=too-many-statements
    @pytest.mark.cluster_user_ops
    @pytest.mark.lc
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-35001")
    def test_35001(self):
        """
        Validate support bundle contains component logs
        """
        self.LOGGER.info("STARTED: Test to validate support bundle contains component logs")

        self.LOGGER.info("Step 1: Generate support bundle")
        dest_dir = "file://" + constants.R2_SUPPORT_BUNDLE_PATH

        for pod in constants.SB_POD_PREFIX_AND_COMPONENT_LIST:
            pod_list = self.node_obj.get_all_pods(pod_prefix=pod)
            machine_id = self.node_obj.get_machine_id_for_pod(pod_list[0])

            cmd_get_container_of_pod = comm.KUBECTL_GET_POD_CONTAINERS.format(pod_list[0])
            output = self.node_obj.execute_cmd(cmd=cmd_get_container_of_pod, read_lines=True)
            container_list = output[0].split()
            container_name = container_list[0]

            self.LOGGER.info("Generating support bundle for pod: %s", pod_list[0])
            sb_identifier = system_utils.random_string_generator(10)
            self.LOGGER.info("Support Bundle identifier of : %s", sb_identifier)

            resp = sb.generate_sb_lc(dest_dir, sb_identifier, pod_list[0],
                                     "TEST-35001", container_name)
            self.LOGGER.info("response of support bundle generation: %s", resp)
            sb_local_path = os.path.join(os.getcwd(), "support_bundle_copy")

            self.LOGGER.info("Step 2: Creating local directory")
            if os.path.exists(sb_local_path):
                self.LOGGER.info("Removing existing directory %s", sb_local_path)
                shutil.rmtree(sb_local_path)
            os.mkdir(sb_local_path)
            self.LOGGER.info("sb copy path: %s", sb_local_path)

            self.LOGGER.info("Step 3: Copy support bundle to local directory")
            copy_sb_from_path = constants.R2_SUPPORT_BUNDLE_PATH + sb_identifier
            sb_copy_path = "/root/support_bundle/"
            copy_sb_cmd = comm.K8S_CP_TO_LOCAL_CMD.format(pod_list[0], copy_sb_from_path,
                                        sb_copy_path, container_name)
            self.node_obj.execute_cmd(cmd=copy_sb_cmd, read_lines=True)

            sb_copy_full_path = sb_copy_path + sb_identifier + "_" + machine_id + ".tar.gz"
            sb_local_full_path = sb_local_path + "/" + sb_identifier +".tar.gz"
            self.node_obj.copy_file_to_local(sb_copy_full_path, sb_local_full_path)

            self.LOGGER.info("Step 4: Extract support bundle tar file")
            tar_cmd = comm.CMD_TAR.format(sb_local_full_path, sb_local_path)
            system_utils.run_local_cmd(cmd=tar_cmd)
            comp_in_sb = os.listdir(sb_local_path + "/" + sb_identifier)

            self.LOGGER.info("Step 5: Checking component log files in collected support bundle")
            comp_list = constants.SB_POD_PREFIX_AND_COMPONENT_LIST[pod]
            for comp in comp_list:
                if comp in comp_in_sb:
                    comp_dir_path = sb_local_path + "/" + sb_identifier + "/" + comp
                    comp_tar_files = os.listdir(comp_dir_path)
                    os.mkdir(comp_dir_path + "/" + comp)
                    tar_cmd = comm.CMD_TAR.format(comp_dir_path + "/" +
                                                  comp_tar_files[0], comp_dir_path + "/" + comp)
                    system_utils.run_local_cmd(cmd=tar_cmd)
                    comp_dir_path = comp_dir_path + "/" + comp

                    if comp == "hare":
                        hare_dir = os.listdir(comp_dir_path)
                        unzip_hare_dir = comp_dir_path + "/" + hare_dir[0]
                        resp = sb.file_with_prefix_exists_on_path(unzip_hare_dir +
                                                                  constants.SB_EXTRACTED_PATH +
                                                                  "hare/log/" + machine_id, "hare")
                        if resp:
                            self.LOGGER.info("hare logs are present in support Bundle")
                        else:
                            assert_utils.assert_true(False, "No hare log file "
                                                            "found in support bundle")
                    if comp == "motr":
                        motr_dir = os.listdir(comp_dir_path)
                        unzip_motr_dir = comp_dir_path + "/" + motr_dir[0]
                        resp = sb.file_with_prefix_exists_on_path(unzip_motr_dir, "m0reportbug")
                        if resp:
                            self.LOGGER.info("motr logs are present in support Bundle")
                        else:
                            assert_utils.assert_true(False, "No motr log file "
                                                            "found in support bundle")
                    if comp == "rgw":
                        resp = sb.file_with_prefix_exists_on_path(comp_dir_path, "rgw")
                        if resp:
                            self.LOGGER.info("rgw logs are present in support Bundle")
                        else:
                            assert_utils.assert_true(False, "No rgw log file found in "
                                                            "support bundle")
                    if comp == "utils":
                        resp = sb.file_with_prefix_exists_on_path(comp_dir_path + "/logs", "utils")
                        if resp:
                            self.LOGGER.info("utils logs are present in support Bundle")
                        else:
                            assert_utils.assert_true(False, "No utils log file "
                                                            "found in support bundle")
                    if comp == "csm":
                        resp = sb.file_with_prefix_exists_on_path(comp_dir_path, "csm")
                        if resp:
                            self.LOGGER.info("csm logs are present in support Bundle")
                        else:
                            assert_utils.assert_true(False, "No csm log file "
                                                            "found in support bundle")
                else:
                    self.LOGGER.info("assert: %s", comp)
                    assert_utils.assert_true(False, f"No {comp} dir in collected support bundle")

        self.LOGGER.info("ENDED: Test to validate support bundle contains component logs")
