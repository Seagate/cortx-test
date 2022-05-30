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
import pytest
import logging

from libs.csm.csm_setup import CSMConfigsCheck
from commons import configmanager
from commons import cortxlogging
from libs.csm.csm_interface import csm_api_factory
from http import HTTPStatus

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
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_information.yaml")
        cls.log.info("Ended test module setups")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_s3account_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3()
        assert setup_ready
        cls.created_iam_users = set()
        cls.csm_obj = csm_api_factory("rest")
        cls.log.info("Initiating Rest Client ...")

    def teardown_method(self):
        """
        Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        self.log.info("Teardown ended")

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
        self.log.info("[START] Testing Version Compatability")
        # For Happy path with valid inputs
        # call api compatible version
        payload = self.csm_obj.get_version_compatibility_payload("compatible")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("node", "control-control", payload)
        res_dict = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert res_dict["compatible"] == True, "Compatibility Check failed"
        assert res_dict["reason"] == "Versions are compatible for update.", "response reason is not correct"
        self.log.info("[END] Testing Version Compatability")

        self.log.info("[START] Testing Version Compatability with incompatible version rules")
        payload = self.csm_obj.get_version_compatibility_payload("incompatible")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("node", "control-control", payload)
        res_dict = response.json()
        assert response.status_code == HTTPStatus.OK, "Status code check failed"
        assert res_dict["compatible"] == False, "Compatibility Check failed"
        assert res_dict["reason"] != "Versions are compatible for update.", "response reason is not correct"
        self.log.info("[END] Testing Version Compatability with incompatible version rules")
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
        self.log.info("[START] Testing Version Compatability")
        # For Happy path with valid inputs
        payload = self.csm_obj.get_version_compatibility_payload()
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("cluster", "cortx-cluster", payload)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for invalid resource"

        payload = self.csm_obj.get_version_compatibility_payload("invalid_rules")
        self.log.info("payload :  %s", payload)
        response = self.csm_obj.verify_version_compatibility("cluster", "cortx-cluster", payload)
        assert response.status_code == HTTPStatus.NOT_FOUND, "Status code check failed for invalid resource"

        self.log.info("[END] Testing Version Compatability")
