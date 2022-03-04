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
import random
import json
import pandas as pd
from config import CMN_CFG
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons import commands
from commons import constants
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class SystemCapacity(RestTestLib):
    """RestCsmUser contains all the Rest API calls for system health related
    operations"""

    def __init__(self):
        """
        """
        super().__init__()
        self.row_temp = "N{} failure"

    @RestTestLib.authenticate_and_login
    def get_capacity_usage(self):
        """Get the system capacity usage

        :return [obj]: Json response
        """
        try:
            # Building request url
            self.log.info("Reading System Capacity...")
            endpoint = self.config["capacity_endpoint"]
            self.log.info("Endpoint for reading capacity is %s", endpoint)

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

    def validate_metrics(self, data, endpoint_param='bytecount'):
        """
        Validate the parameters in rest response
        :param data: rest response data to check for parameters
        :param endpoint_param: which endpoint to check for parameters
        :return : True/False based of parameter match in data provided
        """
        keys = self.config["degraded_cap_keys"]
        for key in keys[0]:
            try:
                _ = data['bytecount'][key]
            except KeyError:
                return False
        if endpoint_param != 'bytecount':
            for key in keys[1]:
                try:
                    _ = data['filesystem'][key]
                except KeyError:
                    return False
        return True

    @RestTestLib.authenticate_and_login
    def get_degraded_capacity(self, endpoint_param='bytecount'):
        """
        Get degraded capacity from CSM
        :param endpoint_param: which endpoint to check for parameters
        :return : Rest output response
        """
        self.log.info("Reading System Capacity...")
        endpoint = self.config["degraded_cap_complete_endpoint"]
        if endpoint_param == 'bytecount':
            endpoint = self.config["degraded_cap_endpoint"]
        self.log.info("Endpoint for reading capacity is %s", endpoint)
        # Fetching api response
        response = self.restapi.rest_call(request_type="get", endpoint=endpoint,
                                          headers=self.headers)
        return response

    def get_degraded_capacity_custom_login(self, header, endpoint_param='bytecount'):
        """
        Get degraded capacity from CSM
        :param header: header for authentication
        :param endpoint_param: which endpoint to check for parameters
        :return : Rest output response
        """
        self.log.info("Reading System Capacity...")
        endpoint = self.config["degraded_cap_complete_endpoint"]
        if endpoint_param == 'bytecount':
            endpoint = self.config["degraded_cap_endpoint"]
        self.log.info("Endpoint for reading capacity is %s", endpoint)
        # Fetching api response
        response = self.restapi.rest_call(request_type="get", endpoint=endpoint,
                                          headers=header)
        return response

    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-locals
    def verify_degraded_capacity(
            self, resp: dict, healthy=None, degraded=None, critical=None, damaged=None,
            repaired=None, err_margin: int = 0, total: int = None):
        """
        Verify the degraded capacity parameter are within the error margin specified.
        :param resp: response of the csm/hctl/consul
        :param healthy: expected healthy byte count
        :param degraded: expected degraded byte count
        :param critical: expected critical byte count
        :param damaged: expected damaged byte count
        :param repaired: expected repaired byte count
        :param err_margin: margin of error for expected values.
        :param total: expected total of all params healthy, degraded...
        TODO: Dummy function as degraded capacity csm specs is not defined yet.
        resp is dict
        """
        checklist = []
        if healthy is not None:
            checklist.append("healthy")
        if degraded is not None:
            checklist.append("degraded")
        if critical is not None:
            checklist.append("critical")
        if damaged is not None:
            checklist.append("damaged")
        if repaired is not None:
            checklist.append("repaired")
        result_flag = True
        result_msg = ""

        if total is not None:
            self.log.info("Expected total bytes : %s", total)
            self.log.info("Actual total bytes : %s", sum(resp.values()))
            result_flag = sum(resp.values()) == total
            result_msg = "Summation check failed."

        for chk in checklist:
            # pylint: disable=eval-used
            expected = eval(chk)
            actual = resp[chk]
            self.log.info("Expected %s byte count within error margin %s bytes of : %s"
                          "bytes", chk, err_margin, expected)
            self.log.info("Actual healthy byte count : %s", actual)
            flag = expected - err_margin <= actual <= expected + err_margin
            if flag:
                msg = f"{chk} byte count check passed.\n"
                self.log.info(msg)
            else:
                msg = f"{chk} byte count check failed.\n"
                self.log.error(msg)
            result_msg = result_msg + msg
            result_flag = result_flag and flag
            return result_flag, result_msg

    def get_capacity_consul(self, node=0):
        """
        Reads the capacity from consul
        """
        self.log.info("Reading capacity from consul from node : %s", node)
        node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                               username=CMN_CFG["nodes"][node]["username"],
                               password=CMN_CFG["nodes"][node]["password"])
        data_pods = node_obj.get_all_pods_and_ips("data")
        self.log.debug("Data pods on the setup: %s", data_pods)
        data_pod = random.choice(list(data_pods.keys()))
        self.log.info("Reading the stats from data pod : %s , Container: %s", data_pod,
                      constants.HAX_CONTAINER_NAME)
        cmd_suffix = f"-c {constants.HAX_CONTAINER_NAME} -- {commands.GET_BYTECOUNT}"
        resp = node_obj.send_k8s_cmd(operation="exec", pod=data_pod, namespace=constants.NAMESPACE,
                                     command_suffix=cmd_suffix,
                                     decode=True)
        self.log.info("Response : %s", resp)
        resp = "{\"" + resp.replace("bytecount/","").replace("\n" , ",\"").replace(":", "\":")+"}"
        self.log.info("Parsed response : %s", resp)
        return json.loads(resp)

    def get_dataframe_all(self, num_nodes: int):
        """
        Creates dataframe for the storing degraded capacity for csm, hctl, consul
        """
        col = ["consul_healthy", "consul_degraded", "consul_critical", "consul_damaged",
               "consul_repaired", "hctl_healthy", "hctl_degraded", "hctl_critical", "hctl_damaged",
               "hctl_repaired", "csm_healthy", "csm_degraded", "csm_critical", "csm_damaged",
               "csm_repaired"]
        row = ["No failure"]
        for node in range(1, num_nodes+1):
            row.append(self.row_temp.format(node))
        cap_df = pd.DataFrame(columns=col, index=row)
        return cap_df

    def verify_degraded_capacity_all(self, cap_df, num_nodes: int, data_written: int = 0):
        """
        Verify the consistency of degraded, healthy.. bytes for csm, consul, hctl in data frame
        """
        self.log.info(
            "Checking HCTL , CSM and Consul healthy byte response are consistent.")
        cap_df['result'] = ((cap_df['consul_healthy'] == cap_df['hctl_healthy']) &
                            (cap_df['consul_healthy'] == cap_df['csm_healthy']))
        healthy_eq = cap_df["result"].all()

        self.log.info(
            "Checking HCTL , CSM and Consul degraded byte response are consistent.")
        cap_df['result'] = ((cap_df['consul_degraded'] == cap_df['hctl_degraded']) &
                            (cap_df['consul_degraded'] == cap_df['csm_degraded']))
        degraded_eq = cap_df["result"].all()

        self.log.info(
            "Checking HCTL , CSM and Consul Critical byte response are consistent.")
        cap_df['result'] = ((cap_df['consul_critical'] == cap_df['hctl_critical']) &
                            (cap_df['consul_critical'] == cap_df['csm_critical']))
        critical_eq = cap_df["result"].all()

        self.log.info(
            "Checking HCTL , CSM and Consul damaged byte response are consistent.")
        cap_df['result'] = ((cap_df['consul_damaged'] == cap_df['hctl_damaged']) &
                            (cap_df['consul_damaged'] == cap_df['csm_damaged']))
        damaged_eq = cap_df["result"].all()

        self.log.info(
            "Checking HCTL , CSM and Consul repaired byte response are consistent.")
        cap_df['result'] = ((cap_df['consul_repaired'] == cap_df['hctl_repaired']) &
                            (cap_df['consul_repaired'] == cap_df['csm_repaired']))
        repaired_eq = cap_df["result"].all()

        self.log.info("Checking total bytes adds up to data written")
        cap_df["csm_sum"] = cap_df["csm_healthy"] + cap_df["csm_degraded"] + \
            cap_df["csm_critical"] + \
            cap_df["csm_damaged"] + cap_df["csm_repaired"]
        cap_df["total_check"] = data_written == cap_df["csm_sum"]
        total_chk = cap_df["total_check"].all()
        self.log.info(
            "Summation check of the healthy bytes from each node failure for csm")

        actual_written = 0
        for node in range(1, num_nodes+1):
            node_name = self.row_temp.format(node)
            actual_written = actual_written + cap_df.loc[node_name]["csm_healthy"]

        data_written_hchk = data_written == actual_written

        actual_written = 0
        for node in range(1, num_nodes+1):
            node_name = self.row_temp.format(node)
            actual_written = actual_written + cap_df.loc[node_name]["csm_damaged"]

        self.log.info(
            "Summation check of the damaged bytes from each node failure for csm")
        data_written_dchk = data_written == actual_written

        result = (data_written_hchk and data_written_dchk and healthy_eq and degraded_eq and
                  critical_eq and damaged_eq and repaired_eq and total_chk)
        return result
