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
import multiprocessing
import os
import time
from threading import Thread

import pytest
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from config import CMN_CFG, PROV_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_upgrade import ProvUpgradeK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestK8CortxUpgrade:
    """This class contains test cases for K8s CORTX Software Upgrade."""

    @classmethod
    def setup_class(cls):
        """Setup class."""
        LOGGER.info("STARTED: Setup Module operations")
        cls.cortx_control_image = os.getenv("CORTX_CONTROL_IMAGE", None)
        cls.cortx_data_image = os.getenv("CORTX_DATA_IMAGE", None)
        cls.cortx_server_image = os.getenv("CORTX_SERVER_IMAGE", None)
        cls.upgrade_image = cls.cortx_control_image
        cls.prov_conf = PROV_CFG["k8s_cortx_deploy"]
        cls.upgrade_obj = ProvUpgradeK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.collect_sb = True
        cls.upgrade_cleanup = False
        for node in range(cls.num_nodes):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        resp = cls.upgrade_obj.prov_obj.check_s3_status(cls.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        cls.upgrade_obj.retain_solution_file(
            cls.master_node_list[0], cortx_control_img=cls.cortx_control_image,
            cortx_data_img=cls.cortx_data_image, cortx_server_img=cls.cortx_server_image)
        LOGGER.info("Get installed version.")
        installed_version = cls.upgrade_obj.prov_obj.get_installed_version(
            cls.master_node_list[0])
        resp = cls.upgrade_obj.prov_obj.generate_and_compare_both_version(
            cls.upgrade_image, installed_version)
        assert_utils.assert_true(resp[0])
        # Pull upgrade Images on all worker nodes
        pull_image_thread_list = []
        for each in cls.worker_node_list:
            worker_thread = Thread(target=cls.upgrade_obj.prov_obj.pull_cortx_image,
                                   args=(each,))
            worker_thread.start()
            pull_image_thread_list.append(worker_thread)
        for each in pull_image_thread_list:
            each.join()
        LOGGER.info("Done: Setup operations finished.")

    def teardown_class(self):
        """Teardown method."""
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(
                local_dir_path=path, scripts_path=self.prov_conf['k8s_dir'])
        if self.upgrade_cleanup:
            LOGGER.debug("resuming incomplete upgrade")
            resp = self.upgrade_obj.upgrade_software(
                self.master_node_list[0], self.prov_conf['k8s_dir'], exc=False, flag=
                self.prov_conf["upgrade_resume"])
            assert_utils.assert_true(resp[0], resp[1])
            pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
            assert_utils.assert_true(pod_status)

    def rolling_upgrade(self, exc: bool = True, output=None, flag=None):
        """Function calls upgrade and put return value in queue object.
         param: exc: this is to catch the exception True/False
         param: output: this is to store the response
         param: flag: Its for different options support in upgrade script
        """
        resp = self.upgrade_obj.upgrade_software(
            self.master_node_list[0], self.prov_conf['k8s_dir'], exc=exc, flag=flag)
        output.put(resp)

    def get_status(self):
        """This method is used to fetch the status of the upgrade Process """
        status_resp = self.upgrade_obj.upgrade_software(
            self.master_node_list[0], self.prov_conf['k8s_dir'], exc=False, flag=
            self.prov_conf["upgrade_status"])
        return status_resp

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-33660")
    def test_33660(self):
        """Verify CORTX Software upgrade."""
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        resp = HAK8s.get_config_value(self.master_node_list[0])
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
        resp = self.upgrade_obj.prov_obj.check_s3_status(self.master_node_list[0], pod_prefix=
        cons.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Start upgrade.")
        resp = self.upgrade_obj.service_upgrade_software(self.master_node_list[0],
                                                         self.upgrade_image)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Check if installed version is equals to installing version.")
        resp = HAK8s.get_config_value(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        new_installed_version = resp[1]['cortx']['common']['release']['version'].split("-")[1]
        LOGGER.info("New CORTX image version: %s", new_installed_version)
        assert_utils.assert_equals(new_installed_version, upgrade_version,
                                   "new_installed version is equal to upgrade_version.")
        LOGGER.info("Step 7 : Check PODs are up and running.")
        resp = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(resp)
        LOGGER.info("All PODs are up and running.")
        LOGGER.info("Step 8 : Check Cluster health and services.")
        time.sleep(PROV_CFG["deploy_ff"]["per_step_delay"])
        resp = self.upgrade_obj.prov_obj.check_s3_status(self.master_node_list[0], pod_prefix=
                                                            cons.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0], resp[1])
        pod_name = self.master_node_list[0].get_pod_name(pod_prefix=cons.POD_NAME_PREFIX)
        assert_utils.assert_true(pod_name[0], pod_name[1])
        resp = self.upgrade_obj.prov_obj.get_hctl_status(self.master_node_list[0], pod_name[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and all services are started.")
        self.collect_sb = False
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-33669")
    def test_33669(self):
        """Verify Hotfix upgrade for same or lower version."""
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        resp = HAK8s.get_config_value(self.master_node_list[0])
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
        resp = self.upgrade_obj.service_upgrade_software(self.master_node_list[0],
                                                         self.upgrade_image)
        assert_utils.assert_false(resp[0], resp[1])

        if int(upgrade_version) <= int(installed_version):
            assert_utils.assert_true(resp[0],
                                     "Installed version is same or higher than installing version")
        self.collect_sb = False
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-41953")
    def test_41953(self):
        """Verify resume of in progress rolling upgrade."""
        process_list = []
        LOGGER.info("Test Started.")
        que = multiprocessing.Queue()
        start_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            True, que, self.prov_conf["upgrade_start"]))
        resume_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            False, que, self.prov_conf["upgrade_resume"]))
        # start the upgrade thread
        LOGGER.info("Step 2: Start the upgrade.")
        start_upgrade_proc.start()
        process_list.append(start_upgrade_proc)
        time.sleep(self.prov_conf["sleep_time"])  # Wait to start upgrade
        # verify the status of upgrade
        LOGGER.info("Step 3: Verify the upgrade status.")
        status_resp = self.get_status()
        LOGGER.info("Upgrade status is %s", status_resp)
        # resume the already in-progress upgrade
        LOGGER.info("Step 4: Resume the upgrade.")
        resume_upgrade_proc.start()
        process_list.append(resume_upgrade_proc)
        resp = que.get(1)
        LOGGER.debug("upg resp is %s", resp)
        assert_utils.assert_in(cons.UPGRADE_IN_PROGRESS_MSG, resp[1])
        for process in process_list:
            process.join()
            process.close()
        LOGGER.info("Step 5: Verify the PODs and Services status.")
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        resp = self.upgrade_obj.prov_obj.check_service_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        installed_version = self.upgrade_obj.prov_obj.get_installed_version(
            self.master_node_list[0])
        LOGGER.info("Upgraded to version %s", installed_version)
        self.collect_sb = False
        LOGGER.info("--------- Test Completed ---------")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-42176")
    def test_42176(self):
        """Verify resume  functionality of upgrade,when abruptly stopped the upgrade process."""
        process_list = []
        LOGGER.info("Test Started.")
        que = multiprocessing.Queue()
        start_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            True, que, self.prov_conf["upgrade_start"]))
        suspend_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            True, que, self.prov_conf["upgrade_suspend"]))
        # start upgrade thread.
        LOGGER.info("Step 2: Start the upgrade.")
        start_upgrade_proc.start()
        process_list.append(start_upgrade_proc)
        time.sleep(self.prov_conf["sleep_time"])  # Wait to start upgrade_thread thread
        # Verify the upgrade status.
        LOGGER.info("Step 3: Verify the upgrade status.")
        status_resp = self.get_status()
        LOGGER.info("Status is %s", status_resp)
        # suspend the upgrade.
        LOGGER.info("Step 4: Suspend the upgrade.")
        suspend_upgrade_proc.start()
        process_list.append(suspend_upgrade_proc)
        # get the suspend response.
        resp = que.get(1)
        LOGGER.debug("suspend %s", resp)
        assert_utils.assert_in(cons.UPGRADE_SUSPEND_MSG, resp[1])
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        for process in process_list:
            process.terminate()
            process.join()
            process.close()
        # resume the suspended upgrade.
        LOGGER.info("Step 5: Resume the Upgrade...")
        resp = self.upgrade_obj.upgrade_software(
            self.master_node_list[0], self.prov_conf["k8s_dir"], flag=
            self.prov_conf["upgrade_resume"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Verify the PODs and Services status.")
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        resp = self.upgrade_obj.prov_obj.check_service_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        installed_version = self.upgrade_obj.prov_obj.get_installed_version(
            self.master_node_list[0])
        LOGGER.info("Upgraded to version %s", installed_version)
        self.collect_sb = False
        LOGGER.info("--------- Test Completed ---------")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-42179")
    def test_42179(self):
        """Verify suspend/resume  functionality of upgrade"""
        process_list = []
        count = 1
        LOGGER.info("Test Started.")
        que = multiprocessing.Queue()
        start_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            True, que, self.prov_conf["upgrade_start"]))
        LOGGER.info("Step 2: Start the upgrade.")
        # start the Upgrade
        start_upgrade_proc.start()
        process_list.append(start_upgrade_proc)
        time.sleep(self.prov_conf["sleep_time"])  # Wait to start upgrade_thread thread
        while count <= len(self.worker_node_list):
            resume_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
                False, que, self.prov_conf["upgrade_resume"]))
            LOGGER.debug("Iteration is %s", count)
            LOGGER.info("Step 3: Suspend the upgrade.")
            suspend_resp = self.upgrade_obj.upgrade_software(
                self.master_node_list[0], self.prov_conf['k8s_dir'], exc=False, flag=
                self.prov_conf["upgrade_suspend"])
            assert_utils.assert_true(suspend_resp[0])
            # verify the upgrade status
            status_resp = self.get_status()
            LOGGER.info("Status is %s", status_resp[1])
            time.sleep(self.prov_conf["sleep_time"])
            # Resume the upgrade
            LOGGER.info("Step 4: Resume the upgrade.")
            resume_upgrade_proc.start()
            process_list.append(resume_upgrade_proc)
            time.sleep(self.prov_conf["sleep_time"])
            # verify the upgrade status
            status_resp = self.get_status()
            LOGGER.info("Status is %s", status_resp[1])
            for process in process_list:
                process.terminate()
                process.join()
                process.close()
            process_list.clear()
            count = count+1
        LOGGER.info("Step 5: Verify the PODs and Services status.")
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        resp = self.upgrade_obj.prov_obj.check_service_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        self.collect_sb = False
        LOGGER.info("--------- Test Completed ---------")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-41951")
    def test_41951(self):
        """Verify suspend already suspended upgrade."""
        LOGGER.info("Test Started.")
        que = multiprocessing.Queue()
        start_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            True, que, self.prov_conf["upgrade_start"]))
        # start the Upgrade
        LOGGER.info("Step 1: Start the upgrade.")
        start_upgrade_proc.start()
        time.sleep(self.prov_conf["sleep_time"])  # Wait to start upgrade_thread thread
        # Verify the upgrade status.
        LOGGER.info("Step 2: Verify the upgrade status.")
        status_resp = self.get_status()
        assert_utils.assert_true(status_resp[0])
        LOGGER.info("Status is %s", status_resp)
        # suspend the upgrade.
        LOGGER.info("Step 3: Suspend the upgrade.")
        suspend_resp = self.upgrade_obj.upgrade_software(self.master_node_list[0],
                                                         self.prov_conf['k8s_dir'],
                                                         exc=False, flag=
                                                         self.prov_conf["upgrade_suspend"])
        assert_utils.assert_true(suspend_resp[0])
        assert_utils.assert_in(cons.UPGRADE_SUSPEND_MSG, suspend_resp[1])
        # verify the upgrade status
        status_resp = self.get_status()
        LOGGER.info("Status is %s", status_resp)
        # Verify the POD status
        LOGGER.info("Step 4: Verify the PODs status.")
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        # Verify the already paused process by giving pause command
        LOGGER.info("Step 5: verify the already suspended status.")
        suspended_resp = self.upgrade_obj.upgrade_software(self.master_node_list[0],
                                                           self.prov_conf['k8s_dir'],
                                                           exc=False, flag=
                                                           self.prov_conf["upgrade_suspend"])
        assert_utils.assert_true(suspended_resp[0])
        assert_utils.assert_in(cons.UPGRADE_ALREADY_SUSPENDED, suspended_resp[1])
        time.sleep(self.prov_conf["sleep_time"])
        start_upgrade_proc.kill()
        # Verify the POD and Service status
        LOGGER.info("Step 6: Verify the PODs and Services status.")
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        time.sleep(self.prov_conf["sleep_time"])
        resp = self.upgrade_obj.prov_obj.check_service_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        installed_version = self.upgrade_obj.prov_obj.get_installed_version(
            self.master_node_list[0])
        LOGGER.info("Upgraded to version %s", installed_version)
        self.upgrade_cleanup = True
        self.collect_sb = False
        LOGGER.info("--------- Test Completed ---------")

    @pytest.mark.lc
    @pytest.mark.cortx_upgrade
    @pytest.mark.tags("TEST-41952")
    def test_41952(self):
        """Verify start and upgrade status during upgrade."""
        LOGGER.info("Test Started.")
        que = multiprocessing.Queue()
        start_upgrade_proc = multiprocessing.Process(target=self.rolling_upgrade, args=(
            True, que, self.prov_conf["upgrade_start"]))
        # start the Upgrade
        LOGGER.info("Step 1: Start the upgrade.")
        start_upgrade_proc.start()
        time.sleep(self.prov_conf["sleep_time"])  # Wait to start upgrade_thread thread
        # Verify the upgrade status.
        LOGGER.info("Step 2: Verify the upgrade status.")
        status_resp = self.get_status()
        LOGGER.info("Status is %s", status_resp)
        assert_utils.assert_true(status_resp[0])
        assert_utils.assert_in(cons.UPGRADE_IN_PROGRESS_MSG, status_resp[1])
        start_upgrade_proc.join()
        # Verify the POD and Service status
        LOGGER.info("Step 3: Verify the PODs and Services status.")
        pod_status = self.upgrade_obj.prov_obj.check_pods_status(self.master_node_list[0])
        assert_utils.assert_true(pod_status)
        resp = self.upgrade_obj.prov_obj.check_service_status(self.master_node_list[0])
        assert_utils.assert_true(resp[0], resp[1])
        installed_version = self.upgrade_obj.prov_obj.get_installed_version(
            self.master_node_list[0])
        LOGGER.info("Upgraded to version %s", installed_version)
        self.collect_sb = False
        LOGGER.info("--------- Test Completed ---------")
