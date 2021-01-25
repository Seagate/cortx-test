#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Account User Management test module."""

import time
import logging
import pytest

from commons.constants import const
from commons.ct_fail_on import ct_fail_on
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.helpers.s3_helper import S3Helper
from commons.utils.system_utils import create_file, remove_file
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.iam_test_lib import IamTestLib

iam_obj = IamTestLib()
s3_obj = S3TestLib()
try:
    s3hobj = S3Helper()
except ImportError as err:
    s3hobj = S3Helper.get_instance()

LOGGER = logging.getLogger(__name__)
TEST_CFG = read_yaml("config/s3/test_account_user_management.yaml")[1]
CMN_CFG = read_yaml("config/common_config.yaml")[1]


class TestAccountUserManagement:
    """Account User Management TestSuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        LOGGER.info("STARTED: setup test suite operations.")
        cls.acc_user_config = TEST_CFG["acc_user_mng"]
        cls.ca_cert_path = const.CA_CERT_PATH
        cls.ldap_user = CMN_CFG["ldap_username"]
        cls.ldap_passwd = CMN_CFG["ldap_passwd"]
        LOGGER.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        LOGGER.info("STARTED: teardown test suite operations.")
        del cls.acc_user_config
        LOGGER.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        LOGGER.info("STARTED: Setup operations.")
        LOGGER.info("Certificate path: %s", self.ca_cert_path)
        LOGGER.info("LDAP credentials.")
        LOGGER.info(self.ldap_user)
        LOGGER.info(self.ldap_passwd)
        LOGGER.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        all_users = iam_obj.list_users()[1]
        users_list = [user["UserName"]
                      for user in all_users
                      if self.acc_user_config["user_name"] in user["UserName"]]
        LOGGER.info("IAM users: %s", str(users_list))
        if users_list:
            LOGGER.info("Deleting IAM users...")
            for user in users_list:
                res = iam_obj.list_access_keys(user)
                if res[0]:
                    LOGGER.info("Deleting user access key...")
                    keys_meta = res[1]["AccessKeyMetadata"]
                    for key in keys_meta:
                        iam_obj.delete_access_key(
                            user, key["AccessKeyId"])
                    LOGGER.info("Deleted user access key.")
                try:
                    LOGGER.info("Deleting a user: %s", str(user))
                    iam_obj.delete_user(user)
                except CTException as error:
                    LOGGER.error(error)
        LOGGER.info("Deleted users successfully.")
        account_name = self.acc_user_config["account_name"]
        acc_list = iam_obj.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_passwd)[1]
        all_acc = [acc["AccountName"]
                   for acc in acc_list if account_name in acc["AccountName"]]
        if all_acc:
            LOGGER.info("Accounts to delete: %s", str(all_acc))
            for acc in all_acc:
                try:
                    LOGGER.info("Deleting %s account", str(acc))
                    iam_obj.reset_access_key_and_delete_account_s3iamcli(acc)
                    LOGGER.info("Deleted %s account", str(acc))
                except CTException as error:
                    LOGGER.info(error)
        LOGGER.info("ENDED: Teardown Operations.")

    def create_account(self, account_name):
        """create s3 account using s3iamcli."""
        return iam_obj.create_account_s3iamcli(
            account_name,
            self.acc_user_config["email_id"].format(account_name),
            self.ldap_user,
            self.ldap_passwd)

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5440")
    @ct_fail_on(error_handler)
    def test_create_new_account_1968(self):
        """Create new account."""
        LOGGER.info("START: Test create new account.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        LOGGER.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        LOGGER.info(
            "Step 2: Verifying that new account is created successfully")
        assert resp[0], resp[1]
        LOGGER.info("END: Tested create new account.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5429")
    @ct_fail_on(error_handler)
    def test_list_account_1969(self):
        """List account."""
        LOGGER.info("START: Test List account.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        LOGGER.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Listing account to verify new account is created")
        list_of_accounts = iam_obj.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_passwd)
        assert list_of_accounts[0], list_of_accounts[1]
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        LOGGER.info(new_accounts)
        assert account_name not in new_accounts
        LOGGER.info("END: Tested List account.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5432")
    @ct_fail_on(error_handler)
    def test_delete_account_1970(self):
        """Delete Account."""
        LOGGER.info("START: Test Delete Account.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        LOGGER.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        LOGGER.info(
            "Step 2: Deleting account with name %s", str(account_name))
        resp = iam_obj.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("END: Tested Delete Account.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5443")
    @ct_fail_on(error_handler)
    def test_create_n_number_of_account_1971(self):
        """Create 'N' No of Accounts."""
        LOGGER.info("START: Create 'N' No of Accounts.")
        total_account = TEST_CFG["test_8531"]["total_accounts"]
        LOGGER.info("Step 1: Creating %s accounts", str(total_account))
        # Defining list.
        account_list, access_keys, secret_keys = list(), list(), list()
        acc_name = self.acc_user_config["account_name"]
        LOGGER.info("account prefix: %s", str(acc_name))
        for cnt in range(total_account):
            account_name = f"{acc_name}{cnt}{cnt}{str(int(time.time()))}"
            email_id = f"{acc_name}{cnt}{cnt}@seagate.com"
            LOGGER.info("account name: %s", str(account_name))
            LOGGER.info("email id: %s", str(email_id))
            resp = iam_obj.create_account_s3iamcli(
                account_name, email_id, self.ldap_user, self.ldap_passwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            account_list.append(account_name)
            LOGGER.info("account list: %s", str(account_list))
        LOGGER.info("Created %s accounts", str(total_account))
        LOGGER.info(
            "Step 2: Verifying %s accounts are created by listing accounts",
            str(total_account))
        list_of_accounts = iam_obj.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_passwd)
        assert list_of_accounts[0], list_of_accounts[1]
        new_accounts = [acc["AccountName"] for acc in list_of_accounts[1]]
        for cnt in range(total_account):
            assert account_list[cnt] in new_accounts
        LOGGER.info(
            "Verified %s accounts are created by listing accounts",
            str(total_account))
        LOGGER.info("Create 'N' No of Accounts.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5437")
    @ct_fail_on(error_handler)
    def test_create_new_account_with_existing_name_1972(self):
        """Creating new account with existing account name."""
        LOGGER.info(
            "STARTED: Test creating new account with existing account name.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        LOGGER.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Created a new account with name %s", str(account_name))
        LOGGER.info(
            "Step 2: Creating another account with existing account name")
        try:
            resp = self.create_account(account_name)
            LOGGER.info(resp)
            assert not resp[0], resp[1]
        except CTException as error:
            assert TEST_CFG["test_8532"]["err_message"] not in error.message, error.message
        LOGGER.info("Created another account with existing account name")
        LOGGER.info(
            "END: Tested creating new account with existing account name")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5434")
    @ct_fail_on(error_handler)
    def test_crud_operations_with_valid_cred_1973(self):
        """CRUD operations with valid login credentials."""
        LOGGER.info("START: Test CRUD operations with valid login credentials.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Create new account and new user in it")
        LOGGER.info("account name: %s", str(account_name))
        LOGGER.info("user name: %s", str(user_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        LOGGER.info("access key: %s", str(access_key))
        LOGGER.info("secret key: %s", str(secret_key))
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Created new account and new user in it")
        LOGGER.info("Step 2: Create access key for newly created user")
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.create_access_key(user_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info("Created access key for newly created user")
        s3_user_obj = S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        LOGGER.info(
            "Step 3: Performing CRUD operations using valid user's credentials")
        bucket_name = f'{TEST_CFG["test_8533"]["bucket_name"]}-{str(int(time.time()))}'
        LOGGER.info("Creating a bucket with name %s", str(bucket_name))
        resp = s3_user_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Bucket with name %s is created successfully", str(bucket_name))
        obj_name = TEST_CFG["test_8533"]["obj_name"]
        LOGGER.info("Object name: %s", str(obj_name))
        resp = create_file(
            self.acc_user_config["test_file_path"],
            TEST_CFG["test_8533"]["file_size"])
        LOGGER.info(resp)
        LOGGER.info("Putting object %s to bucket %s", obj_name, bucket_name)
        resp = s3_user_obj.put_object(
            bucket_name, obj_name, self.acc_user_config["test_file_path"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Object {0} successfully put to bucket %s", str(
                obj_name, bucket_name))
        LOGGER.info("Downloading object from bucket %s", str(bucket_name))
        resp = s3_user_obj.object_download(
            bucket_name, obj_name, self.acc_user_config["test_file_path"])
        LOGGER.info(resp)
        assert resp[0], resp[1]
        assert resp[1] == self.acc_user_config["test_file_path"], resp[1]
        LOGGER.info(
            "Downloading object from bucket %s successfully", str(bucket_name))
        LOGGER.info(
            "Step 3: Performed CRUD operations using valid user's credentials")
        # Cleanup activity
        resp = s3_user_obj.delete_bucket(bucket_name, force=True)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("END: Tested CRUD operations with valid login credentials")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5435")
    @ct_fail_on(error_handler)
    def test_crud_operations_with_invalid_cred_1974(self):
        """CRUD operations with invalid login credentials."""
        LOGGER.info(
            "START: Test CRUD operations with invalid login credentials.")
        LOGGER.info("Step 1: Create new account and new user in it.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("username: %s", str(user_name))
        LOGGER.info("account name: %s", str(account_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Created new account and new user in it.")
        # Dummy access and secret keys.
        user_access_key = TEST_CFG["test_8534"]["user_access_key"]
        user_secret_key = TEST_CFG["test_8534"]["user_secret_key"]
        LOGGER.info("user_access_key: %s", str(user_access_key))
        LOGGER.info("user_secret_key: %s", str(user_secret_key))
        s3_user_obj = S3TestLib(
            access_key=user_access_key,
            secret_key=user_secret_key)
        LOGGER.info(
            "Step 2: Performing CRUD operations with invalid user's credentials.")
        bucket_name = TEST_CFG["test_8534"]["bucket_name"]
        LOGGER.info(bucket_name)
        LOGGER.info("Creating a bucket with name %s", str(bucket_name))
        err_message = TEST_CFG["test_8534"]["error"]
        try:
            resp = s3_user_obj.create_bucket(bucket_name)
            assert not resp[0], resp[1]
        except CTException as error:
            assert err_message not in error.message, error.message
        LOGGER.info("Bucket with name %s is not created", str(bucket_name))
        obj_name = TEST_CFG["test_8534"]["obj_name"]
        LOGGER.info("Putting object %s to bucket %s", obj_name, bucket_name)
        try:
            respo = create_file(
                self.acc_user_config["test_file_path"],
                TEST_CFG["test_8534"]["file_size"])
            LOGGER.info(respo)
            resp = s3_user_obj.put_object(
                bucket_name, obj_name, self.acc_user_config["test_file_path"])
            assert resp[0], resp[1]
        except CTException as error:
            assert err_message not in error.message, error.message
        LOGGER.info(
            "Could not put object {0} to bucket %s", str(
                obj_name, bucket_name))
        LOGGER.info("Downloading object from bucket %s", str(bucket_name))
        try:
            resp = s3_user_obj.object_download(
                bucket_name, obj_name, self.acc_user_config["test_file_path"])
            LOGGER.info(resp)
            assert resp[0], resp[1]
        except CTException as error:
            assert TEST_CFG["test_8534"]["download_obj_err"] not in error.message, error.message
        LOGGER.info(
            "Could not download object from bucket %s", str(bucket_name))
        LOGGER.info(
            "Step 2: Performed CRUD operations with invalid user's credentials.")
        LOGGER.info("END: CRUD operations with invalid login credentials")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5439")
    @ct_fail_on(error_handler)
    def test_create_new_user_from_current_account_2076(self):
        """Create new user for current Account."""
        LOGGER.info("START: Create new user for current Account.")
        LOGGER.info("Step 1: Create new account and new user in it")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("account_name: %s", str(account_name))
        LOGGER.info("user_name: %s", str(user_name))
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        LOGGER.info("access key: %s", str(access_key))
        LOGGER.info("secret key: %s", str(secret_key))
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Created new account and new user in it.")
        LOGGER.info("Step 2: Listing users and verifying user is created.")
        resp = iam_obj.list_users_s3iamcli(access_key, secret_key)
        LOGGER.info(resp)
        LOGGER.info("Users_List %s", str(resp[1]))
        assert resp[0], resp[1]
        assert user_name not in resp[1], resp[1]
        LOGGER.info("Listed users and verified user is created")
        LOGGER.info("END: Create new user for current Account.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5422")
    @ct_fail_on(error_handler)
    def test_update_user_2077(self):
        """Update User."""
        LOGGER.info("START: Update User.")
        LOGGER.info("Step 1: Create new account and new user in it")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Created new account and new user in it")
        LOGGER.info("Step 2: Updating user name of already existing user")
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        new_user_name = TEST_CFG["test_8676"]["new_user_name"]
        resp = new_iam_obj.update_user(new_user_name, user_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Updated user name of already existing user")
        LOGGER.info("Step 3: Listing users and verifying user name is updated.")
        resp = iam_obj.list_users_s3iamcli(access_key, secret_key)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        assert TEST_CFG["test_8676"]["new_user_name"] not in resp[1], resp[1]
        LOGGER.info("Listed users and verified user name is updated.")
        LOGGER.info("END: Update User.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5428")
    @ct_fail_on(error_handler)
    def test_list_user_2078(self):
        """list user."""
        LOGGER.info("START: list user")
        LOGGER.info("Step 1: Create new account and new user in it")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Created new account and new user in it")
        LOGGER.info(
            "Step 2: Listing users and verifying user details are listed")
        resp = iam_obj.list_users_s3iamcli(access_key, secret_key)
        assert resp[0], resp[1]
        assert user_name not in resp[1], resp[1]
        LOGGER.info("Listed users and verified user details are listed")
        LOGGER.info("END: list user.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5431")
    @ct_fail_on(error_handler)
    def test_delete_user_2079(self):
        """Delete User."""
        LOGGER.info("START: Delete User")
        LOGGER.info("Step 1: Create new account and new user in it.")
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("Created new account and new user in it")
        LOGGER.info("Step 2: Deleting user")
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        resp = new_iam_obj.delete_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Deleted user successfully")
        LOGGER.info("END: Delete User")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5438")
    @ct_fail_on(error_handler)
    def test_create_n_number_of_users_2080(self):
        """Created 'N' No of Users."""
        LOGGER.info("Created 'N' No of Users")
        total_users = TEST_CFG["test_8679"]["total_users"]
        LOGGER.info("Step 1: Create new %s account", str(total_users))
        account_name = f'{self.acc_user_config["account_name"]}_{str(int(time.time()))}'
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        LOGGER.info("Created new account successfully.")
        LOGGER.info("Step 2: Creating %s users", str(total_users))
        for cnt in range(total_users):
            my_user_name = f"{user_name}{cnt}"
            LOGGER.info("Creating user with name %s", str(my_user_name))
            resp = iam_obj.create_user_using_s3iamcli(
                my_user_name, access_key, secret_key)
            assert resp[0], resp[1]
            LOGGER.info("Created user with name %s", str(my_user_name))
        LOGGER.info("Step 2: Created %s users", str(total_users))
        LOGGER.info("Verifying %s users are created", (total_users))
        new_iam_obj = IamTestLib(access_key=access_key, secret_key=secret_key)
        list_of_users = new_iam_obj.list_users()[1]
        LOGGER.info(list_of_users)
        LOGGER.info("Number of users : %s", str(len(list_of_users)))
        assert resp[0], resp[1]
        assert len(list_of_users) >= total_users, list_of_users[1]
        LOGGER.info("Verified %s users are created", str(total_users))
        LOGGER.info("END: Created 'N' No of Users.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5438")
    @ct_fail_on(error_handler)
    def test_create_user_with_existing_name_2081(self):
        """creating user with existing name."""
        LOGGER.info("START: creating user with existing name.")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created user with name %s", str(user_name))
        LOGGER.info(
            "Step 2: Creating user with existing name %s", str(user_name))
        try:
            resp = iam_obj.create_user(user_name)
            LOGGER.info(resp)
            assert not resp[0], resp[1]
        except CTException as error:
            assert TEST_CFG["test_8680"]["err_message"] not in error.message, error.message
        LOGGER.info(
            "Could not create user with existing name %s", str(user_name))
        LOGGER.info("END: creating user with existing name.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5442")
    @ct_fail_on(error_handler)
    def test_create_access_key_to_the_user_2082(self):
        """Create Access key to the user."""
        LOGGER.info("START: Create Access key to the user")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Verifying user is created by listing users")
        resp = iam_obj.list_users()
        LOGGER.info("Users list %s", str(resp[1]))
        assert resp[0], resp[1]
        assert user_name not in str(resp[1]), resp[1]
        LOGGER.info("Verified that user is created by listing users")
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Created access key for the user")
        LOGGER.info("END: Create Access key to the user")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5430")
    @ct_fail_on(error_handler)
    def test_list_access_keys_for_the_user_2083(self):
        """list accesskeys for the user."""
        LOGGER.info("START: List accesskeys for the user")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        LOGGER.info("Created access key for the user")
        LOGGER.info("Step 3: Listing access key of the user")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        resp_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        assert user_access_key == resp_access_key, resp[1]
        LOGGER.info("Listed access key of the user successfully")
        LOGGER.info("END: List accesskeys for the user")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5433")
    @ct_fail_on(error_handler)
    def test_delete_access_key_of_a_user_2084(self):
        """Delete Accesskey of a user."""
        LOGGER.info("START: Delete Accesskey of a users")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        assert resp[0], resp[1]
        user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
        LOGGER.info("Created access key for the user")
        LOGGER.info("Step 3: Deleting access key of the user")
        resp = iam_obj.delete_access_key(user_name, user_access_key)
        assert resp[0], resp[1]
        LOGGER.info("Deleted access key of the user")
        LOGGER.info("Step 4: Listing access key of the user")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        # Verifying list is empty.
        assert len(resp[1]["AccessKeyMetadata"]
                   ) == 0, resp[1]["AccessKeyMetadata"]
        LOGGER.info("Listed access key of the user successfully.")
        LOGGER.info("END: Delete Accesskey of a users")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5425")
    @ct_fail_on(error_handler)
    def test_update_access_key_of_a_user_2085(self):
        """Update Accesskey of a user."""
        LOGGER.info("START: Update Accesskey of a user.")
        test_8684_cfg = TEST_CFG["test_8684"]
        LOGGER.info("Update Accesskey of a user")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Updating access key of user")
        resp = iam_obj.update_access_key(
            access_key_to_update, test_8684_cfg["status"], user_name)
        assert resp[0], resp[1]
        LOGGER.info("Updated access key of user")
        LOGGER.info("Step 4: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert new_access_key == access_key_to_update, resp[1]
        assert status == test_8684_cfg["status"], resp[1]
        LOGGER.info("Verified that access key of user is updated successfully")
        LOGGER.info("END: Update Accesskey of a user.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5424")
    @ct_fail_on(error_handler)
    def test_update_accesskey_of_user_with_inactive_mode_2086(self):
        """update accesskey of a user with inactive mode."""
        LOGGER.info("START: update accesskey of a user with inactive mode.")
        test_8685_cfg = TEST_CFG["test_8685"]
        LOGGER.info("update accesskey of a user with inactive mode")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info("Step 2: Creating access key for the user")
        resp = iam_obj.create_access_key(user_name)
        access_key_to_update = resp[1]["AccessKey"]["AccessKeyId"]
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Updating access key of user")
        resp = iam_obj.update_access_key(
            access_key_to_update, test_8685_cfg["status"], user_name)
        assert resp[0], resp[1]
        LOGGER.info("Updated access key of user")
        LOGGER.info("Step 4: Verifying that access key of user is updated")
        resp = iam_obj.list_access_keys(user_name)
        assert resp[0], resp[1]
        new_access_key = resp[1]["AccessKeyMetadata"][0]["AccessKeyId"]
        status = resp[1]["AccessKeyMetadata"][0]["Status"]
        assert new_access_key == access_key_to_update, resp[1]
        assert status == test_8685_cfg["status"], resp[1]
        LOGGER.info("Verified that access key of user is updated successfully")
        LOGGER.info("END: update accesskey of a user with inactive mode")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5441")
    @ct_fail_on(error_handler)
    def test_create_max_accesskey_with_existing_user_name_2087(self):
        """create max accesskey with existing user name."""
        LOGGER.info("START: create max accesskey with existing user name.")
        test_8686_cfg = TEST_CFG["test_8686"]
        LOGGER.info("create max accesskey with existing user name")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info("Step 2: Creating %s access keys for user %s",
                    test_8686_cfg["max_access_keys"], user_name)
        for _ in range(test_8686_cfg["max_access_keys"]):
            resp = iam_obj.create_access_key(user_name)
            assert resp[0], resp[1]
        LOGGER.info("END: create max accesskey with existing user name")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5423")
    @ct_fail_on(error_handler)
    def test_update_login_profile_2088(self):
        """update login profile."""
        LOGGER.info("START: update login profile.")
        test_8687_cfg = TEST_CFG["test_8687"]
        LOGGER.info("update login profile")
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info(
            "Step 2: Creating login profile for user %s", str(user_name))
        resp = iam_obj.create_user_login_profile(
            user_name, test_8687_cfg["password"], test_8687_cfg["password_reset"])
        assert resp[0], resp[1]
        LOGGER.info("Created login profile for user %s", str(user_name))
        LOGGER.info(
            "Step 3: Updating login profile for user %s", str(user_name))
        resp = iam_obj.update_user_login_profile(
            user_name,
            test_8687_cfg["new_password"],
            test_8687_cfg["password_reset"])
        assert resp[0], resp[1]
        LOGGER.info("Updated login profile for user %s", str(user_name))
        LOGGER.info("END: update login profile")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5427")
    @ct_fail_on(error_handler)
    def test_ssl_certificate_2090(self):
        """SSL certificate."""
        LOGGER.info("START: SSL certificate.")
        test_8689_cfg = TEST_CFG["test_8689"]
        resp = s3hobj.is_s3_server_path_exists(self.ca_cert_path)
        assert resp, "certificate path not present: {}".format(
            self.ca_cert_path)
        s3hobj.copy_s3server_file(
            self.ca_cert_path, test_8689_cfg["local_cert_path"])
        with open(test_8689_cfg["local_cert_path"], "r") as file:
            file_data = file.readlines()
        LOGGER.info(file_data)
        assert test_8689_cfg["starts_with"] not in file_data[0],\
            test_8689_cfg["err_message_1"].format(test_8689_cfg["starts_with"])
        assert test_8689_cfg["ends_with"] not in file_data[-1],\
            test_8689_cfg["err_message_2"].format(test_8689_cfg["ends_with"])
        remove_file(test_8689_cfg["local_cert_path"])
        LOGGER.info("END: SSL certificate.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5426")
    @ct_fail_on(error_handler)
    def test_check_ssl_certificate_present_2091(self):
        """ssl certificate present."""
        LOGGER.info("START: ssl certificate present.")
        LOGGER.info(
            "Step 1: Checking if %s file exists on server", str(
                self.ca_cert_path))
        resp = s3hobj.is_s3_server_path_exists(self.ca_cert_path)
        assert resp, "certificate path not present: {}".format(
            self.ca_cert_path)
        LOGGER.info(
            "Verified that %s file exists on server", str(self.ca_cert_path))
        LOGGER.info("END: ssl certificate present.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-5444")
    @ct_fail_on(error_handler)
    def test_change_pwd_for_iam_user_2092(self):
        """change passsword for IAM user."""
        LOGGER.info("START: Change password for IAM user.")
        test_8691_cfg = TEST_CFG["test_8691"]
        user_name = f'{self.acc_user_config["user_name"]}_{str(int(time.time()))}'
        LOGGER.info("Step 1: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user(user_name)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info(
            "Step 2: Creating login profile for user %s", str(user_name))
        resp = iam_obj.create_user_login_profile(
            user_name, test_8691_cfg["password"], test_8691_cfg["pwd_reset"])
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Created login profile for user %s", str(user_name))
        LOGGER.info(
            "Step 3: Creating access key for user %s", str(user_name))
        resp = iam_obj.create_access_key(user_name)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Created access key for user %s", str(user_name))
        access_key = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
        LOGGER.info("Step 4: Changing password for %s user", str(user_name))
        resp = iam_obj.change_user_password(
            test_8691_cfg["password"],
            test_8691_cfg["new_password"],
            access_key,
            secret_key)
        LOGGER.info(resp)
        assert resp[0], resp[1]
        LOGGER.info("Changed password for %s user", str(user_name))
        LOGGER.info("END: Change password for IAM user.")

    @pytest.mark.parallel
    @pytest.mark.account_user_management
    @pytest.mark.tag("TEST-8718")
    @ct_fail_on(error_handler)
    def test_create_user_account_and_check_arn_4625(self):
        """Test Create user for the account and verify output with proper ARN format."""
        LOGGER.info(
            "STARTED: Test Create user for the account and verify output with proper ARN format")
        test_4625_cfg = TEST_CFG["test_4625"]
        account_name = f"{self.acc_user_config['account_name']}_{str(int(time.time()))}"
        user_name = f"{self.acc_user_config['user_name']}_{str(int(time.time()))}"
        LOGGER.info(
            "Step 1: Creating a new account with name %s", str(account_name))
        resp = self.create_account(account_name)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        account_id = resp[1]["Account_Id"]
        LOGGER.info("Created a new account with name %s", str(account_name))
        LOGGER.info("Step 2: Creating a user with name %s", str(user_name))
        resp = iam_obj.create_user_using_s3iamcli(
            user_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info("Created a user with name %s", str(user_name))
        LOGGER.info(
            "Step 3: Verifying ARN format of user %s", str(user_name))
        arn_format = test_4625_cfg["arn_str"].format(account_id, user_name)
        assert arn_format == resp[1]["ARN"], test_4625_cfg["err_message"]
        LOGGER.info(
            "Step 3: Verified ARN format of user %s successfully",
            str(user_name))
        LOGGER.info(
            "ENDED: Test Create user for the account and verify output with proper ARN format")
