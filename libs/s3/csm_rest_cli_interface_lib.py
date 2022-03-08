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

"""S3 interface Library."""

import logging
from abc import ABC, abstractmethod
from http import HTTPStatus

from commons.exceptions import CTException
from config import CMN_CFG
from config import CSM_REST_CFG
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3.cortxcli_test_lib import CSMAccountOperations
from libs.s3.cortxcli_test_lib import CortxCliTestLib
from libs.s3.csm_restapi_interface_lib import CSMRestAPIInterfaceOperations
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI

LOGGER = logging.getLogger(__name__)


class CSMAccountInterface(ABC):
    """S3 interface class to declare the abstract methods."""

    @abstractmethod
    def create_s3_using_csm_rest_cli(self, **kwargs):
        """Abstract method to create the s3 account using given CSM user credential."""
        LOGGER.info("Abstract method to create the s3 account using given CSM user credential.")

    @abstractmethod
    def delete_s3_acc_using_csm_rest_cli(self, **kwargs):
        """Abstract method to delete s3 account using given CSM user credential."""
        LOGGER.info("Abstract method to delete s3 account using given CSM user credential.")

    @abstractmethod
    def create_csm_account_rest_cli(self, **kwargs):
        """Abstract method to create csm account."""
        LOGGER.info("Abstract method to create csm account.")

    @abstractmethod
    def delete_csm_account_rest_cli(self, **kwargs):
        """Abstract method to delete csm account."""
        LOGGER.info("Abstract method to delete csm account.")

    @abstractmethod
    def edit_csm_user_rest_cli(self, **kwargs):
        """Abstract method to edit csm account."""
        LOGGER.info("Abstract method to edit csm account.")

    @abstractmethod
    def csm_user_show_s3_acc_rest_cli(self, **kwargs):
        """Abstract method to list created s3 accounts for given CSM user credential."""
        LOGGER.info("Abstract method to list created s3 accounts for given CSM user credential.")

    @abstractmethod
    def reset_s3_password_rest_cli(self, **kwargs):
        """Abstract method to Reset password for s3 account using given CSM user credential."""
        LOGGER.info("Abstract method to Reset password for s3 account using given "
                    "CSM user credential.")


