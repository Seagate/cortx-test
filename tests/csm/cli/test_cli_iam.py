"""CSM CLI IAM user TestSuite"""

import time
import logging
import pytest
from commons.utils import assert_utils
from commons import cortxlogging
from libs.csm.cli.cli_iam_user import CortxCliIAMLib

IAM_OBJ = CortxCliIAMLib()
LOGGER = logging.getLogger(__name__)


def setup_function():

    """
    This function will be invoked prior to each test function in the module.
    It is performing below operations as pre-requisites.
        - Login to CORTX CLI as s3account user.
    """
    LOGGER.info("STARTED : Setup operations for test function")
    LOGGER.info("Login to CORTX CLI using s3 account")
    login = IAM_OBJ.login_cortx_cli(username="cli_s3acc", password="Seagate@1")
    assert_utils.assert_equals(login[0], True, "Server authentication check failed")
    LOGGER.info("ENDED : Setup operations for test function")


def teardown_function():

    """
    This function will be invoked after each test function in the module.
    It is performing below operations.
        - Delete IAM users created in a s3account
        - Log out from CORTX CLI console.
    """
    resp = IAM_OBJ.list_iam_user(output_format="json")
    if resp[0]:
        resp = resp[1]["iam_users"]
        user_del_list = [user["user_name"]
                         for user in resp if "iam_user" in user["user_name"]]
        for each_user in user_del_list:
            LOGGER.info(
                "Deleting IAM user %s", each_user)
            resp = IAM_OBJ.delete_iam_user(each_user)
            assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
            LOGGER.info(
                "Deleted IAM user %s", each_user)
    IAM_OBJ.logout_cortx_cli()


@pytest.mark.csm
@pytest.mark.csm.iamuser
@pytest.mark.tags("TEST-10858")
def test_867():
    """
    Test that ` s3iamuser create <user_name>` with
    correct username and password should create new IAM user
    """
    test_case_name = cortxlogging.get_frame()
    LOGGER.info("##### Test started -  %s #####", test_case_name)
    user_name = "{0}{1}".format("iam_user", str(int(time.time())))
    password = "Seagate@1"
    LOGGER.info("Creating iam user with name %s", user_name)
    resp = IAM_OBJ.create_iam_user(user_name=user_name,
                                   password=password,
                                   confirm_password=password)
    assert_utils.assert_exact_string(resp[1], user_name)
    LOGGER.info("Created iam user with name %s", user_name)
    LOGGER.info("##### Test Ended -  %s #####", test_case_name)


@pytest.mark.csm
@pytest.mark.csm.iamuser
@pytest.mark.tags("TEST-10861")
def test_875():
    """
    Test that ` s3iamuser delete <iam_user_name>` must delete the given IAM user
    """
    test_case_name = cortxlogging.get_frame()
    LOGGER.info("##### Test started -  %s #####", test_case_name)
    user_name = "{0}{1}".format("iam_user", str(int(time.time())))
    LOGGER.info("Creating iam user with name %s", user_name)
    resp = IAM_OBJ.create_iam_user(user_name=user_name,
                                   password="Seagate@1",
                                   confirm_password="Seagate@1")
    assert_utils.assert_exact_string(resp[1], user_name)
    LOGGER.info("Created iam user with name %s", user_name)
    LOGGER.info("Deleting iam user with name %s", user_name)
    resp = IAM_OBJ.delete_iam_user(user_name)
    assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
    LOGGER.info("Deleted iam user with name %s", user_name)
    LOGGER.info("##### Test Ended -  %s #####", test_case_name)
