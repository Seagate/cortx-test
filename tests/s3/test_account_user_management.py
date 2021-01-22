#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging
import pytest

from commons.constants import const
from commons.ct_fail_on import ct_fail_on
from commons.exceptions import CTException
from commons.utils.assert_utils import assert_equals
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import create_file
from commons.helpers.s3_helper import S3Helper
from commons.helpers.node_helper import Node
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.iam_test_lib import IamTestLib

iam_obj = IamTestLib()
s3_obj = S3TestLib()
try:
    s3hobj = S3Helper()
except ImportError as err:
    s3hobj = S3Helper.get_instance()

acc_usr_mng_conf = read_yaml("config/s3/test_account_user_management.yaml")[1]
cmn_config = read_yaml("config/common_config.yaml")[1]


class TestAccountUserManagement:
    """Account User Management TestSuite"""

    acc_user_config = acc_usr_mng_conf["acc_user_mng"]

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        self.log.info("STARTED: Setup operations.")
        self.log = logging.getLogger(__name__)
        self.build_ver = cmn_config["BUILD_VER_TYPE"]
        self.cons_obj_dict = const.S3_BUILD_VER[self.build_ver]
        self.ldap_user = const.S3_BUILD_VER[self.build_ver]["ldap_creds"]["ldap_username"]
        self.ldap_passwd = const.S3_BUILD_VER[self.build_ver]["ldap_creds"]["ldap_passwd"]
        self.log.info("LDAP credentials.")
        self.log.info(self.ldap_user)
        self.log.info(self.ldap_passwd)
        self.log.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown Operations.")
        all_users = iam_obj.list_users()[1]
        users_list = [user["UserName"] for user in all_users if self.acc_user_config["user_name"] in user["UserName"]]
        self.log.info("IAM users: {0}".format(users_list))
        if users_list:
            self.log.info("Deleting IAM users...")
            for user in users_list:
                res = iam_obj.list_access_keys(user)
                if res[0]:
                    self.log.info("Deleting user access key...")
                    keys_meta = res[1]["AccessKeyMetadata"]
                    for key in keys_meta:
                        iam_obj.delete_access_key(
                            user, key["AccessKeyId"])
                    self.log.info("Deleted user access key.")
                try:
                    self.log.info("Deleting a user: {}".format(user))
                    iam_obj.delete_user(user)
                except CTException as error:
                    self.log.error(error)
        self.log.info("Deleted users successfully.")
        account_name = self.acc_user_config["account_name"]
        acc_list = iam_obj.list_accounts_s3iamcli(self.ldap_user, self.ldap_passwd)[1]
        all_acc = [acc["AccountName"] for acc in acc_list if account_name in acc["AccountName"]]
        if all_acc:
            self.log.info("Accounts to delete: {0}".format(all_acc))
            for acc in all_acc:
                try:
                    self.log.info("Deleting {0} account".format(acc))
                    iam_obj.reset_access_key_and_delete_account_s3iamcli(acc)
                    self.log.info("Deleted {0} account".format(acc))
                except CTException as error:
                    self.log.info(error)
        self.log.info("ENDED: Teardown Operations.")

    @pytest.fixture
    def create_account(self, account_name):
        return iam_obj.create_account_s3iamcli(account_name,
                                               self.acc_user_config["email_id"].format(account_name),
                                               self.ldap_user,
                                               self.ldap_passwd)

    @pytest.mark.account_user_management
    def test_1968(self):
        """
        Create new account.
        """
        self.log.info("START: Test create new account.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a new account with name {0}".format(account_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        self.log.info("Step 2: Verifying that new account is created successfully")
        assert resp[0], resp[1]
        self.log.info("END: Tested create new account.")

    @pytest.mark.account_user_management
    def test_1969(self):
        """
        List account.
        """
        self.log.info("START: Test List account.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a new account with name {0}".format(account_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 2: Listing account to verify new account is created")
        list_of_accounts = iam_obj.list_accounts_s3iamcli(self.ldap_user, self.ldap_passwd)
        assert list_of_accounts[0], list_of_accounts[1]
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        self.log.info(new_accounts)
        assert account_name not in new_accounts
        self.log.info("END: Tested List account.")

    @pytest.mark.account_user_management
    def test_1970(self):
        """
        Delete Account.
        """
        self.log.info("START: Test Delete Account.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a new account with name {0}".format(account_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: Deleting account with name {0}".format(account_name))
        resp = iam_obj.delete_account_s3iamcli(account_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("END: Tested Delete Account.")

    @pytest.mark.account_user_management
    def test_1971(self):
        """
        Create 'N' No of Accounts.
        """
        self.log.info("START: Create 'N' No of Accounts.")
        total_account = acc_usr_mng_conf["test_8531"]["total_accounts"]
        self.log.info("Step 1: Creating {0} accounts".format(total_account))
        account_list, access_keys, secret_keys = list(), list(), list()  # Defining list.
        acc_name = self.acc_user_config["account_name"]
        self.log.info("account prefix: {}".format(acc_name))
        for n in range(total_account):
            account_name = f"{acc_name}{n}{n}{str(int(time.time()))}"
            email_id = f"{acc_name}{n}{n}@seagate.com"
            self.log.info("account name: {}".format(account_name))
            self.log.info("email id: {}".format(email_id))
            resp = iam_obj.create_account_s3iamcli(account_name, email_id, self.ldap_user, self.ldap_passwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            account_list.append(account_name)
            self.log.info("account list: {}".format(account_list))
        self.log.info("Created {0} accounts".format(total_account))
        self.log.info("Step 2: Verifying {0} accounts are created by listing accounts".format(total_account))
        list_of_accounts = iam_obj.list_accounts_s3iamcli(self.ldap_user, self.ldap_passwd)
        assert list_of_accounts[0], list_of_accounts[1]
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        for n in range(total_account):
            assert account_list[n] not in new_accounts
        self.log.info("Verified {0} accounts are created by listing accounts".format(total_account))
        self.log.info("Create 'N' No of Accounts")

    def test_1972(self):
        """
        Creating new account with existing account name.
        """
        self.log.info("STARTED: Test creating new account with existing account name.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a new account with name {0}".format(account_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created a new account with name {0}".format(account_name))
        self.log.info("Step 2: Creating another account with existing account name")
        try:
            resp = self.create_account(account_name)
            self.log.info(resp)
            assert not resp[0], resp[1]
        except CTException as error:
            assert acc_usr_mng_conf["test_8532"]["err_message"] not in error.message, error.message
        self.log.info("Created another account with existing account name")
        self.log.info("END: Tested creating new account with existing account name")

    @pytest.mark.account_user_management
    def test_1973(self):
        """
        CRUD operations with valid login credentials.
        """
        self.log.info("START: Test CRUD operations with valid login credentials.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Create new account and new user in it")
        self.log.info("account name: {}".format(account_name))
        self.log.info("user name: {}".format(user_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("access key: {}".format(access_key))
        self.log.info("secret key: {}".format(secret_key))
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created new account and new user in it")
        self.log.info("Step 2: Create access key for newly created user")
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.create_access_key(user_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        self.log.info("Created access key for newly created user")
        s3_user_obj = S3TestLib(access_key=user_access_key, secret_key=user_secret_key)
        self.log.info("Step 3: Performing CRUD operations using valid user's credentials")
        bucket_name = f'{acc_usr_mng_conf["test_8533"]["bucket_name"]}-{str(int(time.time()))}'
        self.log.info("Creating a bucket with name {0}".format(bucket_name))
        resp = s3_user_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Bucket with name {0} is created successfully".format(bucket_name))
        obj_name = acc_usr_mng_conf["test_8533"]["obj_name"]
        self.log.info("Object name: {}".format(obj_name))
        resp = create_file(self.acc_user_config["test_file_path"], acc_usr_mng_conf["test_8533"]["file_size"])
        self.log.info(resp)
        self.log.info("Putting object {0} to bucket {1}".format(obj_name, bucket_name))
        resp = s3_user_obj.put_object(bucket_name, obj_name, self.acc_user_config["test_file_path"])
        assert resp[0], resp[1]
        self.log.info("Object {0} successfully put to bucket {0}".format(obj_name, bucket_name))
        self.log.info("Downloading object from bucket {0}".format(bucket_name))
        resp = s3_user_obj.object_download(bucket_name, obj_name, self.acc_user_config["test_file_path"])
        self.log.info(resp)
        assert resp[0], resp[1]
        assert resp[1] == self.acc_user_config["test_file_path"], resp[1]
        self.log.info("Downloading object from bucket {0} successfully".format(bucket_name))
        self.log.info("Step 3: Performed CRUD operations using valid user's credentials")
        # Cleanup activity
        resp = s3_user_obj.delete_bucket(bucket_name, force=True)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("END: Tested CRUD operations with valid login credentials")

    @pytest.mark.account_user_management
    def test_1974(self):
        """
        CRUD operations with invalid login credentials.
        """
        self.log.info("START: Test CRUD operations with invalid login credentials.")
        self.log.info("Step 1: Create new account and new user in it.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("username: {}".format(user_name))
        self.log.info("account name: {}".format(account_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created new account and new user in it.")
        # Dummy access and secret keys.
        user_access_key = acc_usr_mng_conf["test_8534"]["user_access_key"]
        user_secret_key = acc_usr_mng_conf["test_8534"]["user_secret_key"]
        self.log.info("user_access_key: {}".format(user_access_key))
        self.log.info("user_secret_key: {}".format(user_secret_key))
        s3_user_obj = S3TestLib(access_key=user_access_key, secret_key=user_secret_key)
        self.log.info("Step 2: Performing CRUD operations with invalid user's credentials.")
        bucket_name = acc_usr_mng_conf["test_8534"]["bucket_name"]
        self.log.info(bucket_name)
        self.log.info("Creating a bucket with name {0}".format(bucket_name))
        err_message = acc_usr_mng_conf["test_8534"]["error"]
        try:
            resp = s3_user_obj.create_bucket(bucket_name)
            assert not resp[0], resp[1]
        except CTException as error:
            assert err_message not in error.message, error.message
        self.log.info("Bucket with name {0} is not created".format(bucket_name))
        obj_name = acc_usr_mng_conf["test_8534"]["obj_name"]
        self.log.info("Putting object {0} to bucket {1}".format(obj_name, bucket_name))
        try:
            respo = create_file(self.acc_user_config["test_file_path"], acc_usr_mng_conf["test_8534"]["file_size"])
            self.log.info(respo)
            resp = s3_user_obj.put_object(bucket_name, obj_name, self.acc_user_config["test_file_path"])
            assert resp[0], resp[1]
        except CTException as error:
            assert err_message not in error.message, error.message
        self.log.info("Could not put object {0} to bucket {0}".format(obj_name, bucket_name))
        self.log.info("Downloading object from bucket {0}".format(bucket_name))
        try:
            resp = s3_user_obj.object_download(bucket_name, obj_name, self.acc_user_config["test_file_path"])
            self.log.info(resp)
            assert resp[0], resp[1]
        except CTException as error:
            assert acc_usr_mng_conf["test_8534"]["download_obj_err"] not in error.message, error.message
        self.log.info("Could not download object from bucket {0}".format(bucket_name))
        self.log.info("Step 2: Performed CRUD operations with invalid user's credentials.")
        self.log.info("END: CRUD operations with invalid login credentials")

    @pytest.mark.account_user_management
    def test_2076(self):
        """
        Create new user for current Account.
        """
        self.log.info("START: Create new user for current Account.")
        self.log.info("Step 1: Create new account and new user in it")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("account_name: {}".format(account_name))
        self.log.info("user_name: {}".format(user_name))
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("access key: {}".format(access_key))
        self.log.info("secret key: {}".format(secret_key))
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created new account and new user in it.")
        self.log.info("Step 2: Listing users and verifying user is created.")
        resp = iam_obj.list_users_s3iamcli(access_key, secret_key)
        self.log.info(resp)
        self.log.info("Users_List {}".format(resp[1]))
        assert resp[0], resp[1]
        assert user_name not in resp[1], resp[1]
        self.log.info("Listed users and verified user is created")
        self.log.info("END: Create new user for current Account.")

    @pytest.mark.account_user_management
    def test_2077(self):
        """
        Update User.
        """
        self.log.info("START: Update User.")
        self.log.info("Step 1: Create new account and new user in it")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Updating user name of already existing user")
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        new_user_name = acc_usr_mng_conf["test_8676"]["new_user_name"]
        resp = new_iam_obj.update_user(new_user_name, user_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Updated user name of already existing user")
        self.log.info("Step 3: Listing users and verifying user name is updated.")
        resp = iam_obj.list_users_s3iamcli(access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        assert acc_usr_mng_conf["test_8676"]["new_user_name"] not in resp[1], resp[1]
        self.log.info("Listed users and verified user name is updated.")
        self.log.info("END: Update User.")

    @pytest.mark.account_user_management
    def test_2078(self):
        """
        list user.
        """
        self.log.info("START: list user")
        self.log.info("Step 1: Create new account and new user in it")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created new account and new user in it")
        self.log.info("Step 2: Listing users and verifying user details are listed")
        resp = iam_obj.list_users_s3iamcli(access_key, secret_key)
        assert resp[0], resp[1]
        assert user_name not in resp[1], resp[1]
        self.log.info("Listed users and verified user details are listed")
        self.log.info("END: list user.")

    @pytest.mark.account_user_management
    def test_2079(self):
        """
        Delete User.
        """
        self.log.info("START: Delete User")
        self.log.info("Step 1: Create new account and new user in it.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("Created new account and new user in it")
        self.log.info("Step 2: Deleting user")
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.delete_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Deleted user successfully")
        self.log.info("END: Delete User")

    @pytest.mark.account_user_management
    def test_2080(self):
        """
        Created 'N' No of Users.
        """
        self.log.info("Created 'N' No of Users")
        total_users = acc_usr_mng_conf["test_8679"]["total_users"]
        self.log.info("Step 1: Create new {} account".format(total_users))
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Created new account successfully.")
        self.log.info("Step 2: Creating {0} users".format(total_users))
        for n in range(total_users):
            my_user_name = f"{user_name}{n}"
            self.log.info("Creating user with name {0}".format(my_user_name))
            resp = iam_obj.create_user_using_s3iamcli(my_user_name, access_key, secret_key)
            assert resp[0], resp[1]
            self.log.info("Created user with name {0}".format(my_user_name))
        self.log.info("Step 2: Created {0} users".format(total_users))
        self.log.info("Verifying {0} users are created".format(total_users))
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        list_of_users = new_iam_obj.list_users()[1]
        self.log.info(list_of_users)
        self.log.info("Number of users : {}".format(len(list_of_users)))
        assert resp[0], resp[1]
        assert len(list_of_users) >= total_users, list_of_users[1]
        self.log.info("Verified {0} users are created".format(total_users))
        self.log.info("END: Created 'N' No of Users")

    def test_2081(self):
        """
        creating user with existing name.
        """
        self.log.info("START: creating user with existing name.")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created user with name {0}".format(user_name))
        self.log.info("Step 2: Creating user with existing name {0}".format(user_name))
        try:
            resp = iam_obj.create_user(user_name)
            self.log.info(resp)
            assert not resp[0], resp[1]
        except CTException as error:
            assert acc_usr_mng_conf["test_8680"]["err_message"] not in error.message, error.message
        self.log.info("Could not create user with existing name {0}".format(user_name))
        self.log.info("END: creating user with existing name.")

    @pytest.mark.account_user_management
    def test_2082(self):
        """
        Create Access key to the user.
        """
        self.log.info("START: Create Access key to the user")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Verifying user is created by listing users")
        resp = iam_obj.list_users()
        self.log.info("Users list {}".format(resp[1]))
        assert resp[0], resp[1]
        assert user_name not in str(resp[1]), resp[1]
        self.log.info("Verified that user is created by listing users")
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Created access key for the user")
        self.log.info("END: Create Access key to the user")

    @pytest.mark.account_user_management
    def test_2083(self):
        """
        list accesskeys for the user.
        """
        self.log.info("START: List accesskeys for the user")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        self.log.info("Created access key for the user")
        self.log.info("Step 3: Listing access key of the user")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        resp_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        assert user_access_key == resp_access_key, resp[1]
        self.log.info("Listed access key of the user successfully")
        self.log.info("END: List accesskeys for the user")

    @pytest.mark.account_user_management
    def test_2084(self):
        """
        Delete Accesskey of a user.
        """
        self.log.info("START: Delete Accesskey of a users")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        self.log.info("Created access key for the user")
        self.log.info("Step 3: Deleting access key of the user")
        resp = iam_obj.delete_access_key(user_name, user_access_key)
        assert resp[0], resp[1]
        self.log.info("Deleted access key of the user")
        self.log.info("Step 4: Listing access key of the user")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        # Verifying list is empty.
        assert len(resp[1]["AccessKeyMetadata"]) == 0, resp[1]["AccessKeyMetadata"]
        self.log.info("Listed access key of the user successfully.")
        self.log.info("END: Delete Accesskey of a users")

    @pytest.mark.account_user_management
    def test_2085(self):
        """
        Update Accesskey of a user.
        """
        self.log.info("START: Update Accesskey of a user.")
        test_8684_cfg = acc_usr_mng_conf["test_8684"]
        self.log.info("Update Accesskey of a user")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert resp[0], resp[1]
        self.log.info("Step 3: Updating access key of user")
        resp = iam_obj.update_access_key(access_key_to_update, test_8684_cfg["status"], user_name)
        assert resp[0], resp[1]
        self.log.info("Updated access key of user")
        self.log.info("Step 4: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert new_access_key == access_key_to_update, resp[1]
        assert status == test_8684_cfg["status"], resp[1]
        self.log.info("Verified that access key of user is updated successfully")
        self.log.info("END: Update Accesskey of a user.")

    @pytest.mark.account_user_management
    def test_2086(self):
        """
        update accesskey of a user with inactive mode.
        """
        self.log.info("START: update accesskey of a user with inactive mode.")
        test_8685_cfg = acc_usr_mng_conf["test_8685"]
        self.log.info("update accesskey of a user with inactive mode")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert resp[0], resp[1]
        self.log.info("Step 3: Updating access key of user")
        resp = iam_obj.update_access_key(access_key_to_update, test_8685_cfg["status"], user_name)
        assert resp[0], resp[1]
        self.log.info("Updated access key of user")
        self.log.info("Step 4: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert new_access_key == access_key_to_update, resp[1]
        assert status == test_8685_cfg["status"], resp[1]
        self.log.info("Verified that access key of user is updated successfully")
        self.log.info("END: update accesskey of a user with inactive mode")

    @pytest.mark.account_user_management
    def test_2087(self):
        """
        create max accesskey with existing user name.
        """
        self.log.info("START: create max accesskey with existing user name.")
        test_8686_cfg = acc_usr_mng_conf["test_8686"]
        self.log.info("create max accesskey with existing user name")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating {0} access keys for user {1}".format(test_8686_cfg["max_access_keys"],
                                                                             user_name))
        for n in range(test_8686_cfg["max_access_keys"]):
            resp = iam_obj.create_access_key(user_name)
            assert resp[0], resp[1]
        self.log.info("END: create max accesskey with existing user name")

    @pytest.mark.account_user_management
    def test_2088(self):
        """
        update login profile.
        """
        self.log.info("START: update login profile.")
        test_8687_cfg = acc_usr_mng_conf["test_8687"]
        self.log.info("update login profile")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating login profile for user {0}".format(user_name))
        resp = iam_obj.create_user_login_profile(user_name, test_8687_cfg["password"], test_8687_cfg["password_reset"])
        assert resp[0], resp[1]
        self.log.info("Created login profile for user {0}".format(user_name))
        self.log.info("Step 3: Updating login profile for user {0}".format(user_name))
        resp = iam_obj.update_user_login_profile(user_name, test_8687_cfg["new_password"],
                                                 test_8687_cfg["password_reset"])
        assert resp[0], resp[1]
        self.log.info("Updated login profile for user {0}".format(user_name))
        self.log.info("END: update login profile")

    @pytest.mark.account_user_management
    def test_2090(self):
        """
        SSL certificate.
        """
        self.log.info("START: SSL certificate.")
        test_8689_cfg = acc_usr_mng_conf["test_8689"]
        ca_cert_path = self.cons_obj_dict["ca_cert_path"]
        resp = s3hobj.is_s3_server_path_exists(ca_cert_path)
        assert resp, "certificate path not present: {}".format(ca_cert_path)
        s3hobj.copy_s3server_file(ca_cert_path, test_8689_cfg["local_cert_path"])
        with open(test_8689_cfg["local_cert_path"], "r") as file:
            file_data = file.readlines()
        self.log.info(file_data)
        assert test_8689_cfg["starts_with"] not in file_data[0], test_8689_cfg["err_message_1"].format(
            test_8689_cfg["starts_with"])
        assert test_8689_cfg["ends_with"] not in file_data[-1], test_8689_cfg["err_message_2"].format(
            test_8689_cfg["ends_with"])
        remove_file(test_8689_cfg["local_cert_path"])
        self.log.info("END: SSL certificate.")

    @pytest.mark.account_user_management
    def test_2091(self):
        """
        ssl certificate present.
        """
        self.log.info("START: ssl certificate present.")
        ca_cert_path = self.cons_obj_dict["ca_cert_path"]
        self.log.info("Step 1: Checking if {0} file exists on server".format(ca_cert_path))
        resp = s3hobj.is_s3_server_path_exists(ca_cert_path)
        assert resp, "certificate path not present: {}".format(ca_cert_path)
        self.log.info("Verified that {0} file exists on server".format(ca_cert_path))
        self.log.info("END: ssl certificate present.")

    @pytest.mark.account_user_management
    def test_2092(self):
        """
        change passsword for IAM user.
        """
        self.log.info("START: Change password for IAM user.")
        test_8691_cfg = acc_usr_mng_conf["test_8691"]
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        self.log.info("Step 1: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 2: Creating login profile for user {0}".format(user_name))
        resp = iam_obj.create_user_login_profile(user_name, test_8691_cfg["password"], test_8691_cfg["pwd_reset"])
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created login profile for user {0}".format(user_name))
        self.log.info("Step 3: Creating access key for user {0}".format(user_name))
        resp = iam_obj.create_access_key(user_name)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Created access key for user {0}".format(user_name))
        access_key = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        self.log.info("Step 4: Changing password for {0} user".format(user_name))
        resp = iam_obj.change_user_password(test_8691_cfg["password"], test_8691_cfg["new_password"],
                                            access_key, secret_key)
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Changed password for {0} user".format(user_name))
        self.log.info("END: Change password for IAM user.")

    @pytest.mark.account_user_management
    def test_4625(self):
        """
        Test Create user for the account and verify output with proper ARN format.
        """
        self.log.info("STARTED: Test Create user for the account and verify output with proper ARN format")
        test_4625_cfg = acc_usr_mng_conf["test_4625"]
        account_name = f"{self.acc_user_config['account_name']}_{str(int(time.time()))}"
        user_name = f"{self.acc_user_config['user_name']}_{str(int(time.time()))}"
        self.log.info("Step 1: Creating a new account with name {0}".format(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        account_id = resp[1]["Account_Id"]
        self.log.info("Created a new account with name {0}".format(account_name))
        self.log.info("Step 2: Creating a user with name {0}".format(user_name))
        resp = iam_obj.create_user_using_s3iamcli(user_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info("Created a user with name {0}".format(user_name))
        self.log.info("Step 3: Verifying ARN format of user {0}".format(user_name))
        arn_format = test_4625_cfg["arn_str"].format(account_id, user_name)
        assert arn_format ==  resp[1]["ARN"], test_4625_cfg["err_message"]
        self.log.info("Step 3: Verified ARN format of user {0} successfully".format(user_name))
        self.log.info("ENDED: Test Create user for the account and verify output with proper ARN format")