class CSMAccountIntOperations(CSMAccountInterface):
    """S3 account interface class to do s3 account operations."""

    def __init__(self):
        """S3 account operations constructor."""
        prod_type = CMN_CFG.get("product_type", None)
        self.cli_obj = CortxCliTestLib() if prod_type == "node" else None
        self.csmacc_op_cli = CSMAccountOperations() if prod_type == "node" else None
        self.s3acc_op_rest = S3AccountOperationsRestAPI()
        self.csmacc_op_rest = CSMRestAPIInterfaceOperations()
        self.csm_s3_rest = RestS3user()

    def __del__(self):
        """Destroy created objects"""
        try:
            del self.cli_obj
            del self.csmacc_op_cli
            del self.s3acc_op_rest
            del self.csm_s3_rest
            del self.csmacc_op_rest
        except NameError as error:
            LOGGER.warning(str(error))

    # pylint: disable=too-many-arguments
    # pylint: disable=W0221
    def create_s3_using_csm_rest_cli(
            self,
            acc_name,
            email_id,
            acc_pwd,
            csm_user=None,
            csm_pwd=None,
            **kwargs):
        """
        Rest/CLI interface function To Create the s3 account using given CSM user credential

        :param acc_name: Name of the S3 account user.
        :param email_id: Email id of the s3 account user.
        :param acc_pwd: Password of the s3 account user.
        :param csm_user: Name of the CSM user
        :param csm_pwd: Password of the CSM user
        :param kwargs: keyword arguments of Login dict of CSM user credential
        :return: bool, response of create s3 account request
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc and (csm_user and csm_pwd):
                login_acc = {"username": csm_user, "password": csm_pwd}
            elif not login_acc:
                login_acc = "csm_admin_user"
            status, response = self.s3acc_op_rest.create_s3_account(
                user_name=acc_name, email_id=email_id, passwd=acc_pwd, login_as=login_acc)
            if not status:
                raise RuntimeError(response) from RuntimeError
            response.update({"password": CSM_REST_CFG["test_s3account_password"]})
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.csm_user_create_s3account(
                acc_name, email_id, acc_pwd, csm_user, csm_pwd)
            if status:
                response.update({"password": acc_pwd})
        return status, response

    def delete_s3_acc_using_csm_rest_cli(
            self,
            s3acc_name,
            csm_user=None,
            csm_pwd=None,
            **kwargs):
        """
        Rest/CLI interface function To Delete the s3 account using given CSM user credential

        :param s3acc_name: Name of the S3 account user.
        :param csm_user: Name of the CSM user
        :param csm_pwd: Password of the CSM user
        :param kwargs: keyword arguments of Login dict of CSM user credential
        :return: bool, response of delete s3 account request
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc and (csm_user and csm_pwd):
                login_acc = {"username": csm_user, "password": csm_pwd}
            elif not login_acc:
                login_acc = "csm_admin_user"
            status, response = self.s3acc_op_rest.delete_s3_account(
                user_name=s3acc_name, login_as=login_acc)
            if not status and "not exist" not in response:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.csm_user_delete_s3account(
                s3_user=s3acc_name, csm_user=csm_user, passwd=csm_pwd)
        return status, response

    # pylint: disable=too-many-arguments
    def create_csm_account_rest_cli(
            self,
            csm_user=None,
            csm_email=None,
            csm_pwd=None,
            role="manage",
            alert="true",
            **kwargs):
        """
        Rest/CLI interface function To Create CSM account using given CSM user credential

        :param csm_user: Name of the CSM user
        :param csm_email: Email id of the CSM account user.
        :param csm_pwd: Password of the CSM user
        :param role: Roll of the CSM user
        :param alert: Password of the CSM user
        :param kwargs: keyword arguments of Login dict of CSM user credential
        :return: bool, response of create csm account request
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc:
                login_acc = "csm_admin_user"
            status, response = self.csmacc_op_rest.create_csm_user_rest(
                uname=csm_user, e_id=csm_email, pwd=csm_pwd, role=role,
                alert_notice=alert, login_as=login_acc)
            if not status:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.csm_user_create(
                csm_user, csm_email, csm_pwd, role)
        return status, response

    def delete_csm_account_rest_cli(self, csm_user=None, csm_pwd=None, **kwargs):
        """
        Rest/CLI interface function To Delete CSM user

        :param csm_user: Name of the CSM user
        :param csm_pwd: Password of the CSM user
        :param kwargs: keyword arguments of Login dict of CSM user credential
        :return: bool, response of delete account request
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc and (csm_user and csm_pwd):
                login_acc = {"username": csm_user, "password": csm_pwd}
            elif not login_acc:
                login_acc = "csm_admin_user"
            status, response = self.csmacc_op_rest.delete_csm_user_rest(
                csm_user, login_as=login_acc)
            if not status:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.csm_user_delete(csm_user)
        return status, response

    # pylint: disable=too-many-arguments
    def edit_csm_user_rest_cli(
            self,
            csm_user=None,
            role=None,
            csm_email=None,
            csm_new_pwd=None,
            csm_pwd=None,
            **kwargs):
        """
        Rest/CLI interface function To Edit CSM user

        :param csm_user: Name of the CSM user
        :param role: Role of the CSM user
        :param csm_email: Email ID of the CSM user
        :param csm_new_pwd: New password of the CSM user
        :param csm_pwd: Current password of the CSM user
        :param kwargs: keyword arguments of Login dict of CSM user credential
        :return: bool, response of edit CSM user operation
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc:
                login_acc = "csm_admin_user"
            status, response = self.csmacc_op_rest.edit_csm_user_rest(
                user=csm_user, role=role, email=csm_email,
                password=csm_new_pwd, current_password=csm_pwd, login_as=login_acc)
            if not status:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.csm_user_update_role(csm_user, csm_pwd, role)
        return status, response

    def csm_user_show_s3_acc_rest_cli(self, csm_user=None, csm_pwd=None, **kwargs):
        """
        Rest/CLI interface function To list s3 user for CSM user

        :param csm_user: Name of the CSM user
        :param csm_pwd: Password of the CSM user
        :return: bool, response of edit CSM user operation
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc and (csm_user and csm_pwd):
                login_acc = {"username": csm_user, "password": csm_pwd}
            elif not login_acc:
                login_acc = "csm_admin_user"
            rest_response = self.csm_s3_rest.list_all_created_s3account(login_as=login_acc)
            status = rest_response.status_code == HTTPStatus.OK
            if not status:
                raise RuntimeError(rest_response) from RuntimeError
            response = [item["account_name"] for item in rest_response.json()["s3_accounts"]]
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.csm_user_show_s3accounts(csm_user, csm_pwd)
        return status, response

    def reset_s3_password_rest_cli(
            self,
            acc_name=None,
            passwd=None,
            csm_user=None,
            csm_pwd=None,
            **kwargs):
        """
        REST/CLI Interface function to Reset password for s3 account.

        :param acc_name: Name of the S3 account user.
        :param passwd: Password of the s3 account user.
        :param csm_user: Name of the CSM user
        :param csm_pwd: Password of the CSM user
        :return: bool, response of reset s3 account password
        """
        try:
            login_acc = kwargs.get("login_as", None)
            if not login_acc and (csm_user and csm_pwd):
                login_acc = {"username": csm_user, "password": csm_pwd}
            elif not login_acc:
                login_acc = "csm_admin_user"
            status, response = self.csmacc_op_rest.reset_s3_user_password(
                username=acc_name, new_password=passwd, login_as=login_acc)
            if not status:
                raise RuntimeError(response) from RuntimeError
        except (RuntimeError, CTException) as err:
            if not self.cli_obj:
                raise RuntimeError(err) from RuntimeError
            LOGGER.exception(str(err))
            status, response = self.csmacc_op_cli.reset_s3acc_password(
                csm_user, csm_pwd, acc_name, passwd)

        return status, response
