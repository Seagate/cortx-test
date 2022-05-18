# pylint: disable=too-many-lines
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
"""Tests system statistics using REST API
"""
import logging
import random
import time
from http import HTTPStatus

from random import SystemRandom
import pytest

from commons import configmanager
from commons.constants import CONTROL_POD_NAME_PREFIX
from commons import cortxlogging
from commons.constants import Rest as const
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from libs.csm.rest.csm_rest_cluster import RestCsmCluster
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_stats import SystemStats
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.hs_bench import hsbench

# pylint: disable-msg=too-many-public-methods
class TestSystemStats():
    """System Health Testsuite
    """

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.system_stats = SystemStats()
        cls.log.info("Initiating Rest Client for Alert ...")
        cls.test_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_system_stats.yaml")
        cls.csm_user = RestCsmUser()
        cls.cryptogen = SystemRandom()
        cls.nd_obj = LogicalNode(hostname=CMN_CFG["nodes"][0]["hostname"],
                                 username=CMN_CFG["nodes"][0]["username"],
                                 password=CMN_CFG["nodes"][0]["password"])
        cls.csm_cluster = RestCsmCluster()
        cls.username = cls.csm_user.config["csm_admin_user"]["username"]
        cls.user_pass = cls.csm_user.config["csm_admin_user"]["password"]

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14752')
    def test_4956(self):
        """Test that GET API returns 200 response code
        and appropriate json response for metric stats
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started - %s #####", test_case_name)
        expected_response = const.SUCCESS_STATUS
        response = self.system_stats.get_stats()
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed.")
        actual_response = response.json()
        expected_response = self.test_conf["test_4956"]
        for test_param in ['panel_list', 'metric_list', 'unit_list']:
            result = self.system_stats.verify_list(
                expected_response[test_param],
                actual_response[test_param])
            assert result, self.log.error("%s didn't match", test_param)
        assert_utils.assert_false(': null' in actual_response,
                                  "Null values in the response")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14751')
    def test_4958(self):
        """TA CSM REST Automation: TEST-4958: Test that GET API returns 200
        as response code and appropriate json response with valid values
        for paramerter `from`, `to`, `interval` and `metric`,
        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        interval = self.test_conf["test_4958"]["interval_secs"]
        epoc_time_diff = self.test_conf["test_4958"]["epoc_time_diff"]
        expected_response = const.SUCCESS_STATUS
        metrics = self.system_stats.get_metrics()
        for metric in metrics:
            self.log.info(
                "============== Checking for metrics : %s==============", metric)
            to_time = int(time.time())
            from_time = int(time.time() - epoc_time_diff)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=interval)
            assert_utils.assert_equals(response.status_code,
                                       expected_response, "Status code check failed.")
            actual_response = response.json()
            assert_utils.assert_equals(
                actual_response["metrics"][0]["name"], metric, "Metric name mismatch")
            expected_cnt = self.system_stats.expected_entry_cnt(
                to_time, from_time, interval=interval)
            self.log.info(
                "Expected number of entries : %s", expected_cnt)
            actual_cnt = len(actual_response["metrics"][0]["data"][0])
            self.log.info("Actual number of entries : %s", actual_cnt)
            assert_utils.assert_equals(actual_cnt, expected_cnt,
                                       "Sample count check failed")
            assert_utils.assert_false(': null' in actual_response,
                                      "Null values in the response")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14753')
    def test_4959(self):
        """Test that GET API returns 200 as response code and
        appropriate json response with valid values for paramerter
        `from`, `to`, `metric` and both (`interval`, `total_sample`)
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        expected_response = const.SUCCESS_STATUS
        interval = int(self.test_conf["test_4959"]["interval_secs"])
        total_sample = int(self.test_conf["test_4959"]["total_sample"])
        epoc_time_diff = self.test_conf["test_4959"]["epoc_time_diff"]
        metrics = self.system_stats.get_metrics()
        for metric in metrics:
            self.log.info(
                "============== Checking for metrics : %s==============", metric)
            to_time = int(time.time())
            from_time = int(time.time() - epoc_time_diff)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=interval,
                                                   total_sample=total_sample)
            assert_utils.assert_equals(response.status_code,
                                       expected_response, "Status code check failed.")
            actual_response = response.json()
            actual_cnt = len(actual_response["metrics"][0]["data"][0])
            self.log.info("Actual number of entries : %s", actual_cnt)
            expected_cnt = self.system_stats.expected_entry_cnt(
                to_time,
                from_time,
                interval=interval,
                total_sample=total_sample)
            self.log.info(
                "Expected number of entries : %s", expected_cnt)
            assert_utils.assert_equals(actual_cnt, expected_cnt,
                                       "Sample count check failed")
            assert_utils.assert_false(': null' in actual_response,
                                      "Null values in the response")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.skip("Known issue EOS-23135")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-13084')
    def test_4961(self):
        """Test that GET API returns 400 and appropriate error response with
        invalid values for params.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        epoc_time_diff = self.test_conf["test_4961"]["epoc_time_diff"]
        to_time = int(time.time())
        from_time = int(time.time() - epoc_time_diff)
        metrics = self.system_stats.get_metrics()
        expected_response = self.test_conf["test_4961"]["expected_response"]
        expected_response = [int(tmp) for tmp in expected_response]
        interval = int(self.test_conf["test_4961"]["valid_interval_secs"])
        total_sample = int(self.test_conf["test_4961"]["valid_total_sample"])

        self.log.info("##### Testing with invalid METRIC param  #####")
        invalid_metrics = self.test_conf["test_4961"]["invalid_metrics"]
        for invalid_metric in invalid_metrics:
            response = self.system_stats.get_stats(metrics=[invalid_metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=interval,
                                                   total_sample=total_sample)
            self.log.info("Expected response : %s", expected_response)
            self.log.info("Actual response : %s", response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid METRICS.")

        self.log.info("##### Testing with invalid TOTAL SAMPLEs param  #####")
        invalid_samples = self.test_conf["test_4961"]["invalid_samples"]
        for invalid_sample in invalid_samples:
            metric = self.cryptogen.randrange(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=interval,
                                                   total_sample=invalid_sample)
            self.log.info("Expected response : %s", expected_response)
            self.log.info("Actual response : %s", response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid TOTAL samples.")

        self.log.info("##### Testing with invalid INTERVALs param  #####")
        invalid_intervals = self.test_conf["test_4961"]["invalid_intervals"]
        for invalid_interval in invalid_intervals:
            metric = self.cryptogen.randrange(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=invalid_interval,
                                                   total_sample=total_sample)
            self.log.info("Expected response : %s", expected_response)
            self.log.info("Actual response : %s", response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid INTERVALS.")

        self.log.info("##### Testing with invalid TO and FROM param  #####")
        invalid_times = self.test_conf["test_4961"]["invalid_times"]
        for invalid_time in invalid_times:
            metric = random.choice(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=invalid_time,
                                                   to_time=to_time,
                                                   interval=interval,
                                                   total_sample=total_sample)
            self.log.info("Expected response : %s", expected_response)
            self.log.info("Actual response : %s", response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid FROM"
                                   " time : %s.", invalid_time)

            metric = random.choice(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=invalid_time,
                                                   interval=interval,
                                                   total_sample=total_sample)
            self.log.info("Expected response : %s", expected_response)
            self.log.info("Actual response : %s", response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid TO time.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16547')
    def test_4962(self):
        """Test that GET API returns 400 for missing mandatory params.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        epoc_time_diff = self.test_conf["test_4962"]["epoc_time_diff"]
        to_time = int(time.time())
        from_time = int(time.time() - epoc_time_diff)
        expected_response = self.test_conf["test_4962"]["expected_response"]
        expected_response = [int(tmp) for tmp in expected_response]
        metrics = self.system_stats.get_metrics()
        total_sample = int(self.test_conf["test_4962"]["total_sample"])
        interval = int(self.test_conf["test_4962"]["interval_secs"])

        # self.log.info("##### Testing with missing METRIC param  #####")
        # response = self.system_stats.get_stats(from_time=from_time,
        #                                       to_time=to_time,
        #                                       total_sample=total_sample)
        # self.log.info(f"Expected response : {expected_response}")
        # self.log.info(f"Actual response : {response.status_code}")
        # assert_utils.assert_equals(response.status_code, expected_response,
        #                 "Status code check failed with missing METRIC param.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with missing FROM param for metrics %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               to_time=to_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed with missing FROM param.")

        metric = random.choice(metrics)
        self.log.info(
            f"##### Testing with missing TO param for metric {metric} #####")
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=from_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed with missing TO param.")

        expected_response = const.SUCCESS_STATUS
        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with missing TOTAL SAMPLE AND INTERVAL param for "
            "metric %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=from_time,
                                               to_time=to_time)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed with missing TOTAL"
                                   " SAMPLE AND INTERVAL param.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with missing INTERVAL param and with TOTAL SAMPLE "
            "for metric %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=from_time,
                                               to_time=to_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed with missing "
                                   "INTERVAL param and with TOTAL SAMPLE.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with missing TOTAL SAMPLE param and with INTERVAL"
            " for metric %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=from_time,
                                               to_time=to_time,
                                               interval=interval)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed with missing TOTAL"
                                   " SAMPLE param and with INTERVA.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16548')
    def test_4963(self):
        """Test that GET API returns 400 for empty values for params from, to, metric.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        empty_val = ""
        epoc_time_diff = self.test_conf["test_4963"]["epoc_time_diff"]
        to_time = int(time.time())
        from_time = int(time.time() - epoc_time_diff)
        total_sample = int(self.test_conf["test_4963"]["total_sample"])
        expected_response = self.test_conf["test_4963"]["expected_response"]
        expected_response = [int(tmp) for tmp in expected_response]
        metrics = self.system_stats.get_metrics()
        self.log.info("##### Testing with empty METRIC param #####")
        response = self.system_stats.get_stats(metrics=[empty_val],
                                               from_time=from_time,
                                               to_time=to_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with empty FROM param for metrics %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=empty_val,
                                               to_time=to_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with empty TO param for metric %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=from_time,
                                               to_time=empty_val,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s", expected_response)
        self.log.info("Actual response : %s", response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed.")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16217')
    def test_4957(self):
        """TA CSM REST Automation: TEST-4957: Test that GET API returns 200
        as response code and appropriate json response with valid values
        for paramerter `from`, `to`, `total_sample` and `metric`
        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        total_sample = self.test_conf["test_4957"]["total_sample"]
        epoc_time_diff = self.test_conf["test_4957"]["epoc_time_diff"]
        value = self.test_conf["test_4957"]["value"]
        expected_response = const.SUCCESS_STATUS
        metrics = self.system_stats.get_metrics()
        for metric in metrics:
            self.log.info(
                "============== Checking for metrics : %s==============", metric)
            to_time = int(time.time())
            from_time = int(time.time() - epoc_time_diff)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   total_sample=total_sample)
            self.log.debug("Verifying the response:%s", response)
            assert_utils.assert_equals(response.status_code,
                                       expected_response, "Status code check failed.")
            actual_response = response.json()

            self.log.debug("Verifying the metric name:%s",
                           actual_response["metrics"][0]["name"])
            assert_utils.assert_equals(
                actual_response["metrics"][0]["name"], metric, "Metric name mismatch")
            expected_cnt = self.system_stats.expected_entry_cnt(
                to_time, from_time, total_sample=total_sample)
            self.log.info(
                "Expected number of entries : %s", expected_cnt)
            actual_cnt = len(actual_response["metrics"][0]["data"][0])
            self.log.debug("Actual number of entries : %s", actual_cnt)
            assert_utils.assert_equals(actual_cnt, expected_cnt,
                                       "Sample count check failed")
            self.log.debug("Verifying the response")
            assert_utils.assert_false(value in actual_response,
                                      "Null values in the response")
        self.log.info(
            "##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16218')
    def test_4960(self):
        """TA CSM REST Automation: TEST-4960: Test the GET API returns 200
        as response code and appropriate json response for no param interval
        and total_sample in the request
        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        epoc_time_diff = self.test_conf["test_4960"]["epoc_time_diff"]
        default_interval = self.test_conf["test_4960"]["default_interval"]
        value = self.test_conf["test_4960"]["value"]
        expected_response = const.SUCCESS_STATUS
        metrics = self.system_stats.get_metrics()
        for metric in metrics:
            self.log.info(
                "============== Checking for metrics : %s==============", metric)
            to_time = int(time.time())
            from_time = int(time.time() - epoc_time_diff)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time)
            assert_utils.assert_equals(response.status_code,
                                       expected_response, "Status code check failed.")
            actual_response = response.json()
            assert_utils.assert_equals(
                actual_response["metrics"][0]["name"], metric, "Metric name mismatch")
            expected_cnt = self.system_stats.expected_entry_cnt(
                to_time, from_time, interval=default_interval)
            self.log.info(
                "Expected number of entries : %s", expected_cnt)
            actual_cnt = len(actual_response["metrics"][0]["data"][0])
            self.log.info("Actual number of entries : %s", actual_cnt)
            assert_utils.assert_equals(actual_cnt, expected_cnt,
                                       "Sample count check failed")
            assert_utils.assert_false(value in actual_response,
                                      "Null values in the response")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="Failing due to EOS-23026")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16545')
    def test_4967(self):
        """Test that GET API returns 400 response code if value of
         `from` param is greater that value of `to` param
        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        epoc_time_diff = self.test_conf["test_4967"]["epoc_time_diff"]
        interval = self.test_conf["test_4967"]["default_interval"]
        expected_response = self.test_conf["test_4967"]["expected_response"]
        error_msg = self.test_conf["test_4967"]["error_msg"]
        metrics = self.system_stats.get_metrics()
        for metric in metrics:
            self.log.info(
                "============== Checking for metrics : %s ==============", metric)
            to_time = int(time.time())
            from_time = int(time.time() + epoc_time_diff)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   interval=interval,
                                                   from_time=from_time,
                                                   to_time=to_time)
            assert_utils.assert_equals(response.status_code,
                                       expected_response,
                                       f"Status code check failed for metric: {metric}")
            actual_response = response.json()['message']
            self.log.info(actual_response)
            assert_utils.assert_in(error_msg,
                                   actual_response, "Error message check failed")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16546')
    def test_4968(self):
        """Test that GET API returns 403 for unauthorized request of stats
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        epoc_time_diff = self.test_conf["test_4968"]["epoc_time_diff"]
        interval = self.test_conf["test_4968"]["default_interval"]
        error_msg = self.test_conf["test_4968"]["error_msg"]
        expected_response = const.FORBIDDEN
        metrics = self.system_stats.get_metrics()
        metric = random.choice(metrics)
        self.log.info("Checking for metrics : %s", metric)
        to_time = int(time.time())
        from_time = int(time.time() - epoc_time_diff)
        response = self.system_stats.get_stats(metrics=[metric],
                                               interval=interval,
                                               from_time=from_time,
                                               to_time=to_time,
                                               login_as="s3account_user")
        assert_utils.assert_equals(response.status_code,
                                   expected_response,
                                   f"Status code check failed for metric: {metric}")
        actual_response = response.text
        assert_utils.assert_in(error_msg, actual_response,
                               f"Couldnt find {error_msg} in {actual_response}")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32674')
    def test_32674(self):
        """
        Check the api response for unauthorized request for stats
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to True")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header to invalid key")
        header['Authorization1'] = header.pop('Authorization')
        self.log.info("Step 5: Call metrics with invalid key in header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed for invalid key access")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32675')
    def test_32675(self):
        """
        Check the api response for appropriate error when missing Param provided
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to True")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header for missing params")
        header[''] = header.pop('Authorization')
        header[''] = ''
        self.log.info("Step 5: Call metrics with missing params in header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32676')
    def test_32676(self):
        """
        Check the api response when telemetry_auth: 'false' and without key and value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to False")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header to delete key and value")
        del header['Authorization']
        self.log.info("Step 5: Call metrics with deleted key and value in header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32677')
    def test_32677(self):
        """
        Check the api response when telemetry_auth: 'false' and with valid key and value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to False")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Call metrics with valid header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32678')
    def test_32678(self):
        """
        Check the api response when telemetry_auth: 'false' and invalid value
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to False")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header for invalid value")
        header['Authorization'] = 'abc'
        self.log.info("Step 5: Call metrics with invalid header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32679')
    def test_32679(self):
        """
        Check the api response when telemetry_auth:'true', key=valid and value="Invalid"
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to True")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Modify header for invalid value")
        header['Authorization'] = 'abc'
        self.log.info("Step 5: Call metrics with invalid header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.UNAUTHORIZED,
                                   "Status code check failed")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32661')
    def test_32661(self):
        """
        Check all Metrics Name and data with zero values are coming (ALL Metrics)
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Change telemetry_auth to True")
        resp, pod_name = self.nd_obj.get_pod_name(pod_prefix=CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp, pod_name)
        csm_list_key_value = []
        csm_list_key = self.test_conf["csm_telemetry_auth_url"]["csm_key"]
        csm_list_value = self.test_conf["csm_telemetry_auth_url"]["csm_value"]
        csm_list_key_value.append(dict(zip(csm_list_key, csm_list_value)))
        csm_resp = self.csm_cluster.set_telemetry_auth(pod_name, csm_list_key_value,
                                                       csm_rest_api=True)
        assert_utils.assert_true(csm_resp[0], csm_resp[1])
        self.log.info("Step 2: Delete control pod and wait for restart")
        resp = self.csm_cluster.restart_control_pod(self.nd_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Get header for admin user")
        header = self.csm_user.get_headers(self.username, self.user_pass)
        self.log.info("Step 4: Call metrics with valid header")
        response = self.system_stats.get_perf_stats_custom_login(header)
        assert_utils.assert_equals(response.status_code, HTTPStatus.OK,
                                   "Status code check failed")
        self.log.info("Step 5: Check metric data with zero values")
        text = response.text()
        resp, val = self.system_stats.validate_perf_metrics(text, 0)
        assert_utils.assert_true(resp, f"Metric data validation failed: {val}")
        self.log.info("Step 6: Verified metric data with zero values")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32662')
    def test_32662(self):
        """
        Check the Metrics data are in correct format which is supported by Prometheus
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get perf metrics data")
        resp = self.system_stats.get_perf_stats()
        text = resp.text()
        self.log.info("Step-2: Check perf data compatibility with prometheus ")
        resp = self.system_stats.check_prometheus_compatibility(text)
        assert_utils.assert_true(resp, "Metric data compatibility with prometheus failed")
        self.log.info("Step 3: Verified metric data compatibility with prometheus")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32663')
    def test_32663(self):
        """
        Check the data integrity for metric "throughput_read"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32664')
    def test_32664(self):
        """
        Check the data integrity for metric "throughput_write"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32665')
    def test_32665(self):
        """
        Check the data integrity for metric "latency_create_object"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32666')
    def test_32666(self):
        """
        Check the data integrity for metric "latency_delete_object"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32667')
    def test_32667(self):
        """
        Check the data integrity for metric "latency_write_object"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32668')
    def test_32668(self):
        """
        Check the data integrity for metric "latency_read_object"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32669')
    def test_32669(self):
        """
        Check the data integrity for metric "iops_read_object"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32670')
    def test_32670(self):
        """
        Check the data integrity for metric "iops_write_object"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32671')
    def test_32671(self):
        """
        Check the data integrity for metric "iops_read_bucket"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable-msg=too-many-locals
    @pytest.mark.lc
    @pytest.mark.csmrest
    @pytest.mark.cluster_perf_stats
    @pytest.mark.tags('TEST-32673')
    def test_32673(self):
        """
        Check the data integrity for metric "iops_write_bucket"
        """
        test_case_name = cortxlogging.get_frame()
        test_dict = self.system_stats.fetch_data(test_case_name)
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Step-1: Get performance data of '%s' metric", test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        list_data_value_before_io = self.system_stats.perf_metric_name_value_compare(resp,
                                                                                     test_dict
                                                                                     ['name_metric']
                                                                                     )
        self.log.info("%s value before IO is : '%s'", test_dict['name_metric'],
                      list_data_value_before_io)
        self.log.info("Step-1: Get performance data of '%s' metric completed",
                      test_dict['name_metric'])

        self.log.info("Step-2: Running Hsbench tool and parsing data")
        for workload in test_dict['workloads']:
            resp = hsbench.hsbench(ACCESS_KEY, SECRET_KEY,
                                   obj_size=workload,
                                   test_duration=test_dict['test_time'],
                                   threads=test_dict['thread'],
                                   bucket=test_dict['bucket'],
                                   json_path=test_dict['json_path'],
                                   log_file_prefix=f"TEST-hsbench_run_{test_case_name}")
            self.log.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not hsbench.check_log_file_error(resp[1]), \
                f"Hsbench workload for object size {workload} failed. " \
                f"Please read log file {resp[1]}"
        self.log.info(" Parse Hsbench tool result from file %s", resp[0])
        data_dict = hsbench.parse_hsbench_output(resp[0])
        self.log.info(" Parse Metric value of '%s' ", test_dict['name_metric'])
        data_value_io = hsbench.parse_metrics_value(test_dict['name_metric'],
                                                    test_dict['mode_value'],
                                                    test_dict['operation_value'],
                                                    data_dict)
        self.log.info("Step-2: Running Hsbench tool and parsing data completed")

        self.log.info("Step-3: Get Performance data of '%s' metric after Hsbench tool",
                      test_dict['name_metric'])
        resp = self.system_stats.get_perf_stats()
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK, "Status code check failed")
        resp_val = self.system_stats.perf_metric_name_value_compare(resp, test_dict['name_metric'],
                                                                    comparison=True,
                                                                    compare_value=data_value_io[1])
        assert_utils.assert_true(resp_val, f"{test_dict['name_metric']} value from rest is not"
                                           " within provided Percentage range of hsbench output")
        self.log.info("##### Test ended -  %s #####", test_case_name)
