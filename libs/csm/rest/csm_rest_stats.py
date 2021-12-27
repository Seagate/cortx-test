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
"""Test library for System Stats related operations.
   Author: Divya Kachhwaha
"""
import datetime
import math

import dateutil.relativedelta
from prometheus_client.parser import text_string_to_metric_families

import commons.errorcodes as err
from commons.constants import Rest as const
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class SystemStats(RestTestLib):
    """SystemStats contains all the Rest API calls for reading system stats"""

    @RestTestLib.authenticate_and_login
    def get_stats(self, stats_id=None, panel=None, metrics=None,
                  from_time=None, to_time=None, interval=None,
                  total_sample=None, op_format=None):
        """Get the status of the given Metric

        :param str stats_id: Stat ID
        :param str panel: Panel
        :param str metrics: Stat metric
        :param int from_time: From time for the requested stats
        :param int to_time: to time for the requested stats
        :param int interval: Interval between the stats data points
        :param int total_sample: Number of the samples of the stats data points
        :param str op_format: output format
        :return [obj]: response
        """
        try:
            # Building request url
            self.log.info("Reading stats...")
            endpoint = self.config["stats_endpoint"]
            # Adding parameters
            endpoint = self._add_parameters(endpoint, stats_id, panel,
                                            metrics, from_time, to_time,
                                            interval, total_sample, op_format)
            self.log.info("Endpoint for reading stats is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           SystemStats.get_stats.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def verify_list(self, expected_list, actual_list):
        """Verifies if the given list is the sub set of the actual list

        :param list expected_list: expected list -subset
        :param list actual_list: actual list - main list
        :return [bool]: True if it is subset else False
        """
        self.log.info("Expected List : %s", expected_list)
        self.log.info("Actual List : %s", actual_list)
        return all(x in actual_list for x in expected_list)

    def get_time_diff(self, to_time, from_time):
        """Time calculation for response

        :param int to_time: to time for stats
        :param int from_time: from time for stats
        :return obj: datetime diff object
        """
        self.log.info("To Time : %s", to_time)
        self.log.info("From Time : %s", from_time)
        to_time = datetime.datetime.fromtimestamp(to_time)
        from_time = datetime.datetime.fromtimestamp(from_time)
        rdd = dateutil.relativedelta.relativedelta(to_time, from_time)
        rdd.months = rdd.months + rdd.years * 12
        rdd.days = rdd.days + rdd.months * 30
        rdd.hours = rdd.hours + rdd.days * 12
        rdd.minutes = rdd.minutes + rdd.hours * 60
        rdd.seconds = rdd.seconds + rdd.minutes * 60
        return rdd

    def expected_entry_cnt(self, to_time, from_time, interval=None,
                           total_sample=None):
        """Finds the expected entries.
        NOTE: Interval or total_sample is required.

        :param int to_time: to time of stats
        :param int from_time: from time of stats
        :param int interval: interval for stats
        :param int total_sample: total sample for stats
        :return int: count of expected entried
        """
        rdd = self.get_time_diff(to_time, from_time)
        diff_sec = rdd.seconds
        self.log.info("Time difference in seconds : %s", total_sample)
        if total_sample is not None:
            samples = total_sample
            self.log.info("Expected total samples : %s", total_sample)
        else:
            if interval is not None:
                samples = math.ceil(diff_sec / interval)
                self.log.info(
                    "Requires Interval or total Sample : %s", samples)
            else:
                samples = None
                self.log.error("Interval and total sample both were None")
        return samples

    def _add_parameters(self, endpoint, stats_id=None, panel=None,
                        metrics=False, from_time=None, to_time=None,
                        interval=None, total_sample=None, op_format=None):
        """Add parameters to the endpoint

        :param str endpoint: Given endpoints
        :param str stats_id: adds given stat id to endpoint
        :param str panel: adds given panel to endpoint
        :param str metrics: adds metrics to endpoint
        :param int from_time: add from time to the endpoint
        :param int to_time: adds to time  to endpoint
        :param int interval: adds interval to endpoint
        :param int total_sample: adds total sample to endpoint
        :param str op_format: adds output format to endpoint
        :return [str]: modified endpoint
        """
        if stats_id is not None:
            endpoint = "{}/{}".format(endpoint, stats_id)

        params = []
        if panel is not None:
            params.append("panel=%s" % str(panel).lower())
        if from_time is not None:
            params.append("from=%s" % str(from_time).lower())
        if to_time is not None:
            params.append("to=%s" % to_time)
        if interval is not None:
            params.append("interval=%s" % interval)
        if total_sample is not None:
            params.append("total_sample=%s" % total_sample)
        if op_format is not None:
            params.append("op_format=%s" % op_format)
        if metrics is not None:
            for metric in metrics:
                params.append("metric=%s" % str(metric).lower())

        first_ele_flag = False
        for param in params:
            if param is not None:
                if not first_ele_flag:
                    endpoint = "{}?".format(endpoint)
                    first_ele_flag = True
                else:
                    endpoint = "{}&".format(endpoint)
                endpoint = "{}{}".format(endpoint, param)
        self.log.info("Endpoint : %s", endpoint)
        return endpoint

    @RestTestLib.authenticate_and_login
    def get_metrics(self):
        """Read the metric list

        :return [list]: metric list
        """
        try:
            self.log.info("Reading the stats...")
            response = self.get_stats()
            response_json = response.json()
            metric_list = response_json["metric_list"]
            self.log.info("Metric list read is : %s", metric_list)
            return metric_list

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           SystemStats.get_metrics.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def get_perf_stats(self):
        """
        Read the metric list
        :return [list]: metric list
        """
        try:
            # Building request url
            self.log.info("Reading perf stats...")
            endpoint = self.config["perf_stats_endpoint"]
            self.log.info("Endpoint for reading stats is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            return response
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           SystemStats.get_perf_stats.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def get_perf_stats_custom_login(self, header):
        """
        Read the metric list
        :param str header: Header for authentication
        :return [list]: metric list
        """
        try:
            # Building request url
            self.log.info("Reading perf stats...")
            endpoint = self.config["perf_stats_endpoint"]
            self.log.info("Endpoint for reading stats is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=header)
            return response
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           SystemStats.get_perf_stats.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def validate_perf_metrics(self, text, value=None):
        """
        Validate perf metrics rest api output for all metrics names and value
        :param str text: metrics text format output of rest call
        :param int value: Value which should be expected from rest call
        :return True/False: If all metrics are present in text param with provided value
        """
        self.log.info("Validating perf metrics")
        expected_values = const.PERF_STAT_METRICS
        family = list(text_string_to_metric_families(text))
        for item in family:
            items = item.samples
            for sample in items:
                sample_value = sample.value
                sample_name = sample.name
                value_matched = True
                if value and value != sample_value:
                    value_matched = False
                if sample_name in expected_values and value_matched:
                    expected_values.remove(sample_name)
                else:
                    return False, sample_name
        return len(expected_values) == 0, expected_values

    def check_prometheus_compatibility(self, text):
        """
        Check format of text with prometheus format by using parsing method
        :param str text: metrics text format output of rest call
        :return True/False: If metrics text format is as per prometheus format
        """
        self.log.info("Validating perf metrics format with prometheus format")
        try:
            for family in text_string_to_metric_families(text):
                for sample in family.samples:
                    self.log.info("Name: {0} Labels: {1} Value: {2}".format(*sample))
            return True
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           SystemStats.check_prometheus_compatibility.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def perf_metric_name_value_compare(self, text, metric_name,
                                       comparison=False, compare_value=None):
        """Read the metric_name, compare/no_compare the value

        :return True/False: (comparision=True) If metrics name value is 10 percent comparable to \
                            provided value  OR
                value : (comparision=False) Performace metric name average value
        """
        try:
            self.log.info("Reading the '%s' stats...", metric_name)
            metric_value_list = []
            for family in text_string_to_metric_families(text):
                for sample in family.samples:
                    res = f"Name={sample[0]}\nLabels={sample[1]}\n Value={sample[2]}"
                    out = dict(item.split("=") for item in res.split("\n"))
                    if out['Name'] == metric_name:
                        metric_value_list.append(float(out[' Value']))
            self.log.info("Metric value list for '%s' is : %s", metric_name, metric_value_list)
            if len(metric_value_list) != 0:
                data_value = sum(metric_value_list)/len(metric_value_list)
                self.log.info("Average Value for '%s' is : %s", metric_name, data_value)
            if comparison and compare_value is not None:
                self.log.info("Comparing the values..")
                return bool((compare_value + (compare_value * 0.1) >= data_value) or \
                (compare_value - (compare_value * 0.1) <= data_value))

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           SystemStats.perf_metric_name_value_compare.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error
        return data_value
