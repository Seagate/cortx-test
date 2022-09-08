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
from commons.constants import LOCAL_SOLUTION_PATH, K8S_SCRIPTS_PATH
from commons import commands as cmds
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class QueryDeployment(RestTestLib):
    """This class contains all the Rest API calls for all query deployment operations"""

    def __init__(self):
        super(QueryDeployment, self).__init__()
        self.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        self.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")

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
    def verify_system_topology(self, deploy_version, expected_response=HTTPStatus.OK):
        """
        Verify Get system topology
        """
        err_msg = ""
        unique_list = []
        time_list= []
        resp = self.get_system_topology()
        result = True
        if resp.status_code == expected_response:
            result = True
            get_response = resp.json()
            self.log.info("1. Verify id fields have unique values")
            for elements in get_response["topology"]:
                if 'id' in elements.keys():
                    unique_list.append(elements['id'])
            if len(set(unique_list)) == len(unique_list):
                self.log.info("id fields have unique values")
            else:
                err_msg = "Duplicate values found for id fields"
                self.log.error(err_msg)
                result = False
            self.log.info("2. Verify deployment version and time")
            response_version = get_response["topology"]["version"]
            if response_version == deploy_version:
                self.log.info("Version match found")
            else:
                err_msg = err_msg + "Version mismatch found"
                self.log.error(err_msg)
                result = False
            for nodes in get_response["topology"]["nodes"][0]:
                time_list.append(nodes["deployment_time"])
            #compare deployment times
            #verify node details(call verify storage details inside)
            self.log.info("Verify certificate details")
            result, err_msg = self.verify_certificate_details(expected_response=HTTPStatus.OK)
            assert result, err_msg
        else:
            self.log.error("Status code check failed.")
            result = False
        return result, get_response

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
            resp_hostnames = []
            for names in get_response["topology"]["nodes"]:
                resp_hostnames.append(names["hostname"])
            #compare for hostnames list received from each pod
            self.log.info("Verify number of nodes in resp and solution yaml")
            nodes = len(get_response["topology"]["nodes"])
            num_nodes = len(solution_yaml["solution"]["storage_set"]["nodes"])
            if num_nodes != nodes:
                self.log.error("Actual and expected response for number of nodes didnt match")
                result = False
        else:
            self.log.error("Status code check failed.")
        return result

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
            self.log.info("Printing dix value from response and solution yaml %s and %s",
                               resp_dix, input_dix)
            resp_sns = get_response[
                "topology"]["storage_sets"][0]["durability"]["metadata"]
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
                self.log.info("Printing version from command %s", version_cmd)
                break
        get_response_version = get_response_version.split(".")[1]
        self.log.info("Printing get response version %s", get_response_version)
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
            self.log.info("Printing issuer details %s", get_response)
            result, err_msg = self.verify_issuer_details(issuer_dict)
            assert result, err_msg
            self.log.info("Verify subject details")
            subject_dict = get_response["subject"]
            self.log.info("Printing issuer details %s", subject_dict)
            result, err_msg = self.verify_subject_details(subject_dict)
            assert result, err_msg
        else:
            err_msg = "Status code check failed"
            self.log.error(err_msg)
        return result, err_msg
