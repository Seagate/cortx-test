import pytest
import time
import logging
from commons.utils import assert_utils
from libs.csm.cli.cortxcli_s3_bucket_test_lib import CortxCliS3BucketOperations

s3bkt_obj = CortxCliS3BucketOperations()
logger = logging.getLogger(__name__)
bkt_name_prefix = "clis3bkt"


def setup_module(module):
    s3account_name = "clis3bkt_acc_{}".format(int(time.time()))
    s3account_password = "Seagate55%"
    login = s3bkt_obj.login_cortx_cli(username=s3account_name, password=s3account_password)
    assert_utils.assert_equals(True, login[0])


def teardown_module(module):
    s3bkt_obj.logout_cortx_cli()


def setup_function(function):
    """ setup any state tied to the execution of the given function.
    Invoked for every test function in the module.
    """
    pass


def teardown_function(function):
    """ teardown any state that was previously setup with a setup_function
    call.
    """
    pass


@pytest.mark.tags("TEST-971")
def test_verify_delete_bucket():
    bucket_name = "{0}{1}".format(bkt_name_prefix, int(time.time()))
    resp = s3bkt_obj.create_bucket_cortx_cli(bucket_name)
    assert_utils.assert_equals(True, resp[0])
    logger.info("Created bucket {}".format(bucket_name))
    resp = s3bkt_obj.delete_bucket_cortx_cli(bucket_name)
    assert_utils.assert_equals(True, resp[0])
    logger.info("Deleted bucket {}".format(bucket_name))
