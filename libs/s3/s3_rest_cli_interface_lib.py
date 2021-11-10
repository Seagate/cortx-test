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
from config import CMN_CFG
from libs.s3.cortxcli_test_lib import CortxCliTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI


LOGGER = logging.getLogger(__name__)


class S3AccountInterface(ABC):
    """S3 interface class to declare the abstract methods."""

    @abstractmethod
    def create_s3_account(self, **kwargs):
        """Abstract method to create the s3 account."""
        LOGGER.info("Abstract method to create the s3 account.")

    @abstractmethod
    def delete_s3_account(self, **kwargs):
        """Abstract method to delete s3 account."""
        LOGGER.info("Abstract method to delete s3 account.")

    @abstractmethod
    def list_s3_accounts(self):
        """Abstract method to list s3 accounts."""
        LOGGER.info("Abstract method to list s3 accounts.")

    @abstractmethod
    def update_s3_account(self, **kwargs):
        """Abstract method to update s3 account."""
        LOGGER.info("Abstract method to update s3 account.")

    @abstractmethod
    def generate_s3_access_key(self, **kwargs):
        """Abstract method to create new s3 access key."""
        LOGGER.info("Abstract method to create new s3 access key.")


class S3AccountOperations(S3AccountInterface):
    """S3 account interface class to do s3 account operations."""

    def __init__(self):
        """S3 account operations constructor."""
        self.cli_obj = CortxCliTestLib() if CMN_CFG.get("product_type") == "node" else None
        self.rest_obj = S3AccountOperationsRestAPI()

    def __del__(self):
        """Destroy created objects"""
        try:
            del self.cli_obj
            del self.rest_obj
        except NameError as err:
            LOGGER.warning(err)

    # pylint: disable=W0221
    def create_s3_account(self, acc_name=None,
                          email_id=None, passwd=None) -> tuple:
        """
        Create s3 account and return response dict.

        :param acc_name: Name of the S3 account user.
        :param email_id: Email id of the s3 account user.
        :param passwd: Password of the s3 account user.
        :return: bool, response of create user dict
        """
        try:
            status, response = self.rest_obj.create_s3_account(
                acc_name, email_id, passwd)
            if not status and not (
                    "already exists" in response or "Password Policy Not Met" in response):
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(err)
            status, response = self.cli_obj.create_account_cortxcli(
                acc_name, email_id, passwd)

        return status, response

    def list_s3_accounts(self) -> tuple:
        """
        List all s3 accounts and return account list.

        :return: bool, response of s3 accounts list.
        """
        try:
            status, response = self.rest_obj.list_s3_accounts()
            if not status:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(err)
            response = self.cli_obj.list_accounts_cortxcli()
            status = True if response else False

        return status, response

    # pylint: disable=W0221
    def update_s3_account(self, acc_name=None, new_passwd=None) -> tuple:
        """
        Reset s3 account password.

        :param acc_name: Name of the S3 account user.
        :param new_passwd: New password of the s3 account user.
        :return: bool, response of update user.
        """
        try:
            status, response = self.rest_obj.reset_s3account_password(
                acc_name, new_passwd)
            if not status and "Password Policy Not Met" not in response:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(err)
            status, response = self.cli_obj.reset_s3_account_password(
                acc_name, new_password=new_passwd)

        return status, response

    # pylint: disable=W0221
    def delete_s3_account(self, acc_name=None) -> tuple:
        """
        Delete s3 account and return delete response.

        :param acc_name: Name of the S3 account user.
        :return: bool, response of delete user.
        """
        try:
            status, response = self.rest_obj.delete_s3_account(acc_name)
            if not status and "not exist" not in response:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(err)
            status, response = self.cli_obj.delete_account_cortxcli(acc_name)

        return status, response

    # pylint: disable=W0221
    def generate_s3_access_key(self, acc_name=None, passwd=None) -> tuple:
        """
        REST/CLI Interface function to Generate new access key for s3 account.

        :param acc_name: Name of the S3 account user.
        :param passwd: Password of the s3 account user.
        :return: bool, response of generated s3 account access key
        """
        try:
            status, response = self.rest_obj.create_s3account_access_key(acc_name, passwd)
            if not status:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(err)
            status, response = self.cli_obj.create_s3_user_access_key(acc_name, passwd, acc_name)

        return status, response
