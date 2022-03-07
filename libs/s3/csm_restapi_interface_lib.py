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

"""CSM REST API operation Library."""

import json
import logging
from http import HTTPStatus

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
        super().__init__()
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
        :return: bool, response of create user operation
        """
        try:
            # Building request url
            self.log.debug("Creating CSM user")
            self.log.debug("Endpoint for CSM user creation is  %s", self.endpoint)
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
            if response.status_code != HTTPStatus.OK and response.ok is not True:
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
        :return: bool, response of delete user operation
        """
        try:
            # Building request url
            self.log.debug("Deleting CSM user")
            endpoint = f"{self.endpoint}/{username}"
            self.log.debug("Endpoint for CSM user creation is  %s", endpoint)
            # Fetching api response
            self.headers.update(Rest.CONTENT_TYPE)
            response = self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)
            if response.status_code != HTTPStatus.OK and response.ok is not True:
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
        :return: bool, response of edit CSM user operation
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

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def reset_s3_user_password(
            self,
            username: str = None,
            new_password: str = None,
            reset_access_key: str = "False"):
        """
        This function will reset s3 account user password
        :param username: Name of S3 account user
        :param reset_access_key: True reset of access key also required with reset password
        :param new_password: New password to be set for s3 user
        :return: bool, response of reset s3 user password operation
        """
        # Prepare patch for s3 account user
        patch_payload = {"password": new_password, "reset_access_key": reset_access_key}
        self.log.debug("editing user {}".format(patch_payload))
        endpoint = "{}/{}".format(self.config["s3accounts_endpoint"], username)
        self.log.debug("Endpoint for s3 accounts is {}".format(endpoint))
        self.headers.update(Rest.CONTENT_TYPE)
        try:
            # Fetching api response
            response = self.restapi.rest_call("patch", data=json.dumps(patch_payload),
                                              endpoint=endpoint, headers=self.headers)
            if response.status_code != HTTPStatus.OK and response.ok is not True:
                return False, response
            return True, response.json()
        except BaseException as error:
            self.log.error("%s %s: %s",
                           Rest.EXCEPTION_ERROR,
                           CSMRestAPIInterfaceOperations.reset_s3_user_password.__name__,
                           error)
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error) from error
