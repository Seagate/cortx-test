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
""" Script for creating S3 account. """

import argparse
import requests


def login(mgmt_vip, username, password, port=28100, set_secure=True):
    """[summary]

    :param mgmt_vip: Management IP address
    :param username: CSM login Username
    :param password: CSM login password
    :param port: CSM connection port
    :param set_secure: True than https will be used else http
    :return [tuple]: base_url, headers
    """
    if set_secure:
        start = "https://"
    else:
        start = "http://"
    base_url = "{}{}:{}".format(start, mgmt_vip, str(port))
    login_data = {"username": username, "password": password}
    login_url = base_url + "/api/v2/login"
    print(f"URL : {login_url}")
    print(f"Credentials : {login_data}")
    response = requests.post(url=login_url, data=login_data, verify=False)
    print("Response: ", response)
    if response.status_code == 200:
        headers = {'Authorization': response.headers['Authorization']}
        return base_url, headers
    else:
        return None


def create_s3_account(account_name, account_email, account_password,
                      mgmt_vip, username, password, **kwargs):
    """Create S3 account

    :param account_name: S3 aaccount name
    :param account_email:  S3 account email
    :param account_password: S3 account password
    :param mgmt_vip: Management IP address
    :param username: CSM login Username
    :param password: CSM login password
    :return [Dict]:{'account_name': '', 'account_email': '', 'account_id': '', 'canonical_id': '', 
    'access_key': '', 'secret_key': ''}
    """
    base_url, headers = login(mgmt_vip, username, password, **kwargs)
    create_s3_url = base_url + "/api/v2/s3_accounts"
    data = {"account_name": account_name,
            "account_email": account_email,
            "password": account_password}
    print("URL :", create_s3_url)
    print("Credentials : ", data)
    print("Headers : ", headers)
    response = requests.post(url=create_s3_url, data=data, verify=False, headers=headers, json=None)
    print("Response: ", response.status_code)
    print("Response: ", response.json())
    if response.status_code == 200:
        return response.json()
    else:
        return None


if __name__ == '__main__':
    # Setup details
    parser = argparse.ArgumentParser(description='Create s3 account')
    parser.add_argument('--mgmt_vip', dest='mgmt_vip', help='Management IP', type=str)
    parser.add_argument('--username', dest='username', help='CSM admin username', type=str)
    parser.add_argument('--password', dest='password', help='CSM admin password', type=str)
    parser.add_argument('--account_name', dest='account_name', help='New S3 account name', type=str)
    parser.add_argument(
        '--account_email',
        dest='account_email',
        help='New S3 account email',
        type=str)
    parser.add_argument(
        '--account_password',
        dest='account_password',
        help='New S3 account password',
        type=str)
    args = parser.parse_args()
    create_s3_account(
        args.account_name,
        args.account_email,
        args.account_password,
        args.mgmt_vip,
        args.username,
        args.password)
