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
import math
import time
from http import HTTPStatus
from random import SystemRandom
from string import Template

from commons import configmanager
from commons.constants import Rest as const
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.s3 import s3_misc

class GetSetQuota(RestTestLib):
    """RestIamUser contains all the Rest API calls for iam user operations"""

    def __init__(self):
        super(GetSetQuota, self).__init__()
        self.template_payload = Template(const.IAM_USER_DATA_PAYLOAD)
        self.iam_user = None
        self.cryptogen = SystemRandom()
        self.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_capacity.yaml")
        self.bucket = "iam-user-bucket-" + str(int(time.time_ns()))
        self.obj_name_prefix = "created_obj"
        self.obj_name = f'{self.obj_name_prefix}{time.perf_counter_ns()}'

    @RestTestLib.authenticate_and_login
    def get_user_quota(self, uid, **kwargs):
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
        endpoint = endpoint.format(uid)
        response = self.restapi.rest_call("get", endpoint=endpoint,
                                          headers=header)
        self.log.info("Get user quota request successfully sent...")
        return response

    #pylint disable=no-self-use
    def iam_user_quota_payload(self):
        """
        Create IAM user quota payload
        """
        payload = {}
        quota_type = self.csm_conf["test_values"]["quota_type"]
        enabled = self.csm_conf["test_values"]["enabled"]
        max_size = self.csm_conf["test_values"]["max_size"]
        max_objects = self.csm_conf["test_values"]["max_objects"]
        payload.update({"quota_type": quota_type})
        payload.update({"enabled": enabled})
        payload.update({"max_size": max_size})
        payload.update({"max_objects" : max_objects})
        self.log.info("Payload: %s", payload)
        return payload

    @RestTestLib.authenticate_and_login
    def set_user_quota(self, uid, payload: dict, **kwargs):
        """
        Set user or bucket quota
        :param uid: userid
        :param header: header for api authentication
        :param payload: IAM User quota payload
        :return: response
        """
        self.log.info("Get IAM user request....")
        if "headers" in kwargs.keys():
            header = kwargs["headers"]
        else:
            header = self.headers
        endpoint = self.config["get_set_quota"]
        endpoint = endpoint.format(uid)
        response = self.restapi.rest_call("put", endpoint=endpoint,
                                          json_dict=json.dumps(payload),
                                          headers=header)
        self.log.info("Set user quota request successfully sent...")
        return response

    def verify_get_set_user_quota(self, uid: str, payload: dict, verify_response=False,
                                  expected_response = HTTPStatus.CREATED):
        """
        Verify get and set user quota
        """
        set_response = self.set_user_quota(uid, payload)
        result = True
        if set_response.status_code == expected_response:
            self.log.info("SET response check passed.")
        else:
            self.log.error("SET response check failed")
            result = False
            return result, set_response
        get_response = self.get_user_quota(uid)
        if get_response.status_code == expected_response:
            result = True
            get_response = get_response.json()
            if verify_response:
                self.log.info("Checking response...")
                for key, value in get_response.items():
                    self.log.info("Expected response for %s: %s", key, value)
                    if key in ("enabled","max_size","max_objects","check_on_raw"):
                        continue
                    if key == "max_size_kb":
                        payload.update({"max_size_kb":get_response["max_size"]/1000})
                    self.log.info("Actual response for %s: %s", key, payload[key])
                    if value != payload[key]:
                        self.log.error("Actual and expected response for %s didnt match", key)
                        result = False
        else:
            self.log.error("Status code check failed.")
            result = False
        return result, get_response

    def verify_max_size(self, max_size: int, akey: str, skey: str):
        """
        Perform put operation with 1 object and then perform put
        of random size and check if that fails
        """
        self.log.info("Perform Put operation for 1 object of max size")
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                          akey, skey, object_size=max_size)
        assert resp, "Put object Failed"
        self.log.info("Perform Put operation of Random size and 1 object")
        random_size = self.cryptogen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                          akey, skey, object_size=random_size)
        assert not resp, "User is able to perform put object after exceeding max_size"

    def verify_max_objects(self, max_size: int, max_objects: int, akey: str, skey: str):
        """
        Perform put operation of N object of max_size/obj_cnt and
        check if one more put fails
        """
        self.log.info("Perform Put operation of small size and N object")
        small_size = math.floor(max_size / max_objects)
        for _ in range(0, max_objects):
            resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                              akey, skey, object_size=small_size)
            assert resp, "Put object Failed"
        self.log.info("Perform Put operation of Random size and 1 object")
        random_size = self.cryptogen.randrange(1, max_size)
        resp = s3_misc.create_put_objects(self.obj_name, self.bucket,
                                          akey, skey, object_size=random_size)
        assert not resp, "User is able to perform put object after exceeding max_objects"
