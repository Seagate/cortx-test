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
# -*- coding: utf-8 -*-
# !/usr/bin/python
""" Module to configure s3 dns"""
import threading

import pytest

from commons.utils import system_utils


def dns_rr_counter():
    """Increments round robin global counter """
    with threading.Lock():
        pytest.dns_rr_counter += 1
        return pytest.dns_rr_counter


def dns_rr(S3_CFG, node_count, setup_details):
    """Method to configure s3 and iam_url

    :param S3_CFG: S3 configure files
    :param node_count: Number of nodes in cluster
    :param setup_details: setup database
    :return: None
    """
    node_index = dns_rr_counter()
    counter = int(node_index) % node_count
    res_url = system_utils.get_s3_url(setup_details, counter)
    if "s3_url" in S3_CFG.keys():
        S3_CFG["s3_url"] = res_url["s3_url"]
        S3_CFG["iam_url"] = res_url["iam_url"]
