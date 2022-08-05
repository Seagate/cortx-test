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
from commons import configmanager
from commons.constants import LOCAL_SOLUTION_PATH
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class QueryDeployment(RestTestLib):
    """This class contains all the Rest API calls for all query deployment operations"""

    def __init__(self):
        super(QueryDeployment, self).__init__()
        self.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_query_deployment.yaml")
        self.local_sol_path = LOCAL_SOLUTION_PATH
        self.resp_dix = None
        self.resp_sns = None
        self.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        self.master_node_obj = RestTestLib()

    def get_solution_yaml(self):
        """
        Read solution yaml into a dictionary
        """
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.example.yaml"
        self.log.info("Path for solution yaml on remote node: %s", remote_sol_path)
        solution_path = self.csm_obj.master.copy_file_to_local(remote_path=remote_sol_path,
                                                               local_path=self.local_sol_path)
        data = yaml.safe_load(solution_path)
        self.log.info("Printing solution yaml contents: %s", data)
        return data

    @RestTestLib.authenticate_and_login
    def get_system_topology(self, auth_header=None, query_param=None):
        """
        Get system topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Get system topology request....")
        if auth_header is None:
            headers = self.headers
        else:
            headers = auth_header
        endpoint = self.config["system_topology_endpoint"]
        if query_param is not None:
            endpoint = endpoint + '/' + query_param
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

    @RestTestLib.authenticate_and_login
    def get_cluster_topology(self, auth_header=None, cluster_id=None):
        """
        Get cluster topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Get cluster topology request....")
        query_param = 'cluster'
        if cluster_id is not None:
            query_param = query_param + '/' + cluster_id
        self.log.info("Logging query parameter for cluster topology: %s", query_param)
        response = self.get_system_topology(auth_header, query_param)
        return response

    @RestTestLib.authenticate_and_login
    def get_storage_topology(self, auth_header=None, storage_set_id=None):
        """
        Get storage topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Get storage topology request....")
        query_param = 'storage_set'
        if storage_set_id is not None:
            query_param = query_param + '/' + storage_set_id
        response = self.get_cluster_topology(auth_header, query_param)
        return response

    @RestTestLib.authenticate_and_login
    def get_node_topology(self, auth_header=None, node_id=None, cluster_id=None):
        """
        Get node topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Get node topology request....")
        query_param = cluster_id + '/' + 'node'
        if node_id is not None:
            query_param = query_param + '/' + node_id
        response = self.get_cluster_topology(auth_header, query_param)
        return response

    def verify_nodes(self, expected_response=HTTPStatus.OK):
        """
        Verify number of nodes and node names
        """
        resp = self.get_storage_topology()
        solution_yaml = self.get_solution_yaml()
        result = resp.status_code == expected_response
        if result:
            get_response = resp.json()
            self.log.info("Verify node names")
            self.log.info("Verify number of nodes in resp and solution yaml")
            nodes = len(get_response["topology"]["cluster"]["nodes"])
            num_nodes = len(solution_yaml["solution"]["storage_set"]["nodes"])
            if num_nodes != nodes:
                self.log.error("Actual and expected response for number of nodes didnt match")
                result = False
        else:
            self.log.error("Status code check failed.")
        return result

    def verify_storage_set(self, storage_set_id: str = None, expected_response=HTTPStatus.OK):
        """
        Verify storage set details
        """
        resp = self.get_storage_topology(storage_set_id)
        solution_yaml = self.get_solution_yaml()
        result = resp.status_code == expected_response
        if result:
            get_response = resp.json()
            self.log.info("Verifying sns and dix values in resp and solution yaml")
            storage_set_dix = get_response[
                "topology"]["cluster"]["storage_set"]["durability"]["dix"]
            resp_dix = resp_dix.join([str(storage_set_dix["data"]), str(storage_set_dix["parity"]),
                                      str(storage_set_dix["spare"])])
            input_dix = solution_yaml["solution"]["storage_set"]["durability"]["dix"]
            if input_dix != resp_dix:
                self.log.error("Actual and expected response for dix didn't match")
                result = False
            storage_set_sns = get_response[
                "topology"]["cluster"]["storage_set"]["durability"]["sns"]
            resp_sns = resp_sns.join([str(storage_set_sns["data"]), str(storage_set_sns["parity"]),
                                      str(storage_set_sns["spare"])])
            input_sns = solution_yaml["solution"]["storage_set"]["durability"]["sns"]
            if input_sns != resp_sns:
                self.log.error("Actual and expected response for sns didnt match")
                result = False
        else:
            self.log.error("Status code check failed.")
            result = False
        return resp, result
