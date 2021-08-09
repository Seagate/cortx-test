#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for s3 rest cli api test library which contains s3 CRUD operations."""

import time
import logging

from config import CSM_CFG
from commons.utils import assert_utils
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


class TestS3RestCliAPI:
    """Class to test the s3 rest cli api lib."""

    def setup_method(self):
        """Method is for test set-up."""
        self.log = logging.getLogger(__name__)
        self.username = "csm_user_manage{}".format(time.perf_counter_ns())
        self.email = "{}@seagate.com".format(self.username)
        self.password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        self.new_password = CSM_CFG["CliConfig"]["csm_user"]["password"]
        self.s3_obj = S3AccountOperations()

    def teardown_method(self):
        """Method is for cleanup tests."""
        s3_list = self.s3_obj.list_s3_accounts()[1]
        if self.username in s3_list:
            resp = self.s3_obj.delete_s3_account(self.username)
            assert_utils.assert_true(resp[0], resp[1])

    def test_create_s3_account(self):
        """Test create s3 account."""
        resp = self.s3_obj.create_s3_account(
            self.username, self.email, self.password)
        assert_utils.assert_true(resp[0], resp)
        resp = self.s3_obj.create_s3_account(
            self.username, self.email, self.password)
        assert_utils.assert_false(resp[0], resp)

    def test_list_s3_accounts(self):
        """Test list s3 accounts."""
        resp = self.s3_obj.list_s3_accounts()
        assert_utils.assert_true(resp[0], resp[1])

    def test_delete_s3_account(self):
        """Test delete s3 account."""
        resp = self.s3_obj.create_s3_account(
            self.username, self.email, self.password)
        assert_utils.assert_true(resp[0], resp)
        resp = self.s3_obj.delete_s3_account(self.username)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.delete_s3_account(self.username)
        assert_utils.assert_false(resp[0], resp[1])

    def test_reset_s3account_password(self):
        """Test reset s3 account password."""
        resp = self.s3_obj.create_s3_account(
            self.username, self.email, self.password)
        assert_utils.assert_true(resp[0], resp)
        resp = self.s3_obj. update_s3_account(
            self.username, self.new_password)
        assert_utils.assert_true(resp[0], resp[1])

    def test_create_s3account_access_key(self):
        """Test create s3 account access key."""
        resp = self.s3_obj.create_s3_account(
            self.username, self.email, self.password)
        assert_utils.assert_true(resp[0], resp)
        resp = self.s3_obj.generate_s3_access_key(
            self.username, self.password)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.generate_s3_access_key(
            self.username, self.password)
        assert_utils.assert_true(resp[0], resp[1])
