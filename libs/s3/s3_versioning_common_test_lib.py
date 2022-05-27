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
#
"""Contains common functions for S3 Versioning tests."""
import logging

from commons.utils import assert_utils
from libs.s3 import s3_test_lib
from libs.s3 import s3_versioning_test_lib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI

LOG = logging.getLogger(__name__)


def create_s3_user_get_s3lib_object(
        user_name: str = None,
        email_id: str = None,
        password: str = None) -> tuple:
    """
    Function will create s3 accounts with specified account name and email-id.

    :param str user_name: Name of user to be created.
    :param str email_id: Email id for user creation.
    :param password: user password.
    :return tuple: It returns multiple values such as access_key,
    secret_key and S3 objects which required to perform further operations.
    """
    rest_obj = S3AccountOperationsRestAPI()
    LOG.info("Creating account with name %s and email_id %s",
             account_name, email_id)
    new_user = rest_obj.create_s3_account(user_name=user_name, 
                                          email_id=email_id,
                                          passwd=password)
    assert_utils.assert_true(new_user[0], new_user[1])
    access_key = new_user[1]["access_key"]
    secret_key = new_user[1]["secret_key"]
    del rest_obj
    LOG.info("Successfully created the S3 account")
    s3_obj = s3_versioning_test_lib.S3VersioningTestLib(access_key=access_key, 
                                                        secret_key=secret_key,
                                                        endpoint_url=S3_CFG["s3_url"])
    response = (s3_obj, access_key, secret_key)
    return response
