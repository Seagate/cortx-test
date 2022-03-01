#!/usr/bin/env python3
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

"""Management operations needed during the DI tests."""

import time
import random
import logging
import json
from http import HTTPStatus

import boto3
from config import CMN_CFG
from config import CSM_CFG
from config import S3_CFG
from config import DI_CFG
from commons.utils import assert_utils
from libs.s3 import cortxcli_test_lib as cctl
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.iam_test_lib import IamTestLib
from libs.di.di_base import _init_s3_conn

LOGGER = logging.getLogger(__name__)


class ManagementOPs:

    email_suffix = "@seagate.com"
    user_prefix = 'di_user'

    @classmethod
    def create_iam_users(cls, nusers=10):
        """
        Creates s3 iam users to upload DI test data. This function uses
        REST APIs to create s3 account and iam users
        :param nusers: number of iam users to create
        :return: Dictionary of IAM users details
        """
        iam_users = dict()
        # Create S3 user
        iam_users.update(
            {'user_name': 's3' + cls.user_prefix + str(random.randint(100, 1000))})
        iam_users.update({'emailid': iam_users['user_name'] + cls.email_suffix})
        iam_users.update(
            {'password': DI_CFG["DiUserConfig"]["s3_account"]["password"]})
        s3acc_obj = S3AccountOperationsRestAPI()
        resp = s3acc_obj.create_s3_account(
            user_name=iam_users['user_name'],
            email_id=iam_users['emailid'],
            passwd=iam_users['password'])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Created s3 account %s", iam_users['user_name'])
        iam_users.update({'accesskey': resp[1]["access_key"]})
        iam_users.update({'secretkey': resp[1]["secret_key"]})

        # Create IAM users
        time_stamp = time.strftime("%Y%m%d_%H%M%S")
        users = {
            "iam_{}{}_{}".format(
                cls.user_prefix,
                i,
                time_stamp): dict() for i in range(
                1,
                nusers + 1)}
        iam_obj = IamTestLib(
            access_key=iam_users['accesskey'],
            secret_key=iam_users['secretkey'])
        iam_user_passwd = DI_CFG["DiUserConfig"]["iam_user"]["password"]
        for i in range(1, nusers + 1):
            udict = dict()
            user = "iam_{}{}_{}".format(cls.user_prefix, i, time_stamp)
            email = user + cls.email_suffix
            udict.update({'emailid': email})
            udict.update({'user_name': user})
            udict.update({'password': iam_user_passwd})
            resp = iam_obj.create_user(user)
            assert_utils.assert_true(resp[0], resp[1])
            resp = iam_obj.create_access_key(user)
            LOGGER.info(resp)
            assert_utils.assert_true(resp[0], resp[1])
            udict.update({'accesskey': resp[1]["AccessKey"]["AccessKeyId"]})
            udict.update({'secretkey': resp[1]["AccessKey"]["SecretAccessKey"]})
            users.update({user: udict})
        iam_users.update({'iam_users': users})
        return iam_users

    @classmethod
    def create_account_users(cls,
                             nusers: int = 10,
                             use_cortx_cli: bool = False) -> dict:
        """
        Creates s3 account users to upload DI test data. This function uses
        REST or CLI to create users based on use_cortx_cli option.
        :param use_cortx_cli: Not in use will remove later
        :param nusers: number of users to create
        :return:
        """
        LOGGER.info(f"Creating Cortx s3 account users with {use_cortx_cli}")
        if use_cortx_cli:
            s3acc_obj = cctl.CortxCliTestLib()
            s3acc_obj.open_connection()
        else:
            s3acc_obj = RestS3user()
        ts = time.strftime("%Y%m%d_%H%M%S")
        users = {"{}{}_{}".format(cls.user_prefix, i, ts): dict() for i in range(1, nusers + 1)}
        s3_user_passwd = DI_CFG["DiUserConfig"]["s3_account"]["password"]
        for i in range(1, nusers + 1):
            udict = dict()
            user = "{}{}_{}".format(cls.user_prefix, i, ts)
            email = user + cls.email_suffix
            udict.update({'user_name': user})
            udict.update({'emailid': email})
            udict.update({'password': s3_user_passwd})
            if use_cortx_cli:
                result, acc_details = s3acc_obj.create_account_cortxcli(
                    user, email, s3_user_passwd)
                assert_utils.assert_true(result, 'S3 account user not created.')
            else:
                resp = s3acc_obj.create_an_account(
                    user, s3_user_passwd)
                assert_utils.assert_equal(
                    resp.status_code, 201,
                    'S3 account user not created.')
                acc_details = json.loads(resp.text)

            LOGGER.info("Created s3 account %s", user)
            udict.update({'accesskey': acc_details["access_key"]})
            udict.update({'secretkey': acc_details["secret_key"]})
            users.update({user: udict})
        LOGGER.debug("Users %s created for I/O", users)
        return users

    @classmethod
    def create_buckets(cls, nbuckets, users=None, use_cortxcli=False):
        """
        Creates random buckets for each user. This api
        caches buckets for continuous crud operations on
        them.
        :param nbuckets: No of buckets to be created per user
        :param users: user dict
        :return:
        """
        users = dict() if not users else users

        # Create S3 account
        if use_cortxcli:
            cli = cctl.CortxCliTestLib()

        buckets = {"user{}".format(i): list() for i in range(1, nbuckets + 1)}

        # create 10 buckets per user
        for k in users:
            if use_cortxcli:
                cli.login_cortx_cli(k, users[k]["password"])
                bkts = [
                    cli.create_bucket_cortx_cli('{}bucket{}'.format(
                        k.replace('_', '-'), i))[1] for i in range(
                        1, nbuckets + 1)]
                bkts_lst = [i.split(" ")[2].split(
                    '\nBucket')[0] for i in bkts if 'created' in i]
                buckets[k] = bkts_lst
                cli.logout_cortx_cli()
            else:
                access_key = users[k].get("accesskey")
                secret_key = users[k].get("secretkey")
                s3_obj = _init_s3_conn(access_key, secret_key, k)
                bkts_lst = [
                    s3_obj.create_bucket(Bucket='{}bucket{}'.format(
                        k.replace('_', '-'), i)).name for i in range(
                        1, nbuckets + 1)]
            users[k]["buckets"] = bkts_lst
        return users

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
        Creates random s3 users and random buckets for each user. This api
        caches users and their buckets for continuous crud operations on
        them.
        :param maxusers:
        :param maxbuckets:
        :return:
        """
        users = cls.create_account_users(nusers=maxusers)
        users = cls.create_buckets(nbuckets=maxbuckets, users=users)
        return users

    @classmethod
    def create_s3_user_csm_rest(cls, user_name, passwd):
        udict = dict()
        s3acc_obj = RestS3user()
        resp = s3acc_obj.create_an_account(user_name, passwd)
        assert_utils.assert_equal(resp.status_code, HTTPStatus.CREATED,
                                  'S3 account user not created.')
        acc_details = json.loads(resp.text)
        LOGGER.info("Created s3 account %s", user_name)
        udict.update({'accesskey': acc_details["access_key"]})
        udict.update({'secretkey': acc_details["secret_key"]})
        return udict

    @classmethod
    def delete_s3_users_csm_rest(cls, prefix):
        """Function will delete all csm s3 accounts with prefix.
        """
        s3acc_obj = RestS3user()
        responses = s3acc_obj.list_all_created_s3account().json()["s3_accounts"]
        for resp in responses:
            acc_name = resp["account_name"]
            if acc_name.startswith(prefix):
                s3acc_obj.delete_s3_account_user(acc_name)

    @classmethod
    def delete_s3_user_csm_rest(cls, acc_name):
        """Function will delete all csm s3 accounts with prefix.
        """
        s3acc_obj = RestS3user()
        s3acc_obj.delete_s3_account_user(acc_name)