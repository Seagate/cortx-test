# -*- coding: utf-8 -*-
# ~!/usr/bin/python
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

"""Support Bundle Test Module."""

import time
import os
import posixpath
from multiprocessing import Process, Manager

import logging
import pytest
from commons.exceptions import CTException
from commons.constants import const
from commons import commands as cmd
from commons.ct_fail_on import CTFailOn
from commons.utils.system_utils import run_remote_cmd
from commons.errorcodes import error_handler
from commons.utils.assert_utils import assert_false, assert_true
from commons.utils.config_utils import read_yaml
from commons.helpers.node_helper import Node
from config import CMN_CFG as CM_CFG
from libs.s3 import S3H_OBJ, S3_CFG
from commons.params import LOG_DIR
from commons.utils import support_bundle_utils as sb
from commons.utils import system_utils
from commons.utils import assert_utils

manager = Manager()


class TestSupportBundle:
    """Support Bundle Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup operations")
        cls.file_lst = []
        cls.pcs_start = True
        cls.host_ip = CM_CFG["nodes"][0]["host"]
        cls.uname = CM_CFG["nodes"][0]["username"]
        cls.passwd = CM_CFG["nodes"][0]["password"]
        cls.sys_bundle_dir = const.REMOTE_DEFAULT_DIR
        cls.tar_postfix = "tar.xz"
        cls.tmp_dir = "tmp"
        cls.extracted_m0trace_path = "s3_m0trace_files"
        cls.s3server_pre = "s3server"
        cls.m0postfix = "m0trace"
        cls.common_dir = "s3"
        cls.log.info("ENDED: Setup operations")
        cls.bundle_dir = os.path.join(LOG_DIR, "latest", "support_bundle")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.
        """
        self.node_obj = Node(hostname=self.host_ip, username=self.uname, password=self.passwd)
        self.node_obj.connect()
        self.host_obj = self.node_obj.host_obj
        self.node_obj.connect_pysftp()
        self.pysftp_obj = self.host_obj.open_sftp()
        self.bundle_prefix = "auto_bundle_{}"
        self.common_dir = "s3"
        if system_utils.path_exists(self.bundle_dir):
            self.log.info("Removing existing directory %s", self.bundle_dir)
            system_utils.remove_dirs(self.bundle_dir)
        system_utils.make_dirs(self.bundle_dir)

    def create_support_bundle(
            self,
            bundle_name,
            dest_dir,
            host_ip,
            resp_lst=None):
        """
        Function creates the support bundle collection tar file on the remote s3server.

        :param str bundle_name: Name of the bundle file to be created
        :param str dest_dir: Destination path where support bundle will be created
        :param None or List resp_lst: list containing response
        :param str host_ip: IP of the s3 remote server
        :return: (Boolean and Response)
        """
        success_msg = const.SUPPORT_BUNDLE_SUCCESS_MSG
        final_cmd = "{} {} {}".format(cmd.BUNDLE_CMD, bundle_name, dest_dir)
        self.log.info("Command to execute : %s", final_cmd)
        resp = run_remote_cmd(
            final_cmd, host_ip, self.uname, self.passwd)
        if resp[0]:
            if success_msg in str(resp[1]):
                if resp_lst:
                    resp_lst.append(True, resp[1])
                return True, resp[1]
        if resp_lst:
            resp_lst.append(False, resp[1])
        return False, resp[1]

    def get_s3_instaces_and_ism0exists(self, abs_path, check_file):
        """
        Function returns the s3server instances and m0traces files and check.

        weather m0trances are present in the remote s3server bundle support
        :param str abs_path: Absolute path of the remote server
        :param str check_file: Name of the file need to be checked
        :return: Boolean and dictionary containing the s3server instances
        and m0instances
        """
        var_mero_dict = dict()
        self.log.debug("Client connected")
        try:
            dir_lst = self.pysftp_obj.listdir(abs_path)
            for directory in [dir_el for dir_el in dir_lst if "s3server" in dir_el]:
                abs_dir_name = os.path.join(abs_path, directory)
                file_lst = self.pysftp_obj.listdir(abs_dir_name)
                var_mero_dict[abs_dir_name] = [
                    file for file in file_lst if check_file in file]
                m0_flag = [True for file in file_lst if check_file in file]
                if not any(m0_flag):
                    return False, var_mero_dict
            return True, var_mero_dict
        except Exception as error:
            self.log.error(error)
            return False, error

    def validate_time_stamp(self, org_file_path, ext_file_path):
        """
        Function compares the last modified time of the two files.

        :param str org_file_path: Absolute remote path of the server
        where actual logs are created by s3server instances
        :param str ext_file_path: Support bundle path of the file
        :return: Boolean
        """
        self.log.info(
            "Validating the time stamp of : %s with %s",
            org_file_path, ext_file_path)
        tmpstamp1 = self.pysftp_obj.stat(org_file_path)
        tmpstamp2 = self.pysftp_obj.stat(ext_file_path)
        if tmpstamp1.st_mtime == tmpstamp2.st_mtime:
            return True
        return False

    def validate_file_checksum(
            self,
            org_m0trace_lst,
            x_m0trace_lst):
        """
        Function validates and compares the md5sum checksum of list of m0traces.

        files with the actual s3server instances m0traces files
        :param list org_m0trace_lst: Actual m0traces of s3server instances files
        :param list x_m0trace_lst: Bundle support m0traces files
        :return: Boolean
        """
        md5cmd = "md5sum {}"
        for org_file in org_m0trace_lst:
            for ext_file in x_m0trace_lst:
                if org_file.split("/")[-1] == ext_file.split("/")[-1]:
                    if self.validate_time_stamp(org_file, ext_file):
                        md5cmd_1 = md5cmd.format(org_file)
                        md5cmd_2 = md5cmd.format(ext_file)
                        cheksum_res_1 = run_remote_cmd(
                            md5cmd_1, self.host_ip, self.uname, self.passwd)
                        cheksum_res_2 = run_remote_cmd(
                            md5cmd_2, self.host_ip, self.uname, self.passwd)
                        cheksum_res_1 = cheksum_res_1[0].split()[0].strip()
                        cheksum_res_2 = cheksum_res_2[0].split()[0].strip()
                        if cheksum_res_1 != cheksum_res_2:
                            self.log.info(
                                "Failed Checksum: %s:%s and %s:%s",
                                md5cmd_1,
                                cheksum_res_1,
                                md5cmd_2,
                                cheksum_res_2)
                            return False
        return True

    def compare_files(self, remotepath, ext_path_dict):
        """
        Function compares two remote files on the remote s3server.

        :param remotepath:
        :param dict ext_path_dict: dictionary contains bundled remote server
         path and list of m0traces files
        :return: (Boolean, m0traces_list)
        """
        x_m0trace_lst = list()
        m0post_fix = self.m0postfix
        for filename in self.pysftp_obj.listdir(remotepath):
            rpath = posixpath.join(remotepath, filename)
            if self.s3server_pre in filename:
                org_m0trace_lst = self.pysftp_obj.listdir(rpath)
                org_m0trace_lst = [
                    os.path.join(rpath, file)
                    for file in org_m0trace_lst if m0post_fix in file]
                for dirname, x_m0trace_lst in ext_path_dict.items():
                    if dirname.split("/")[-1] == filename:
                        x_m0trace_lst = [
                            os.path.join(
                                dirname,
                                file) for file in x_m0trace_lst]
                        resp = self.validate_file_checksum(
                            org_m0trace_lst, x_m0trace_lst)
                        if not resp:
                            return False, org_m0trace_lst
        return True, x_m0trace_lst

    def extract_tar_file(self, tar_file_path, tar_dest_dir, **kwargs):
        """
        Function to extract tar file in remote node.

        :param tar_file_path: Path to the tar file
        :param tar_dest_dir: Destination path to for extracting tar
        :keyword host: Host name or ip
        :return:
        """
        host = kwargs.get("host", self.host_ip)
        tar_cmd = "tar -xvf {} -C {}".format(tar_file_path, tar_dest_dir)
        self.log.debug("Command to be executed %s on %s", tar_cmd, host)
        return run_remote_cmd(
            tar_cmd, host, self.uname, self.passwd)

    def pcs_start_stop_cluster(self, start_stop_cmd, status_cmd):
        """
        Function start and stops the cluster using the pcs command.

        :param string start_stop_cmd: start and stop command option
        :param string status_cmd: status command option
        :return: (Boolean and response)
        """
        cluster_msg = const.CLUSTER_STATUS_MSG
        self.host_obj.exec_command(start_stop_cmd)
        time.sleep(30)
        _, stdout, stderr = self.host_obj.exec_command(status_cmd)
        result = stdout.readlines() if stdout.readlines() else stderr.readlines()
        for value in result:
            if cluster_msg in value:
                return False, result
        return True, result

    def hctl_stop_cmd(self):
        """
        Function stops the cluster using hctl command.

        :return:(Boolean and response)
        """
        cluster_msg = const.CLUSTER_NOT_RUNNING_MSG
        stop_cmd = cmd.PCS_CLUSTER_STOP.format("--all")
        status_cmd = cmd.MOTR_STATUS_CMD
        resp = run_remote_cmd(
            stop_cmd, self.host_ip, self.uname, self.passwd)
        self.log.info("hctl Stop resp : %s", resp)
        time.sleep(30)
        _, stdout, stderr = self.host_obj.exec_command(status_cmd)
        result = stdout.readlines() if stdout.readlines() else stderr.readlines()
        if cluster_msg in result[0].strip():
            return True, result
        return False, result

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform all cleanup operations.
        """
        self.log.info("STARTED: Teardown operations")
        if not self.pcs_start:
            self.log.info("Step : Starting cluster")
            S3H_OBJ.enable_disable_s3server_instances(resource_disable=False)
            resp = self.pcs_start_stop_cluster(
                cmd.PCS_CLUSTER_START.format("--all"),
                cmd.PCS_CLUSTER_STATUS)
            self.pcs_start = resp[0]
        self.log.info("Step: Deleting all the remote files")
        if self.file_lst:
            for path in self.file_lst:
                self.log.info("Deleting %s", path)
                S3H_OBJ.delete_remote_dir(self.pysftp_obj, path)
        run_remote_cmd(
            "rm -rf /tmp/s3_support_bundle*",
            self.host_ip,
            self.uname,
            self.passwd)
        self.node_obj.disconnect()
        self.log.info("Step : Deleted all the files")
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8024 ")
    @CTFailOn(error_handler)
    def test_dest_has_less_space_5274(self):
        """Support bundle collection when destination has less space than required."""
        self.log.info(
            "STARTED: Support bundle collection when destination has less space than required")
        common_dir = self.common_dir
        dir_path = os.path.join(common_dir, "/boot")
        remote_path = self.node_obj.make_dir(dir_path)
        assert_true(remote_path, f"Path not exists: {dir_path}")
        self.file_lst.append(os.path.join(dir_path))
        for i in range(10):
            bundle_name = "{}_{}".format(self.bundle_prefix.format("5274"), str(i))
            self.log.info(
                "Step 1: Creating support bundle %s.tar.gz", bundle_name)
            resp = self.create_support_bundle(
                bundle_name, dir_path, self.host_ip)
            if not resp[0]:
                self.log.info(
                    "Step 1: Failed to create support bundle %s.tar.gz message : %s",
                    bundle_name, resp)
                break
            self.log.info(
                "Step 1: Successfully created support bundle message : %s, %s",
                bundle_name, resp)
            assert_false(resp[0], resp[1])
        self.log.info(
            "ENDED: Support bundle collection when destination has less space than required")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8025")
    @CTFailOn(error_handler)
    def test_collect_triggered_simultaneously_5280(self):
        """Test multiple Support bundle collection triggered simultaneously."""
        self.log.info(
            "STARTED: Test multiple Support bundle collection triggered simultaneously")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        resp_lst = manager.list()
        process_lst = []
        self.log.info(
            "Step 1: Creating support bundle parallely %s.tar.gz",
            self.bundle_prefix.format("5280"))
        for i in range(3):
            bundle_name = "{}_{}".format(self.bundle_prefix.format("5280"), str(i))
            process = Process(
                target=self.create_support_bundle,
                args=(bundle_name,
                      remote_path,
                      self.host_ip,
                      resp_lst))
            process_lst.append(process)
        for process in process_lst:
            process.start()
        for process in process_lst:
            process.join()
        true_flag = all([temp[0] for temp in resp_lst])
        assert_true(true_flag, resp_lst)
        self.log.info(
            "Step 1: validated all support bundle created parallely %s.tar.gz",
            self.bundle_prefix.format("5280"))
        self.log.info(
            "ENDED: Test multiple Support bundle collection triggered simultaneously")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8026")
    @CTFailOn(error_handler)
    def test_core_m0traces_all_instances_5282(self):
        """Validate Support bundle contains cores and m0traces for all instances."""
        self.log.info(
            "STARTED: Validate Support bundle contains cores and m0traces for all instances")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        for i in range(1):
            bundle_name = "{}_{}".format(self.bundle_prefix.format("5282"), str(i))
            bundle_tar_name = "s3_{}.{}".format(
                bundle_name, self.tar_postfix)
            self.log.info(
                "Step 1: Creating support bundle %s", bundle_tar_name)
            resp = self.create_support_bundle(
                bundle_name, remote_path, self.host_ip)
            assert_true(resp[0], resp[1])
            self.log.info(
                "Step 1: Successfully created support bundle: %s, %s",
                bundle_name, resp)
            tar_file_path = os.path.join(
                remote_path, tar_dest_dir, bundle_tar_name)
            extracted_dir = os.path.join(tar_dest_dir, bundle_name)
            self.node_obj.make_dir(extracted_dir)
            self.log.info(
                "Step 2 and 3: Extracting the tar file and "
                "validating the tar extraction")
            self.extract_tar_file(tar_file_path, tar_dest_dir)
            dir_list = self.pysftp_obj.listdir(
                os.path.join(extracted_dir, self.tmp_dir))
            abs_m0trace_path = os.path.join(
                extracted_dir,
                self.tmp_dir,
                dir_list[0],
                self.extracted_m0trace_path)
            self.log.info(abs_m0trace_path)
            file_prefix = self.m0postfix
            resp = self.get_s3_instaces_and_ism0exists(
                abs_m0trace_path, file_prefix)
            assert_true(resp[0], resp[1])
            var_path = self.sys_bundle_dir
            res = self.compare_files(var_path, resp[1])
            assert_true(res[0], res[1])
            self.log.info(
                "Step 2 and 3: Extracted the tar file and validated tar file")
        self.log.info(
            "ENDED: Validate Support bundle contains cores and m0traces for all instances")

    # As this test cases requires destructive operations to be performed on the node
    # causing cluster failure so disabling this test-case
    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8691 ")
    def test_collection_with_network_fluctuation_5272(self):
        """Support bundle collection with network fluctuation."""
        self.log.info(
            "STARTED: Test Support bundle collection with network fluctuation")
        bundle_name = self.bundle_prefix.format("5272")
        common_dir = self.common_dir
        network_service = S3_CFG["s3_services"]["network"]
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        resp_lst = manager.list()
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 1: Creating support bundle %s.tar.gz", bundle_name)
        process = Process(target=self.create_support_bundle, args=(
            bundle_name, remote_path, self.host_ip, resp_lst))
        process.start()
        self.log.info(
            "Step 2: Restart network service when collection is progress")
        S3H_OBJ.restart_s3server_service(network_service)
        self.log.info("Waiting till cluster is up")
        time.sleep(300)
        resp = S3H_OBJ.get_s3server_service_status(network_service)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Restarted %s service successfully", network_service)
        true_flag = all([temp[0] for temp in resp_lst])
        assert_true(true_flag, resp_lst)
        resp = self.node_obj.path_exists(tar_file_path)
        assert_false(resp, f"Support bundle present at {tar_file_path}")
        self.log.info("Step 1: Support bundle did not created")
        self.log.info(
            "ENDED: Test Support bundle collection with network fluctuation")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8692 ")
    @CTFailOn(error_handler)
    def test_collecion_primary_secondary_nodes_5273(self):
        """Test Support bundle collection from Primary and Secondary nodes of cluster."""
        self.log.info(
            "STARTED: Test Support bundle collection from Primary and Secondary nodes of cluster")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        node_list = [self.host_ip, CM_CFG["nodes"][1]["host"]]
        self.log.info(
            "Step 1 Creating support bundle on primary and secondary nodes")
        for node_id, hostname in enumerate(node_list):
            host = CM_CFG["nodes"][node_id]["host"]
            uname = CM_CFG["nodes"][node_id]["username"]
            passwd = CM_CFG["nodes"][node_id]["password"]
            node_obj = Node(hostname=host, username=uname, password=passwd)
            bundle_name = "{}_{}".format(self.bundle_prefix.format("5273"), str(hostname))
            bundle_tar_name = "s3_{}.{}".format(
                bundle_name, self.tar_postfix)
            tar_file_path = os.path.join(
                remote_path, tar_dest_dir, bundle_tar_name)
            self.log.info(
                "Step : Creating support bundle %s on node %s",
                bundle_tar_name, hostname)
            resp = self.create_support_bundle(
                bundle_name, remote_path, hostname)
            assert_true(resp[0], resp[1])
            resp = S3H_OBJ.is_s3_server_path_exists(tar_file_path, host=hostname)
            assert_true(resp[0], resp[1])
            self.log.info(
                "Step : Created support bundle %s on node %s",
                bundle_tar_name, hostname)
            self.node_obj.connect(hostname, username=self.uname, password=self.passwd)
            sftp = self.host_obj.open_sftp()
            S3H_OBJ.delete_remote_dir(sftp, remote_path)
            sftp.close()
        self.log.info(
            "Step 1:Support Bundle was created on primary and secondary nodes")
        self.log.info(
            "ENDED: Test Support bundle collection from Primary and Secondary nodes of cluster")

    # As this test cases requires destructive operations on the node
    # causing cluster failure so disabling this test-case
    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8694")
    @CTFailOn(error_handler)
    def test_collet_authservice_down_5276(self):
        """Test Support bundle collection when authserver service is down."""
        self.log.info(
            "STARTED: Test Support bundle collection when authserver service is down")
        bundle_name = self.bundle_prefix.format("5276")
        common_dir = self.common_dir
        service_name = S3_CFG["s3_services"]["authserver"]
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        self.log.info("Step 1: Stopping the service : %s", service_name)
        resp = S3H_OBJ.stop_s3server_service(service_name, self.host_ip)
        assert_false(resp[0], resp[1])
        self.log.info(
            "Step 1: Service %s was stopped successfully",
            service_name)
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 2: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 2: Support bundle created successfully")
        self.log.info("Step 3: Starting the service : %s", service_name)
        resp = S3H_OBJ.start_s3server_service(service_name, self.host_ip)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Started the service : %s", service_name)
        self.log.info(
            "ENDED: Test Support bundle collection when authserver service is down")

    # As this test cases requires destructive operations on the node
    # causing cluster failure so disabling this test-case
    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8695")
    @CTFailOn(error_handler)
    def test_collection_haproxy_down_5277(self):
        """Test Support bundle collection when haproxy service is down."""
        self.log.info(
            "STARTED: Test Support bundle collection when haproxy service is down")
        bundle_name = self.bundle_prefix.format("5277")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        service_name = S3_CFG["s3_services"]["haproxy"]
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        self.log.info("Step 1: Stopping the service : %s", service_name)
        resp = S3H_OBJ.stop_s3server_service(service_name, self.host_ip)
        assert_false(resp[0], resp[1])
        self.log.info(
            "Step 1: Service %s was stopped successfully",
            service_name)
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 2: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 2: Support bundle created successfully")
        self.log.info("Step 3: Starting the service : %s", service_name)
        resp = S3H_OBJ.start_s3server_service(service_name, self.host_ip)
        assert_true(resp[0], resp[1])
        self.log.info("Step 3: Started the service : %s", service_name)
        self.log.info(
            "ENDED: Test Support bundle collection when haproxy service is down")

    # As this test cases requires destructive operations on the node
    # causing cluster failure so disabling this test-case
    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8696")
    @CTFailOn(error_handler)
    def test_collection_cluster_down_5278(self):
        """Test Support bundle collection when Cluster is shut down."""
        self.log.info(
            "STARTED: Test Support bundle collection when Cluster is shut down")
        bundle_name = self.bundle_prefix.format("5278")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        self.log.info("Step 1: Stopping the cluster")
        self.pcs_start = False
        resp = self.hctl_stop_cmd()
        assert_true(resp[0], resp[1])
        self.log.info("Step 1: Cluster is stopped")
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 2: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info(
            "ENDED: Test Support bundle collection when Cluster is shut down")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8697")
    @CTFailOn(error_handler)
    def test_collection_one_after_other_5279(self):
        """Test multiple Support bundle collections one after the other."""
        self.log.info(
            "STARTED: Test multiple Support bundle collections one after the other")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        self.log.info(
            "Step 1: Creating multiple support bundle")
        for i in range(3):
            bundle_name = "{}_{}".format(self.bundle_prefix.format("5279"), str(i))
            bundle_tar_name = "s3_{}.{}".format(
                bundle_name, self.tar_postfix)
            tar_file_path = os.path.join(
                remote_path, tar_dest_dir, bundle_tar_name)
            self.log.info(
                "Step : Creating support bundle %s.tar.gz", bundle_name)
            resp = self.create_support_bundle(
                bundle_name, remote_path, self.host_ip)
            assert_true(resp[0], resp[1])
            resp = self.node_obj.path_exists(tar_file_path)
            assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
            self.log.info(
                "Step : Created support bundle %s.tar.gz", bundle_name)
            self.log.info(
                "Step 1: Successfully created support bundle message : %s, %s",
                bundle_name, resp)
        self.log.info(
            "ENDED: Test multiple Support bundle collections one after the other")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8698 ")
    @CTFailOn(error_handler)
    def test_s3server_logs_all_instances_5281(self):
        """Validate Support bundle contains s3server logs for all instances."""
        self.log.info(
            "STARTED: Validate Support bundle contains s3server logs for all instances")
        bundle_name = self.bundle_prefix.format("5281")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 1: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 1: Support bundle tar created successfully")
        self.log.info(
            "Step 2: Validating the s3server logs in the support bundle tar")
        self.extract_tar_file(tar_file_path, tar_dest_dir)
        extracted_file_path = "{}{}".format(
            tar_dest_dir, const.S3_LOG_PATH)
        self.extract_tar_file(tar_file_path, tar_dest_dir)
        resp = self.get_s3_instaces_and_ism0exists(
            extracted_file_path, self.s3server_pre)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Validated the s3server logs of the support bundle tar")
        self.log.info(
            "ENDED: Validate Support bundle contains s3server logs for all instances")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8699")
    @CTFailOn(error_handler)
    def test_authserver_logs_5283(self):
        """Validate Support bundle contains authserver logs."""
        self.log.info(
            "STARTED: Validate Support bundle contains authserver logs")
        bundle_name = self.bundle_prefix.format("5283")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 1: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 1: Support bundle tar created successfully")
        self.log.info("Step 2: Validating the authserver logs in the tar")
        self.extract_tar_file(tar_file_path, tar_dest_dir)
        auth_server_path = "{}{}".format(
            tar_dest_dir, const.AUTHSERVER_LOG_PATH)
        resp = self.node_obj.get_file_size(auth_server_path)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Validated the authserver logs of the tar")
        self.log.info(
            "ENDED: Validate Support bundle contains authserver logs")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8700")
    @CTFailOn(error_handler)
    def test_haproxy_logs_5284(self):
        """Validate Support bundle contains haproxy logs."""
        self.log.info(
            "STARTED: Validate Support bundle contains haproxy logs")
        bundle_name = self.bundle_prefix.format("5284")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 1: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 1: Support bundle tar created successfully")
        self.log.info("Step 2: Validating the haproxy logs in the tar")
        self.extract_tar_file(tar_file_path, tar_dest_dir)
        auth_server_path = "{}{}".format(
            tar_dest_dir, const.HAPROXY_LOG_PATH)
        resp = self.node_obj.get_file_size(auth_server_path)
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Validated the haproxy logs of the tar")
        self.log.info(
            "ENDED: Validate Support bundle contains haproxy logs")

    # As this test cases requires destructive operations on the node
    # causing cluster failure so disabling this test-case
    @pytest.mark.skip
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8693")
    @CTFailOn(error_handler)
    def test_collection_s3server_down_5275(self):
        """Test Support bundle collection when s3server services are down."""
        self.log.info(
            "STARTED: Test Support bundle collection when s3server services are down")
        bundle_name = self.bundle_prefix.format("5275")
        common_dir = self.common_dir
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        self.log.info("Step 1: Stopping the s3server services")
        self.pcs_start = False
        resp = S3H_OBJ.enable_disable_s3server_instances(
            resource_disable=True)
        assert_true(resp[0], resp[1])
        resp = S3H_OBJ.check_s3services_online()
        assert_false(resp[0], resp[1])
        self.log.info("Step 1: s3server services was stopped successfully")
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 2: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 2: Support bundle created successfully")
        resp = S3H_OBJ.enable_disable_s3server_instances(
            resource_disable=False)
        assert_true(resp[0], resp[1])
        self.pcs_start = True
        self.log.info(
            "ENDED: Test Support bundle collection when s3server services are down")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8701")
    @CTFailOn(error_handler)
    def test_collection_script_5270(self):
        """Test Support bundle collection through command/script."""
        self.log.info(
            "STARTED: Test Support bundle collection through command/script")
        bundle_name = self.bundle_prefix.format("5270")
        common_dir = self.common_dir
        dir_path = os.path.join(common_dir, self.sys_bundle_dir)
        remote_path = self.node_obj.make_dir(dir_path)
        assert_true(remote_path, dir_path)
        self.file_lst.append(os.path.join(dir_path))
        tar_dest_dir = os.path.join(dir_path, common_dir)
        bundle_tar_name = "s3_{}.{}".format(
            bundle_name, self.tar_postfix)
        tar_file_path = os.path.join(tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 1: Creating support bundle %s.tar.gz", bundle_name)
        resp = self.create_support_bundle(
            bundle_name, dir_path, self.host_ip)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created support bundle %s.tar.gz", bundle_name)
        self.log.info("Step 2: Verifying that support bundle is created")
        resp = self.node_obj.path_exists(tar_file_path)
        assert_true(resp, f"Support bundle does not exist at {tar_file_path}")
        self.log.info("Step 2: Verified that support bundle is created")
        self.log.info(
            "ENDED: Test Support bundle collection through command/script")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8689")
    @CTFailOn(error_handler)
    def test_system_configs_5285(self):
        """Validate Support bundle contains system related configs."""
        self.log.info(
            "STARTED: Validate Support bundle contains system related configs")
        bundle_name = self.bundle_prefix.format("5285")
        common_dir = self.common_dir
        ex_cfg_files = []
        dir_path = os.path.join(common_dir, self.sys_bundle_dir)
        remote_path = self.node_obj.make_dir(dir_path)
        assert_true(remote_path, f"Failed to create directory: {dir_path}")
        self.file_lst.append(os.path.join(dir_path))
        tar_dest_dir = os.path.join(dir_path, self.common_dir)
        bundle_name = "{0}_{1}".format(bundle_name, str(1))
        bundle_tar_name = "s3_{0}.{1}".format(
            bundle_name, self.tar_postfix)
        self.log.info(
            "Step 1: Creating support bundle %s", bundle_tar_name)
        resp = self.create_support_bundle(
            bundle_name, dir_path, self.host_ip)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created support bundle successfully: %s %s",
            bundle_name, resp)
        tar_file_path = os.path.join(
            dir_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 2: Extracting the support bundle %s", bundle_tar_name)
        self.extract_tar_file(tar_file_path, tar_dest_dir)
        self.log.info(
            "Step 2: Extracted the support bundle %s", bundle_tar_name)
        self.log.info(
            "Step 3: Checking config files are present under %s after "
            "extracting a support bundle", tar_dest_dir)
        cfg_5285 = const.CFG_FILES
        for file in cfg_5285:
            file_path = f"{tar_dest_dir}{file}"
            resp = self.node_obj.path_exists(file_path)
            assert_true(resp, f"Support bundle does not exist at {file_path}")
            ex_cfg_files.append(file_path)
        self.log.info(
            "Step 3: Checked for config files are present under %s after "
            "extracting a support bundle", tar_dest_dir)
        self.log.info(
            "Step 4: Verifying contents of extracted config files with system config files")
        resp = self.validate_file_checksum(cfg_5285, ex_cfg_files)
        assert_true(resp, f"validate file checksum failed.")
        self.log.info(
            "Step 4: Verified that contents of extracted config files are "
            "same as system config files")
        self.log.info(
            "ENDED: Validate Support bundle contains system related configs")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_support_bundle
    @pytest.mark.tags("TEST-8690")
    @CTFailOn(error_handler)
    def test_collect_system_info_stats_5286(self):
        """Validate Support bundle collects system information and stats."""
        self.log.info(
            "STARTED: Validate Support bundle collects system information and stats")
        bundle_name = self.bundle_prefix.format("5286")
        common_dir = self.common_dir
        stat_files = []
        remote_path = os.path.join(common_dir, self.sys_bundle_dir)
        resp = self.node_obj.make_dir(remote_path)
        assert_true(resp, remote_path)
        self.file_lst.append(os.path.join(remote_path))
        tar_dest_dir = os.path.join(remote_path, common_dir)
        bundle_name = "{0}_{1}".format(bundle_name, str(1))
        bundle_tar_name = "s3_{0}.{1}".format(
            bundle_name, self.tar_postfix)
        self.log.info(
            "Step 1: Creating support bundle %s", bundle_tar_name)
        resp = self.create_support_bundle(
            bundle_name, remote_path, self.host_ip)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created support bundle successfully: %s, %s",
            bundle_name, resp)
        tar_file_path = os.path.join(
            remote_path, tar_dest_dir, bundle_tar_name)
        self.log.info(
            "Step 2: Extracting the support bundle %s", bundle_tar_name)
        self.extract_tar_file(tar_file_path, tar_dest_dir)
        self.log.info(
            "Step 2: Extracted the support bundle %s", bundle_tar_name)
        self.log.info(
            "Step 3: Checking if system level stat files are collected")
        tmp_stat_files_dir = self.tmp_dir
        stat_files_dir = self.pysftp_obj.listdir(os.path.join(
            tar_dest_dir, tmp_stat_files_dir))
        bundle_stat_dir = [
            dir_el for dir_el in stat_files_dir if "s3_support_bundle_" in dir_el][0]
        stat_dir_path = os.path.join(
            tar_dest_dir,
            tmp_stat_files_dir,
            bundle_stat_dir)
        for file in S3_CFG["stat_files"]:
            stat_file_path = f"{stat_dir_path}/{file}"
            resp = self.node_obj.path_exists(stat_file_path)
            assert_true(resp, f"Support bundle does not exist at {stat_file_path}")
            stat_files.append(stat_file_path)
        self.log.info(
            "Step 3: Checked that system level stat files are collected")
        self.log.info(
            "Step 4 : Verifying that system level stat files are not empty")
        for file in stat_files:
            resp = self.node_obj.get_file_size(file)
            assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4 : Verified that system level stat files are not empty")
        self.log.info(
            "ENDED: Validate Support bundle collects system information and stats")

    @pytest.mark.cluster_user_ops
    @pytest.mark.support_bundle
    @pytest.mark.tags("TEST-31677")
    def test_31677_support_bundle_status(self):
        """
        Validate status of support bundle collection for each of the components/nodes
        """
        self.log.info("Step 1: Generating support bundle through cli")
        resp = sb.create_support_bundle_single_cmd(
            self.bundle_dir, bundle_name="test_31677", comp_list="s3server")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Generated support bundle through cli")
        self.log.info("Step 2: Validated status of Support bundle")
