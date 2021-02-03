#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for IAM test helper library which contains admin_path operations."""

import os
import time
import shutil
import logging
import pytest

from commons.utils import system_utils
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.helpers.s3_helper import S3Helper
from libs.s3 import iam_test_lib, s3_test_lib

IAM_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
UT_OBJ = system_utils
try:
    S3OBJ = S3Helper()
except ImportError as err:
    S3OBJ = S3Helper.get_instance()

CMN_CFG = read_yaml("config/common_config.yaml")[1]


class TestIamLib:
    """S3 Iam test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        logging.basicConfig(
            filename="unittest.log",
            filemode="w",
            level=logging.DEBUG)
        cls.log = logging.getLogger(__name__)
        cls.user_name_prefix = "ut-usr"
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.test_file_path = "/root/test_folder/hello.txt"
        cls.test_folder_path = "/root/test_folder"
        cls.ldap_user = CMN_CFG["ldap_username"]
        cls.ldap_pwd = CMN_CFG["ldap_passwd"]

    @classmethod
    def teardown_class(cls):
        """Test teardown class."""
        cls.log.info("Test teardown completed.")

    def setup_method(self):
        """
        Function will be invoked before test execution.

        It will perform prerequisite test steps if any
        Defined var for log, onfig, creating common dir
        """
        self.log.info("STARTED: Setup operations")
        if not os.path.exists(self.test_folder_path):
            os.mkdir(self.test_folder_path)
        self.d_user_name = "dummy_user"
        self.status = "Inactive"
        self.d_status = "dummy_Inactive"
        self.d_nw_user_name = "dummy_user"
        self.email = "{}@seagate.com"
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after test case.

        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        self.log.info("STARTED: Teardown operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        account_name = self.acc_name_prefix
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user,
            self.ldap_pwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if account_name in acc["AccountName"]]
        if all_acc:
            for acc in all_acc:
                resp = IAM_OBJ.reset_account_access_key_s3iamcli(
                    acc, self.ldap_user, self.ldap_pwd)
                access_key = resp[1]["AccessKeyId"]
                secret_key = resp[1]["SecretKey"]
                s3_temp_obj = s3_test_lib.S3TestLib(
                    access_key=access_key, secret_key=secret_key)
                test_buckets = s3_temp_obj.bucket_list()[1]
                if test_buckets:
                    self.log.info("Deleting all buckets...")
                    bkt_list = s3_temp_obj.bucket_list()[1]
                    bk_list = [
                        each_bkt for each_bkt in bkt_list if each_bkt.startswith(
                            self.bkt_name_prefix)]
                    self.log.info("bucket-list: %s", bk_list)
                    resp = s3_temp_obj.delete_multiple_buckets(bk_list)
                    assert resp[0], resp[1]
                    self.log.info("Deleted all buckets")
                self.log.info("Deleting IAM accounts...")
                resp = IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(
                    acc)
                assert resp[0], resp[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.bkt_name_prefix)]
        self.log.info("bucket-list: %s", pref_list)
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("Deleting Common dir and files...")
        if os.path.exists(self.test_folder_path):
            shutil.rmtree(self.test_folder_path)
        if os.path.exists(self.test_file_path):
            UT_OBJ.remove_file(self.test_file_path)

        user_name = self.user_name_prefix
        usr_list = IAM_OBJ.list_users()[1]
        self.log.debug("Listing users: %s", usr_list)
        all_usrs = [usr["UserName"]
                    for usr in usr_list if user_name in usr["UserName"]]
        IAM_OBJ.delete_users_with_access_key(all_usrs)
        self.log.info("ENDED: Teardown operations")

    def test_01_create_user(self):
        """Test create user."""
        resp = IAM_OBJ.create_user("ut-usr-01")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.create_user("ut-usr-01")
        except CTException as error:
            assert "already exists" not in str(error.message), error.message

    def test_02_list_users(self):
        """Test list users."""
        resp = IAM_OBJ.list_users()
        assert resp[0], resp[1]

    def test_03_create_access_key(self):
        """Test create access key."""
        resp = IAM_OBJ.create_user("ut-usr-03")
        assert resp[0], resp[1]
        resp = IAM_OBJ.create_access_key("ut-usr-03")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.create_access_key(self.d_user_name)
        except CTException:
            pass

    def test_04_update_access_key(self):
        """Test update access key."""
        resp = IAM_OBJ.create_user("ut-usr-04")
        assert resp[0], resp[1]
        resp = IAM_OBJ.create_access_key("ut-usr-04")
        accesid = resp[1]['AccessKey']['AccessKeyId']
        assert resp[0], resp[1]
        resp = IAM_OBJ.update_access_key(accesid, self.status, "ut-usr-04")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.update_access_key(accesid, self.status, self.d_user_name)
        except CTException:
            pass

    def test_05_list_access_keys(self):
        """Test list access keys."""
        resp = IAM_OBJ.create_user("ut-usr-05")
        assert resp[0], resp[1]
        resp = IAM_OBJ.list_access_keys("ut-usr-05")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.list_access_keys(self.d_user_name)
        except CTException:
            pass

    def test_06_delete_access_key(self):
        """Test delete access key."""
        resp = IAM_OBJ.create_user("ut-usr-06")
        assert resp[0], resp[1]
        resp = IAM_OBJ.create_access_key("ut-usr-06")
        accessid = resp[1]['AccessKey']['AccessKeyId']
        assert resp[0], resp[1]
        resp = IAM_OBJ.delete_access_key("ut-usr-06", accessid)
        assert resp[0], resp[1]
        try:
            IAM_OBJ.delete_access_key(self.d_user_name, accessid)
        except CTException:
            pass

    def test_07_create_modify_delete_access_key(self):
        """Test create modify delete access key."""
        resp = IAM_OBJ.create_user("ut-usr-07")
        assert resp[0], resp[1]
        resp = IAM_OBJ.create_modify_delete_access_key(
            "ut-usr-07", self.status)
        assert resp[0], resp[1]
        try:
            IAM_OBJ.create_modify_delete_access_key(
                self.d_user_name, self.status)
        except CTException:
            pass

    def test_08_update_user(self):
        """Test update user."""
        IAM_OBJ.create_user("ut-usr-08")
        resp = IAM_OBJ.update_user("ut-usr-08-new",
                                   "ut-usr-08"
                                   )
        assert resp[0], resp[1]
        try:
            IAM_OBJ.update_user(self.d_user_name, self.d_nw_user_name)
        except CTException:
            pass

    def test_09_s3_user_operation(self):
        """Test s3 user operation."""
        IAM_OBJ.create_user("ut-usr-09")
        resp = IAM_OBJ.s3_user_operation("ut-usr-09", "ut-bkt-09")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.s3_user_operation(self.d_user_name, "dummy")
        except CTException:
            pass

    def test_10_delete_user(self):
        """"Test delete user."""
        resp = IAM_OBJ.create_user("ut-usr-10")
        assert resp[0], resp[1]
        resp = IAM_OBJ.delete_user("ut-usr-10")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.delete_user(self.d_user_name)
        except CTException:
            pass

    def test_11_create_account_s3iamcli(self):
        """Test create account s3iamcli."""
        resp = IAM_OBJ.create_account_s3iamcli(
            "ut-usr-11",
            self.email.format("ut-usr-11"),
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        try:
            IAM_OBJ.create_account_s3iamcli(
                "ut-usr-11",
                self.email.format("ut-usr-11"),
                self.ldap_user,
                self.ldap_pwd)
        except CTException:
            pass

    def test_12_list_accounts_s3iamcli(self):
        """Test list accounts s3iamcli."""
        resp = IAM_OBJ.list_accounts_s3iamcli(self.ldap_user,
                                              self.ldap_pwd)
        assert resp[0], resp[1]

    def test_13_list_users_s3iamcli(self):
        """Test list users s3iamcli."""
        access_key, secret_key = S3OBJ.get_local_keys()
        resp = IAM_OBJ.list_users_s3iamcli(access_key, secret_key)
        assert resp[0], resp[1]

    def test_14_create_and_delete_account_s3iamcli(self):
        """Test create and delete account s3iamcli."""
        access_key, secret_key = S3OBJ.get_local_keys()
        resp = IAM_OBJ.create_and_delete_account_s3iamcli(
            "ut-accnt-14", self.email.format("ut-accnt-14"),
            access_key, secret_key)
        assert resp[0], resp[1]

    def test_15_create_account_login_profile_s3iamcli(self):
        """Test create account login s3iamcli."""
        acc_name = "{}{}".format("ut-accnt-15", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-15"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, "test15pwd", resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val = IAM_OBJ.delete_account_s3iamcli(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val[0], op_val[1]
        try:
            IAM_OBJ.create_account_login_profile_s3iamcli(
                acc_name, 'test_acc_login_p', resp[1]['access_key'], resp[1]['secret_key'])
        except CTException:
            pass

    def test_16_update_account_login_profile_s3iamcli(self):
        """Test update account login profile s3iamcli."""
        acc_name = "{}{}".format("ut-accnt-16", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-16"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, "test16pwd", resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.update_account_login_profile_s3iamcli(
            acc_name,
            "test16pwd",
            resp[1]['access_key'],
            resp[1]['secret_key'],
            True)
        assert op_val1[0], op_val1[1]
        op_val = IAM_OBJ.delete_account_s3iamcli(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val[0], op_val[1]
        try:
            IAM_OBJ.update_account_login_profile_s3iamcli(
                acc_name,
                "test16pwd",
                resp[1]['access_key'],
                resp[1]['secret_key'],
                True)
        except CTException:
            pass

    def test_17_get_account_login_profile_s3iamcli(self):
        """Test get account login profile s3iamcli."""
        acc_name = "{}{}".format("ut-accnt-17", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-17"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, "test17pwd", resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.get_account_login_profile_s3iamcli(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val = IAM_OBJ.delete_account_s3iamcli(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val[0], op_val[1]
        try:
            IAM_OBJ.get_account_login_profile_s3iamcli(
                acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        except CTException:
            pass

    def test_18_create_user_login_profile_s3iamcli(self):
        """"Test create user login profile s3iamcli."""
        user_name = "{}{}".format("ut-usr-18", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        op_val1 = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name, user_name, True, access_key, secret_key)
        assert op_val1[0], op_val1[1]

    def test_19_create_user_login_profile(self):
        """"Test create user login profile."""
        user_name = "{}{}".format("ut-usr-19", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        assert op_val1[0], op_val1[1]

    def test_20_update_user_login_profile(self):
        """Test update user login profile."""
        user_name = "{}{}".format("ut-usr-20", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.update_user_login_profile(
            user_name, user_name, False)
        assert op_val1[0], op_val1[1]

    def test_21_get_user_login_profile(self):
        """Test get user login profile."""
        user_name = "{}{}".format("ut-usr-21", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.get_user_login_profile(user_name)
        assert op_val1[0], op_val1[1]

    def test_22_update_user_login_profile_s3iamcli(self):
        """"Test update user login profile s3iamcli."""
        user_name = "{}{}".format("ut-usr-22", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        assert op_val1[0], op_val1[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        op_val1 = IAM_OBJ.update_user_login_profile_s3iamcli(
            user_name, user_name, False, access_key, secret_key)
        assert op_val1[0], op_val1[1]

    def test_23_get_user_login_profile_s3iamcli(self):
        """"Test get user login profile s3iamcli."""
        user_name = "{}{}".format("ut-usr-23", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        assert op_val1[0], op_val1[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        op_val1 = IAM_OBJ.get_user_login_profile_s3iamcli(user_name,
                                                          access_key,
                                                          secret_key)
        assert op_val1[0], op_val1[1]

    def test_24_create_user_login_profile_s3iamcli_with_both_options(self):
        """"Test create user login profile s3iamcli with both options."""
        user_name = "{}{}".format("ut-usr-24", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        op_val1 = IAM_OBJ.create_user_login_profile_s3iamcli_with_both_reset_options(
            user_name, "test24pwd", access_key, secret_key, True)
        assert op_val1[0], op_val1[1]
        user_name = "{}{}".format("ut-usr-24", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        op_val1 = IAM_OBJ.create_user_login_profile_s3iamcli_with_both_reset_options(
            user_name, "test24pwd", access_key, secret_key, False)
        assert op_val1[0], op_val1[1]

    def test_25_update_user_login_profile_without_password_and_reset_option(
            self):
        """Test update user login profile without password and reset option."""
        user_name = "{}{}".format("ut-usr-25", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        try:
            IAM_OBJ.update_user_login_profile_without_passowrd_and_reset_option(
                user_name, access_key, secret_key)
        except CTException:
            pass

    def test_26_reset_account_access_key_s3iamcli(self):
        """Test reset account key s3iamcli."""
        acc_name = "{}{}".format("ut-accnt-26", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-26"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val = IAM_OBJ.reset_account_access_key_s3iamcli(acc_name,
                                                           self.ldap_user,
                                                           self.ldap_pwd
                                                           )
        assert op_val[0], op_val[1]

    def test_27_reset_access_key_and_delete_account_s3iamcli(self):
        """Test reset access key and delete account s3iamcli."""
        acc_name = "{}{}".format("ut-accnt-27", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-27"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val = IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        assert op_val[0], op_val[1]

    def test_28_create_user_using_s3iamcli(self):
        """Test create user using s3iamcli."""
        acc_name = "{}{}".format("ut-accnt-28", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-28"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        user_name = "{}{}".format("ut-usr-28", str(time.time()))
        op_val1 = IAM_OBJ.create_user_using_s3iamcli(
            user_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    def test_29_get_temp_auth_credentials_account(self):
        """Test get temp auth credentials account."""
        acc_name = "{}{}".format("ut-accnt-29", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-29"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pwd = "test29pwd"
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val2 = IAM_OBJ.get_temp_auth_credentials_account(
            acc_name, acc_pwd, duration=1200)
        assert op_val2[0], op_val2[1]

    def test_30_get_temp_auth_credentials_user(self):
        """Test get temp auth credentials user."""
        acc_name = "{}{}".format("ut-accnt-30", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-30"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        user_name = "{}{}".format("ut-usr-30", str(time.time()))
        op_val1 = IAM_OBJ.create_user_using_s3iamcli(
            user_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        user_pwd = "test30pwd"
        op_val2 = IAM_OBJ.create_user_login_profile_s3iamcli(
            user_name, user_pwd, False,
            resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val2[0], op_val2[0]
        op_val3 = IAM_OBJ.get_temp_auth_credentials_user(
            acc_name, user_name, user_pwd, duration=1200)
        assert op_val3[0], op_val3[1]

    def test_31_s3_ops_using_temp_auth_creds(self):
        """"Test s3 ops using temp auth creds."""
        acc_name = "{}{}".format("ut-accnt-31", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-31"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pwd = "test31pwd"
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val2 = IAM_OBJ.get_temp_auth_credentials_account(
            acc_name, acc_pwd, duration=1200)
        assert op_val2[0], op_val2[1]
        op_val3 = IAM_OBJ.s3_ops_using_temp_auth_creds(
            op_val2[1]['access_key'],
            op_val2[1]['secret_key'],
            op_val2[1]['session_token'],
            "ut-bkt-31")
        assert op_val3[0], op_val3[1]

    def test_32_change_user_password(self):
        """Test change user password."""
        user_name = "{}{}".format("ut-usr-32", str(time.time()))
        op_val = IAM_OBJ.create_user(user_name)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_user_login_profile(user_name,
                                                   "test32pwd",
                                                   True)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_access_key(user_name)
        assert op_val[0], op_val[1]
        access_key = op_val[1]['AccessKey']['AccessKeyId']
        secret_key = op_val[1]['AccessKey']['SecretAccessKey']
        op_val = IAM_OBJ.change_user_password(
            "test32pwd", "test32nwpwd",
            access_key, secret_key)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.delete_access_key(user_name, access_key)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.delete_user(user_name)
        assert op_val[0], op_val[1]

    def test_33_update_user_login_profile_s3iamcli_with_both_reset_options(
            self):
        """Test update user login profile s3iamcli with both reset options."""
        user_name = "{}{}".format("ut-usr-33", str(time.time()))
        op_val = IAM_OBJ.create_user(user_name)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_user_login_profile(user_name,
                                                   "test33pwd",
                                                   True)
        assert op_val[0], op_val[1]
        access_key, secret_key = S3OBJ.get_local_keys()
        op_val = IAM_OBJ.update_user_login_profile_s3iamcli_with_both_reset_options(
            user_name, "test32pwd", access_key, secret_key)
        assert op_val[0], op_val[1]

    def test_34_update_user_login_profile_no_pwd_reset(self):
        """Test update user login profile no pwd reset."""
        user_name = "{}{}".format("ut-usr-34", str(time.time()))
        op_val = IAM_OBJ.create_user(user_name)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_user_login_profile(user_name,
                                                   "test34pwd",
                                                   True)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.update_user_login_profile_no_pwd_reset(user_name,
                                                                "test34pwd"
                                                                )
        assert op_val[0], op_val[1]

    def test_35_create_account_login_profile_both_reset_options(self):
        """Test 35 create account login profile both reset options."""
        acc_name = "{}{}".format("ut-accnt-35", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-35"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pwd = "test35pwd"
        op_val1 = IAM_OBJ.create_account_login_profile_both_reset_options(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    def test_36_create_account_login_profile_without_both_reset_options(self):
        """Test create account login profile without both reset options."""
        acc_name = "{}{}".format("ut-accnt-36", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-36"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pwd = "test36pwd"
        op_val1 = IAM_OBJ.create_account_login_profile_without_both_reset_options(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    def test_37_update_account_login_profile_both_reset_options(self):
        """Test update account login profile both reset options."""
        acc_name = "{}{}".format("ut-accnt-37", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format("ut-accnt-37"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pwd = "test37pwd"
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.update_account_login_profile_both_reset_options(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    def test_38_create_multiple_accounts_users(self):
        """Test create multiple accounts users."""
        access_key, secret_key = S3OBJ.get_local_keys()
        resp = IAM_OBJ.create_multiple_accounts_users(
            access_key, secret_key, 3, 3)
        assert resp[0], resp[1]

    def test_39_delete_multiple_accounts(self):
        """Test 39 delete multiple accounts."""
        ac_list = []
        for acc_cnt in range(3):
            acc_name = "{}{}{}".format(self.acc_name_prefix,
                                       str(time.time()),
                                       acc_cnt)
            email = "{}{}".format(acc_name, "@seagate.com")
            resp = IAM_OBJ.create_account_s3iamcli(
                acc_name, email,
                self.ldap_user,
                self.ldap_pwd
            )
            assert resp[0], resp[1]
            ac_list.append(acc_name)
        resp2 = IAM_OBJ.delete_multiple_accounts(ac_list)
        assert resp2[0], resp2[1]

    def test_40_create_multiple_accounts(self):
        """Test create multiple accounts."""
        resp = IAM_OBJ.create_multiple_accounts(3,
                                                self.acc_name_prefix)
        assert resp[0], resp[1]

    def test_41_create_user_access_key(self):
        """Test create user access key."""
        resp = IAM_OBJ.create_user_access_key("ut-usr-41")
        assert resp[0], resp[1]

    def test_42_delete_account_s3iamcli_using_temp_creds(self):
        """"Test delete account s3iamcli using temp creds."""
        acc_name = "{}{}".format("ut-usr-42", str(time.time()))
        resp = IAM_OBJ.create_account_s3iamcli(
            acc_name, self.email.format(),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pwd = "test42pwd"
        op_val1 = IAM_OBJ.create_account_login_profile_s3iamcli(
            acc_name, acc_pwd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val2 = IAM_OBJ.get_temp_auth_credentials_account(
            acc_name, acc_pwd, duration=1200)
        assert op_val2[0], op_val2[1]
        op_val3 = IAM_OBJ.delete_account_s3iamcli_using_temp_creds(
            acc_name,
            op_val2[1]['access_key'],
            op_val2[1]['secret_key'],
            op_val2[1]['session_token'])
        assert op_val3[0], op_val3[1]
