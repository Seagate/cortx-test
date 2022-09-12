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
from datetime import datetime

import yaml

from config import PROV_TEST_CFG
from commons import configmanager
from commons.constants import CLUSTER_YAML_PATH, LOCAL_SOLUTION_PATH
from commons.constants import K8S_SCRIPTS_PATH, POD_NAME_PREFIX, LOCAL_CLS_YAML_PATH
from commons import commands as cmds
from libs.csm.rest.csm_rest_test_lib import RestTestLib

# pylint: disable-msg=too-many-public-methods
class QueryDeployment(RestTestLib):
    """This class contains all the Rest API calls for all query deployment operations"""

    def __init__(self):
        super(QueryDeployment, self).__init__()
        self.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        self.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        self.pod_list = self.master.get_all_pods(pod_prefix=POD_NAME_PREFIX)
        self.log.info("Pod list : %s ", self.pod_list)

    def get_solution_yaml(self):
        """
        Read solution yaml into a dictionary
        """
        local_sol_path = LOCAL_SOLUTION_PATH
        remote_sol_path = K8S_SCRIPTS_PATH + 'solution.yaml'
        self.log.info("Path for solution yaml on remote node: %s", remote_sol_path)
        solution_path = self.master.copy_file_to_local(remote_path=remote_sol_path,
                                                               local_path=local_sol_path)
        self.log.info(solution_path)
        with open(local_sol_path, 'rb') as yaml_file:
            data = yaml.safe_load(yaml_file)
        self.log.info("Solution yaml contents: %s", data)
        return data

    def get_cluster_yaml(self):
        """Get cluster yaml contents"""

        local_cls_path = LOCAL_CLS_YAML_PATH
        remote_cls_path = CLUSTER_YAML_PATH
        self.log.info("Path for cluster yaml on remote node: %s", remote_cls_path)
        copy_cmd = f'cat {remote_cls_path} > {local_cls_path}'
        resp = self.master.execute_cmd(
                cmd=cmds.K8S_POD_INTERACTIVE_CMD.format(self.pod_list[0],
                copy_cmd), read_lines=True)
        self.log.info(resp)
        cluster_yaml_path = self.master.copy_file_to_local(remote_path=local_cls_path,
                                                               local_path=local_cls_path)
        self.log.info(cluster_yaml_path)
        with open(local_cls_path, 'rb') as yaml_file:
            data = yaml.safe_load(yaml_file)
        return data

    @RestTestLib.authenticate_and_login
    def get_system_topology(self, uri_param=None, auth_header=None):
        """
        Get system topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Auth header %s and query param %s ", auth_header, uri_param)
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

    def verify_system_topology(self, deploy_start_time: str, deploy_end_time: str,
                             expected_response=HTTPStatus.OK):
        """
        Verify Get system topology
        """
        get_response = self.get_system_topology()
        self.log.info("Get system topology response %s", get_response)
        result = get_response.status_code == expected_response
        if result:
            self.log.info("Step 1: Verify id fields have unique values")
            result, err_msg = self.verify_unique_ids()
            assert result, err_msg
            self.log.info("Step 2: Verify deployment version and time")
            result, err_msg = self.verify_deployment_version_time(get_response.json(),
                             deploy_start_time, deploy_end_time)
            assert result, err_msg
            self.log.info("Step 3: Verify node details")
            result, err_msg = self.verify_node_details(get_response.json())
            assert result, err_msg
            self.log.info("Step 4: Verify storage details")
            result, err_msg = self.verify_storage_details(get_response.json())
            assert result, err_msg
            self.log.info("Step 5: Verify storage set details")
            resp, result, err_msg = self.verify_storage_set()
            self.log.info("Storage set verification response %s ", resp)
            assert result, err_msg
            self.log.info("Step 6: Verify certificate details")
            result, err_msg = self.verify_certificate_details(expected_response=HTTPStatus.OK)
            assert result, err_msg
        else:
            err_msg = "Status code check failed"
            self.log.error(err_msg)
        return result, err_msg

    def get_certificate_topology(self, auth_header=None):
        """
        Get certificate topology
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Get certificate topology request....")
        uri_param = 'certificates'
        self.log.info("Logging query parameter for certificate topology: %s", uri_param)
        response = self.get_system_topology(uri_param, auth_header)
        return response

    def get_storage_topology(self, storage_set_id=None, auth_header=None):
        """
        Get storage topology
        :param header: header for api authentication
        :storage_set_id: id for particular storage set
        :return: response
        """
        self.log.info("Get storage topology request....")
        uri_param = 'storage_sets'
        if storage_set_id is not None:
            uri_param = uri_param + '/' + storage_set_id
        self.log.info("storage topology endpoint: %s", uri_param)
        self.log.info("Logging query parameter for storage topology: %s", uri_param)
        response = self.get_system_topology(uri_param, auth_header)
        return response

    def get_node_topology(self, node_id=None, auth_header=None):
        """
        Get node topology
        :param header: header for api authentication
        :node_id: id for particular node in cluster
        :return: response
        """
        self.log.info("Get node topology request....")
        uri_param = 'nodes'
        if node_id is not None:
            uri_param = uri_param + '/' + node_id
        self.log.info("node topology endpoint: %s", uri_param)
        self.log.info("Logging query parameter for node topology: %s", uri_param)
        response = self.get_system_topology(uri_param, auth_header)
        return response

    def verify_node_topology(self, expected_response: str):
        """
        Verify node topology
        """
        get_resp = self.get_node_topology()
        self.log.info("Node topology response %s ", get_resp.json())
        result = get_resp.status_code == expected_response
        if result:
            self.log.info("Step 1: Verify node id and hostname")
            result, err_msg = self.verify_id_and_hostname()
            assert result, err_msg
            self.log.info("Step 2: Verify services list")
            result, err_msg = self.verify_services_list(get_resp.json())
            assert result, err_msg
        else:
            err_msg = "Status code check failed"
            self.log.error(err_msg)
        return result, err_msg

    def verify_unique_ids(self):
        """
        Function to verify cluster ids have unique values
        """
        err_msg = ""
        result = True
        node_id_list, hostname_list = self.generate_node_hostname_list()
        self.log.info("List of hostnames: %s ", hostname_list)
        self.log.info("List of unique ids: %s ", node_id_list)
        if len(set(node_id_list)) == len(node_id_list):
            self.log.info("id fields have unique values")
        else:
            err_msg = "Duplicate values found for id fields"
            self.log.error(err_msg)
            result = False
        return result, err_msg

    def verify_deployment_version_time(self, get_response: dict, deploy_start_time: float,
                                    deploy_end_time: float):
        """
        Function to verify deployment version and time
        """
        err_msg = ""
        time_list = []
        result = True
        self.log.info("Verify deployment version")
        response_version = get_response["topology"]["version"]
        resp = self.master.execute_cmd(
                cmd=cmds.K8S_POD_INTERACTIVE_CMD.format(self.pod_list[0], cmds.CMD_CORTX_VERSION),
                read_lines=True)
        resp = resp.decode() if isinstance(resp, bytes) else resp
        deploy_version = [res.strip().split()[1] for res in resp]
        deploy_version = ''.join(deploy_version).strip('\"')
        self.log.info("Deploy_version %s ", deploy_version)
        if response_version == deploy_version:
            self.log.info("Deployment Version match found")
        else:
            err_msg = "Deployment Version mismatch found. "
            self.log.error(err_msg)
            result = False
        self.log.info("Verify deployment time of nodes")
        for dicts in get_response["topology"]["nodes"]:
            if 'deployment_time' in dicts.keys():
                time_list.append(dicts['deployment_time'])
        self.log.info("List of deployment times: %s", time_list)
        for times in time_list:
            if deploy_start_time <= int(times) <= deploy_end_time:
                self.log.info("Deployment time verification successful")
            else:
                err_msg = err_msg + "Deployment time verification failed"
                self.log.error(err_msg)
                result = False
        return result, err_msg

    def verify_node_details(self, get_response: dict):
        """
        Verify node details
        """
        err_msg = ""
        result = True
        self.log.info("Check if all key parameters are present for node")
        list_params = ['id', 'version', 'services', 'type', 'storage_set',
                'deployment_time', 'hostname']
        for dicts in get_response["topology"]["nodes"]:
            for param in list_params:
                self.log.info("Node param: %s", param)
                if param in dicts.keys() and dicts[param] != "":
                    self.log.info("Node param verification successful")
                else:
                    err_msg = "Node param verification failed"
                    self.log.error(err_msg)
                    result = False
        return result, err_msg

    def verify_storage_details(self, get_response: dict):
        """
        Verify storage details present for data node
        """
        solution_yaml = self.get_solution_yaml()
        storage1 = solution_yaml["solution"]["storage_sets"][0]["storage"]
        number_of_cvgs = len(storage1)
        cvg_dict = {}
        for number in range(0, number_of_cvgs):
            cvg_dict.update({number:storage1[number]["name"]})
        self.log.info("cvg dict: %s ", cvg_dict)
        for dicts in get_response["topology"]["nodes"]:
            self.log.info("dict is: %s ", dicts)
            for key, value in cvg_dict.items():
                self.log.info("Verifying for: %s %s", key, value)
                if 'storage' in dicts.keys() and dicts["storage"][0]["name"] == value:
                    resp = dicts["storage"][0]["devices"]
                    self.log.info("Resp is %s ", resp)
                    solution = storage1[key]["devices"]
                    self.log.info("Solution is %s ", solution)
                    result, err_msg = self.verify_cvg_details(resp, solution, value)
                    assert result, err_msg
                else:
                    self.log.info("Node other than data node")
        return result, err_msg

    def verify_cvg_details(self, resp: dict, solution: dict, cvg: str):
        """
        Verify cvg details
        """
        err_msg = ""
        result = True
        self.log.info("Check for metadata fields")
        if resp['metadata'][0] == solution['metadata'][0]['path']:
            self.log.info(f"Metadata fields match for {cvg}. ")
        else:
            err_msg = f"Metadata fields match failed for {cvg}. "
            self.log.error(err_msg)
            result = False
        self.log.info("Check for data fields")
        if resp['data'][0] == solution['data'][0]['path']:
            self.log.info(f"Data fields match for {cvg}. ")
        else:
            err_msg = err_msg + f"data fields match failed for {cvg}."
            self.log.error(err_msg)
            result = False
        self.log.info("Check for data fields")
        if resp['data'][1] == solution['data'][1]['path']:
            self.log.info(f"Data fields match for {cvg}. ")
        else:
            err_msg = err_msg + f"Data fields match failed for {cvg}."
            self.log.error(err_msg)
            result = False
        return result, err_msg

    def generate_node_hostname_list(self):
        """
        Generate list of node ids
        """
        node_id_list = []
        hostname_list = []
        self.log.info("Step 1: Send node details query request")
        resp = self.get_node_topology()
        assert resp.status_code == HTTPStatus.OK, \
						   "Status code check failed for get node topology"
        self.log.info("Step 2: Send same request with node id")
        for dicts in resp.json()["topology"]["nodes"]:
            node_id_list.append(dicts["id"])
            hostname_list.append(dicts["hostname"])
        return node_id_list, hostname_list

    def verify_id_and_hostname(self):
        """
        Function to verify machine id
        """
        err_msg = ""
        hostname_list = []
        result = True
        node_id_list, hostname_list = self.generate_node_hostname_list()
        self.log.info("Node ids list: %s", node_id_list)
        for node_ids in node_id_list:
            self.log.info("Checking for node id: %s ", node_ids)
            get_resp = self.get_node_topology(node_id = node_ids)
            assert get_resp.status_code == HTTPStatus.OK, \
						   "Status code check failed for get node topology"
            self.log.info("Verify only one node is present in response")
            if len(get_resp.json()["topology"]["nodes"]) == 1:
                self.log.info("Verified only one node is present in response")
        for pod_name in self.pod_list:
            self.log.info(" Step 3: login to each pod and get machine-id")
            resp = self.master.get_machine_id_for_pod(pod_name)
            self.log.info("Machine id in resp %s ", resp)
            if resp in node_id_list:
                self.log.info("Machine id match successful")
            else:
                err_msg = "Machine id mismatch found. "
                self.log.info(err_msg)
                result = False

            self.log.info("Step 4: login to each pod and check hostname")
            resp = self.master.get_pod_fqdn(pod_name=pod_name)
            self.log.info("Hostname from resp: %s ", resp)
            self.log.info("Hostname list: %s ", hostname_list)
            if resp in hostname_list:
                self.log.info("Hostname match successful")
            else:
                err_msg = err_msg + "Hostname mismatch found"
                self.log.info(err_msg)
                result = False
        return result, err_msg

    def get_services_dict(self):
        """
        Verify list of services for cluster nodes
        """
        yaml_services_dict = {}
        self.log.info("Read data from cluster.yaml")
        cluster_yaml = self.get_cluster_yaml()
        cluster = cluster_yaml["cluster"]["node_types"]
        for elements in cluster:
            self.log.info("Remove client node details which are not required")
            removed_value = elements.pop('client_node', 'No Key found')
            self.log.info("removed value: %s ", str(removed_value))
            if elements["name"] == 'data_node/0' or elements["name"] == 'data_node/1':
                yaml_services_dict.update({elements['name']:elements["components"][1]["services"]})
            elif elements["name"] == 'server_node':
                yaml_services_dict.update({elements['name']:elements["components"][2]["services"]})
            elif elements["name"] == 'control_node':
                yaml_services_dict.update({elements['name']:elements["components"][1]["services"]})
            else:
                self.log.info("Ha node service details missing so cannot update dict")
            #need to check how ha node services would appear after Bug=CORTX-34129 is resolved
        self.log.info("Yaml service dict: %s ", yaml_services_dict)
        return yaml_services_dict

    def verify_services_list(self, get_resp: dict):
        """Verify services list"""
        err_msg = ""
        result = True
        yaml_services_dict = self.get_services_dict()
        for dicts in get_resp["topology"]["nodes"]:
            if 'data_node' in dicts["type"]:
                if dicts["services"] == yaml_services_dict['data_node/0']:
                    self.log.info("Services list matched for data nodes")
                else:
                    result = False
                    err_msg = "Services list match failed for data nodes"
                    self.log.error(err_msg)
            elif dicts["type"] == 'server_node':
                if dicts["services"] == yaml_services_dict['server_node']:
                    self.log.info("Services list matched for server nodes")
                else:
                    result = False
                    err_msg = err_msg + "Services list match failed for server nodes"
                    self.log.error(err_msg)
            elif dicts["type"] == 'control_node':
                if dicts["services"] == yaml_services_dict['control_node']:
                    self.log.info("Services list matched for control nodes")
                else:
                    result = False
                    err_msg = err_msg + "Services list match failed for control nodes"
                    self.log.error(err_msg)
            else:
                self.log.info("Node other than above node types")
        return result, err_msg

    def verify_storage_set(self, storage_set_id: str = None,
                                 expected_response=HTTPStatus.OK):
        """
        Verify storage set details
        """
        resp_dix = ""
        err_msg = ""
        resp = self.get_storage_topology(storage_set_id = storage_set_id)
        result = resp.status_code == expected_response
        solution_yaml = self.get_solution_yaml()
        if result:
            get_response = resp.json()
            self.log.info("Verifying sns and dix values in resp and solution yaml")
            resp_dix = get_response[
                "topology"]["storage_sets"][0]["durability"]["data"]
            input_dix = solution_yaml["solution"]["storage_sets"][0]["durability"]["dix"]
            self.log.info("Dix value from response and solution yaml %s and %s",
                               resp_dix, input_dix)
            resp_sns = get_response[
                "topology"]["storage_sets"][0]["durability"]["metadata"]
            input_sns = solution_yaml["solution"]["storage_sets"][0]["durability"]["sns"]
            self.log.info("Sns value from response and solution yaml %s and %s",
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

    def verify_datetime_details(self, validity_str: str, get_response_date: str,
                                get_response_time: str):
        """
        Verify what date certificate is valid before
        """
        err_msg = ""
        output = []
        flat_list = []
        result = True
        self.log.info("Verify certificate startdate")
        resp = self.master.execute_cmd(
                cmd=cmds.CMD_DECRYPT_CERTIFICATE.format(validity_str), read_lines=True)
        resp = resp.decode() if isinstance(resp, bytes) else resp
        self.log.info("Print resp: %s", resp)
        for element in resp:
            output.append(element.strip().split())
        for elements in output:
            flat_list.extend(elements)
        date_cmd = f'{flat_list[1]}-{flat_list[0].split("=")[1]}-{flat_list[3]}'
        self.log.info("Date from command: %s", date_cmd)
        my_date = datetime.strptime(get_response_date, "%Y-%m-%d")
        date_resp = f'{my_date.day}-{my_date.strftime("%b")}-{my_date.year}'
        self.log.info("Date from response: %s", date_resp)
        if date_cmd != date_resp:
            err_msg = "Date Verification failed."
            self.log.error(err_msg)
            result = False
        else:
            self.log.info("Date Verification successful")
        self.log.info("Verify time in date details")
        time_cmd = flat_list[2]
        self.log.info("Time from get_response: %s", time_cmd)
        self.log.info("Time from command: %s", time_cmd)
        if time_cmd != get_response_time:
            err_msg = err_msg + " Time details match failed"
            self.log.error(err_msg)
            result = False
        else:
            self.log.info("Time details match successful")
        return result, err_msg

    def verify_serial_number(self, get_response_number: int):
        """
        Verify serial number for certificate
        """
        err_msg = ""
        cmd = cmds.CMD_DECRYPT_CERTIFICATE.format("serial")
        resp = self.master.execute_cmd(cmd=cmd, read_lines=True)
        resp = resp.decode() if isinstance(resp, bytes) else resp
        self.log.info("Print resp: %s", resp)
        output_cmd = [res.strip().split("=")[1] for res in resp]
        output_cmd = int((''.join(output_cmd)), 16)
        self.log.info("Print serial number from response %s ", get_response_number)
        self.log.info("Print serial number from command %s", output_cmd)
        result = output_cmd == get_response_number
        if result:
            self.log.info("Serial number match successful")
        else:
            err_msg = "Serial number match failed"
            self.log.error(err_msg)
        return result, err_msg

    def verify_version_number(self, get_response_version: str):
        """
        Verify certificate version
        """
        err_msg = ""
        version_cmd = None
        resp = self.master.execute_cmd(
                cmd=cmds.CMD_DECRYPT_CERTIFICATE.format("text"), read_lines=True)
        resp = resp.decode() if isinstance(resp, bytes) else resp
        self.log.info("Print resp: %s", resp)
        for version_cmd in resp:
            if "version" in version_cmd.lower():
                version_cmd = "v" + version_cmd.strip().split()[1]
                self.log.info("Version from command %s", version_cmd)
                break
        get_response_version = get_response_version.split(".")[1]
        self.log.info("Get response version %s", get_response_version)
        result = version_cmd == get_response_version
        if result:
            self.log.info("Version number match successful")
        else:
            err_msg = "Version number match failed"
            self.log.error(err_msg)
        return result, err_msg

    def verify_issuer_details(self, issuer_dict: dict):
        """
        Verify certificate issuer details
        """
        err_msg = ""
        values_list = []
        flat_list = []
        resp = self.master.execute_cmd(
                cmd=cmds.CMD_FETCH_CERTIFICATE_DETAILS.format("issuer"), read_lines=True)
        resp = resp.decode() if isinstance(resp, bytes) else resp
        self.log.info("Print resp: %s", resp)
        for elements in resp:
            values_list.append(elements.strip().split("="))
        for elements in values_list:
            flat_list.extend(elements)
        res_dct = {flat_list[i]: flat_list[i + 1] for i in range(0, len(flat_list), 2)}
        del res_dct["issuer"]
        self.log.info("res dict %s ", res_dct)
        self.log.info("issuer dict %s ", issuer_dict)
        result = res_dct == issuer_dict
        if result:
            self.log.info("Issuer details match successful")
        else:
            err_msg = "Issuer details match failed"
            self.log.error(err_msg)
        return result, err_msg

    def verify_subject_details(self, subject_dict: dict):
        """
        Verify certificate subject details
        """
        err_msg = ""
        values_list = []
        flat_list = []
        resp = self.master.execute_cmd(
                cmd=cmds.CMD_FETCH_CERTIFICATE_DETAILS.format("subject"), read_lines=True)
        resp = resp.decode() if isinstance(resp, bytes) else resp
        self.log.info("Print resp: %s", resp)
        for elements in resp:
            values_list.append(elements.strip().split("="))
        for elements in values_list:
            flat_list.extend(elements)
        res_dct = {flat_list[i]: flat_list[i + 1] for i in range(0, len(flat_list), 2)}
        del res_dct["subject"]
        self.log.info("res dict %s ", res_dct)
        self.log.info("subject dict %s ", subject_dict)
        result = res_dct == subject_dict
        if result:
            self.log.info("Subject details match successful")
        else:
            err_msg = "Subject details match failed"
            self.log.error(err_msg)
        return result, err_msg

    def verify_certificate_details(self, expected_response=HTTPStatus.OK):
        """
        Verify certificate details
        """
        get_response = self.get_certificate_topology()
        result = get_response.status_code == expected_response
        if result:
            self.log.info("Status code check passed")
            self.log.info("Verify Certificate date time details")
            self.log.info("Verify valid before date")
            get_response = get_response.json()["topology"]["certificates"][0]
            get_response_date = get_response["not_valid_before"].split()[0]
            get_response_time = get_response["not_valid_before"].split()[1]
            result, err_msg = self.verify_datetime_details("startdate",
                                      get_response_date, get_response_time)
            assert result, err_msg
            self.log.info("Verified certificate startdate")
            self.log.info("Verify valid after date")
            get_response_date = get_response["not_valid_after"].split()[0]
            get_response_time = get_response["not_valid_after"].split()[1]
            result, err_msg = self.verify_datetime_details("enddate",
                                      get_response_date, get_response_time)
            assert result, err_msg
            self.log.info("Verified certificate enddate")
            self.log.info("Verify serial number")
            get_response_number = get_response["serial_number"]
            result, err_msg = self.verify_serial_number(get_response_number)
            assert result, err_msg
            self.log.info("Verify version number")
            get_response_version = get_response["version"]
            result, err_msg = self.verify_version_number(get_response_version)
            self.log.info("result err_msg is %s and %s ", result, err_msg)
            assert result, err_msg
            self.log.info("Verify issuer details")
            issuer_dict = get_response["issuer"]
            self.log.info("Issuer details %s", get_response)
            result, err_msg = self.verify_issuer_details(issuer_dict)
            assert result, err_msg
            self.log.info("Verify subject details")
            subject_dict = get_response["subject"]
            self.log.info("Subject details %s", subject_dict)
            result, err_msg = self.verify_subject_details(subject_dict)
            assert result, err_msg
        else:
            err_msg = "Status code check failed"
            self.log.error(err_msg)
        return result, err_msg


    def get_sns_value(self):
        """
        return SNS value using Query deployment table
        """
        resp = self.get_storage_topology()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        data = resp.json()['topology']['storage_sets'][0]['durability']['data']
        data = data.split("+")
        kvalue = int(data[0])
        nvalue = int(data[1])
        svalue = int(data[2])
        return kvalue, nvalue, svalue

    def get_dix_value(self):
        """
        return SNS value using Query deployment table
        """
        resp = self.get_storage_topology()
        assert resp.status_code == HTTPStatus.OK, "Status code check failed."
        data = resp.json()['topology']['storage_sets'][0]['durability']['metadata']
        data = data.split("+")
        dvalue = int(data[0])
        ivalue = int(data[1])
        xvalue = int(data[2])
        return dvalue, ivalue, xvalue
