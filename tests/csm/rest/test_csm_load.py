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
#
"""Tests for performing load testing using Jmeter"""

import logging
import os
import time
import pytest
import shutil
from commons import cortxlogging
from commons.utils import config_utils
from commons.constants import SwAlerts as const
from commons import constants as cons
from config import CSM_REST_CFG, CMN_CFG, RAS_VAL
from libs.jmeter.jmeter_integration import JmeterInt
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_stats import SystemStats
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.sw_alerts import SoftwareAlert


class TestCsmLoad():
    """Test cases for performing CSM REST API load testing using jmeter"""
    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("[STARTED]: Setup class")
        cls.jmx_obj = JmeterInt()
        cls.system_stats = SystemStats()
        cls.sw_alert_obj = SoftwareAlert(CMN_CFG["nodes"][0]["hostname"],
                                         CMN_CFG["nodes"][0]["username"],
                                         CMN_CFG["nodes"][0]["password"])
        cls.csm_alert_obj = SystemAlerts(cls.sw_alert_obj.node_utils)
        cls.config_chk = CSMConfigsCheck()
        cls.test_cfgs = config_utils.read_yaml('config/csm/test_jmeter.yaml')[1]
        cls.config_chk.delete_csm_users()
        cls.config_chk.delete_s3_users()
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

    def setup_method(self):
        self.log.info("Deleting older jmeter logs : %s",self.jmx_obj.jtl_log_path )
        shutil.rmtree(self.jmx_obj.jtl_log_path)

    def teardown_method(self):
        """Teardown method
        """
        if self.default_cpu_usage:
            self.log.info("\nStep 4: Resolving CPU usage fault. ")
            self.log.info("Updating default CPU usage threshold value")
            resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(self.default_cpu_usage)
            assert resp[0], resp[1]
            self.log.info("\nStep 4: CPU usage fault is resolved.\n")
            self.default_cpu_usage = False

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
        resp = self.jmx_obj.run_jmx(jmx_file)
        assert resp, "Jmeter Execution Failed."
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
        resp = self.jmx_obj.run_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert resp, "Jmeter Execution Failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.lr
    @pytest.mark.jmeter
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-22204')
    def test_22204(self):
        """Test maximum number of different users which can login using CSM REST per second
        using CSM REST
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.test_cfgs["test_22204"]
        jmx_file = "CSM_Concurrent_Different_User_Login.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        resp = self.jmx_obj.run_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert resp, "Jmeter Execution Failed."
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
        resp = self.system_stats.get_stats()
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
        resp = self.jmx_obj.run_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert resp, "Jmeter Execution Failed."
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
        test_cfg = self.test_cfgs["test_22208"]
        self.log.info("\nGenerate CPU usage fault.")
        starttime = time.time()
        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
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
                                                 const.AlertType.FAULT,
                                                 False,
                                                 test_cfg["resource_type"])
        assert resp[0], resp[1]
        self.log.info("\nStep 3: Successfully verified CPU usage fault alert on CSM REST API. \n")

        jmx_file = "CSM_Concurrent_alert.jmx"
        self.log.info("Running jmx script: %s", jmx_file)
        resp = self.jmx_obj.run_jmx(jmx_file,
                                    threads=test_cfg["threads"],
                                    rampup=test_cfg["rampup"],
                                    loop=test_cfg["loop"])
        assert resp, "Jmeter Execution Failed."
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
                                                 const.AlertType.FAULT,
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
        resp = self.jmx_obj.run_jmx(
            jmx_file,
            threads=test_cfg["threads"],
            rampup=test_cfg["rampup"],
            loop=test_cfg["loop"])
        assert resp, "Jmeter Execution Failed."
        err_cnt, total_cnt = self.jmx_obj.get_err_cnt(os.path.join(self.jmx_obj.jtl_log_path,
                                                      "statistics.json"))
        assert err_cnt == 0, f"{err_cnt} of {total_cnt} requests have failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)
