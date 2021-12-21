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
import os

import commons.errorcodes as err
from commons.constants import Rest as const
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.s3.s3_test_lib import S3TestLib


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
                           AccountCapacity.get_account_capacity.__name__,
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

    def perform_io_validate_data_usage(self, user_data, workload_in_mb: list,
                                       validate_data_usage: bool) -> bool:
        """
        Perform put operation using specified S3 account on the given bucket and validate data usage
        param: user_data - list of userdata
        return : Boolean
        """
        s3_user = user_data[0]
        access_key = user_data[1]
        secret_key = user_data[2]
        bucket_name = user_data[3]
        s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)
        total_cap = 0
        for sz in workload_in_mb:
            test_file = f"file_io_{sz}"
            file_path = os.path.join(TEST_DATA_FOLDER, test_file)
            self.log.info("Creating a file with name %s", test_file)
            system_utils.create_file(file_path, sz, "/dev/urandom")

            self.log.info("Uploading a object %s to a bucket %s", test_file, bucket_name)
            s3t_obj.put_object(bucket_name, test_file, file_path)
            system_utils.remove_file(file_path)
            total_cap = total_cap + sz

            if validate_data_usage:
                self.log.info("Verify capacity of account after put operations")
                s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
                resp = self.verify_account_capacity(s3_account)
                if not resp[0]:
                    self.log.error("Account capacity did not match for account : %s", resp[1])
                    return False

        return True
