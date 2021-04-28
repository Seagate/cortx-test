#!/usr/bin/env python3
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

"""Management operations needed during the DI tests."""

import logging
import random
import time

import boto3

from commons.utils import assert_utils
from config import CMN_CFG
from config import CSM_CFG
from config import S3_CFG
from libs.s3 import cortxcli_test_lib as cctl
from libs.s3 import iam_core_lib
from libs.s3.iam_core_lib import S3IamCli

LOGGER = logging.getLogger(__name__)


class ManagementOPs:
    email_suffix = "@seagate.com"
    user_prefix = 'di_user'

    @classmethod
    def create_iam_users(cls, nusers=10):
        """
        Creates s3 iam users to upload DI test data. This function uses S3IamCli
        to create account and iam user
        :param nusers: number of iam users to create
        :return:
        """
        user = 's3' + cls.user_prefix + str(random.randint(100, 1000))
        email = user + cls.email_suffix
        # Create S3 account user
        cli = S3IamCli()
        resp = cli.create_account_s3iamcli(email,
                                           CMN_CFG["ldap"]["username"],
                                           CMN_CFG["ldap"]["password"])

        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        users = {"{}{}".format(cls.user_prefix, i): tuple() for i in range(1, nusers + 1)}

        # Create IAM users
        for i in range(1, nusers + 1):
            udict = dict()
            user = cls.user_prefix + str(i)
            email = user + cls.email_suffix
            udict.update({'emailid': email})
            cli.create_user_using_s3iamcli(user, access_key, secret_key)
            resp = cli.create_access_key(user)
            user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
            user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
            users[user] = user_access_key, user_secret_key, email
        return users

    @classmethod
    def create_account_users(cls,
                             nusers: int = 10,
                             use_cortx_cli: bool = True) -> dict:
        """
        Creates s3 account users to upload DI test data. This function uses S3IamCli
        to create users.
        :param use_cortx_cli: Not in use will remove later
        :param nusers: number of users to create
        :return:
        """
        LOGGER.info(f"Creating Cortx s3 account users with {use_cortx_cli}")
        s3acc_obj = cctl.CortxCliTestLib()
        ts = time.strftime("%Y%m%d_%H%M%S")
        users = {"{}{}_{}".format(cls.user_prefix, i, ts): dict() for i in range(1, nusers + 1)}
        s3_user_passwd = CSM_CFG["CliConfig"]["s3_account"]["password"]
        for i in range(1, nusers + 1):
            udict = dict()
            user = "{}{}_{}".format(cls.user_prefix, i, ts)
            email = user + cls.email_suffix
            udict.update({'user_name': user})
            udict.update({'emailid': email})
            udict.update({'password': s3_user_passwd})

            result, acc_details = s3acc_obj.create_account_cortxcli(user, email,
                                                                    s3_user_passwd)
            assert_utils.assert_true(result, 'S3 account use not created.')
            LOGGER.info("Created s3 account %s", user)
            udict.update({'accesskey': acc_details["access_key"]})
            udict.update({'secretkey': acc_details["secret_key"]})
            users.update({user: udict})
        LOGGER.debug("Users %s created for I/O", users)
        return users

    @classmethod
    def create_buckets(cls, nbuckets):
        """
        Creates random buckets for each user. This api
        caches buckets for continuous crud operations on
        them.
        :param nbuckets:
        :return:
        """
        users = dict()

        # Create S3 account
        cli = iam_core_lib.S3IamCli()
        resp = cli.create_account_s3iamcli(CMN_CFG['emailid'],
                                           CMN_CFG['ldap_username'],
                                           CMN_CFG['ldap_passwd'])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        buckets = {"user{}".format(i): list() for i in range(1, nbuckets + 1)}

        # create 10 buckets per user
        for k in users:
            bkts = [cli.create_bucket('{}bucket{}'.format(k, i)) for i in range(1, nbuckets + 1)]
            buckets[k] = bkts

    @classmethod
    def crud_csm_users(cls):
        """
        Perform continuous cruds on cached users. Cache will be typically a hashmap or lru cache
        :return:
        """
        pass

    @classmethod
    def crud_iam_users(cls):
        """
        Perform continuous cruds on cached iam users. These users and buckets should be
        different from those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def crud_buckets(cls):
        """
        Perform continuous cruds on cached buckets of users. These users and buckets should be
        different from those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def crud_policy(cls):
        """
        Perform continuous cruds on cached policies. These policies should be
        different from those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def safe_crud_account_users(cls):
        """
        Perform continuous cruds on cached s3 account users used for IOs.
        :return:
        """
        pass

    @classmethod
    def safe_crud_iam_users(cls):
        """
        Perform continuous cruds on cached iam users. These users and buckets should be
        same as those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def safe_crud_buckets(cls):
        """
        Perform continuous cruds on cached buckets which are used for IOs in DI test runs.
        :return:
        """

    @classmethod
    def safe_crud_policy(cls):
        """
        Perform continuous cruds on cached policies belonging to buckets used for
        IOs in DI test runs
        :return:
        """
        pass

    @classmethod
    def create_users_and_buckets(cls, maxusers=100, maxbuckets=100):
        """
        Creates random users and random buckets for each user. This api
        caches users and their buckets for continuous crud operations on
        them.
        :param maxusers:
        :param maxbuckets:
        :return:
        """
        users = dict()

        # Create S3 account
        cli = iam_core_lib.S3IamCli()
        resp = cli.create_account_s3iamcli(CMN_CFG['emailid'],
                                           CMN_CFG['ldap_username'],
                                           CMN_CFG['ldap_passwd'])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        """Creating Connection"""
        iam = boto3.client('iam', verify=S3_CFG['iam_cert_path'],
                           aws_access_key_id=access_key,
                           aws_secret_access_key=secret_key,
                           endpoint_url=S3_CFG['iam_url'])

        users = {"user{}".format(i): tuple() for i in range(1, maxusers + 1)}
        buckets = {"user{}".format(i): list() for i in range(1, maxbuckets + 1)}
        # Create IAM users
        for i in range(1, maxusers + 1):
            cli.create_user_using_s3iamcli("user{}".format(i), access_key, secret_key)
            resp = cli.create_access_key("user{}".format(i))
            user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
            user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
            users["user{}".format(i)] = user_access_key, user_secret_key
        # create 10 buckets per user
        for k in users:
            bkts = [cli.create_bucket('{}bucket{}'.format(k, i)) for i in range(1, maxbuckets + 1)]
            buckets[k] = bkts
