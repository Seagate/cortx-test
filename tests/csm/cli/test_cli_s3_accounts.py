"""Test suite for S3 bucket operations"""

import logging
import time
import pytest
from commons.utils import assert_utils
from config import CSM_CFG
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations

S3ACC_OBJ = CortxCliS3AccountOperations()
LOGGER = logging.getLogger(__name__)


class TestCliS3ACC:
    """CORTX CLI Test suite for S3 bucket operations"""

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        LOGGER.info("STARTED : Setup operations at test function level")
        self.s3acc_name = "cli_s3acc_{}".format(int(time.time()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.s3acc_password = CSM_CFG["CliConfig"]["acc_password"]
        login = S3ACC_OBJ.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        LOGGER.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        It is performing below operations as pre-requisites
            - Initializes common variables
            - Login to CORTX CLI as admin user
        """
        LOGGER.info("STARTED : Teardown operations at test function level")
        S3ACC_OBJ.logout_cortx_cli()

    @pytest.mark.csm
    @pytest.mark.s3account
    @pytest.mark.tags("TEST-10872")
    def test_1008(self):
        """
        Verify that S3 account should be deleted successfully on executing delete command
        """
        resp = S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Created s3 account %s", self.s3acc_name)
        logout = S3ACC_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = S3ACC_OBJ.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = S3ACC_OBJ.delete_s3account_cortx_cli(
            account_name=self.s3acc_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Deleted s3 account %s", self.s3acc_name)

    @pytest.mark.csm
    @pytest.mark.s3account
    @pytest.mark.tags("TEST-10877")
    def test_1012(self):
        """
        Verify that appropriate error msg should be returned when s3 account tries to
        delete different s3 account
        """
        resp = S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Created s3 account %s", self.s3acc_name)
        s3acc_name2 = "cli_s3acc_{}".format(int(time.time()))
        s3acc_email2 = "{}@seagate.com".format(s3acc_name2)
        resp = S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=s3acc_name2,
            account_email=s3acc_email2,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Created another s3 account %s", s3acc_name2)
        logout = S3ACC_OBJ.logout_cortx_cli()
        assert_utils.assert_equals(True, logout[0], logout[1])
        login = S3ACC_OBJ.login_cortx_cli(
            username=self.s3acc_name,
            password=self.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        resp = S3ACC_OBJ.delete_s3account_cortx_cli(account_name=s3acc_name2)
        assert_utils.assert_equals(False, resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "Access denied")
        LOGGER.info(
            "Deleting different account failed with error %s", resp[1])
