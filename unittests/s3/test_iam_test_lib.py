#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for IAM core, test library which contains admin_path operations."""

import time
import logging
import pytest

from commons.exceptions import CTException
from libs.s3 import iam_test_lib
from libs.s3 import S3H_OBJ, LDAP_PASSWD, LDAP_USERNAME

IAM_OBJ = iam_test_lib.IamTestLib()


class TestIamLib:
    """S3 Iam test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup class operations.")
        cls.user_name_prefix = "ut-usr"
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.d_user_name = "dummy_user"
        cls.status = "Inactive"
        cls.d_status = "dummy_Inactive"
        cls.d_nw_user_name = "dummy_user"
        cls.email = "{}@seagate.com"
        cls.log.info("Ldap user: %s", cls.ldap_user)
        cls.log.info("ENDED: Setup operations completed.")

    @classmethod
    def teardown_class(cls):
        """Test teardown class."""
        cls.log.info("STARTED: teardown class operations.")
        cls.log.info("teardown class completed.")
        cls.log.info("STARTED: teardown class operations completed.")

    def setup_method(self):
        """
        Function will be invoked before test execution.

        It will perform prerequisite test steps if any
        Defined var for log, onfig, creating common dir
        """
        self.log.info("STARTED: Setup operations")
        # Delete created user with prefix.
        self.log.info(
            "Delete created user with prefix: %s",
            self.user_name_prefix)
        usr_list = IAM_OBJ.list_users()[1]
        self.log.debug("Listing users: %s", usr_list)
        all_usrs = [usr["UserName"]
                    for usr in usr_list if self.user_name_prefix in usr["UserName"]]
        if all_usrs:
            IAM_OBJ.delete_users_with_access_key(all_usrs)
        # Delete account created with prefix.
        self.log.info(
            "Delete created account with prefix: %s",
            self.acc_name_prefix)
        acc_list = IAM_OBJ.list_accounts(
            self.ldap_user,
            self.ldap_pwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.acc_name_prefix in acc["AccountName"]]
        if all_acc:
            IAM_OBJ.delete_multiple_accounts(all_acc)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after test case.

        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        self.log.info("STARTED: Teardown operations")
        # Delete created user with prefix.
        self.log.info(
            "Delete created user with prefix: %s",
            self.user_name_prefix)
        usr_list = IAM_OBJ.list_users()[1]
        self.log.debug("Listing users: %s", usr_list)
        all_usrs = [usr["UserName"]
                    for usr in usr_list if self.user_name_prefix in usr["UserName"]]
        if all_usrs:
            IAM_OBJ.delete_users_with_access_key(all_usrs)
        # Delete account created with prefix.
        self.log.info(
            "Delete created account with prefix: %s",
            self.acc_name_prefix)
        acc_list = IAM_OBJ.list_accounts(
            self.ldap_user,
            self.ldap_pwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.acc_name_prefix in acc["AccountName"]]
        if all_acc:
            IAM_OBJ.delete_multiple_accounts(all_acc)
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.s3unittest
    def test_01_create_user(self):
        """Test create user."""
        resp = IAM_OBJ.create_user("ut-usr-01")
        self.log.info(resp)
        assert resp[0], resp[1]
        try:
            IAM_OBJ.create_user("ut-usr-01")
        except CTException as error:
            assert "already exists" in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_02_list_users(self):
        """Test list users."""
        resp = IAM_OBJ.list_users()
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
    def test_09_s3_user_operation(self):
        """Test s3 user operation."""
        IAM_OBJ.create_user("ut-usr-09")
        resp = IAM_OBJ.s3_user_operation("ut-usr-09", "ut-bkt-09")
        assert resp[0], resp[1]
        try:
            IAM_OBJ.s3_user_operation(self.d_user_name, "dummy")
        except CTException:
            pass

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
    def test_11_create_account(self):
        """Test create account."""
        resp = IAM_OBJ.create_account(
            "ut-accnt-11",
            self.email.format("ut-accnt-11"),
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        try:
            IAM_OBJ.create_account(
                "ut-accnt-11",
                self.email.format("ut-accnt-11"),
                self.ldap_user,
                self.ldap_pwd)
        except CTException:
            pass

    @pytest.mark.s3unittest
    def test_12_list_accounts(self):
        """Test list accounts."""
        resp = IAM_OBJ.list_accounts(self.ldap_user,
                                              self.ldap_pwd)
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_14_create_and_delete_account(self):
        """Test create and delete account."""
        resp = IAM_OBJ.create_and_delete_account(
            "ut-accnt-14", self.email.format("ut-accnt-14"))
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_15_create_account_login_profile(self):
        """Test create account login."""
        acc_name = "{}{}".format("ut-accnt-15", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-15"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name, "test15pd", access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val = IAM_OBJ.delete_account(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val[0], op_val[1]
        try:
            IAM_OBJ.create_account_login_profile(
                acc_name, 'test_acc_login_p', access_key=resp[1]['access_key'],
                secret_key=resp[1]['secret_key'])
        except CTException:
            pass

    @pytest.mark.s3unittest
    def test_16_update_account_login_profile(self):
        """Test update account login profile."""
        acc_name = "{}{}".format("ut-accnt-16", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-16"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name, "test16pd", access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.update_account_login_profile(
            acc_name,
            "test16pd",
            access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'],
            password_reset=True)
        assert op_val1[0], op_val1[1]
        op_val = IAM_OBJ.delete_account(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val[0], op_val[1]
        try:
            IAM_OBJ.update_account_login_profile(
                acc_name,
                "test16pd",
                access_key=resp[1]['access_key'],
                secret_key=resp[1]['secret_key'],
                password_reset=True)
        except CTException:
            pass

    @pytest.mark.s3unittest
    def test_17_get_account_login_profile(self):
        """Test get account login profile."""
        acc_name = "{}{}".format("ut-accnt-17", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-17"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name, "test17pd", access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.get_account_login_profile(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val = IAM_OBJ.delete_account(
            acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val[0], op_val[1]
        try:
            IAM_OBJ.get_account_login_profile(
                acc_name, resp[1]['access_key'], resp[1]['secret_key'])
        except CTException:
            pass

    @pytest.mark.s3unittest
    def test_18_create_user_login_profile(self):
        """"Test create user login profile."""
        user_name = "{}{}".format("ut-usr-18", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        op_val1 = IAM_OBJ.create_user_login_profile(
            user_name, user_name, True, access_key=access_key, secret_key=secret_key)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_19_create_user_login_profile(self):
        """"Test create user login profile."""
        user_name = "{}{}".format("ut-usr-19", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_20_update_user_login_profile(self):
        """Test update user login profile."""
        user_name = "{}{}".format("ut-usr-20", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.update_user_login_profile(
            user_name, user_name, False)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_21_get_user_login_profile(self):
        """Test get user login profile."""
        user_name = "{}{}".format("ut-usr-21", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.get_user_login_profile(user_name)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_22_update_user_login_profile(self):
        """"Test update user login profile."""
        user_name = "{}{}".format("ut-usr-22", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        op_val1 = IAM_OBJ.update_user_login_profile(
            user_name, user_name, False, access_key=access_key, secret_key=secret_key)
        self.log.info(op_val1)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_23_get_user_login_profile(self):
        """"Test get user login profile."""
        user_name = "{}{}".format("ut-usr-23", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        op_val1 = IAM_OBJ.create_user_login_profile(user_name, user_name)
        assert op_val1[0], op_val1[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        op_val1 = IAM_OBJ.get_user_login_profile(user_name,
                                                          access_key,
                                                          secret_key)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_24_create_user_login_profile_with_both_options(self):
        """"Test create user login profile with both options."""
        user_name = "{}{}".format("ut-usr-24", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        op_val1 = IAM_OBJ.create_user_login_profile_with_both_reset_options(
            user_name,
            "test24pd",
            access_key=access_key,
            secret_key=secret_key,
            both_reset_options=True)
        assert op_val1[0], op_val1[1]
        user_name = "{}{}".format("ut-usr-24", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        op_val1 = IAM_OBJ.create_user_login_profile_with_both_reset_options(
            user_name,
            "test24pd",
            access_key=access_key,
            secret_key=secret_key,
            both_reset_options=False)
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_25_update_user_login_profile_without_password_and_reset_option(
            self):
        """Test update user login profile without password and reset option."""
        user_name = "{}{}".format("ut-usr-25", str(time.time()))
        op_val0 = IAM_OBJ.create_user(user_name)
        self.log.info(op_val0)
        assert op_val0[0], op_val0[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        try:
            IAM_OBJ.update_user_login_profile_without_passowrd_and_reset_option(
                user_name, access_key, secret_key)
        except CTException:
            pass

    @pytest.mark.s3unittest
    def test_26_reset_account_access_key(self):
        """Test reset account key."""
        acc_name = "{}{}".format("ut-accnt-26", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-26"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        op_val = IAM_OBJ.reset_account_access_key(acc_name,
                                                           self.ldap_user,
                                                           self.ldap_pwd
                                                           )
        assert op_val[0], op_val[1]

    @pytest.mark.s3unittest
    def test_27_reset_access_key_and_delete_account(self):
        """Test reset access key and delete account."""
        acc_name = "{}{}".format("ut-accnt-27", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-27"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        op_val = IAM_OBJ.reset_access_key_and_delete_account(acc_name)
        assert op_val[0], op_val[1]

    @pytest.mark.s3unittest
    def test_28_create_user(self):
        """Test create user using."""
        acc_name = "{}{}".format("ut-accnt-28", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-28"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        user_name = "{}{}".format("ut-usr-28", str(time.time()))
        op_val1 = IAM_OBJ.create_user(
            user_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_29_get_temp_auth_credentials_account(self):
        """Test get temp auth credentials account."""
        acc_name = "{}{}".format("ut-accnt-29", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-29"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        acc_pd = "test29pd"
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name,
            acc_pd,
            access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val2 = IAM_OBJ.get_temp_auth_credentials_account(
            acc_name, acc_pd, duration=1200)
        assert op_val2[0], op_val2[1]

    @pytest.mark.s3unittest
    def test_30_get_temp_auth_credentials_user(self):
        """Test get temp auth credentials user."""
        acc_name = "{}{}".format("ut-accnt-30", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-30"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        user_name = "{}{}".format("ut-usr-30", str(time.time()))
        op_val1 = IAM_OBJ.create_user(
            user_name, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        user_pd = "test30pd"
        op_val2 = IAM_OBJ.create_user_login_profile(
            user_name, user_pd, False,
            access_key=resp[1]['access_key'], secret_key=resp[1]['secret_key'])
        assert op_val2[0], op_val2[0]
        op_val3 = IAM_OBJ.get_temp_auth_credentials_user(
            acc_name, user_name, user_pd, duration=1200)
        assert op_val3[0], op_val3[1]

    @pytest.mark.s3unittest
    def test_31_s3_ops_using_temp_auth_creds(self):
        """"Test s3 ops using temp auth creds."""
        acc_name = "{}{}".format("ut-accnt-31", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-31"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        acc_pd = "test31pd"
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name,
            acc_pd,
            access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val2 = IAM_OBJ.get_temp_auth_credentials_account(
            acc_name, acc_pd, duration=1200)
        assert op_val2[0], op_val2[1]
        op_val3 = IAM_OBJ.s3_ops_using_temp_auth_creds(
            op_val2[1]['access_key'],
            op_val2[1]['secret_key'],
            op_val2[1]['session_token'],
            "ut-bkt-31")
        assert op_val3[0], op_val3[1]

    @pytest.mark.s3unittest
    def test_32_change_user_password(self):
        """Test change user password."""
        user_name = "{}{}".format("ut-usr-32", str(time.time()))
        op_val = IAM_OBJ.create_user(user_name)
        self.log.info(op_val)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_user_login_profile(user_name,
                                                   "test32pd",
                                                   True)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_access_key(user_name)
        assert op_val[0], op_val[1]
        access_key = op_val[1]['AccessKey']['AccessKeyId']
        secret_key = op_val[1]['AccessKey']['SecretAccessKey']
        op_val = IAM_OBJ.change_user_password(
            "test32pd", "test32nwpd",
            access_key, secret_key)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.delete_access_key(user_name, access_key)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.delete_user(user_name)
        assert op_val[0], op_val[1]

    @pytest.mark.s3unittest
    def test_33_update_user_login_profile_with_both_reset_options(
            self):
        """Test update user login profile with both reset options."""
        user_name = "{}{}".format("ut-usr-33", str(time.time()))
        op_val = IAM_OBJ.create_user(user_name)
        self.log.info(op_val)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_user_login_profile(user_name,
                                                   "test33pd",
                                                   True)
        assert op_val[0], op_val[1]
        access_key, secret_key = S3H_OBJ.get_local_keys()
        op_val = IAM_OBJ.update_user_login_profile_with_both_reset_options(
            user_name, "test32pd", access_key, secret_key)
        assert op_val[0], op_val[1]

    @pytest.mark.s3unittest
    def test_34_update_user_login_profile_no_pwd_reset(self):
        """Test update user login profile no pwd reset."""
        user_name = "{}{}".format("ut-usr-34", str(time.time()))
        op_val = IAM_OBJ.create_user(user_name)
        self.log.info(op_val)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_user_login_profile(user_name,
                                                   "test34pd",
                                                   True)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.update_user_login_profile_no_pwd_reset(user_name,
                                                                "test34pd"
                                                                )
        assert op_val[0], op_val[1]

    @pytest.mark.s3unittest
    def test_35_create_account_login_profile_both_reset_options(self):
        """Test 35 create account login profile both reset options."""
        acc_name = "{}{}".format("ut-accnt-35", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-35"),
            self.ldap_user,
            self.ldap_pwd
        )
        assert resp[0], resp[1]
        acc_pd = "test35pd"
        op_val1 = IAM_OBJ.create_account_login_profile_both_reset_options(
            acc_name, acc_pd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_36_create_account_login_profile_without_both_reset_options(self):
        """Test create account login profile without both reset options."""
        acc_name = "{}{}".format("ut-accnt-36", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-36"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        acc_pd = "test36pd"
        op_val1 = IAM_OBJ.create_account_login_profile_without_both_reset_options(
            acc_name, acc_pd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_37_update_account_login_profile_both_reset_options(self):
        """Test update account login profile both reset options."""
        acc_name = "{}{}".format("ut-accnt-37", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-accnt-37"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        acc_pd = "test37pd"
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name,
            acc_pd,
            access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val1 = IAM_OBJ.update_account_login_profile_both_reset_options(
            acc_name, acc_pd, resp[1]['access_key'], resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]

    @pytest.mark.s3unittest
    def test_38_create_multiple_accounts_users(self):
        """Test create multiple accounts users."""
        access_key, secret_key = S3H_OBJ.get_local_keys()
        resp = IAM_OBJ.create_multiple_accounts_users(
            access_key, secret_key, 3, 3)
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_39_delete_multiple_accounts(self):
        """Test 39 delete multiple accounts."""
        ac_list = []
        for acc_cnt in range(3):
            acc_name = "{}{}{}".format(self.acc_name_prefix,
                                       str(time.time()),
                                       acc_cnt)
            email = "{}{}".format(acc_name, "@seagate.com")
            resp = IAM_OBJ.create_account(
                acc_name, email,
                self.ldap_user,
                self.ldap_pwd
            )
            self.log.info(resp)
            assert resp[0], resp[1]
            ac_list.append(acc_name)
        resp2 = IAM_OBJ.delete_multiple_accounts(ac_list)
        assert resp2[0], resp2[1]

    @pytest.mark.s3unittest
    def test_40_create_multiple_accounts(self):
        """Test create multiple accounts."""
        resp = IAM_OBJ.create_multiple_accounts(3,
                                                self.acc_name_prefix)
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_41_create_user_access_key(self):
        """Test create user access key."""
        resp = IAM_OBJ.create_user_access_key("ut-usr-41")
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_42_delete_account_using_temp_creds(self):
        """"Test delete account using temp creds."""
        acc_name = "{}{}".format("ut-usr-42", str(time.time()))
        resp = IAM_OBJ.create_account(
            acc_name, self.email.format("ut-usr-42"),
            self.ldap_user,
            self.ldap_pwd
        )
        self.log.info(resp)
        assert resp[0], resp[1]
        acc_pd = "test42pd"
        op_val1 = IAM_OBJ.create_account_login_profile(
            acc_name,
            acc_pd,
            access_key=resp[1]['access_key'],
            secret_key=resp[1]['secret_key'])
        assert op_val1[0], op_val1[1]
        op_val2 = IAM_OBJ.get_temp_auth_credentials_account(
            acc_name, acc_pd, duration=1200)
        assert op_val2[0], op_val2[1]
        op_val3 = IAM_OBJ.delete_account_using_temp_creds(
            acc_name,
            op_val2[1]['access_key'],
            op_val2[1]['secret_key'],
            session_token=op_val2[1]['session_token'])
        assert op_val3[0], op_val3[1]
