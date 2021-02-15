"""Test suite for S3 bucket operations"""

import logging
import time
import pytest
from commons.utils import assert_utils
from config import CSM_CFG
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations

S3BKT_OBJ = CortxCliS3BucketOperations()
S3ACC_OBJ = CortxCliS3AccountOperations()
LOGGER = logging.getLogger(__name__)
BKT_PREFIX = "clis3bkt"


class TestCliS3BKT:
    """CORTX CLI Test suite for S3 bucket operations"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        LOGGER.info("STARTED : Setup operations at test suit level")
        cls.s3acc_name = "clis3bkt_acc_{}".format(int(time.time()))
        cls.s3acc_email = "{}@seagate.com".format(cls.s3acc_name)
        cls.s3acc_password = CSM_CFG["CliConfig"]["acc_password"]
        response = S3ACC_OBJ.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, response[0], response[1])
        login = S3BKT_OBJ.login_cortx_cli(
            username=cls.s3acc_name,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        LOGGER.info("ENDED : Setup operations at test suit level")

    @classmethod
    def teardown_class(cls):
        """
        Teardown any state that was previously setup with a setup_class
        """
        LOGGER.info("STARTED : Teardown operations at test suit level")
        S3BKT_OBJ.logout_cortx_cli()
        login = S3ACC_OBJ.login_cortx_cli(
            username=cls.s3acc_name,
            password=cls.s3acc_password)
        assert_utils.assert_equals(True, login[0], login[1])
        response = S3ACC_OBJ.delete_s3account_cortx_cli(
            account_name=cls.s3acc_name)
        assert_utils.assert_equals(True, response[0], response[1])
        LOGGER.info("ENDED : Setup operations at test suit level")

    @pytest.mark.csm
    @pytest.mark.s3bucket
    @pytest.mark.tags("TEST-10805")
    def test_971_verify_delete_bucket(self):
        """
        Test that S3 account user able to delete the bucket using CORTX CLI
        """
        bucket_name = "{0}{1}".format(BKT_PREFIX, int(time.time()))
        resp = S3BKT_OBJ.create_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Created bucket %s", bucket_name)
        resp = S3BKT_OBJ.delete_bucket_cortx_cli(bucket_name)
        assert_utils.assert_equals(True, resp[0], resp[1])
        LOGGER.info("Deleted bucket %s", bucket_name)
