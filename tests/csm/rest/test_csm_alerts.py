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
"""Tests CSM Alerts scenarios using REST API
"""
import logging
import random

from random import SystemRandom
import pytest
from commons import configmanager
from commons import constants as consts
from commons import cortxlogging
from commons.constants import Rest as const
from commons.helpers.node_helper import Node
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib


class TestCsmAlerts():
    """
    REST API Test cases for CSM Alerts
    """

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        if CMN_CFG["product_family"] == consts.PROD_FAMILY_LR and \
                CMN_CFG["product_type"] == consts.PROD_TYPE_NODE:
            cls.node_obj = Node(hostname=CMN_CFG["nodes"][0]["hostname"],
                                username=CMN_CFG["nodes"][0]["username"],
                                password=CMN_CFG["nodes"][0]["password"])
        else:
            cls.node_obj = LogicalNode(hostname=CMN_CFG["nodes"][0]["hostname"],
                                username=CMN_CFG["nodes"][0]["username"],
                                password=CMN_CFG["nodes"][0]["password"])
        cls.csm_alerts = SystemAlerts(cls.node_obj)
        cls.log.info("Checking if predefined CSM users are present...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_csm_alert.yaml")
        cls.resolve_type = None
        cls.alert_timeout = None
        cls.alert_type = None
        cls.cryptogen = SystemRandom()
        cls.ras_test_obj = RASTestLib(host=CMN_CFG["nodes"][0]["hostname"],
                                      username=CMN_CFG["nodes"][0]["username"],
                                      password=CMN_CFG["nodes"][0]["password"])
        cls.log.info("Initiating Rest Client for Alert ...")
        field_list = ("primary_controller_ip", "secondary_controller_ip",
                      "primary_controller_port", "secondary_controller_port",
                      "user", "password", "secret")
        cls.log.info("Putting expected values in KV store")
        for field in field_list:
            _ = cls.ras_test_obj.put_kv_store(CMN_CFG["enclosure"]["enclosure_user"],
                                                CMN_CFG["enclosure"]["enclosure_pwd"],
                                                field)

    def teardown_method(self):
        """Teardown method
        """
        if self.resolve_type is not None:
            result = self.csm_alerts.resolve_alert(self.resolve_type, 100)
            assert result, "Teardown: Failed to resolve alert"

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17185')
    def test_607(self):
        """
        Test that Get request with valid Severity ,Acknowledged as false and Resolved parameters
        as true returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_607"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_607"]["alert_type"]
        self.resolve_type = self.csm_conf["test_607"]["resolve_type"]
        alert_severity = self.csm_conf["test_607"]["alert_severity"]
        resolve_severity = self.csm_conf["test_607"]["resolve_severity"]
        self.log.info("Creating alert and checking get alert response with acknowledged False and "
                      "resolved True")
        result = self.csm_alerts.create_alert(self.alert_type, self.alert_timeout,
                                              acknowledged=False, resolved=True,
                                              severity=alert_severity)
        assert result, "Failed to create alert"
        new_alerts, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "Unack resolved Alerts before and after create alert is not same."
        response = self.csm_alerts.get_alerts(
            alert_id=self.cryptogen.randrange(new_alerts))
        assert_utils.assert_equals(response.json()['severity'], alert_severity)
        self.log.info("Resolving alert and checking get alert response with acknowledged False and "
                      "resolved True")
        result = self.csm_alerts.resolve_alert(self.resolve_type, self.alert_timeout,
                                               acknowledged=False, resolved=True,
                                               severity=resolve_severity)
        assert result, "Failed to resolve alert"
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert diff_resolve , "Resolved and UnAcknowledged alert after alert resolve is same."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17183')
    def test_608(self):
        """
        Test that Get request with Acknowledged False and Resolved parameters as true and severity
        error returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_608"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_608"]["alert_type"]
        alert_severity = self.csm_conf["test_608"]["alert_severity"]
        self.log.info(
            "Creating alert and checking get alert response with acknowledged False, resolved True")
        result = self.csm_alerts.create_alert(self.alert_type, self.alert_timeout,
                                              acknowledged=False, resolved=True,
                                              severity=alert_severity)
        assert result, "Failed to create alert"
        new_alerts, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "Unack resolved Alerts before and after create alert is not same."
        response = self.csm_alerts.get_alerts(
            alert_id=random.choice(new_alerts))
        assert_utils.assert_equals(response.json()['severity'], alert_severity)
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17184')
    def test_609(self):
        """
        Test that Get request with specific severity returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_609"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_609"]["alert_type"]
        self.resolve_type = self.csm_conf["test_609"]["resolve_type"]
        alert_severity = self.csm_conf["test_609"]["alert_severity"]
        self.log.info(
            "Creating alert and checking get alert response with severity param")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, severity=alert_severity)
        assert result, "Failed to create alert"
        new_alerts, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert diff_alert , "No new alert created"
        for alert_id in after_alerts:
            response = self.csm_alerts.get_alerts(alert_id=alert_id)
            assert_utils.assert_equals(
                response.json()['severity'], alert_severity, "Severity check failed!")
        response = self.csm_alerts.get_alerts(
            alert_id=random.choice(new_alerts))
        assert_utils.assert_equals(response.json()['severity'], alert_severity)
        self.log.info(
            "Resolving alert and checking get alert response with severity param")
        result = self.csm_alerts.resolve_alert(
            self.resolve_type, self.alert_timeout, severity=alert_severity)
        assert result, "Failed to resolve alert"
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-19207')
    def test_610(self):
        """
        Test that Get request with specific severity and resolved parameter as true returns
        correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_610"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_610"]["alert_type"]
        self.resolve_type = self.csm_conf["test_610"]["resolve_type"]
        alert_severity = self.csm_conf["test_610"]["alert_severity"]
        resolve_severity = self.csm_conf["test_610"]["resolve_severity"]
        self.log.info(
            "Creating alert and checking get alert response with severity param")
        result = self.csm_alerts.create_alert(self.alert_type, self.alert_timeout,
                                              severity=alert_severity, resolved=True)
        assert result, "Failed to create alert"
        _, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "Resolved alerts before and after alert is not same."
        for alert_id in after_alerts:
            response = self.csm_alerts.get_alerts(alert_id=alert_id)
            assert_utils.assert_equals(
                response.json()['severity'], alert_severity, "Severity check failed!")
            assert response.json()['resolved'], "Resolved check failed!"
        self.log.info(
            "Resolving alert and checking get alert response with severity param")
        result = self.csm_alerts.resolve_alert(self.resolve_type, self.alert_timeout,
                                               severity=resolve_severity, resolved=True)
        before_resolve, after_resolve = result
        for alert_id in after_resolve:
            response = self.csm_alerts.get_alerts(alert_id=alert_id)
            assert_utils.assert_equals(
                response.json()['severity'], resolve_severity, "Severity check failed!")
            assert_utils.assert_equals(
                response.json()['resolved'], True, "Resolved check failed!")
        assert result, "Failed to resolve alert"
        diff_alert = list(set(after_resolve) - set(before_resolve))
        assert diff_alert , "Resolved alerts before and after alert is not same."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-19208')
    def test_611(self):
        """
        Test that Get request with specific severity and resolved parameter as false returns
        correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_611"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_611"]["alert_type"]
        self.resolve_type = self.csm_conf["test_611"]["resolve_type"]
        alert_severity = self.csm_conf["test_611"]["alert_severity"]
        resolve_severity = self.csm_conf["test_611"]["resolve_severity"]
        self.log.info(
            "Creating alert and checking get alert response with severity param")
        result = self.csm_alerts.create_alert(self.alert_type, self.alert_timeout,
                                              severity=alert_severity, resolved=False)
        assert result, "Failed to create alert"
        _, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert diff_alert , "No new alert created"
        for alert_id in after_alerts:
            response = self.csm_alerts.get_alerts(alert_id=alert_id)
            assert_utils.assert_equals(
                response.json()['severity'], alert_severity, "Severity check failed!")
            assert not response.json()['resolved'], "Resolved check failed!"
        self.log.info(
            "Resolving alert and checking get alert response with severity param")
        result = self.csm_alerts.resolve_alert(self.resolve_type, self.alert_timeout,
                                               severity=resolve_severity, resolved=False)
        _, after_resolve = result
        for alert_id in after_resolve:
            response = self.csm_alerts.get_alerts(alert_id=alert_id)
            assert_utils.assert_equals(
                response.json()['severity'], resolve_severity, "Severity check failed!")
            assert not response.json()['resolved'], "Resolved check failed!"
        assert result, "Failed to resolve alert"
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17178')
    def test_616(self):
        """
        Test that Get request with Resolved parameter as true returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_616"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_616"]["alert_type"]
        self.resolve_type = self.csm_conf["test_616"]["resolve_type"]
        self.log.info(
            "Creating alert and checking get alert response with resolved True...")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, resolved=True)
        assert result, "Failed to create alert."
        new_alerts, before_alerts, after_alerts = result
        for new_alert in new_alerts:
            self.log.info("New Alert created: %s", new_alert)
            response = self.csm_alerts.get_alerts(alert_id=new_alert)
            self.log.info("New Alert details : %s", response.json())
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "Resolved alerts before and after create alert is not same."
        self.log.info(
            "Resolving alert and checking get alert response with resolved True...")
        result = self.csm_alerts.resolve_alert(
            self.resolve_type, self.alert_timeout, resolved=True)
        assert result, "Failed to resolve alert."
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert diff_resolve , "Alert is not resolved on CSM."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17179')
    def test_617(self):
        """
        Test that Get request with Resolved parameter as false returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_617"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_617"]["alert_type"]
        self.resolve_type = self.csm_conf["test_617"]["resolve_type"]
        self.log.info(
            "Creating alert and checking get alert response with resolved False...")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, resolved=False)
        assert result, "Failed to create alert."
        new_alerts, before_alerts, after_alerts = result
        for new_alert in new_alerts:
            self.log.info("New Alert created: %s", new_alert)
            response = self.csm_alerts.get_alerts(alert_id=new_alert)
            self.log.info("New Alert details : %s", response.json())
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert diff_alert , "Not resolved alerts before and after create alert is same."
        self.log.info(
            "Resolving alert and checking get alert response with resolved False...")
        result = self.csm_alerts.resolve_alert(
            self.resolve_type, self.alert_timeout, resolved=False)
        assert result, "Failed to resolve alert."
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert diff_resolve , "Alert is not resolved on CSM."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17180')
    def test_618(self):
        """
        Test that Get request with Acknowledged parameter as true returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_618"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_618"]["alert_type"]
        self.resolve_type = self.csm_conf["test_618"]["resolve_type"]
        self.log.info(
            "Creating alert and checking get alert response with acknowledged True...")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, acknowledged=True)
        assert result, "Failed to create alert."
        new_alerts, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "Acknowledged alerts before and after create alert is not same."
        for new_alert in new_alerts:
            self.log.info("New Alert created: %s", new_alert)
            response = self.csm_alerts.get_alerts(alert_id=new_alert)
            self.log.info("New Alert details : %s", response.json())
            self.log.info("Acknowledging alert: %s", new_alert)
            self.csm_alerts.edit_alerts(new_alert, ack=True)
        self.log.info("Get alerts with acknowledged True...")
        response = self.csm_alerts.get_alerts(acknowledged=True)
        expected_response = const.SUCCESS_STATUS
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed.")
        ack_alerts = self.csm_alerts.extract_alert_ids(response)
        diff_ack = list(set(ack_alerts) - set(after_alerts))
        assert diff_ack , "No new alert acknowledged."
        self.log.info(
            "Resolving alert and checking get alert response with acknowledged True...")
        result = self.csm_alerts.resolve_alert(
            self.resolve_type, self.alert_timeout, acknowledged=True)
        assert result, "Failed to resolve alert"
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert diff_resolve , "Resolved and Acknowledged alert is not moved to history."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17181')
    def test_619(self):
        """
        Test that Get request with Acknowledged parameter as true and Resolved parameter as false
        returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_619"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_619"]["alert_type"]
        self.resolve_type = self.csm_conf["test_619"]["resolve_type"]
        self.log.info("Creating alert and checking get alert response with acknowledged True and "
                      "resolved False")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, acknowledged=True, resolved=False)
        assert result, "Failed to create alert."
        new_alerts, before_alerts, after_alerts = result
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "Ack unresolved alerts before and after create alert is not same."
        for new_alert in new_alerts:
            self.log.info("New Alert created: %s", new_alert)
            response = self.csm_alerts.get_alerts(alert_id=new_alert)
            self.log.info("New Alert details : %s", response.json())
            self.log.info("Acknowledging new alert...")
            self.csm_alerts.edit_alerts(new_alert, ack=True)
        self.log.info(
            "Get alerts with acknowledged True and resolved False...")
        response = self.csm_alerts.get_alerts(
            acknowledged=True, resolved=False)
        expected_response = const.SUCCESS_STATUS
        assert_utils.assert_equals(response.status_code, expected_response,
                                   "Status code check failed.")
        ack_alerts = self.csm_alerts.extract_alert_ids(response)
        diff_ack = list(set(ack_alerts) - set(after_alerts))
        assert diff_ack , "No new alert acknowledged."
        self.log.info("Resolving alert and checking get alert response with acknowledged True and "
                      "resolved False")
        result = self.csm_alerts.resolve_alert(
            self.resolve_type, self.alert_timeout, acknowledged=True, resolved=False)
        assert result, "Failed to resolve alert."
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert diff_resolve , "Ack unresolved alerts before and after resolve alert is same."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.tags('TEST-19209')
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    def test_620(self):
        """
        Test that Get request with Acknowledged parameter as false returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_620"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_620"]["alert_type"]
        self.resolve_type = self.csm_conf["test_620"]["resolve_type"]
        self.log.info(
            "Creating alert and checking get alert response with acknowledged False")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, acknowledged=False)
        assert result, "Failed to create alert."
        new_alerts, before_alerts, after_alerts = result
        for new_alert in new_alerts:
            self.log.info("New Alert created: %s", new_alert)
            response = self.csm_alerts.get_alerts(alert_id=new_alert)
            self.log.info("New Alert details : %s", response.json())
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert diff_alert , "UnAck Alerts before and after create alert is same."
        self.log.info("Resolving alert and checking get alert response with acknowledged False.")
        result = self.csm_alerts.resolve_alert(self.resolve_type, self.alert_timeout,
                                               acknowledged=False)
        assert result, "Failed to resolve alert."
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert not diff_resolve, "UnAck Alerts before and after resolve alert is same."
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17182')
    def test_621(self):
        """
        Test that Get request with Acknowledged parameter as false and Resolved parameter as
        true returns correct data.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.alert_timeout = self.csm_conf["test_621"]["alert_timeout"]
        self.alert_type = self.csm_conf["test_621"]["alert_type"]
        self.resolve_type = self.csm_conf["test_621"]["resolve_type"]
        self.log.info("Creating alert and checking get alert response with acknowledged False and "
                      "resolved True")
        result = self.csm_alerts.create_alert(
            self.alert_type, self.alert_timeout, acknowledged=False, resolved=True)
        assert result, "Failed to create alert."
        new_alerts, before_alerts, after_alerts = result
        for new_alert in new_alerts:
            self.log.info("New Alert created: %s", new_alert)
            response = self.csm_alerts.get_alerts(alert_id=new_alert)
            self.log.info("New Alert details : %s", response.json())
        diff_alert = list(set(after_alerts) - set(before_alerts))
        assert not diff_alert , "UnAck Resolved Alerts before and after create alert is not same."
        self.log.info("Resolving alert and checking get alert response with acknowledged False and"
                      " resolved True")
        result = self.csm_alerts.resolve_alert(
            self.resolve_type, self.alert_timeout, acknowledged=False, resolved=True)
        assert result, "Failed to resolve alert."
        before_resolve, after_resolve = result
        diff_resolve = list(set(after_resolve) - set(before_resolve))
        assert diff_resolve , "UnAck Resolved Alerts before and after resolve alert is same"
        self.resolve_type = None
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15725')
    def test_1225(self):
        """
        Test that CSM user with role manager can perform GET, POST (for adding comments) API
        request for alerts
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Testing that CSM user with role manager can perform GET, POST (for adding comments)"
            " API request for alerts ")
        comment_data = self.csm_conf["test_1225"]

        # Verifying CSM admin user can perform GET API request for alerts
        self.log.info(
            "Step 1: Verifying CSM admin user can perform GET API request for alerts")

        response = self.csm_alerts.get_alerts(login_as="csm_admin_user")

        self.log.info("Verifying the status code %s and response %s returned",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        assert response.json()
        alert_id = response.json()["alerts"][0]["alert_uuid"]

        self.log.info(
            "Step 1: Verified CSM admin user can perform GET API request for alerts")

        # Verifying CSM admin user can perform POST API request for alerts for adding comments
        self.log.info("Step 2: Verifying CSM admin user can perform POST API request for alerts for"
                      " adding comments")

        response_add = self.csm_alerts.add_comment_to_alerts(
            alert_id=alert_id, comment_text=comment_data["comment_text_admin_user"],
            login_as="csm_admin_user")

        self.log.info("Verifying the status code %s returned",
                      response_add.status_code)
        assert_utils.assert_equals(response_add.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Verifying that comment was added to the alert")
        response = self.csm_alerts.verify_added_alert_comment(
            user="csm_admin_user", alert_id=alert_id,
            response_alert_comment_added=response_add.json())
        assert response

        self.log.info(
            "Step 2: Verified CSM admin user can perform POST API request for alerts for adding "
            "comments")

        # Verifying CSM manage user can perform GET API request for alerts
        self.log.info(
            "Step 3: Verifying CSM manage user can perform GET API request for alerts")

        response = self.csm_alerts.get_alerts(login_as="csm_user_manage")

        self.log.info("Verifying the status code %s and response %s returned",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        assert response.json()
        alert_id = response.json()["alerts"][0]["alert_uuid"]
        self.log.info(
            "Step 3: Verified CSM manage user can perform GET API request for alerts")

        # Verifying CSM manage user can perform POST API request for alerts for adding comments
        self.log.info("Step 4: Verifying CSM manage user can perform POST API request for alerts "
                      "for adding comments")

        response_add = self.csm_alerts.add_comment_to_alerts(
            alert_id=alert_id, comment_text=comment_data["comment_text_manage_user"],
            login_as="csm_user_manage")

        self.log.info("Verifying the status code %s returned",
                      response_add.status_code)
        assert_utils.assert_equals(response_add.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Verifying that comment was added to the alert")
        response = self.csm_alerts.verify_added_alert_comment(
            user="csm_user_manage", alert_id=alert_id,
            response_alert_comment_added=response_add.json())
        assert response

        self.log.info("Step 4: Verified CSM manage user can perform POST API request for alerts for"
                      " adding comments")

        self.log.info("Verified that CSM user with role manager can perform GET, POST (for adding "
                      "comments) API request for alerts ")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15726')
    def test_1231(self):
        """
        Test that CSM user with role monitor can perform GET API request for alerts
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Testing that CSM user with role monitor can perform GET API request for "
                      "alerts")

        # Verifying CSM monitor user can perform GET API request for alerts
        self.log.info("Step 1: Verifying CSM monitor user can perform GET API request for alerts")

        response = self.csm_alerts.get_alerts(login_as="csm_user_monitor")

        self.log.info("Verifying the status returned %s", response.status_code)
        assert_utils.assert_equals(response.status_code, const.SUCCESS_STATUS)

        self.log.info("Step 1: Verified CSM monitor user can perform GET API request for alerts")

        self.log.info("Verified that CSM monitor user can perform GET API request for alerts")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16215')
    def test_1448(self):
        """
        Verify Rest request with default arguments returns  appropriate records.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Testing that Rest request with default arguments returns  appropriate records")

        self.log.info("Fetching get alerts api response...")
        response = self.csm_alerts.get_alerts()
        self.log.debug("Verifying the response %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.debug("Verified the request was successful")

        self.log.info("Step 1: Verifying that acknowledged and resolved combined status is not "
                      "true for all the alerts returned")
        self.log.info("Alert count is: %s",
                      len(response.json()["alerts"]))
        for i in range(0, len(response.json()["alerts"])):
            self.log.info("Alert %s acknowledged status is %s and resolved status is %s",
                          response.json()["alerts"][i]["alert_uuid"],
                          response.json()["alerts"][i]["acknowledged"],
                          response.json()["alerts"][i]["resolved"])
            if (response.json()["alerts"][i]["acknowledged"] and
                    response.json()["alerts"][i]["resolved"]):
                self.log.debug("Alert %s acknowledged status is %s and resolved status is %s",
                               response.json()["alerts"][i]["alert_uuid"],
                               response.json()["alerts"][i]["acknowledged"],
                               response.json()["alerts"][i]["resolved"])
                self.log.error("The acknowledged and resolved combined status is true for the "
                               "alert %s", response.json()["alerts"][i]["alert_uuid"])
                assert False
        self.log.info(
            "Step 1: Verified that acknowledged and resolved combined status is not true for all"
            " the alerts returned")

        self.log.info("Step 2: Verifying if alerts are returned in descending order as per the "
                      "alert created date")
        created_date_list = [item["created_time"]
                             for item in response.json()["alerts"]]
        self.log.info("Created date list for all alerts is:%s",
                      created_date_list)
        assert all(created_date_list[i] >= created_date_list[i + 1]
                   for i in range(len(created_date_list) - 1))
        self.log.info("Step 2: Verified that alerts are returned in descending order as per the "
                      "alert created date")

        self.log.info(
            "Verified that Rest request with default arguments returns  appropriate records")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16216')
    def test_1457(self):
        """
        Test that user is able to un-acknowledge the alert using rest request.
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Testing that user is able to un-acknowledge the alert using rest request.")

        self.log.info("Fetching alerts...")
        response = self.csm_alerts.get_alerts(resolved=False)
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Reading the alert id...")
        alert_id = response.json()["alerts"][0]["alert_uuid"]

        self.log.info("Acknowleding alert %s", alert_id)
        response = self.csm_alerts.edit_alerts(alert_id=alert_id, ack=True)
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Fetching acknowledged alerts...")
        response = self.csm_alerts.get_alerts(acknowledged=True)
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Verifying if alert %s is acknowledged", alert_id)
        alert_id_list = [item["alert_uuid"]
                         for item in response.json()["alerts"]]
        self.log.debug("Alert ids are: %s", alert_id_list)
        assert alert_id in alert_id_list
        self.log.info("Verified alert %s is acknowledged", alert_id)

        self.log.info("Not acknowleging the alert %s", alert_id)
        response = self.csm_alerts.edit_alerts(
            alert_id=alert_id, ack=False)
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Fetching alerts...")
        response = self.csm_alerts.get_alerts()
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info(
            "Verifying if alert %s is unacknowledged", alert_id)
        alert_id_list = [item["alert_uuid"]
                         for item in response.json()["alerts"]]
        self.log.debug("Alert ids are: %s", alert_id_list)
        assert alert_id in alert_id_list

        self.log.info("Verified alert %s is unacknowledged", alert_id)

        self.log.info(
            "Verified that user is able to un-acknowledge the alert using rest request.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    # pylint: disable=too-many-statements
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-16937')
    def test_1039(self):
        """
        Test that S3 account should not have access to alert operations
        :avocado: tags=rest_csm_alerts_test
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Testing that S3 account does not have access to alert operations ")
        comment_data = self.csm_conf["test_1039"]["comment_text"]
        self.log.info("Fetching alerts...")
        response = self.csm_alerts.get_alerts()
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)

        self.log.info("Reading the alert id...")
        alert_id = response.json()["alerts"][0]["alert_uuid"]

        self.log.info(
            "Step 1: Verifying S3 account cannot perform GET API request for alerts")
        response = self.csm_alerts.get_alerts(login_as="s3account_user")
        self.log.info("Verifying the response %s returned", response)
        assert_utils.assert_equals(response.status_code, const.FORBIDDEN)
        self.log.info(
            "Step 1: Verified S3 account cannot perform GET API request for alerts")

        self.log.info(
            "Step 2: Verifying S3 account cannot acknowledge alerts")
        self.log.info("Getting all the alerts which are not acknowledged")
        response = self.csm_alerts.get_alerts(
            acknowledged=False, limit=None, login_as="csm_admin_user")
        # Extract the alert IDs
        self.log.info("Extracting the alert ids")
        alert_id_list = self.csm_alerts.extract_alert_ids(response)
        self.log.info("Trying to acknowledge alerts by logging in as S3 user")
        response = self.csm_alerts.ack_all_unacknowledged_alerts(
            alert_id_list=alert_id_list, login_as="s3account_user")
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code, const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified S3 account cannot acknowledge alerts")

        self.log.info(
            "Step 3: Verifying S3 account cannot perform GET API request for specific alert")
        response = self.csm_alerts.get_alerts(
            alert_id=alert_id, login_as="s3account_user")
        self.log.info("Response returned is:%s ", response)
        assert_utils.assert_equals(response.status_code, const.FORBIDDEN)
        self.log.info(
            "Step 3: Verified S3 account cannot perform GET API request for specific alert")

        self.log.info(
            "Step 4: Verifying S3 account cannot edit specific alert")
        response = self.csm_alerts.edit_alerts(
            alert_id=alert_id, ack=True, login_as="s3account_user")
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 4: Verified S3 account cannot S3 account cannot edit specific alert")

        self.log.info(
            "Step 5: Verifying S3 account cannot perform request to get alert history")
        response = self.csm_alerts.get_alerts_history(
            login_as="s3account_user")
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info("Step 5: Verified S3 account cannot perform request to get alert history")

        self.log.info("Step 6: Verifying S3 account cannot perform request to get alert history for"
                      " specific alert")
        response = self.csm_alerts.get_specific_alert_history(
            alert_id=alert_id, login_as="s3account_user")
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info("Step 6: Verified S3 account cannot perform request to get alert history "
                      "for specific alert")

        self.log.info(
            "Step 7: Verifying S3 account cannot perform request to get alert comments for specific"
            " alert")
        response = self.csm_alerts.get_alert_comments(
            alert_id=alert_id, login_as="s3account_user")
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info("Step 7: Verified S3 account cannot perform request to get alert comments for"
                      " specific alert")

        self.log.info("Step 8: Verifying S3 account cannot perform request to add comments to a "
                      "specific alert")
        response = self.csm_alerts.add_comment_to_alerts(
            alert_id=alert_id, comment_text=comment_data, login_as="s3account_user")
        self.log.debug("Response is: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info("Step 8: Verified S3 account cannot perform request to add comments to a "
                      "specific alert")

        self.log.info("##### Test ended -  %s #####", test_case_name)
