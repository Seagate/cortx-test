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
"""Test library for query deployment related operations."""

from http import HTTPStatus
import yaml

from config import PROV_TEST_CFG
from commons.constants import LOCAL_SOLUTION_PATH, K8S_SCRIPTS_PATH
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class QueryDeployment(RestTestLib):
    """This class contains all the Rest API calls for all query deployment operations"""

    def __init__(self):
        super(QueryDeployment, self).__init__()
        self.local_sol_path = LOCAL_SOLUTION_PATH
        self.k8s_scripts_path = K8S_SCRIPTS_PATH
        self.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        self.rest_test_obj = RestTestLib()

    def get_solution_yaml(self):
        """
        Read solution yaml into a dictionary
        """
        remote_sol_path = self.k8s_scripts_path + 'solution.yaml'
        self.log.info("Path for solution yaml on remote node: %s", remote_sol_path)
        solution_path = self.rest_test_obj.master.copy_file_to_local(remote_path=remote_sol_path,
                                                               local_path=self.local_sol_path)
        self.log.info(solution_path)
        with open(self.local_sol_path, 'r') as yaml_file:
            data = yaml.safe_load(yaml_file)
        self.log.info("Printing solution yaml contents: %s", data)
        return data

    @RestTestLib.authenticate_and_login
    def get_system_topology(self, uri_param=None, auth_header=None):
        """
        Get system topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Printing auth header %s and query param %s ", auth_header, uri_param)
        self.log.info("Get system topology request....")
        if auth_header is None:
            headers = self.headers
        else:
            headers = auth_header
        endpoint = self.config["system_topology_endpoint"]
        if uri_param is not None:
            endpoint = endpoint + '/' + uri_param
        self.log.info("system topology endpoint: %s", endpoint)
        response = self.restapi.rest_call("get", endpoint=endpoint,
                                          headers=headers)
        self.log.info("Get system topology request successfully sent...")
        return response

    # Function not ready
    def verify_system_topology(self, expected_response=HTTPStatus.OK):
        """
        Verify Get system topology
        """
        resp = self.get_system_topology()
        result = True
        if resp.status_code == expected_response:
            result = True
            get_response = resp.json()
            self.log.info("Verify id fields have unique values")
            self.log.info("Verfying cvg and devices in resp and solution yaml")
            # Verify deployment version and deployment time
        else:
            self.log.error("Status code check failed.")
            result = False
        return result, get_response

    def get_cluster_topology(self, uri_param, cluster_id=None, auth_header=None):
        """
        Get cluster topology
        :param header: header for api authentication
        :cluster_id: id for the cluster
        :return: response
        """
        self.log.info("Cluster id in cluster topology %s ", cluster_id)
        self.log.info("query parameter for storage topology: %s", uri_param)
        self.log.info("Get cluster topology request....")
        cluster_param = 'clusters'
        if cluster_id is not None:
            cluster_param = cluster_param + '/' + cluster_id
            self.log.info("Cluster param is %s", cluster_param)
        if uri_param is not None:
            uri_param = cluster_param + '/' + uri_param
        self.log.info("cluster topology endpoint: %s", uri_param)
        self.log.info("Logging query parameter for cluster topology: %s", uri_param)
        response = self.get_system_topology(uri_param, auth_header)
        return response

    def get_certificate_topology(self, cluster_id: str, auth_header=None):
        """
        Get certificate topology
        :param header: header for api authentication
        :cluster_id: id for the cluster
        :return: response
        """
        self.log.info("Get certificate topology request....")
        uri_param = 'certificates'
        self.log.info("Logging query parameter for certificate topology: %s", uri_param)
        response = self.get_cluster_topology(uri_param, cluster_id, auth_header)
        return response

    def get_storage_topology(self, cluster_id, storage_set_id=None, auth_header=None):
        """
        Get storage topology
        :param header: header for api authentication
        :cluster_id: id for the cluster
        :storage_set_id: id for particular storage set
        :return: response
        """
        self.log.info("Cluster id in storage topology %s ", cluster_id)
        self.log.info("Get storage topology request....")
        uri_param = 'storage_set'
        if storage_set_id is not None:
            uri_param = uri_param + '/' + storage_set_id
        self.log.info("storage topology endpoint: %s", uri_param)
        self.log.info("Logging query parameter for storage topology: %s", uri_param)
        response = self.get_cluster_topology(uri_param, cluster_id, auth_header)
        return response

    def get_node_topology(self, cluster_id, node_id=None, auth_header=None):
        """
        Get node topology
        :param header: header for api authentication
        :cluster_id: id for the cluster
        :node_id: id for particular node in cluster
        :return: response
        """
        self.log.info("Get node topology request....")
        uri_param = 'nodes'
        if node_id is not None:
            uri_param = uri_param + '/' + node_id
        self.log.info("node topology endpoint: %s", uri_param)
        self.log.info("Logging query parameter for node topology: %s", uri_param)
        response = self.get_cluster_topology(uri_param, cluster_id, auth_header)
        return response

    #Function Not Ready
    def verify_nodes(self, node_id=None, expected_response=HTTPStatus.OK):
        """
        Verify number of nodes and node names
        """
        resp = self.get_node_topology(node_id)
        solution_yaml = self.get_solution_yaml()
        result = resp.status_code == expected_response
        if result:
            get_response = resp.json()
            self.log.info("Verify node names")  
            self.log.info("Verify number of nodes in resp and solution yaml")
            nodes = len(get_response["topology"]["cluster"][0]["nodes"])
            num_nodes = len(solution_yaml["solution"]["storage_set"]["nodes"])
            if num_nodes != nodes:
                self.log.error("Actual and expected response for number of nodes didnt match")
                result = False
        else:
            self.log.error("Status code check failed.")
        return result

    def verify_storage_set(self, cluster_id: str, storage_set_id: str = None,
                                          expected_response=HTTPStatus.OK):
        """
        Verify storage set details
        """
        resp_dix = ""
        err_msg = ""
        resp = self.get_storage_topology(cluster_id, storage_set_id = storage_set_id)
        result = resp.status_code == expected_response
        solution_yaml = self.get_solution_yaml()
        if result:
            get_response = resp.json()
            self.log.info("Verifying sns and dix values in resp and solution yaml")
            storage_set_dix = get_response[
                "topology"]["cluster"][0]["storage_set"]["durability"]["dix"]
            resp_dix = resp_dix.join([str(storage_set_dix["data"]), str(storage_set_dix["parity"]),
                                      str(storage_set_dix["spare"])])
            input_dix = solution_yaml["solution"]["storage_sets"][0]["durability"]["dix"]
            self.log.info("Printing dix value from response and solution yaml %s and %s",
                               resp_dix, input_dix)
            storage_set_sns = get_response[
                "topology"]["cluster"][0]["storage_set"]["durability"]["sns"]
            resp_sns = resp_sns.join([str(storage_set_sns["data"]), str(storage_set_sns["parity"]),
                                      str(storage_set_sns["spare"])])
            input_sns = solution_yaml["solution"]["storage_sets"][0]["durability"]["sns"]
            self.log.info("Printing sns value from response and solution yaml %s and %s",
                               resp_sns, input_sns)
            if input_dix != resp_dix: 
                err_msg = "Actual and expected response for dix didnt match"
                self.log.error(err_msg)
                result = False
            if input_sns != resp_sns:
                err_msg = err_msg + "Actual and expected response for sns didnt match"
                self.log.error(err_msg)
                result = False
        else:
            err_msg = "Status code check failed."
            self.log.error(err_msg)
            result = False
        return resp, result, err_msg
