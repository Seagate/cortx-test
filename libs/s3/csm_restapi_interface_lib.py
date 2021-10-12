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
#

"""CSM REST API operation Library."""

import json
import logging

from commons import errorcodes as err
from commons.constants import Rest
from commons.exceptions import CTException
from config import CSM_REST_CFG
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_test_lib import RestTestLib

LOGGER = logging.getLogger(__name__)


class CSMRestAPIInterfaceOperations(RestS3user):
    """CSM account operations using csm rest api."""

    def __init__(self):
        """s3 account operations constructor."""
        super(CSMRestAPIInterfaceOperations, self).__init__()
        self.endpoint = CSM_REST_CFG["csmuser_endpoint"]

    # pylint: disable=too-many-arguments
    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def create_csm_user_rest(self, uname, e_id, pwd, role="manage", alert_notice="true"):
        """
        This function will create new CSM user

        :param uname: Name of the CSM user
        :param e_id: Email ID of the CSM user
        :param pwd: Password of the CSM user
        :param role: User role type.
        :param alert_notice: Alert Notice for the CSM user
        :return: response of create user operation
        """
        try:
            # Building request url
            self.log.debug("Creating CSM user")
            self.log.debug(
                "Endpoint for CSM user creation is  %s", self.endpoint)

            # Creating required payload to be added for request
            user_data = {"username": uname,
                         "password": pwd,
                         "role": role,
                         "email": e_id,
                         "alert_notification": alert_notice}
            user_data = json.dumps(user_data)
            self.headers.update(Rest.CONTENT_TYPE)
            response = self.restapi.rest_call("post", endpoint=self.endpoint,
                                              data=user_data, headers=self.headers)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, response
            return True, response.json()
        except BaseException as error:
            self.log.error("%s %s: %s",
                           Rest.EXCEPTION_ERROR,
                           CSMRestAPIInterfaceOperations.create_csm_user_rest.__name__,
                           error)
            raise CTException(
                err.CSM_REST_POST_REQUEST_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def delete_csm_user_rest(self, username):
        """
        This function will Delete CSM user

        :param username: Name of user
        :return: response of delete user operation
        """
        try:
            # Building request url
            self.log.debug("Deleting CSM user")
            endpoint = f"{self.endpoint}/{username}"
            self.log.debug(
                "Endpoint for CSM user creation is  %s", endpoint)
            # Fetching api response
            self.headers.update(Rest.CONTENT_TYPE)
            response = self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, response
            return True, response.json()
        except BaseException as error:
            self.log.error("%s %s: %s",
                           Rest.EXCEPTION_ERROR,
                           CSMRestAPIInterfaceOperations.delete_csm_user_rest.__name__,
                           error)
            raise CTException(err.CSM_REST_DELETE_REQUEST_FAILED, error) from error

    # pylint: disable=too-many-arguments
    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def edit_csm_user_rest(
            self,
            user: str = None,
            role: str = None,
            email: str = None,
            password: str = None,
            current_password: str = None):
        """
        This function will Edit CSM user

        :param user: Name of the CSM user
        :param role: Role of the CSM user
        :param email: Email ID of the CSM user
        :param password: New password of the CSM user
        :param current_password: Current password of the CSM user
        :return: response of edit CSM user operation
        """
        try:
            endpoint = f"{self.endpoint}/{user}"
            patch_payload = {}
            if role is not None:
                patch_payload.update({"role": role})
            if email is not None:
                patch_payload.update({"email": email})
            if password is not None:
                patch_payload.update({"password": password})
            if current_password is not None:
                patch_payload.update({"current_password": current_password})
            self.log.info(patch_payload)
            response = self.restapi.rest_call("patch", data=patch_payload, endpoint=endpoint,
                                              headers=self.headers)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, response
            return True, response.json()
        except BaseException as error:
            self.log.error("%s %s: %s",
                           Rest.EXCEPTION_ERROR,
                           CSMRestAPIInterfaceOperations.edit_csm_user_rest.__name__,
                           error)
            raise CTException(err.CSM_REST_DELETE_REQUEST_FAILED, error) from error
