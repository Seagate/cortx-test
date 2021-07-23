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

"""S3 interface Library."""

import logging
from abc import ABC, abstractmethod

from commons.exceptions import CTException
from libs.s3.cortxcli_test_lib import _S3AccountOperations
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI

cli_obj = _S3AccountOperations()
rest_obj = S3AccountOperationsRestAPI()

LOGGER = logging.getLogger(__name__)


class S3Interface(ABC):
    """S3 interface class to declare the methods."""

    @abstractmethod
    def create_s3_account(self):
        pass

    @abstractmethod
    def delete_s3_account(self):
        pass

    @abstractmethod
    def list_s3_accounts(self):
        pass

    @abstractmethod
    def update_s3_account(self):
        pass

    @abstractmethod
    def generate_access_key(self):
        pass


class S3AccountOperations(S3Interface):
    """S3 account interface class to do s3 account operations."""

    def create_s3_account(self, acc_name=None, email_id=None, passwd=None) -> tuple:
        """
        Create s3 account and return response dict.

        :param acc_name: Name of the S3 account user.
        :param email_id: Email id of the s3 account user.
        :param passwd: Password of the s3 account user.
        :return: bool, response of create user dict
        """
        try:
            response = rest_obj.create_s3_account(acc_name, email_id, passwd)
        except CTException as err:
            LOGGER.error(err.message)
            response = cli_obj.create_account_cortxcli(acc_name, email_id, passwd)

        return response

    def delete_s3_account(self, acc_name=None) -> tuple:
        """
        Delete s3 account and return delete response.

        :param acc_name: Name of the S3 account user.
        :return: bool, response of delete user.
        """
        try:
            response = rest_obj.delete_s3_account(acc_name)
        except CTException as err:
            LOGGER.error(err.message)
            response = cli_obj.delete_account_cortxcli(acc_name)

        return response

    def list_s3_accounts(self) -> tuple:
        """
        List all s3 accounts and return account list.

        :return: bool, response of s3 accounts list.
        """
        try:
            response = rest_obj.list_s3_accounts()
        except CTException as err:
            LOGGER.error(err.message)
            response = cli_obj.list_accounts_cortxcli()

        return response

    def update_s3_account(self, acc_name=None, new_passwd=None) -> tuple:
        """
        Reset s3 account password.

        :param acc_name: Name of the S3 account user.
        :param new_passwd: New password of the s3 account user.
        :return: bool, response of update user.
        """
        try:
            response = rest_obj.reset_s3account_password(acc_name, new_passwd)
        except CTException as err:
            LOGGER.error(err.message)
            response = cli_obj.reset_s3_account_password(acc_name, new_password=new_passwd)

        return response

    def generate_access_key(self, acc_name=None, passwd=None) -> tuple:
        """
        Generate new access key for s3 account.

        :param acc_name: Name of the S3 account user.
        :param passwd: Password of the s3 account user.
        :return: bool, response of generated s3 account access key
        """
        response = rest_obj.create_s3account_access_key(acc_name, passwd)

        return response
