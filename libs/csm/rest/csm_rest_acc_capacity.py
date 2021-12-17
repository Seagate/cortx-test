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
"""Test library for account capacity related operations.
"""
import commons.errorcodes as err
from commons.constants import Rest as const
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib


class AccountCapacity(RestTestLib):
    """
    RestCsmUser contains all the Rest API calls for account capacity related operations
    """

    @RestTestLib.authenticate_and_login
    def get_account_capacity(self, account_id=None):
        """Get account capacity usage
        :return [obj]: Json response
        """
        try:
            # Building request url
            self.log.info("Reading System Capacity...")
            if account_id:
                endpoint = self.config["account_capacity_endpoint"].format(account_id)
            else:
                endpoint = self.config["accounts_capacity_endpoint"]

            self.log.info("Endpoint for reading capacity is {}".format(endpoint))
            # Fetching api response
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint,
                                              headers=self.headers)
            self.log.info("CSM REST response returned is:\n %s", response.json())
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           AccountCapacity.get_all_accounts_capacity.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def verify_account_capacity(self, accounts):
        """
        Verifies given account capacity with rest capacity output
        param: accounts: List of accounts with account info dict
        return: True/False based on verification
        """
        if len(accounts) == 1:
            response = self.get_account_capacity(accounts[0]["account_name"])
            rest_data = response.json()
            if len(rest_data) != 1:
                self.log.error("Rest call received more than 1 account record: %s", rest_data)
                return False, accounts
        else:
            response = self.get_account_capacity()
            rest_data = response.json()
        acc_local_copy = accounts.copy()
        for account in accounts:
            for rest_op in rest_data:
                if account["account_name"] == rest_op["account_name"]:
                    acc_local_copy.remove(account)
                    if account["capacity"] != rest_op["capacity"] or \
                            account["unit"] != rest_op["unit"]:
                        self.log.error("Account information is not matched: User given: %s, "
                                       "Rest received: %s", account, rest_op)
                        return False, account
        if len(acc_local_copy):
            self.log.error("Accounts not found in rest output: %s", acc_local_copy)
        return len(acc_local_copy) == 0, acc_local_copy
