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
import os
import shutil
import pytest
from commons import cortxlogging
from commons import configmanager
from commons.utils import config_utils
from config import CSM_REST_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.csm_interface import csm_api_factory
from libs.jmeter.jmeter_integration import JmeterInt
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.csm.extensions.csm_ext import CSMExt


class TestResourceLimit():
    """Test cases for performing CSM REST API resource limit testing"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("[STARTED]: Setup class")
        cls.jmx_obj = JmeterInt()

        cls.csm_obj = csm_api_factory("rest")
        cls.prov_obj = CSMExt(cls.csm_obj)
        cls.test_cfgs = config_utils.read_yaml('config/csm/test_rest_resource_limit.yaml')[1]
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.update_seconds = 60
        cls.config_chk = CSMConfigsCheck()
        cls.config_chk.delete_csm_users()
        user_already_present = cls.config_chk.check_predefined_csm_user_present()
        if not user_already_present:
            user_already_present = cls.config_chk.setup_csm_users()
            assert user_already_present
        s3acc_already_present = cls.config_chk.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = cls.config_chk.setup_csm_s3()
        assert s3acc_already_present

        cls.default_cpu_usage = False
        cls.buckets_created = []
        cls.iam_users_created = []
        cls.ha_obj = HAK8s()
        cls.jmx_obj = JmeterInt()
        cls.request_usage = cls.csm_obj.get_request_usage_limit()

        cls.log.info("Reading CSM limits from solution.yaml")
        solution_path = cls.prov_obj.copy_sol_file_local()
        assert solution_path[0], solution_path[1]
        cls.pre_m1, cls.pre_m2, cls.pre_c1, cls.pre_c2 = cls.prov_obj.read_csm_res_limit()

        fpath = os.path.join(cls.jmx_obj.jmeter_path, cls.jmx_obj.test_data_csv)
        content = []
        fieldnames = ["role", "user", "pswd"]
        content.append({fieldnames[0]: "admin",
                        fieldnames[1]: CSM_REST_CFG["csm_admin_user"]["username"],
                        fieldnames[2]: CSM_REST_CFG["csm_admin_user"]["password"]})

        cls.log.info("Test data file path : %s", fpath)
        cls.log.info("Test data content : %s", content)
        config_utils.write_csv(fpath, fieldnames, content)

        cls.log.info("[Completed]: Setup class")

    def setup_method(self):
        """
        Setup Method
        """
        self.log.info("[START] Setup Method")
        self.log.info("Deleting older jmeter logs : %s", self.jmx_obj.jtl_log_path)
        if os.path.exists(self.jmx_obj.jtl_log_path):
            shutil.rmtree(self.jmx_obj.jtl_log_path)
        self.log.info("[END] Setup Method")

    def teardown_method(self):
        """Teardown method
        """
        self.log.info("START: Teardown Operations.")
        self.log.info("Revert the solution.yaml")
        post_m1 = self.pre_m1
        post_m2 = self.pre_m2
        post_c1 = self.pre_c1
        post_c2 = self.pre_c2
        resp = self.prov_obj.update_csm_res_limit(post_m1, post_m2, post_c1, post_c2)
        assert resp[0], "Failed to update CSM resource limit"
        self.log.info("Redeploy")
        self.prov_obj.destroy_prep_deploy_cluster()

        self.log.info("END: Teardown Operations.")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44795')
    def test_44795(self):
        """
        Verify CSM load tests with changed values of memory limits in the solution.yaml
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44795"]

        self.log.info("STEP 1: Reading the current resource limit...")
        initial_rl = self.csm_obj.get_request_usage_limit()
        self.log.info("Pre deployment resource limit: %s", initial_rl)

        self.log.info("STEP 2: Change the limits")
        post_m1 = test_cfg["m1"]
        post_m2 = test_cfg["m2"]
        post_c1 = self.pre_c1
        post_c2 = self.pre_c2
        resp = self.prov_obj.update_csm_res_limit(post_m1, post_m2, post_c1, post_c2)
        assert resp[0], "Failed to update CSM resource limit"
        self.log.info("STEP 3: Redeploy")
        self.prov_obj.destroy_prep_deploy_cluster()

        self.log.info("STEP 4: Reading the resource limit...")
        change_rl = self.csm_obj.get_request_usage_limit()
        self.log.info("Post deployment resource limit: %s", change_rl)

        self.log.info("STEP 5: Verifying resource limits have changed...")
        assert change_rl != initial_rl, "Resource limit have not changed after redeployment."

        self.log.info("STEP 6: Run Jmeter test with changed limit...")
        jmx_file = "CSM_Concurrent_Same_User_Login.jmx"
        self.log.info("Running jmx %s with new resource limit", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=change_rl,
            rampup=1,
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44796')
    def test_44796(self):
        """
        Verify deployment fails with invalid values of memory limits in the solution.yaml
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44796"]

        self.log.info("STEP 1: Reading the current resource limit...")
        initial_rl = self.csm_obj.get_request_usage_limit()
        self.log.info("Pre deployment resource limit: %s", initial_rl)

        self.log.info("STEP 2: Change the limits")
        post_m1 = self.pre_m2
        post_m2 = self.pre_m1
        post_c1 = self.pre_c1
        post_c2 = self.pre_c2
        resp = self.prov_obj.update_csm_res_limit(post_m1, post_m2, post_c1, post_c2)
        assert resp[0], "Failed to update CSM resource limit"
        self.log.info("STEP 3: Redeploy")
        self.prov_obj.destroy_prep_deploy_cluster(expect_fail=test_cfg["err_msg"])

        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44797')
    def test_44797(self):
        """
        Verify CSM load tests with changed values of CPU limits in the solution.yaml
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44797"]

        self.log.info("STEP 1: Reading the current resource limit...")
        initial_rl = self.csm_obj.get_request_usage_limit()
        self.log.info("Pre deployment resource limit: %s", initial_rl)

        self.log.info("STEP 2: Change the limits")
        post_m1 = self.pre_m1
        post_m2 = self.pre_m2
        post_c1 = test_cfg["c1"]
        post_c2 = test_cfg["c2"]
        resp = self.prov_obj.update_csm_res_limit(post_m1, post_m2, post_c1, post_c2)
        assert resp[0], "Failed to update CSM resource limit"
        self.log.info("STEP 3: Redeploy")
        self.prov_obj.destroy_prep_deploy_cluster()

        self.log.info("STEP 4: Reading the resource limit...")
        change_rl = self.csm_obj.get_request_usage_limit()
        self.log.info("Post deployment resource limit: %s", change_rl)

        self.log.info("STEP 5: Verifying resource limits have changed...")
        assert change_rl == initial_rl, "Resource limit have changed after redeployment."

        self.log.info("STEP 6: Run Jmeter test with changed limit...")
        jmx_file = "CSM_Concurrent_Same_User_Login.jmx"
        self.log.info("Running jmx %s with new resource limit", jmx_file)
        result = self.jmx_obj.run_verify_jmx(
            jmx_file,
            threads=change_rl,
            rampup=1,
            loop=test_cfg["loop"])
        assert result, "Errors reported in the Jmeter execution"
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-44798')
    def test_44798(self):
        """
        Verify deployment fails with invalid values of  CPU limits in solution.yaml
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_44798"]

        self.log.info("STEP 1: Reading the current resource limit...")
        initial_rl = self.csm_obj.get_request_usage_limit()
        self.log.info("Pre deployment resource limit: %s", initial_rl)

        self.log.info("STEP 2: Change the limits")
        post_m1 = self.pre_m1
        post_m2 = self.pre_m2
        post_c1 = self.pre_c2
        post_c2 = self.pre_c1
        resp = self.prov_obj.update_csm_res_limit(post_m1, post_m2, post_c1, post_c2)
        assert resp[0], "Failed to update CSM resource limit"
        self.log.info("STEP 3: Redeploy")
        self.prov_obj.destroy_prep_deploy_cluster(expect_fail=test_cfg["err_msg"])
        self.log.info("##### Test completed -  %s #####", test_case_name)
