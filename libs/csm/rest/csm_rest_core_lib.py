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
""" This is the core module for REST API. """

import json
import logging
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from commons import constants
from commons.constants import Rest as const
from config import CMN_CFG

class RestClient:
    """
        This is the class for rest calls
    """

    def __init__(self, config):
        """
        This function will initialize this class
        :param config: configuration of setup
        """
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.log = logging.getLogger(__name__)
        self._config = config
        self._request = {"get": requests.get, "post": requests.post,
                         "patch": requests.patch, "delete": requests.delete,
                         "put": requests.put}
        self._base_url = "{}:{}".format(
            self._config["mgmt_vip"], str(self._config["port"]))
        self._json_file_path = self._config[
            "jsonfile"] if 'jsonfile' in self._config else const.JOSN_FILE
        self.secure_connection = self._config["secure"]

    # pylint: disable=too-many-arguments
    def rest_call(self, request_type, endpoint=None,
                  data=None, headers=None, params=None, json_dict=None,
                  save_json=False):
        """
        This function will request REST methods like GET, POST ,PUT etc.
        :param request_type: get/post/delete/update etc
        :param endpoint: endpoint url
        :param secure_connection: HTTP / HTTPS connection required
        :param data: data required for REST call
        :param headers: headers required for REST call
        :param params: parameters required for REST call
        :param save_json: In case user required to store json file
        :return: response of the request
        """
        # Building final endpoint request url
        set_secure = const.SSL_CERTIFIED if self.secure_connection else const.NON_SSL
        if endpoint is None:
            request_url = "{}{}".format(set_secure, self._base_url)
        else:
            request_url = "{}{}{}".format(set_secure, self._base_url, endpoint)
        self.log.debug("Request URL : %s", request_url)
        self.log.debug("Request type : %s", request_type.upper())
        self.log.debug("Header : %s", headers)
        self.log.debug("Parameters : %s", params)
        self.log.debug("json_dict: %s", json.dumps(json_dict))
        # TODO: Need to be verified and fix by CSM team. Temporary fix for s3 failures
        if CMN_CFG.get("product_family") == constants.PROD_FAMILY_LC:
            # To Resolve {'error_code': '4099', 'message': 'Invalid request message received.',
            # 'error_format_args': 'Request body missing'}
            data = json.dumps(data) if isinstance(data, dict) else data
        self.log.debug("Data : %s", data)
        # Request a REST call
        response_object = self._request[request_type](
            request_url, headers=headers,
            data=data, params=params, verify=False, json=json_dict)
        self.log.debug("Response Object: %s", response_object)
        try:
            self.log.debug("Response JSON: %s", response_object.json())
        except BaseException:
            self.log.debug("Response Text: %s", response_object.text)
        # Can be used in case of larger response
        if save_json:
            with open(self._json_file_path, 'w+') as json_file:
                json_file.write(json.dumps(response_object.json(), indent=4))

        return response_object

    def s3auth_rest_call(self, request_type=None, endpoint=None, data=None, headers=None, **kwargs):
        """
        This function will request REST methods like GET, POST, PUT etc.

        :param request_type: get/post/delete/update etc.
        :param endpoint: IAM url.
        :param data: data required for REST call.
        :param headers: headers required for REST call.
        :param params: parameters required for REST call.
        :param save_json: In case user required to store json file.
        :return: response of the request.
        """
        json_dict = kwargs.get("json_dict")
        save_json = kwargs.get("save_json")
        params = kwargs.get("params")
        self.log.debug("Request URL : %s", endpoint)
        self.log.debug("Request type : %s", request_type.upper())
        self.log.debug("Header : %s", headers)
        self.log.debug("Data : %s", data)
        self.log.debug("Parameters : %s", params)
        self.log.debug("json_dict: %s", json_dict)
        # Request a REST call
        response_object = self._request[request_type](
            endpoint, headers=headers,
            data=data, params=params, verify=False, json=json_dict)
        self.log.debug("Response Object: %s", response_object)
        try:
            self.log.debug("Response JSON: %s", response_object.json())
        except BaseException as error:
            self.log.warning(error)
            self.log.debug("Response Text: %s", response_object.text)
        # Can be used in case of larger response
        if save_json:
            with open(self._json_file_path, 'w+') as json_file:
                json_file.write(json.dumps(response_object.json(), indent=4))

        return response_object
