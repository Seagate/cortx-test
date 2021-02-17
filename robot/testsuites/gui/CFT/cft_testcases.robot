*** Settings ***
Documentation    This suite verifies the testcases for csm login
Library     SeleniumLibrary
Resource    ../../../resources/page_objects/loginPage.robot
Resource    ../../../resources/page_objects/dashboard.robot
Resource    ../../../resources/page_objects/alertPage.robot
Resource    ../../../resources/page_objects/s3accountPage.robot
Resource   ../../../resources/common/common.robot
Resource    ../../../resources/page_objects/userSettingsLocalPage.robot
Variables  ../../../resources/common/common_variables.py


Test Setup  CSM GUI Login  ${url}  ${browser}  ${headless}  ${username}  ${password}
Test Teardown  Close Browser
Suite Teardown  Close All Browsers

Force Tags  CSM_GUI  CFT_Test

*** Variables ***
${url}
${browser}  chrome
${headless}  True
${navigate_to_subpage}  False
${Sub_tab}  None
${username}
${password}

*** Test Cases ***

TEST-1226
    [Documentation]  Test that CSM user with role manager cannot update or delete s3 accounts
    ...  Reference : https://jts.seagate.com/browse/TEST-1226
    [Tags]  Priority_High  CFT_test
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  manage1226  ${new_password}  manage
    Click On Confirm Button
    Verify New User  manage1226
    Re-login  manage1226  ${new_password}  MANAGE_MENU_ID
    Validate CSM Login Success  manage1226
    Verify Absence of Edit And Delete Button on S3account
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  manage1226

TEST-1213
    [Documentation]  Test that CSM user with role manager has access to dashboard and perform actions on alerts
    ...  Reference : https://jts.seagate.com/browse/TEST-1213
    [Tags]  Priority_High  CFT_test
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  manage1213  ${new_password}  manage
    Click On Confirm Button
    Verify New User  manage1213
    Re-login  manage1213  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  manage1213
    sleep  2s  # Took time to load full dashboard
    Verify Presence of Stats And Alerts
    Click AlertPage Image
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments Acknowledge
    Click Details Button
    sleep  2s  # Took time to load alert details
    Go Back
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments Acknowledge
    Click Comments Button
    sleep  1s  # Took time to load comments
    Add CommentInCommentBox Text
    sleep  1s  # Took time to save comments
    Click CommentsClose Button
    Click Comments Button
    sleep  1s  # Took time to load comments
    Click CommentsClose Image
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  manage1213

TEST-1219
    [Documentation]  Test that monitor user can view alerts and stats.
    ...  Reference : https://jts.seagate.com/browse/TEST-1219
    [Tags]  Priority_High  CFT_test
    ${new_password}=  Generate New Password
    Navigate To Page  MANAGE_MENU_ID
    Create New CSM User  monitor1219  ${new_password}  monitor
    Click On Confirm Button
    Verify New User  monitor1219
    Re-login  monitor1219  ${new_password}  DASHBOARD_MENU_ID
    Validate CSM Login Success  monitor1219
    sleep  2s  # Took time to load full dashboard
    Verify Presence of Stats And Alerts
    Click AlertPageDashboard Image
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Click Details Button
    sleep  2s  # Took time to load alert details
    Go Back
    sleep  3s  # Took time to load all alerts
    Verify Presence of Details Comments
    Verify Absence of Acknowledge
    Click Comments Button
    sleep  1s  # Took time to save comments
    Click CommentsClose Image
    Re-login  ${username}  ${password}  MANAGE_MENU_ID
    Delete CSM User  monitor1219

TEST-1037
    [Documentation]  Test that S3 account user must not have access to create CSM user
    ...  Reference : https://jts.seagate.com/browse/TEST-1037
    [Tags]  Priority_High  CFT_Test
    Navigate To Page    MANAGE_MENU_ID  S3_ACCOUNTS_TAB_ID
    sleep  2s
    ${S3_account_name}  ${email}  ${password} =  Create S3 account
    sleep  3s
    Re-login  ${S3_account_name}  ${password}  MANAGE_MENU_ID
    sleep  3s  # Took time to load s3 account
    Verify Absence of Admin User Section
    Verify Presence of Edit And Delete
    sleep  2s
    Delete S3 Account  ${S3_account_name}  ${password}  True
