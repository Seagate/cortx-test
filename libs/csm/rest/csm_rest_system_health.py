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
"""Test library for System Health related operations.
   Author: Divya Kachhwaha
"""
import json
import time
from http import HTTPStatus
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.utils import config_utils
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from config import CMN_CFG

class SystemHealth(RestTestLib):
    """RestCsmUser contains all the Rest API calls for system health related
    operations"""

    def __init__(self):
        """
        Initialize the rest api
        """
        super(SystemHealth, self).__init__()
        self.main_conf = config_utils.read_yaml(
            "config\\common_config.yaml")[1]

    @RestTestLib.authenticate_and_login
    def get_health_summary(self):
        """
        Get the health summary.
        """
        try:
            # Building request url
            self.log.info("Reading health summary...")
            endpoint = self.config["health_summary_endpoint"]
            self.log.info(
                "Endpoint for health summary is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.get_health_summary.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def verify_health_summary(self, expected_response, verify_schema=True):
        """
        Verify the health Summary
        :param expected_response: expected response status code
        :param verify_schema: Schema for verification of the response strings,
        defaults to True
        :return: True (Success) / False (Failure)
        """
        try:
            result = False
            # Get Health Summary
            response = self.get_health_summary()
            self.log.info("Verifying health summary status code...")
            self.log.info(
                "Expected status code: %s", expected_response)
            self.log.info("Actual status code: %s",
                           response.status_code)
            if response.status_code == expected_response:
                self.log.info("Status code verification passed !")
                if verify_schema:
                    self.log.info("Verifying health summary schema...")
                    self.log.info("Expected status code: %s",
                                   const.HEALTH_SUMMARY_SCHEMA)
                    self.log.info("Actual status code: %s",
                                   response.json()[const.HEALTH_SUMMARY_INSTANCE])
                    config_utils.verify_json_schema(
                        response.json()[const.HEALTH_SUMMARY_INSTANCE], const.HEALTH_SUMMARY_SCHEMA)
                    self.log.info("Status code verification passed !")
                result = True
            else:
                self.log.info("Status code verification failed !")

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.verify_health_summary.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error
        self.log.info(
            "Verification result of health summary : %s", result)
        return result

    @RestTestLib.authenticate_and_login
    def get_health_node(self, node):
        """
        Get the node health.
        :param node: node alias from "storage", "node-1", "node-2", ""
        :return: response object
        """
        try:
            # Building request url
            self.log.info("Reading node %s health...", node)
            endpoint = self.config["health_node_endpoint"]

            # Adding parameters(if any) to endpoint
            endpoint = self._append_node_id_param(endpoint, node)
            self.log.info("Endpoint to node health is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "Response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.get_health_node.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def verify_health_node(self, expected_response, node, verify_schema=True):
        """
        Get the node health and verify the output
        :param expected_response: expected status code
        :param node: node alias from "storage", "node-1", "node-2", "", "all"
        :param verify_schema: schema for verification
        :return :True (Success) / False (Failure)
        """
        try:
            result = False
            # Get Health Summary
            response = self.get_health_component(node)
            self.log.info("Verifying health node status code...")
            self.log.info(
                "Expected status code: %s", expected_response)
            self.log.info("Actual status code: %s",
                           response.status_code)
            if response.status_code == expected_response:
                self.log.info("Status code verification passed !")
                if verify_schema:
                    self.log.info("Verifying health node schema...")
                    result = self._verify_response(node, response)
                else:
                    result = True
            else:
                self.log.info("Status code verification failed !")

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.verify_health_node.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error
        self.log.info(
            "Verification result of health node : %s", result)
        return result

    @RestTestLib.authenticate_and_login
    def get_health_view(self, node):
        """
        Get health view of the system.
        :param node: node alias "storage", "node-1", "node-2",""
        :return obj: response object
        """
        try:
            # Building request url
            self.log.info("Reading health view for node %s...", node)
            endpoint = self.config["health_view_endpoint"]

            # Adding parameters(if any) to endpoint
            endpoint = self._append_node_id_param(endpoint, node)
            self.log.info("Endpoint to Health View is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.get_health_view.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def verify_health_view(self, expected_response, node, verify_schema=True):
        """
        Get the health view for nodes and verify the output
        :param expected_response: expected status code
        :param node: node alias "storage", "node-1", "node-2",""
        :param verify_schema: schema for response verification
        :return Bool: True (success) / False (Failure)
        """
        try:
            result = False
            # Get Health Summary
            response = self.get_health_node(node)
            self.log.info("Verifying health view status code...")
            self.log.info(
                "Expected status code: %s", expected_response)
            self.log.info("Actual status code: %s",
                           response.status_code)
            if response.status_code == expected_response:
                self.log.info("Status code verification passed !")
                if verify_schema:
                    self.log.info("Verifying health view schema...")
                    result = self._verify_response(node, response)
                else:
                    result = True
            else:
                self.log.info("Status code verification failed !")

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.verify_health_view.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error
        self.log.info(
            "Verification result of health view : %s", result)
        return result

    def _get_node_ids(self, node):
        """
        Generate the node ID from node alias
        :param node: node alias "storage", "node-1", "node-2",""
        :return list: list of node IDs
        """
        node_ids = []
        node = node.lower()
        if node in ("storage", "all"):
            node_ids.append(const.NODE_ID_OPTIONS["storage"])
        elif node in ('node-1', 'all'):
            node_ids.append(const.NODE_ID_OPTIONS["node"].format(CMN_CFG['nodes'][0]["hostname"]))
        elif node in ('node-2', 'all'):
            node_ids.append(const.NODE_ID_OPTIONS["node"].format(CMN_CFG['nodes'][0]["hostname"]))
        elif node == "":
            node_ids.append("")
        else:
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                "Invalid Node Parameter")
        self.log.info("List of the node_ids are %s", node_ids)
        return node_ids

    def _append_node_id_param(self, endpoint, node):
        """
        Appends the node id parameter to the given output
        :param endpoint: endpoint without node parameter appended
        :param node: node alias "storage", "node-1", "node-2",""
        :return str: modified endpoint with node id param
        """
        if endpoint is not None:
            node_id = self._get_node_ids(node)[0]
            self.log.info("node_id= %s", node_id)
            param = {"node_id": [node_id, "node_id="]}
            endpoint = "{}?{}{}".format(
                endpoint, param['node_id'][1], param['node_id'][0])
        return endpoint

    def _verify_response(self, node, response):
        """
        Verify the response for node health view and health node
        :param node: node alias "storage", "node-1", "node-2",""
        :param response: actual response
        :return Bool:True (Success) / False (Failure)
        """
        self.log.info("Get the node IDs for verification...")
        if node == "":
            self.log.info(
                "As the node value selected is blank, All the possible node "
                "values will be verified...")
            node_ids = self._get_node_ids("all")
        else:
            self.log.info("Node value selected is : %s", node)
            node_ids = self._get_node_ids(node)
        self.log.info("Node IDs for verification are : %s", node_ids)

        response_json = response.json()

        cnt = len(response_json)
        self.log.info("Number of entries in response : %s", cnt)
        if cnt == 0:
            self.log.error(
                "Returning False as no entries are found in the response.")
            return False

        for node_id in node_ids:
            self.log.info(
                "Verifying the response for node : %s", node_id)
            node_summary = None
            for i in range(0, cnt):
                if node_id in response_json[i].keys():
                    self.log.info(
                        "Verifying health schema for node : %s", node_id)
                    node_summary = response_json[i][node_id]
                    break

            if node_summary is None:
                self.log.error("Node %s not found in response %s.",
                                node_id, response_json)
                return False

            try:
                self.log.info("Expected status code: %s",
                               const.HEALTH_SUMMARY_SCHEMA)
                self.log.info("Actual status code: %s",
                               node_summary[const.HEALTH_SUMMARY_INSTANCE])
                config_utils.verify_json_schema(
                    node_summary[const.HEALTH_SUMMARY_INSTANCE], const.HEALTH_SUMMARY_SCHEMA)
                self.log.info(
                    "Health schema verification passed for node : %s", node_id)
                return True
            except BaseException:
                self.log.error(
                    "Health schema verification failed for node : %s", node_id)
                return False

    @RestTestLib.authenticate_and_login
    def get_health_component(self, node):
        """
        Get the node health.
        :param node: node alias from "storage", "node-1", "node-2", ""
        :param type: enum of {"storage", "node-1", "node-2", ""}
        :return: response object
        """
        try:
            # Building request url
            self.log.info("Reading node %s health...", node)
            endpoint = self.config["health_component_endpoint"]

            # Adding parameters(if any) to endpoint
            endpoint = self._append_node_id_param(endpoint, node)
            self.log.info("Endpoint to node health is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info(
                "Response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            SystemHealth.get_health_node.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def get_health_status(self, resource: str, parameters: dict = None):
        """
        This method will Get rest API response for the resource system health
        :param parameters: filter the node status response with specific param values
        :param resource: endpoint parameters for rest call
        :return: System health resource Get rest API response
        """
        try:
            # Building request url to get resource Health status
            self.log.info("Reading health of %s ...", resource)
            endpoint = self.config["health_resource_endpoint"].format(resource)
            self.log.info(
                "Endpoint for reading capacity is %s", endpoint)
            self.log.info(
                "Filter get response with parameters %s", parameters)

            # Fetching api response
            response = self.restapi.rest_call(
                request_type="get",
                endpoint=endpoint,
                headers=self.headers,
                params=parameters,
                save_json=True)
            if response.status_code != HTTPStatus.OK:
                self.log.error(f'Response ={response.text}\n'
                               f'Request Headers={response.request.headers}\n'
                               f'Request Body={response.request.body}')
                raise CTException(err.CSM_REST_GET_REQUEST_FAILED,
                                  msg=f"Failed to get {endpoint} response.")

            self.log.info(
                "Response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                         const.EXCEPTION_ERROR,
                         SystemHealth.get_health_status.__name__,
                         error)
            raise CTException(
                err.CSM_REST_GET_REQUEST_FAILED, error) from error

    def verify_node_health_status_rest(
            self,
            exp_status: list,
            node_id: int = None,
            single_node: bool = False):
        """
        This method will get and verify health status of node
        :param exp_status: List of expected node health status
        :param node_id: To get and verify node health status for node_id
        :param single_node: To get for single node status
        :return: bool, Response Message
        """
        if single_node:
            param = dict()
            param["resource_id"] = node_id
            node_resp = self.get_health_status(
                resource="node", parameters=param)
            if node_resp.json()["data"][0]["status"] != exp_status[0].lower():
                return False, f'Node health status is {node_resp.json()["data"][0]["status"]}'
        else:
            node_resp = self.get_health_status(resource="node")
            for index, node_dict in enumerate(node_resp.json()["data"]):
                if node_dict['status'] == exp_status[index].lower():
                    self.log.info(
                        'Node-"%s" health status \nActual: "%s" \nExpected: "%s"',
                        index + 1,
                        node_dict['status'],
                        exp_status[index])
                else:
                    self.log.info(
                        'Node-"%s" health status \nActual: "%s" \nExpected: "%s"',
                        index + 1,
                        node_dict['status'],
                        exp_status[index])
                    return False, f'Node-"{index + 1}" health status is {node_dict["status"]}'
        return True, "Node health status is as expected"

    def check_resource_health_status_rest(self, resource: str, exp_status: str):
        """
        This method will get and check health status of resource health status
        :param resource: Get the health status for resource
        :param exp_status: Expected health status of resource
        :return: bool, Response Message
        """
        health_resp = self.get_health_status(resource=resource)
        health_dict = health_resp.json()["data"][0]
        if health_dict['status'] != exp_status.lower():
            return False, f"{resource}'s health status is {health_dict['status']}"
        return True, f"{resource}'s health status is {health_dict['status']}"

    def check_csr_health_status_rest(self, exp_status: str):
        """
        This method will get and check cluster, site and rack health status
        :param exp_status: Expected health status of cluster, site and rack
        :return: bool, Response Message
        """
        cls_resp = self.check_resource_health_status_rest(resource="cluster", exp_status=exp_status)
        self.log.debug(cls_resp[1])
        if not cls_resp[0]:
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, msg=cls_resp[1])
        site_resp = self.check_resource_health_status_rest(resource="site", exp_status=exp_status)
        self.log.debug(site_resp[1])
        if not site_resp[0]:
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, msg=site_resp[1])
        rack_resp = self.check_resource_health_status_rest(resource="rack", exp_status=exp_status)
        self.log.debug(rack_resp[1])
        if not rack_resp[0]:
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, msg=rack_resp[1])
        if rack_resp[0] and site_resp[0] and cls_resp[0]:
            return True, f"Cluster, site and rack health status is {exp_status}"
        return False, f"Cluster, site and rack health status is not as expected {exp_status}"

    # pylint: disable=too-many-arguments
    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def perform_cluster_operation(
            self,
            operation: str,
            resource: str,
            resource_id: int,
            storage_off: bool = False,
            force_op: bool = False,
            sleep_time: int = 300):
        """
        This method performs cluster operation like stop/start/poweroff with rest API
        :param operation: Operation to be performed on cluster resource
        :param resource: resource type like cluster, node etc
        :param resource_id: Resource ID for the operation
        :param storage_off: If true, The poweroff operation will be performed along
        with powering off the storage. (Valid only with poweroff operation on node.)
        :param force_op: Specifying this enables force operation.
        :param sleep_time: Sleep time for stop/start/poweroff operation to be completed
        :return: bool/cluster operation POST API response
        """
        # Building request url to perform cluster operation
        self.log.info("Performing %s operation on %s ...", operation, resource)
        endpoint = "{}/{}".format(self.config["cluster_operation_endpoint"], resource)
        headers = self.headers
        conf_headers = self.config["Login_headers"]
        headers.update(conf_headers)
        self.log.info(
            "Endpoint for cluster operation is %s", endpoint)
        data_val = {"operation": operation,
                "arguments": {"resource_id": f"{resource_id}"}}
        if operation == "stop":
            data_val['arguments']['force'] = force_op
        elif operation == "poweroff":
            data_val['arguments']["storageoff"] = storage_off
            data_val['arguments']['force'] = force_op
        # Fetching api response
        response = self.restapi.rest_call(
            "post",
            endpoint=endpoint,
            data=json.dumps(data_val),
            headers=headers)
        if response.status_code != HTTPStatus.OK:
            self.log.error("%s operation on %s POST REST API response : %s",
                      operation,
                      resource,
                      response)
            return False, response
        self.log.info("%s operation on %s POST REST API response : %s",
                      operation,
                      resource,
                      response)
        self.log.info("Sleep for node to %s for %s sec", operation, sleep_time)
        time.sleep(sleep_time)
        return True, response

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def check_on_cluster_effect(self, resource_id: int):
        """
        This method Get the effect of node stop/poweroff operation on cluster with rest API
        :param resource_id: Id of the node for which cluster status is to be checked.
        :return: bool/GET effect status of node operation on cluster rest API response
        """
        # Building request url to perform cluster status operation
        self.log.info("Check the effect of node %s stop/poweroff operation on cluster...",
                      resource_id)
        endpoint = "{}/{}".format(self.config["cluster_status_endpoint"], resource_id)
        self.log.info(
            "Endpoint for cluster status operation is %s", endpoint)
        # Fetching api response
        response = self.restapi.rest_call(
            request_type="get",
            endpoint=endpoint,
            headers=self.headers)
        if response.status_code != HTTPStatus.OK:
            self.log.error("cluster status operation response = %s",
                           response.json())
            return False, response
        self.log.info("cluster status operation response = %s",
                      response.json())
        return True, response

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def cluster_operation_signal(
            self,
            operation: str,
            resource: str,
            negative_resp=None,
            expected_response=HTTPStatus.OK):
        """
        Helper method to send the cluster operation signal before operation performed.
        :param operation: Operation to be performed
        :param resource: resource on which operation needs to be performed
        :param negative_resp: Invalid data for negative test scenario verification
        :param expected_response: Expected status code
        :return: boolean, response for POST
        """
        # Building request url to perform cluster operation
        self.log.info("Performing operation on %s ...", resource)
        endpoint = "{}/{}".format(self.config["cluster_operation_endpoint"], resource)
        headers = self.headers
        conf_headers = self.config["Login_headers"]
        headers.update(conf_headers)
        self.log.info("Endpoint for cluster operation is %s", endpoint)
        data_val = {"operation": operation, "arguments": {}}
        copy_auth_token = None
        if negative_resp:
            # Update the Authorization token to verify negative test scenario
            copy_auth_token = headers["Authorization"]
            headers.update({"Authorization":negative_resp})
        # Fetching api response
        response = self.restapi.rest_call("post", endpoint=endpoint,
                                          data=json.dumps(data_val), headers=headers)
        if negative_resp:
            # Update the valid token value for rest logout call
            headers.update({"Authorization":copy_auth_token})
        if response.status_code != expected_response:
            self.log.error("%s operation on %s POST REST API response : %s",
                           operation, resource, response)
            return False, response
        self.log.info("%s operation on %s POST REST API response : %s",
                      operation, resource, response)
        return True, response

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def set_resource_signal(
            self,
            req_body: dict,
            resource: str):
        """
        This method POST resource failure/shutdown signal to cluster
        :param req_body: POST operation request body
        :param resource: Resource type (eg. node)
        :return: bool, POST API response
        """
        # Building request url to POST resource failure signal
        endpoint = "{}/{}".format(self.config["cluster_operation_endpoint"], resource)
        headers = self.headers
        conf_headers = self.config["Login_headers"]
        headers.update(conf_headers)
        self.log.info("POST REST API Endpoint :", endpoint)
        # Fetching api response
        response = self.restapi.rest_call("post", endpoint=endpoint, data=json.dumps(req_body),
                                          headers=headers)
        if response.status_code != HTTPStatus.OK:
            self.log.error("POST REST API response : %s", response)
            return False, response
        self.log.info("POST REST API response : %s", response.json())
        return True, response.json()

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def get_resource_status(
            self,
            resource_id: str,
            resource: str = "node"):
        """
        This method GETs resource status
        :param resource: Resource type (eg. node)
        :param resource_id: Resource ID for which user wants to fetch status
        :return: bool, GET API response
        """
        # Building request url to GET resource status
        self.log.info("GET the status for %s", resource)
        endpoint = "{}/{}/{}".format(self.config["cluster_status_endpoint"], resource, resource_id)
        self.log.info("GET REST API Endpoint: %s", endpoint)
        # Fetching api response
        response = self.restapi.rest_call(request_type="get",
                                          endpoint=endpoint, headers=self.headers)
        if response.status_code != HTTPStatus.OK:
            return False, response
        self.log.info("GET API %s status response = %s", resource, response.json())
        return True, response.json()
