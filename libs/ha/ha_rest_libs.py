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

"""
REST API Health Response Library
"""
import logging
import commons.errorcodes as err
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from commons.exceptions import CTException
from commons.constants import Rest as Restconst

LOGGER = logging.getLogger(__name__)


class HaRestLibs(RestTestLib):
    """This class contains utility methods for all the provisioning related operations"""

    @RestTestLib.authenticate_and_login
    def get_health_status(self, resource: str, parameters: dict = None):
        """
        This method will show csm audit logs
        :param parameters: filter the node status response with specific param values
        :param resource: endpoint parameters for rest call
        :return: show health status rest call response
        """
        try:
            # Building request url to get Node Health status
            LOGGER.info("Reading health of %s ...", resource)
            endpoint = self.config["health_resource_endpoint"]
            LOGGER.info(
                "Endpoint for reading capacity is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(
                request_type="get",
                endpoint=endpoint,
                headers=self.headers,
                params=parameters,
                save_json=True)
            LOGGER.info(
                "Response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            LOGGER.error("%s %s: %s",
                         Restconst.EXCEPTION_ERROR,
                         HaRestLibs.get_health_status.__name__,
                         error)
            raise CTException(
                err.CSM_REST_GET_REQUEST_FAILED, error) from error

    def get_node_health_status(
            self,
            exp_key: str = None,
            exp_val=None,
            res_key: str = None,
            res_val=None,
            node_id: int = None):
        """
        This method will get and verify status of node
        :param exp_val: Expected value from get node health
        :param exp_key: Expected value key from get node health
        :param res_key: Resource key to be get as parameter
        :param res_val: Resource value to be get as parameter
        :param node_id: NodeID for which data to be fetched
        :return: bool, Response Message
        """
        param = None
        if res_key:
            param = dict()
            param[f"{res_key}"] = res_val
        node_resp = self.get_health_status(resource="node", parameters=param)
        if node_id:
            node_dict = node_resp.json()["data"][node_id]
            if node_dict[f"{exp_key}"] == exp_val.lower():
                LOGGER.info('Node "%s" "%s" \nActual: "%s" \nExpected: "%s"',
                            node_id, exp_key, node_dict[f"{exp_key}"], exp_val)
                return True, f'Node "{node_id}" "{exp_key}" is "{exp_val}"'
            LOGGER.info('Node "%s" "%s" \nActual: "%s" \nExpected: "%s"',
                        node_id, exp_key, node_dict[f"{exp_key}"], exp_val)
            return False, f'Node "{node_id}" expected "{exp_key}" is not "{exp_val}"'
        else:
            for node_dict in node_resp.json()["data"]:
                if node_dict[f"{exp_key}"] == exp_val.lower():
                    LOGGER.info('Node "%s" "%s" \nActual: "%s" \nExpected: "%s"',
                        node_dict["id"], exp_key, node_dict[f"{exp_key}"], exp_val)
                else:
                    LOGGER.info('Node "%s" "%s" \nActual: "%s" \nExpected: "%s"',
                        node_dict["id"], exp_key, node_dict[f"{exp_key}"], exp_val)
                    return False, f'Node "{node_dict["id"]}" expected "{exp_key}" is not "{exp_val}"'
                return True, f"All nodes are {exp_val}"

    @staticmethod
    def verify_node_health_status(
            response: list,
            status: str,
            node_id: int = None):
        """
        This method will get number of node
        :param response: List Response for health status command
        :param status: Expected status value for node
        :param node_id: Expected status value for specific node_id
        :return: bool, Response Message
        """
        if not node_id:
            for item in response:
                if item[2] != status:
                    return False, f"Node {item[1 + 1]} status is {item[2]}"
            return True, f"All node status are {status}"
        return status == response[node_id][2], f"Node {node_id} is {response[node_id][2]}"
