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
"""Test library for capacity related operations.
   Author: Divya Kachhwaha
"""
from http import HTTPStatus
from random import SystemRandom
import json
from config import CMN_CFG
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.helpers.pods_helper import LogicalNode
from commons import commands
from commons import constants
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.s3 import s3_misc


class SystemCapacity(RestTestLib):
    """RestCsmUser contains all the Rest API calls for system health related
    operations"""

    def __init__(self):
        """
        """
        super(SystemCapacity, self).__init__()
        self.row_temp = "N{} failure"
        self.cryptogen = SystemRandom()

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
        endpoint = self.config["degraded_cap_endpoint"]
        if endpoint_param is not None:
            endpoint = self.config["degraded_cap_endpoint"] + "/" + endpoint_param
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
        endpoint = self.config["degraded_cap_endpoint"]
        if endpoint_param is not None:
            endpoint = self.config["degraded_cap_endpoint"] + "/" + endpoint_param
        self.log.info("Endpoint for reading capacity is %s", endpoint)
        # Fetching api response
        response = self.restapi.rest_call(request_type="get", endpoint=endpoint,
                                          headers=header)
        return response

    # pylint: disable=eval-used
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
        if err_margin >= 100:
            err_margin -= 0.01
        result_flag = True
        result_msg = ""

        if total is not None:
            self.log.info("Min Expected total bytes : %s", total)
            total_err = total/(1-err_margin/100)
            self.log.info("Max Expected total bytes : %s", total_err)
            self.log.info("Actual total bytes : %s", sum(resp.values()))
            result_flag = total <= sum(resp.values()) <= total_err
            if result_flag:
                result_msg = "Summation check Passed."
            else:
                result_msg = "Summation check failed."

        for chk in checklist:
            expected = eval(chk) # nosec
            actual = float(resp[chk])
            self.log.info("Actual %s byte count : %s", chk, actual)
            expected_err = expected/(1-err_margin/100)
            self.log.info("Error margin : %s percent", err_margin)
            self.log.info("Min Expected %s byte count : %s", chk, expected)
            self.log.info("Max Expected %s byte count : %s", chk, expected_err)
            flag = expected <= actual <= expected_err
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
        data_pod = self.cryptogen.choice(list(data_pods.keys()))
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

    def get_degraded_all(self, master_obj):
        """
        Fetech degraded byte count from HCTL, Consul, CSM and verify data is consistent across
        """
        self.log.info("[Start] Fetch degraded capacity on Consul")
        consul_op = self.get_capacity_consul()
        self.log.info("[End] Fetch degraded capacity on Consul")

        self.log.info("[Start] Fetch degraded capacity on HCTL")
        hctl_op = master_obj.hctl_status_json()["bytecount"]
        self.log.info("[End] Fetch degraded capacity on HCTL")

        self.log.info("[Start] Fetch degraded capacity on CSM")
        resp = self.get_degraded_capacity()
        assert resp.status_code == HTTPStatus.OK.value, "Status code check failed."
        resp = resp.json()["bytecount"]
        self.log.info("[End] Fetch degraded capacity on CSM")

        assert hctl_op["healthy"] == consul_op["healthy"], "HCTL & Consul healthy byte mismatch"
        assert hctl_op["degraded"] == consul_op["degraded"], "HCTL & Consul degraded byte mismatch"
        assert hctl_op["critical"] == consul_op["critical"], "HCTL & Consul critical byte mismatch"
        assert hctl_op["damaged"] == consul_op["damaged"], "HCTL & Consul healthy byte mismatch"
        assert resp["healthy"] == consul_op["healthy"], "CSM & Consul healthy byte mismatch"
        assert resp["degraded"] == consul_op["degraded"], "CSM & Consul degraded byte mismatch"
        assert resp["critical"] == consul_op["critical"], "CSM & Consul critical byte mismatch"
        assert resp["damaged"] == consul_op["damaged"], "CSM & Consul healthy byte mismatch"
        return hctl_op

    def verify_bytecount_all(self, resp, failure_cnt, kvalue, err_margin,
                             total_written,new_write=0):
        """
        Verify degraded, critical, damaged bytecount in the resp.
        """
        if failure_cnt == 0:
            self.log.info("Checking for %s greater than to K value", failure_cnt)
            result = self.verify_degraded_capacity(resp, healthy=total_written,
            degraded=0, critical=0, damaged=0, err_margin=err_margin,
            total=total_written)
        elif failure_cnt < kvalue:
            self.log.info("Checking for %s greater than to K value", failure_cnt)
            result = self.verify_degraded_capacity(resp, healthy=new_write,
            degraded=total_written-new_write, critical=0, damaged=0, err_margin=err_margin,
            total=total_written)
        elif failure_cnt == kvalue:
            self.log.info("Checking for %s greater than to K value", failure_cnt)
            result = self.verify_degraded_capacity(resp, healthy=new_write,
            degraded=0, critical=total_written-new_write, damaged=0, err_margin=err_margin,
            total=total_written)
        else:
            self.log.info("Checking for %s less than to K value", failure_cnt)
            result = self.verify_degraded_capacity(resp, healthy=new_write,
            degraded=0, critical=0, damaged=total_written-new_write, err_margin=err_margin,
            total=total_written)
        return result

    def append_df(self, cap_df, failed_pod, data_written, obj = "NA", bucket = "NA", akey ="NA",
                  skey="NA"):
        """Append the value to the data frame created in the test
        """
        if obj == "NA":
            csum = 0
        else:
            csum = s3_misc.get_object_checksum(obj, bucket, akey, skey)
        new_row = {"data_written":data_written,
                    "csum": csum,
                    "obj": obj,
                    "bucket": bucket,
                    "akey": akey,
                    "skey": skey}
        deploy_list = list(cap_df.columns)
        if "data_written" in deploy_list:
            deploy_list.remove("data_written")
        if "csum" in deploy_list:
            deploy_list.remove("csum")
        if "obj" in deploy_list:
            deploy_list.remove("obj")
        if "akey" in deploy_list:
            deploy_list.remove("akey")
        if "skey" in deploy_list:
            deploy_list.remove("skey")
        if "bucket" in deploy_list:
            deploy_list.remove("bucket")
        for deploy in deploy_list:
            new_row[deploy] = not deploy in failed_pod
        cap_df = cap_df.append(new_row, ignore_index=True)
        self.log.info("%s", cap_df.to_string())
        return cap_df

    # pylint: disable=too-many-branches
    def verify_flexi_protection(self, resp, cap_df, failed_pod:list, kvalue:int, err_margin:int):
        """Check byte count based on flexible protection
        """
        healthy=0
        degraded=0
        critical=0
        damaged=0
        host_list = cap_df.columns.values.tolist()
        if "data_written" in host_list:
            host_list.remove("data_written")
        if "csum" in host_list:
            host_list.remove("csum")
        if "obj" in host_list:
            host_list.remove("obj")
        if "akey" in host_list:
            host_list.remove("akey")
        if "skey" in host_list:
            host_list.remove("skey")
        if "bucket" in host_list:
            host_list.remove("bucket")
        for row in cap_df.index:
            written_on = []
            for node in host_list:
                if cap_df[node][row]:
                    written_on.append(node)
            corrupt_shards = len(set(written_on) & set(failed_pod))
            if corrupt_shards == 0:
                self.log.debug("Checking for %s less than to K value", corrupt_shards)
                healthy += cap_df["data_written"][row]
            elif corrupt_shards < kvalue:
                self.log.debug("Checking for %s greater than to K value", corrupt_shards)
                degraded += cap_df["data_written"][row]
            elif corrupt_shards == kvalue:
                self.log.debug("Checking for %s greater than to K value", corrupt_shards)
                critical += cap_df["data_written"][row]
            else:
                self.log.debug("Checking for %s less than to K value", corrupt_shards)
                damaged += cap_df["data_written"][row]

        total_written = healthy + degraded + critical + damaged
        result = self.verify_degraded_capacity(resp, healthy=healthy,
        degraded=degraded, critical=critical, damaged=damaged, err_margin=err_margin,
        total=total_written)
        return result

    def verify_checksum(self, cap_df):
        """Verify checksum of all the data with dataframe
        """
        checksum_match = True
        for row in cap_df.index:
            obj = cap_df["obj"][row]
            if obj != "NA":
                bucket = cap_df["bucket"][row]
                akey = cap_df["akey"][row]
                skey = cap_df["skey"][row]
                expected_csum = cap_df["csum"][row]
                actual_csm = s3_misc.get_object_checksum(obj, bucket, akey, skey)
                checksum_match = checksum_match and (expected_csum == actual_csm)
                if checksum_match:
                    self.log.info("Check for %s object in %s bucket correct.", obj, bucket)
                else:
                    self.log.error("Check for %s object in %s bucket incorrect.", obj, bucket)
        return checksum_match
