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
