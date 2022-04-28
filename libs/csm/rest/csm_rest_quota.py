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
"""Test library for user and bucket quota related operations."""

import json
from random import SystemRandom
from string import Template

from commons.constants import Rest as const
from config import CSM_REST_CFG
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class GetSetQuota(RestTestLib):
    """RestIamUser contains all the Rest API calls for iam user operations"""

    def __init__(self):
        super.__init__()
        self.template_payload = Template(const.IAM_USER_DATA_PAYLOAD)
        self.iam_user = None
        self.csm_user = RestCsmUser()
        self.cryptogen = SystemRandom()

    @RestTestLib.authenticate_and_login
    def get_user_quota(self, uid, quota_type, **kwargs):
        """
        Get user or bucket quota
        :param uid: userid
        :param header: header for api authentication
        :param quota_type: Can be set to user or bucket
        :return: response
        """
        self.log.info("Get IAM user request....")
        if "headers" in kwargs.keys():
            header = kwargs["headers"]
        else:
            header = self.headers
        endpoint = self.config["get_set_quota"]
        endpoint = endpoint.format(uid, quota_type)
        response = self.restapi.rest_call("get", endpoint=endpoint,
                                          headers=header)
        self.log.info("Get user quota request successfully sent...")
        return response

    @RestTestLib.authenticate_and_login
    def set_user_quota(self, uid, quota_type, enabled, max_size, max_objects, **kwargs):
        """
        Set user or bucket quota
        :param uid: userid
        :param header: header for api authentication
        :param max_size: maximum size for object
        :param max_objects: maximum number of objects
        :param quota_type: Can be set to user or bucket
        :return: response
        """
        self.log.info("Get IAM user request....")
        if "headers" in kwargs.keys():
            header = kwargs["headers"]
        else:
            header = self.headers
        endpoint = self.config["get_set_quota"]
        endpoint = endpoint.format(uid, quota_type)
        set_quota_payload = {"quota_type": quota_type,"enabled": enabled,
               "max_size": max_size,
               "max_objects" : max_objects}
        response = self.restapi.rest_call("put", endpoint=endpoint,
                                          json_dict=json.dumps(set_quota_payload),
                                          headers=header)
        self.log.info("Set user quota request successfully sent...")
        return response
