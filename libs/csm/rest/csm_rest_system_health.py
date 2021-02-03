"""Test library for System Health related operations.
   Author: Divya Kachhwaha
"""
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.utils import config_utils
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class SystemHealth(RestTestLib):
    """RestCsmUser contains all the Rest API calls for system health related
    operations"""

    def __init__(self):
        """
        Initialize the rest api
        """
        super().__init__()
        self.main_conf = config_utils.read_yaml(
            "config\\common_config.yaml")[1]

    @RestTestLib.authenticate_and_login
    def get_health_summary(self):
        """
        Get the health summary.
        """
        try:
            # Building request url
            self._log.info("Reading health summary...")
            endpoint = self.config["health_summary_endpoint"]
            self._log.info(
                "Endpoint for health summary is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.get_health_summary.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

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
            self._log.info("Verifying health summary status code...")
            self._log.info(
                "Expected status code: %s", expected_response)
            self._log.info("Actual status code: %s",
                           response.status_code)
            if response.status_code == expected_response:
                self._log.info("Status code verification passed !")
                if verify_schema:
                    self._log.info("Verifying health summary schema...")
                    self._log.info("Expected status code: %s",
                                   const.HEALTH_SUMMARY_SCHEMA)
                    self._log.info("Actual status code: %s",
                                   response.json()[const.HEALTH_SUMMARY_INSTANCE])
                    self.verify_json_schema(
                        response.json()[const.HEALTH_SUMMARY_INSTANCE], const.HEALTH_SUMMARY_SCHEMA)
                    self._log.info("Status code verification passed !")
                result = True
            else:
                self._log.info("Status code verification failed !")

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.verify_health_summary.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error
        self._log.info(
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
            self._log.info("Reading node %s health...", node)
            endpoint = self.config["health_node_endpoint"]

            # Adding parameters(if any) to endpoint
            endpoint = self._append_node_id_param(endpoint, node)
            self._log.info("Endpoint to node health is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "Response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.get_health_node.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

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
            self._log.info("Verifying health node status code...")
            self._log.info(
                "Expected status code: %s", expected_response)
            self._log.info("Actual status code: %s",
                           response.status_code)
            if response.status_code == expected_response:
                self._log.info("Status code verification passed !")
                if verify_schema:
                    self._log.info("Verifying health node schema...")
                    result = self._verify_response(node, response)
                else:
                    result = True
            else:
                self._log.info("Status code verification failed !")

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.verify_health_node.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error
        self._log.info(
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
            self._log.info("Reading health view for node %s...", node)
            endpoint = self.config["health_view_endpoint"]

            # Adding parameters(if any) to endpoint
            endpoint = self._append_node_id_param(endpoint, node)
            self._log.info("Endpoint to Health View is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.get_health_view.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

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
            self._log.info("Verifying health view status code...")
            self._log.info(
                "Expected status code: %s", expected_response)
            self._log.info("Actual status code: %s",
                           response.status_code)
            if response.status_code == expected_response:
                self._log.info("Status code verification passed !")
                if verify_schema:
                    self._log.info("Verifying health view schema...")
                    result = self._verify_response(node, response)
                else:
                    result = True
            else:
                self._log.info("Status code verification failed !")

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.verify_health_view.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error
        self._log.info(
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
        if node == "storage" or node == "all":
            node_ids.append(const.NODE_ID_OPTIONS["storage"])
        elif node == "node-1" or node == "all":
            node_ids.append(const.NODE_ID_OPTIONS["node"],
                            self.main_conf["server_hostname"], self.main_conf["host_domain"])
        elif node == "node-2" or node == "all":
            node_ids.append(const.NODE_ID_OPTIONS["node"],
                            self.main_conf["machine1_hostname"], self.main_conf["host_domain"])
        elif node == "":
            node_ids.append("")
        else:
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED,
                "Invalid Node Parameter")
        self._log.info("List of the node_ids are %s", node_ids)
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
            self._log.info("node_id= %s", node_id)
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
        self._log.info("Get the node IDs for verification...")
        if node == "":
            self._log.info(
                "As the node value selected is blank, All the possible node "
                "values will be verified...")
            node_ids = self._get_node_ids("all")
        else:
            self._log.info("Node value selected is : %s", node)
            node_ids = self._get_node_ids(node)
        self._log.info("Node IDs for verification are : %s", node_ids)

        response_json = response.json()

        cnt = len(response_json)
        self._log.info("Number of entries in response : %s", cnt)
        if cnt == 0:
            self._log.error(
                "Returning False as no entries are found in the response.")
            return False

        for node_id in node_ids:
            self._log.info(
                "Verifying the response for node : %s", node_id)
            node_summary = None
            for i in range(0, cnt):
                if node_id in response_json[i].keys():
                    self._log.info(
                        "Verifying health schema for node : %s", node_id)
                    node_summary = response_json[i][node_id]
                    break

            if node_summary is None:
                self._log.error("Node %s not found in response %s.",
                                node_id, response_json)
                return False

            try:
                self._log.info("Expected status code: %s",
                               const.HEALTH_SUMMARY_SCHEMA)
                self._log.info("Actual status code: %s",
                               node_summary[const.HEALTH_SUMMARY_INSTANCE])
                self.verify_json_schema(
                    node_summary[const.HEALTH_SUMMARY_INSTANCE], const.HEALTH_SUMMARY_SCHEMA)
                self._log.info(
                    "Health schema verification passed for node : %s", node_id)
                return True
            except:
                self._log.info(
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
            self._log.info("Reading node %s health...", node)
            endpoint = self.config["health_component_endpoint"]

            # Adding parameters(if any) to endpoint
            endpoint = self._append_node_id_param(endpoint, node)
            self._log.info("Endpoint to node health is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self._log.info(
                "Response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self._log.error("%s %s: %s",
                            self.exception_error,
                            SystemHealth.get_health_node.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error
