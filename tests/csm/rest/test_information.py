#Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
"""
Tests various operations on Cortx Information using REST API
"""
import logging
from http import HTTPStatus
from string import Template
import pytest
from commons import configmanager
from commons import cortxlogging
from commons.utils import assert_utils
from libs.csm.csm_interface import csm_api_factory
from config import CSM_REST_CFG

class TestCortxInformation():
    """
    Tests related to Cortx Information
    """
    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups")
        cls.csm_conf = configmanager.get_config_wrapper(
                        fpath="config/csm/test_rest_information.yaml")
        cls.rest_resp_conf = configmanager.get_config_wrapper(
            fpath="config/csm/rest_response_data.yaml")
        cls.log.info("Ended test module setups")
        cls.csm_obj = csm_api_factory("rest")
        cls.log.info("Initiating Rest Client ...")

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-42713')
    def test_42713(self):
        """
        Test that user can check version compatability.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("[START] Testing Version Compatability with compatible versions")
        # For Happy path with valid inputs
        # call api compatible version
        payload = self.csm_obj.get_version_compatibility_payload("compatible")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("node", "cortx-control", payload)
        res_dict = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert res_dict["compatible"], "Compatibility Check failed"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying Reason response...")
            success_reason_msg = "Versions are Compatible"
            assert res_dict["reason"] == success_reason_msg, "response reason is not correct"
        self.log.info("[END] Testing Version Compatability")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-42789')
    def test_42789(self):
        """
        Test that user can check version compatability.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("[START] Testing Version Compatability with incompatible version rules")
        payload = self.csm_obj.get_version_compatibility_payload("incompatible")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("node", "cortx-control", payload)
        res_dict = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert not res_dict["compatible"], "Compatibility Check failed"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying Reason response...")
            success_reason_msg = "Versions are Compatible"
            assert res_dict["reason"] != success_reason_msg, "response reason is not correct"
        self.log.info("[END] Testing Version Compatability with incompatible version rules")

        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-42790')
    def test_42790(self):
        """
        Test that user can check version compatability for invalid payload.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_42790"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]

        self.log.info("[START] Testing Version Compatability with invalid resource")
        # For Non-Happy path with invalid inputs
        payload = self.csm_obj.get_version_compatibility_payload()
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("cluster", "cortx-cluster", payload)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed"
        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(response.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(response.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(response.json()["message"],
                                       Template(msg).substitute(resource="cluster"))
        self.log.info("[END] Testing Version Compatability with invalid resource")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-42719')
    def test_42719(self):
        """
        Test that user can check version compatability for invalid payload.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_42719"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]

        self.log.info("[START] Testing Version Compatability with invalid rules")
        payload = self.csm_obj.get_version_compatibility_payload("invalid_rules")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("node", "cortx-cluster", payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"

        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(response.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(response.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(response.json()["message"],
                                        Template(msg).substitute(rule=payload["requires"]))

        self.log.info("[END] Testing Version Compatability  with invalid rules")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.lc
    @pytest.mark.parallel
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-42792')
    def test_42792(self):
        """
        Test that user can check version compatability for invalid request body.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        test_cfg = self.csm_conf["test_42792"]
        resp_error_code = test_cfg["error_code"]
        resp_msg_id = test_cfg["message_id"]
        resp_data = self.rest_resp_conf[resp_error_code][resp_msg_id]
        resp_msg_index = test_cfg["message_index"]
        msg = resp_data[resp_msg_index]

        self.log.info("[START] Testing Version Compatability with invalid request body")
        payload = self.csm_obj.get_version_compatibility_payload("invalid_unknown_field")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("node", "cortx-cluster", payload)
        assert response.status_code == HTTPStatus.BAD_REQUEST, "Status code check failed"

        if CSM_REST_CFG["msg_check"] == "enable":
            self.log.info("Verifying error response...")
            assert_utils.assert_equals(response.json()["error_code"], resp_error_code)
            assert_utils.assert_equals(response.json()["message_id"], resp_msg_id)
            assert_utils.assert_equals(response.json()["message"],
                                       Template(msg).substitute(key="Random_key"))
        self.log.info("[END] Testing Version Compatability  with invalid  request body")
        self.log.info("##### Test ended -  %s #####", test_case_name)
