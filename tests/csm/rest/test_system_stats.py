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
"""Tests system statistics using REST API
"""
import time
import random
import logging
import pytest
from libs.csm.rest.csm_rest_stats import SystemStats
from commons.utils import config_utils
from commons.utils import assert_utils
from commons import cortxlogging


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
        cls.test_conf = config_utils.read_yaml(
            "config/csm/test_rest_system_stats.yaml")[1]

    @pytest.mark.csmrest
    @pytest.mark.tags('TEST-14752')
    def test_4956(self):
        """Test that GET API returns 200 response code
        and appropriate json response for metric stats
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started - %s #####" , test_case_name)
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

    @pytest.mark.csmrest
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
            self.log.info("Expected response : %s",expected_response)
            self.log.info("Actual response : %s",response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid METRICS.")

        self.log.info("##### Testing with invalid TOTAL SAMPLEs param  #####")
        invalid_samples = self.test_conf["test_4961"]["invalid_samples"]
        for invalid_sample in invalid_samples:
            metric = random.choice(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=interval,
                                                   total_sample=invalid_sample)
            self.log.info("Expected response : %s",expected_response)
            self.log.info("Actual response : %s",response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid TOTAL samples.")

        self.log.info("##### Testing with invalid INTERVALs param  #####")
        invalid_intervals = self.test_conf["test_4961"]["invalid_intervals"]
        for invalid_interval in invalid_intervals:
            metric = random.choice(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=to_time,
                                                   interval=invalid_interval,
                                                   total_sample=total_sample)
            self.log.info("Expected response : %s",expected_response)
            self.log.info("Actual response : %s",response.status_code)
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
            self.log.info("Expected response : %s",expected_response)
            self.log.info("Actual response : %s",response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   f"Status code check failed with invalid FROM"
                                   " time :{invalid_time}.")

            metric = random.choice(metrics)
            response = self.system_stats.get_stats(metrics=[metric],
                                                   from_time=from_time,
                                                   to_time=invalid_time,
                                                   interval=interval,
                                                   total_sample=total_sample)
            self.log.info("Expected response : %s",expected_response)
            self.log.info("Actual response : %s",response.status_code)
            assert_utils.assert_in(response.status_code, expected_response,
                                   "Status code check failed with invalid TO time.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
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
        #self.log.info(f"Expected response : {expected_response}")
        #self.log.info(f"Actual response : {response.status_code}")
        # assert_utils.assert_equals(response.status_code, expected_response,
        #                 "Status code check failed with missing METRIC param.")

        metric = random.choice(metrics)
        self.log.info(
            f"##### Testing with missing FROM param for metrics {metric} #####")
        response = self.system_stats.get_stats(metrics=[metric],
                                               to_time=to_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
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
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
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
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
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
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed with missing TOTAL"
                                   " SAMPLE param and with INTERVA.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
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
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with empty FROM param for metrics %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=empty_val,
                                               to_time=to_time,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed.")

        metric = random.choice(metrics)
        self.log.info(
            "##### Testing with empty TO param for metric %s #####", metric)
        response = self.system_stats.get_stats(metrics=[metric],
                                               from_time=from_time,
                                               to_time=empty_val,
                                               total_sample=total_sample)
        self.log.info("Expected response : %s",expected_response)
        self.log.info("Actual response : %s",response.status_code)
        assert_utils.assert_in(response.status_code, expected_response,
                               "Status code check failed.")

    @pytest.mark.tags('EOS-12359')
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

    @pytest.mark.csmrest
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
    @pytest.mark.tags('TEST-16546')
    def test_4968(self):
        """Test that GET API returns 403 for unauthorized request of stats
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        epoc_time_diff = self.test_conf["test_4968"]["epoc_time_diff"]
        interval = self.test_conf["test_4968"]["default_interval"]
        error_msg = self.test_conf["test_4968"]["error_msg"]
        expected_response = self.system_stats.forbidden
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
