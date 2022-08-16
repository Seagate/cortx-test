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
"""Tests for performing load testing using Jmeter"""

import logging
import math
import os
from http import HTTPStatus
import secrets
import shutil
import time
import pytest

from commons import cortxlogging
from commons import configmanager
from commons import constants as const
from commons.constants import Rest as rest_const
from commons.constants import SwAlerts as sw_alerts
from commons.utils import config_utils
from config import CSM_REST_CFG, CMN_CFG, RAS_VAL
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.csm_interface import csm_api_factory
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_run_man import RunDataCheckManager
from libs.jmeter.jmeter_integration import JmeterInt
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.ras.sw_alerts import SoftwareAlert
from libs.s3 import s3_misc


class TestCsmLoad():
    """Test cases for performing CSM REST API load testing using jmeter"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("[STARTED]: Setup class")
        cls.jmx_obj = JmeterInt()

        cls.csm_obj = csm_api_factory("rest")
        cls.config_chk = CSMConfigsCheck()
        cls.test_cfgs = config_utils.read_yaml('config/csm/test_jmeter.yaml')[1]
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.config_chk.delete_csm_users()
        user_already_present = cls.config_chk.check_predefined_csm_user_present()
        if not user_already_present:
            user_already_present = cls.config_chk.setup_csm_users()
            assert user_already_present
        s3acc_already_present = cls.config_chk.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = cls.config_chk.setup_csm_s3()
        assert s3acc_already_present
        cls.log.info("[Completed]: Setup class")
        cls.default_cpu_usage = False
        cls.buckets_created = []
        cls.iam_users_created = []
        cls.csm_users_created = []
        cls.ha_obj = HAK8s()
        cls.failed_pod = []
        cls.restore_pod = cls.deployment_backup = cls.deployment_name = cls.restore_method = None
        cls.system_random = secrets.SystemRandom()
        cls.request_usage = 122
        cls.sw_alert_obj = None

    def setup_method(self):
        """
        Setup Method
        """
        self.log.info("[START] Setup Method")
        self.log.info("Deleting older jmeter logs : %s", self.jmx_obj.jtl_log_path)
        if os.path.exists(self.jmx_obj.jtl_log_path):
            shutil.rmtree(self.jmx_obj.jtl_log_path)
        self.restore_pod = self.restore_method = self.deployment_name = self.set_name = None
        self.num_replica = 1
        self.log.info("[END] Setup Method")

    def teardown_method(self):
        """Teardown method
        """
        self.log.info("STARTED: Teardown Operations.")
        iam_deleted = []
        csm_deleted = []
        buckets_deleted = []

        if self.restore_pod:
            resp = self.ha_obj.restore_pod(pod_obj=self.csm_obj.master,
                                           restore_method=self.restore_method,
                                           restore_params={"deployment_name": self.deployment_name,
                                                           "deployment_backup":
                                                               self.deployment_backup,
                                                           "num_replica": self.num_replica,
                                                           "set_name": self.set_name})
            self.log.debug("Response: %s", resp)
            assert resp[0], f"Failed to restore pod by {self.restore_method} way"
            self.log.info("Successfully restored pod by %s way", self.restore_method)

        for bucket in self.buckets_created:
            resp = s3_misc.delete_objects_bucket(bucket[0], bucket[1], bucket[2])
            if resp:
                buckets_deleted.append(bucket)
            else:
                self.log.error("Bucket deletion failed for %s ", bucket)
        self.log.info("buckets deleted %s", buckets_deleted)
        for bucket in buckets_deleted:
            self.buckets_created.remove(bucket)

        for iam_user in self.iam_users_created:
            resp = self.csm_obj.delete_iam_user(iam_user)
            if resp:
                iam_deleted.append(iam_user)
            else:
                self.log.error("IAM deletion failed for %s ", iam_user)
        self.log.info("IAMs deleted %s", iam_deleted)
        for iam in iam_deleted:
            self.iam_users_created.remove(iam)

        for csm_user in self.csm_users_created:
            resp = self.csm_obj.delete_csm_user(csm_user)
            if resp:
                csm_deleted.append(csm_user)
            else:
                self.log.error("CSM user deletion failed for %s ", csm_user)
        self.log.info("CSM user deleted %s", csm_deleted)
        for csm in csm_deleted:
            self.csm_users_created.remove(csm)

        if self.default_cpu_usage:
            self.log.info("\nStep 4: Resolving CPU usage fault. ")
            self.log.info("Updating default CPU usage threshold value")
            resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(self.default_cpu_usage)
            assert resp[0], resp[1]
            self.log.info("\nStep 4: CPU usage fault is resolved.\n")
            self.default_cpu_usage = False
        assert len(self.buckets_created) == 0, "Bucket deletion failed"
        assert len(self.iam_users_created) == 0, "IAM deletion failed"
        assert len(self.csm_users_created) == 0, "CSM user deletion failed"
        self.log.info("Done: Teardown completed.")


    @pytest.mark.skip("Dummy test")
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-')
    def test_poc(self):
        """Sample test to run any jmeter script."""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        jmx_file = "CSM_Login.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(jmx_file)
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-locals
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44788')
    def test_44788(self):
        """
        CSM load testing with Get User Capacity while running IOs in parallel
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44788"]
        self.log.info("Step 1: Create account for I/O and GET capacity usage stats")
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=test_cfg["users_count"], use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=test_cfg["buckets_count"], users=users)
        username = list(data.keys())[0]

        self.log.info("Step 2: Start I/O")
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_44788'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=test_cfg["files_count"], prefs=pref_dir)

        self.log.info("Step 3: Poll User Capacity")
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["user"]
        content.append({fieldnames[0]: username})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Poll_User_Capacity.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=self.request_usage,
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"

        stop_res = run_data_chk_obj.stop_io_async(users=data, di_check=True, eventual_stop=True)
        self.log.info("stop_res -  %s", stop_res)

        self.log.info("Perform & Verify GET API to get capacity usage stats")
        resp = self.csm_obj.get_user_capacity_usage("user", username)
        assert resp.status_code == HTTPStatus.OK, \
                "Status code check failed for get capacity"
        t_obj = resp.json()["capacity"]["s3"]["users"][0]["objects"]
        t_size = resp.json()["capacity"]["s3"]["users"][0]["used"]
        m_size = resp.json()["capacity"]["s3"]["users"][0]["used_rounded"]
        self.log.info("objects -  %s", t_obj)
        self.log.info("used capacity-  %s", t_size)
        self.log.info("used_rounded capacity-  %s", m_size)
        assert t_obj > 0, "Number of objects is Zero"
        assert t_size > 0, "Used Size is Zero"
        assert m_size > 0, "Total Size is Zero"
        assert m_size >= t_size, "Used - Used Rounded Size mismatch found"

        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable=too-many-statements
    @pytest.mark.skip(reason="not_in_main_build_yet")
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44794')
    def test_44794(self):
        """
        CSM load testing in degraded mode to view Degraded capacity
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44794"]
        self.log.info("Step 1: Create accounts for I/O")
        mgm_ops = ManagementOPs()
        users = mgm_ops.create_account_users(nusers=test_cfg["users_count"], use_cortx_cli=False)
        data = mgm_ops.create_buckets(nbuckets=test_cfg["buckets_count"], users=users)

        self.log.info("Step 2: [Start] Shutdown the data pod safely")
        num_replica = 0
        self.log.info("Get pod to be deleted")
        sts_dict = self.csm_obj.master.get_sts_pods(pod_prefix=const.POD_NAME_PREFIX)
        sts_list = list(sts_dict.keys())
        self.log.debug("%s Statefulset: %s", const.POD_NAME_PREFIX, sts_list)
        sts = self.system_random.sample(sts_list, 1)[0]
        delete_pod = sts_dict[sts][-1]
        self.log.info("Pod to be deleted is %s", delete_pod)
        set_type, set_name = self.csm_obj.master.get_set_type_name(pod_name=delete_pod)
        if set_type == const.STATEFULSET:
            resp = self.csm_obj.master.get_num_replicas(set_type, set_name)
            assert resp[0], resp
            self.num_replica = int(resp[1])
            num_replica = self.num_replica - 1

        self.log.info("Shutdown random data pod by replica method and "
                    "verify cluster & remaining pods status")
        resp = self.ha_obj.delete_kpod_with_shutdown_methods(
            master_node_obj=self.csm_obj.master, health_obj=self.csm_obj.hlth_master,
            delete_pod=[delete_pod], num_replica=num_replica)
        # Assert if empty dictionary
        assert resp[1], "Failed to shutdown/delete pod"
        pod_name = list(resp[1].keys())[0]
        if set_type == const.STATEFULSET:
            self.set_name = resp[1][pod_name]['deployment_name']
        elif set_type == const.REPLICASET:
            self.deployment_name = resp[1][pod_name]['deployment_name']
        self.restore_pod = True
        self.restore_method = resp[1][pod_name]['method']
        assert resp[0], "Cluster/Services status is not as expected"

        self.log.info("Step 3: Start I/O")
        run_data_chk_obj = RunDataCheckManager(users=data)
        pref_dir = {"prefix_dir": 'test_44794'}
        run_data_chk_obj.start_io_async(
            users=data, buckets=None, files_count=test_cfg["files_count"], prefs=pref_dir)

        self.log.info("Step 4: Poll Degraded Capacity")
        jmx_file = "CSM_Poll_Degraded_Capacity.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=self.request_usage,
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"

        stop_res = run_data_chk_obj.stop_io_async(users=data, di_check=True, eventual_stop=True)
        self.log.info("stop_res -  %s", stop_res)

        self.log.info("Step 5: Call degraded capacity api")
        response = self.csm_obj.get_degraded_capacity(endpoint_param=None)
        assert response.status_code == HTTPStatus.OK , "Status code check failed"
        self.log.info("Step 6: Check all variables are present in rest response")
        resp = self.csm_obj.validate_metrics(response.json(), endpoint_param=None)
        assert resp, "Rest data metrics check failed in full mode"

        resp = self.ha_obj.restore_pod(pod_obj=self.csm_obj.master,
                                        restore_method=self.restore_method,
                                        restore_params={"deployment_name": self.deployment_name,
                                                        "deployment_backup":
                                                            self.deployment_backup,
                                                        "num_replica": self.num_replica,
                                                        "set_name": self.set_name})
        self.log.debug("Response: %s", resp)
        assert resp[0], f"Failed to restore pod by {self.restore_method} way"
        self.restore_pod = False
        self.log.info("Successfully restored pod by %s way", self.restore_method)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-45719')
    def test_45719(self):
        """
        Test user cant create duplicate CSM user in parallel
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_45719"]

        self.log.info("Step 1: Send multiple create CSM users with same creds requests parallel")
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["role", "user", "pswd"]
        content.append({fieldnames[0]: "admin",
                        fieldnames[1]: f'admin_{test_case_name}',
                        fieldnames[2]: CSM_REST_CFG["csm_admin_user"]["password"]})
        content.append({fieldnames[0]: "manage",
                        fieldnames[1]: f'manage_{test_case_name}',
                        fieldnames[2]: CSM_REST_CFG["csm_user_manage"]["password"]})
        content.append({fieldnames[0]: "monitor",
                        fieldnames[1]: f'monitor_{test_case_name}',
                        fieldnames[2]: CSM_REST_CFG["csm_user_monitor"]["password"]})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Create_N_CSM_Users.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx_with_message(
            jmx_file,
            expect_count = self.request_usage - test_cfg["users_count"],
            expect_message = test_cfg["expect_message"],
            threads=self.request_usage,
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"

        self.log.info("Step 2: Add user to list to be deleted")
        self.csm_users_created.append(f'admin_{test_case_name}')
        self.csm_users_created.append(f'manage_{test_case_name}')
        self.csm_users_created.append(f'monitor_{test_case_name}')

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-45718')
    def test_45718(self):
        """
        Test user cant create duplicate IAM user in parallel
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_45718"]

        self.log.info("Step 1: Find and delete if user already exists")
        uid = 'test_45718'
        self.csm_obj.delete_iam_user(uid)

        self.log.info("Step 2: Send multiple create IAM user with same user name requests parallel")
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["uid"]
        content.append({fieldnames[0]: uid})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Create_N_IAM_Users.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx_with_message(
            jmx_file,
            expect_count = self.request_usage - test_cfg["users_count"],
            expect_message = test_cfg["expect_message"],
            threads=self.request_usage,
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"

        self.log.info("Step 3: Add user to list to be deleted")
        self.iam_users_created.append(uid)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lr
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22203')
    def test_22203(self):
        """Test maximum number of same users which can login per second using CSM REST.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_22203"]
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["role", "user", "pswd"]
        content.append({fieldnames[0]: "admin",
                        fieldnames[1]: CSM_REST_CFG["csm_admin_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_admin_user"]["password"]})
        content.append({fieldnames[0]: "manage",
                        fieldnames[1]: CSM_REST_CFG["csm_user_manage"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_user_manage"]["password"]})
        content.append({fieldnames[0]: "monitor",
                        fieldnames[1]: CSM_REST_CFG["csm_user_monitor"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_user_monitor"]["password"]})
        content.append({fieldnames[0]: "s3",
                        fieldnames[1]: CSM_REST_CFG["s3account_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["s3account_user"]["password"]})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Concurrent_Same_User_Login.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44256')
    def test_44256(self):
        """
        Test maximum number of same users which can login per second using CSM REST.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44256"]
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["role", "user", "pswd"]
        content.append({fieldnames[0]: "admin",
                        fieldnames[1]: CSM_REST_CFG["csm_admin_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_admin_user"]["password"]})
        content.append({fieldnames[0]: "manage",
                        fieldnames[1]: CSM_REST_CFG["csm_user_manage"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_user_manage"]["password"]})
        content.append({fieldnames[0]: "monitor",
                        fieldnames[1]: CSM_REST_CFG["csm_user_monitor"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_user_monitor"]["password"]})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Concurrent_Same_User_Login.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lr
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22204')
    def test_22204(self):
        """
        Test maximum number of different users which can login using CSM REST per second
        using CSM REST
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_22204"]
        jmx_file = "CSM_Concurrent_Different_User_Login.jmx"
        self.log.info("Running jmx script: %s", jmx_file)

        resp = self.csm_obj.list_all_created_s3account()
        assert resp.status_code == HTTPStatus.OK, "List S3 account failed."
        user_data = resp.json()
        self.log.info("List user response : %s", user_data)
        existing_user = len(user_data['s3_accounts'])
        self.log.info("Existing S3 users count: %s", existing_user)
        self.log.info("Max S3 users : %s", rest_const.MAX_S3_USERS)
        new_s3_users = rest_const.MAX_S3_USERS - existing_user
        self.log.info("New users to create: %s", new_s3_users)

        self.log.info("Step 1: Listing all csm users")
        response = self.csm_obj.list_csm_users(
            expect_status_code=rest_const.SUCCESS_STATUS,
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == rest_const.SUCCESS_STATUS
        user_data = response.json()
        self.log.info("List user response : %s", user_data)
        existing_user = len(user_data['users'])
        self.log.info("Existing CSM users count: %s", existing_user)
        self.log.info("Max csm users : %s", rest_const.MAX_CSM_USERS)
        new_csm_users = rest_const.MAX_CSM_USERS - existing_user
        self.log.info("New users to create: %s", new_csm_users)
        loops = min(new_s3_users, new_csm_users)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=loops)
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44257')
    def test_44257(self):
        """
        Test maximum number of different users which can login using CSM REST per second
        using CSM REST
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44257"]
        jmx_file = "CSM_Concurrent_Different_User_Login_lc.jmx"
        self.log.info("Running jmx script: %s", jmx_file)

        resp = self.csm_obj.list_iam_users_rgw()
        assert resp.status_code == HTTPStatus.OK, "List IAM user failed."
        user_data = resp.json()
        self.log.info("List user response : %s", user_data)
        existing_user = len(user_data['users'])
        self.log.info("Existing iam users count: %s", existing_user)
        self.log.info("Max iam users : %s", rest_const.MAX_IAM_USERS)
        new_iam_users = rest_const.MAX_IAM_USERS - existing_user
        self.log.info("New users to create: %s", new_iam_users)

        self.log.info("Step 1: Listing all csm users")
        response = self.csm_obj.list_csm_users(
            expect_status_code=rest_const.SUCCESS_STATUS,
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == rest_const.SUCCESS_STATUS
        user_data = response.json()
        self.log.info("List user response : %s", user_data)
        existing_user = len(user_data['users'])
        self.log.info("Existing CSM users count: %s", existing_user)
        self.log.info("Max csm users : %s", rest_const.MAX_CSM_USERS)
        new_csm_users = rest_const.MAX_CSM_USERS - existing_user
        self.log.info("New users to create: %s", new_csm_users)
        loops = min(new_iam_users, new_csm_users,test_cfg["loop"])
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=loops)
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)


    # pylint: disable=too-many-statements
    @pytest.mark.lc
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44799')
    def test_44799(self):
        """
        Verify max number of IAM users using all the required parameters
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        resp = self.csm_obj.list_iam_users_rgw()
        assert resp.status_code == HTTPStatus.OK, "List IAM user failed."
        user_data = resp.json()
        self.log.info("Step 1: List user response : %s", user_data)
        existing_user = len(user_data['users'])
        self.log.info("Existing iam users count: %s", existing_user)
        self.log.info("Max iam users : %s", rest_const.MAX_IAM_USERS)
        new_iam_users = rest_const.MAX_IAM_USERS - existing_user
        self.log.info("New users to create: %s", new_iam_users)

        self.log.info("Step 2: Create users in parallel")
        self.csm_obj.create_multi_iam_user_loaded(new_iam_users, existing_user)

        self.log.info("Find all newly created users")
        resp = self.csm_obj.list_iam_users_rgw()
        assert resp.status_code == HTTPStatus.OK, "List IAM user failed."
        user_data_new = resp.json()
        init_users = user_data['users']
        current_users = user_data_new['users']
        self.log.info("List initial user  : %s", init_users)
        self.log.info("List current user : %s", current_users)
        delete_user_list = current_users
        for user in init_users:
            if user in current_users:
                delete_user_list.remove(user)
        self.iam_users_created.extend(delete_user_list)

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44781')
    def test_44781(self):
        """
        Verify proper error message is returned when number of CSM requests exceeds
        the CSM_REQUEST_USAGE.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["role", "user", "pswd"]
        content.append({fieldnames[0]: "admin",
                        fieldnames[1]: CSM_REST_CFG["csm_admin_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_admin_user"]["password"]})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Concurrent_Same_User_Login.jmx"
        self.log.info("Running jmx scripts: %s", jmx_file)
        request_count_limited = math.floor(self.request_usage - self.request_usage * 0.1)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=request_count_limited,
            rampup=1,
            loop=1)
        assert result, "Errors reported in the Jmeter execution for less than limit"
        request_count_exceed = math.floor(self.request_usage + self.request_usage * 0.1)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=request_count_exceed,
            rampup=1,
            loop=1)
        assert result is False, "Errors not reported in the Jmeter execution for greater than limit"
        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lr
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22207')
    def test_22207(self):
        """Test with maximum number of GET performance stats request using CSM REST"""
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_22207"]
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        resp = self.csm_obj.get_stats()
        assert resp.status_code == 200
        unit_list = resp.json()['unit_list']
        content = []
        fieldnames = ["metric"]
        for metric in unit_list:
            content.append({fieldnames[0]: metric})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Concurrent_Performance.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22208')
    def test_22208(self):
        """Test maximum number of get , patch, post operations on alerts per second using CSM REST
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.sw_alert_obj = SoftwareAlert(CMN_CFG["nodes"][0]["hostname"],
                                    CMN_CFG["nodes"][0]["username"],
                                    CMN_CFG["nodes"][0]["password"])
        self.csm_alert_obj = SystemAlerts(cls.sw_alert_obj.node_utils)
        test_cfg = self.test_cfgs["test_22208"]
        self.log.info("\nGenerate CPU usage fault.")
        starttime = time.time()
        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=const.SSPL_CFG_URL, field=const.CONF_CPU_USAGE)
        resp = self.sw_alert_obj.gen_cpu_usage_fault_thres(test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        self.log.info("\nCPU usage fault is created successfully.\n")

        self.log.info("\nStep 2: Keep the CPU usage above threshold for %s seconds.",
                      RAS_VAL["ras_sspl_alert"]["alert_wait_threshold"])
        time.sleep(RAS_VAL["ras_sspl_alert"]["alert_wait_threshold"])
        self.log.info("\nStep 2: CPU usage was above threshold for %s seconds.\n",
                      RAS_VAL["ras_sspl_alert"]["alert_wait_threshold"])

        self.log.info("\nStep 3: Checking CPU usage fault alerts on CSM REST API ")
        resp = self.csm_alert_obj.wait_for_alert(test_cfg["wait_for_alert"],
                                                 starttime,
                                                 sw_alerts.AlertType.FAULT,
                                                 False,
                                                 test_cfg["resource_type"])
        assert resp[0], resp[1]
        self.log.info("\nStep 3: Successfully verified CPU usage fault alert on CSM REST API. \n")

        jmx_file = "CSM_Concurrent_alert.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
                                    threads=test_cfg["threads"],
                                    rampup=test_cfg["rampup"],
                                    loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("JMX script execution completed")

        self.log.info("\nStep 4: Resolving CPU usage fault. ")
        self.log.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(
            self.default_cpu_usage)
        assert resp[0], resp[1]
        self.log.info("\nStep 4: CPU usage fault is resolved.\n")
        self.default_cpu_usage = False

        self.log.info("\nStep 2: Keep the CPU usage above threshold for %s seconds.",
                      RAS_VAL["ras_sspl_alert"]["alert_wait_threshold"])
        time.sleep(RAS_VAL["ras_sspl_alert"]["alert_wait_threshold"])
        self.log.info("\nStep 2: CPU usage was above threshold for %s seconds.\n",
                      RAS_VAL["ras_sspl_alert"]["alert_wait_threshold"])

        self.log.info("\nStep 3: Checking CPU usage fault alerts on CSM REST API ")
        resp = self.csm_alert_obj.wait_for_alert(test_cfg["wait_for_alert"],
                                                 starttime,
                                                 sw_alerts.AlertType.FAULT,
                                                 True,
                                                 test_cfg["resource_type"])
        assert resp[0], resp[1]
        self.log.info("\nStep 3: Successfully verified CPU usage fault alert on CSM REST API. \n")

        self.log.info("##### Test completed -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-32547')
    def test_32547(self):
        """Test maximum number of same users which can login per second using CSM REST.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_32547"]
        fpath = os.path.join(self.jmx_obj.jmeter_path, self.jmx_obj.test_data_csv)
        content = []
        os.remove(fpath)
        fieldnames = ["role", "user", "pswd"]
        content.append({fieldnames[0]: "admin",
                        fieldnames[1]: CSM_REST_CFG["csm_admin_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_admin_user"]["password"]})
        content.append({fieldnames[0]: "s3",
                        fieldnames[1]: CSM_REST_CFG["s3account_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["s3account_user"]["password"]})
        self.log.info("Test data file path : %s", fpath)
        self.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)
        jmx_file = "CSM_Concurrent_Same_User_Login_lc.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        err_cnt, total_cnt = self.jmx_obj.get_err_cnt(os.path.join(self.jmx_obj.jtl_log_path,
                                                                   "statistics.json"))
        assert err_cnt == 0, f"{err_cnt} of {total_cnt} requests have failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44782')
    def test_44782(self):
        """
        Verify max allowed CSM user limit
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44782"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]
        resp = self.csm_obj.list_csm_users(HTTPStatus.OK, return_actual_response=True)
        existing_user = len(resp.json()['users'])
        result = self.csm_obj.create_multi_csm_user(test_cfg["total_users"], existing_user)
        assert result, "Unable to create max users"
        self.log.info("Create one more user and check for 403 forbidden")
        response = self.csm_obj.create_csm_user(
            user_type="valid", user_role="manage")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == HTTPStatus.FORBIDDEN
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert response.json()["error_code"] == resp_error_code, "Error code check failed"
            assert response.json()["message_id"] == resp_msg_id, "Message ID check failed"
            assert response.json()["message"] == msg, "Message check failed"
        #Delete all created users
        result = self.csm_obj.delete_multi_csm_user(test_cfg["total_users"], existing_user)
        assert result, "Unable to delete max users"
        self.log.info("##### Test completed -  %s #####", test_case_name)
