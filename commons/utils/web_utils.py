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
"""Module to maintain web utils."""

import logging
from typing import Any

import requests
from requests import Response

log = logging.getLogger(__name__)


def http_head_request(url: str, verify: bool = False):
    """
    Head request to specified url.

    :param url: Endpoint url.
    :param verify: True|False.
    :return: response.
    """
    # headers = {
    #     'User-Agent': self.user_agent
    # }
    log.info("Getting head response")
    response = requests.head(url, verify=verify)
    log.debug("Head response: %s", response)

    return response


def http_get_request(url: str, verify: bool = False):
    """
    Function to execute get request.

    :param url: Endpoint url.
    :param verify: True|False.
    :return: response.
    """
    log.info("Getting head response")
    response = requests.get(url, verify=verify)
    log.debug("Get response: %s", response)

    return response


def http_post_request(
        url: str,
        data: Any,
        headers: dict = None,
        verify: bool = False) -> Response:
    """
    Execute post request and return response.

    :param url: Endpoint url
    :param data: data to post.
    :param headers: Additional info.
    :param verify: True|False
    :return: response.
    """
    if headers is None:
        headers = {}
    log.info("Execute post request, url - [%s], data - [%s]", url, data)
    response = requests.post(url, json=data, headers=headers, verify=verify)
    log.info("Post request %s executed successfully.", url)
    if response:
        log.debug("response headers - %s", response.headers)
        log.debug("response content - %s", str(response.text))
    else:
        log.debug("response object is empty")
    return response


def http_patch_request(
        url: str,
        data: Any,
        headers: dict = None,
        verify: bool = False) -> Response:
    """
    Execute patch request and return response.

    :param url: Endpoint url
    :param data: data to post.
    :param headers: Additional info.
    :param verify: True|False
    :return: response.
    """
    if headers is None:
        headers = {}
    log.info("Execute patch request, url - [%s], data - [%s]", url, data)
    response = requests.patch(url, json=data, headers=headers, verify=verify)
    log.info("Patch request %s executed successfully.", url)
    if response:
        log.debug("response headers - %s", response.headers)
        log.debug("response content - %s", str(response.text))
    else:
        log.debug("response object is empty")
    return response
