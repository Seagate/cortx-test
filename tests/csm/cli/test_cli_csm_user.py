"""CSM CLI csm user TestSuite"""

import logging
import time
import pytest
from commons.utils import assert_utils
from libs.csm.cli.cli_csm_user import CortxCliCsmLib
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts
from commons import cortxlogging

CSM_USER = CortxCliCsmLib()
CSM_ALERT = CortxCliAlerts()
LOGGER = logging.getLogger(__name__)


def setup_function():
    """
    This function will be invoked prior to each test function in the module.
    It is performing below operations as pre-requisites.
        - Login to CORTX CLI as admin user.
    """
    LOGGER.info("STARTED : Setup operations for test function")
    LOGGER.info("Login to CORTX CLI using s3 account")
    login = CSM_USER.login_cortx_cli()
    assert_utils.assert_equals(
        login[0], True, "Server authentication check failed")
    LOGGER.info("ENDED : Setup operations for test function")


def teardown_function():
    """
    This function will be invoked after each test function in the module.
    It is performing below operations.
        - Delete CSM users
        - Log out from CORTX CLI console.
    """
    LOGGER.info("STARTED : Teardown operations for test function")
    resp = CSM_USER.list_csm_users(sort_dir="desc")
    assert_utils.assert_equals(
        resp[0], True, "Server authentication check failed")
    all_users = CSM_USER.split_table_response(resp[1])
    my_users = [
        myuser for user in all_users for myuser in user if "auto_csm_user" in myuser]
    if my_users:
        for user in my_users:
            LOGGER.info("Deleting CSM users %s", user)
            CSM_USER.delete_csm_user(user_name=user)
            LOGGER.info("Deleted CSM users %s", user)
    CSM_USER.logout_cortx_cli()
    LOGGER.info("Ended : Teardown operations for test function")


@pytest.mark.csm
@pytest.mark.csm.csmuser
@pytest.mark.tags("TEST-11229")
def test_1143():
    """
    Test that CSM user/admin is able to login to csmcli passing username as parameter
    """
    test_case_name = cortxlogging.get_frame()
    LOGGER.info("##### Test started -  %s #####", test_case_name)
    user_name = "{0}{1}".format("auto_csm_user", str(int(time.time())))
    email_id = "{0}{1}".format(user_name, "@seagate.com")
    LOGGER.info("Creating csm user with name %s", user_name)
    resp = CSM_USER.create_csm_user_cli(
        csm_user_name=user_name,
        email_id=email_id,
        role="manage",
        password="Seagate@1",
        confirm_password="Seagate@1")
    assert_utils.assert_equals(
        resp[0], True, "Server authentication check failed")
    assert_utils.assert_exact_string(resp[1], "User created")
    LOGGER.info("Created csm user with name %s", user_name)
    LOGGER.info(
        "Verifying CSM user is able to login cortxcli by passing username as parameter")
    CSM_USER.logout_cortx_cli()
    resp = CSM_USER.login_with_username_param(
        username=user_name, password="Seagate@1")
    assert_utils.assert_equals(
        resp[0], True, "Server authentication check failed")
    CSM_USER.logout_cortx_cli()
    CSM_USER.login_cortx_cli()
    LOGGER.info(
        "Verified CSM user is able to login cortxcli by passing username as paramter")
    LOGGER.info("##### Test Ended -  %s #####", test_case_name)


@pytest.mark.csm
@pytest.mark.csm.csmuser
@pytest.mark.tags("TEST-13138")
def test_1849():
    """
    Test that csm user with monitor role can list alert using CLI
    """
    test_case_name = cortxlogging.get_frame()
    LOGGER.info("##### Test started -  %s #####", test_case_name)
    user_name = "{0}{1}".format("auto_csm_user", str(int(time.time())))
    email_id = "{0}{1}".format(user_name, "@seagate.com")
    LOGGER.info("Creating csm user with name %s", user_name)
    resp = CSM_USER.create_csm_user_cli(
        csm_user_name=user_name,
        email_id=email_id,
        role="monitor",
        password="Seagate@1",
        confirm_password="Seagate@1")
    assert_utils.assert_equals(
        resp[0], True, "Server authentication check failed")
    assert_utils.assert_exact_string(resp[1], "User created")
    LOGGER.info("Created csm user with name %s", user_name)
    LOGGER.info("Logging using csm monitor role")
    CSM_USER.logout_cortx_cli()
    resp = CSM_ALERT.login_cortx_cli(username=user_name, password="Seagate@1")
    assert_utils.assert_equals(
        resp[0], True, "Server authentication check failed")
    LOGGER.info("Logged in using csm monitor role")
    LOGGER.info("Listing alerts using csm monitor role")
    resp = CSM_ALERT.show_alerts_cli(duration="1d")
    assert_utils.assert_equals(
        resp[0], True, "Server authentication check failed")
    LOGGER.info("Listed alerts using csm monitor role")
    CSM_ALERT.logout_cortx_cli()
    CSM_USER.login_cortx_cli()
    LOGGER.info("##### Test Ended -  %s #####", test_case_name)
