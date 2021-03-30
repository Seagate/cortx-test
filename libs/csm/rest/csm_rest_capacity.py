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
"""Test library for capacity related operations.
   Author: Divya Kachhwaha
"""
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class SystemCapacity(RestTestLib):
    """RestCsmUser contains all the Rest API calls for system health related
    operations"""

    @RestTestLib.authenticate_and_login
    def get_capacity_usage(self):
        """Get the system capacity usage

        :return [obj]: Json response
        """
        try:
            # Building request url
            self.log.info("Reading System Capacity...")
            endpoint = self.config["capacity_endpoint"]
            self.log.info(
                "Endpoint for reading capacity is {}".format(endpoint))

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "CSM REST response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                SystemCapacity.get_capacity_usage.__name__,
                error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def parse_capacity_usage(self, expected_response=const.SUCCESS_STATUS):
        """Parse the Json response to extract used, available and total capacity

        :param expected_response: expected status code
        :return [tuple]: tuple of total_cap, avail_cap, used_cap, used_percent, cap_unit
        """
        response = self.get_capacity_usage()
        if response.status_code == expected_response:
            self.log.info("Expected response check Passed.")
        else:
            self.log.error("Expected response check Failed.")
            return False

        response_json = response.json()
        total_cap = response_json['size']
        avail_cap = response_json['avail']
        used_cap = response_json['used']
        used_percent = response_json['usage_percentage']
        cap_unit = response_json['unit']
        return total_cap, avail_cap, used_cap, used_percent, cap_unit
